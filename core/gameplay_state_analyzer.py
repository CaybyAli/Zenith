from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from core.gameplay_vision_analyzer import GameplayVisionAnalyzer
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow


ENGINE = "gameplay-state-analyzer-v1"
DEFAULT_SAMPLE_SECONDS = 0.5
LOW_MOTION_THRESHOLD = 0.06
ACTION_THRESHOLD = 0.16
STRONG_SCENE_THRESHOLD = 0.18

_ACTIVE_PHASES = {"active_round", "countdown_kickoff"}
_MENU_PHASES = {"menu_wait", "queue_wait"}
_ROUND_END_PHASES = {"round_end"}
_REPLAY_PHASES = {"goal_replay"}
_ACTION_EVENTS = {"high_action_burst", "sustained_action", "kickoff_like"}
_FLASH_EVENTS = {"goal_or_save_like_flash"}
_ROUND_END_EVENTS = {"round_end_dead_time"}
_REPLAY_EVENTS = {"replay_like_moment", "scene_change_moment"}
_WAIT_EVENTS = {"menu_or_idle", "low_gameplay_value"}


class GameplayStateAnalyzer:
    engine = ENGINE

    def analyze(
        self,
        *,
        video_path: str | Path | None = None,
        gameplay_vision_result: object = None,
        gameplay_event_result: object = None,
        round_phase_result: object = None,
        sample_seconds: float = DEFAULT_SAMPLE_SECONDS,
    ) -> GameplayStateResult:
        sample_seconds = max(0.1, self._safe_float(sample_seconds, DEFAULT_SAMPLE_SECONDS))
        vision_result = gameplay_vision_result
        vision_windows = self._vision_windows(vision_result)

        sampled_from_video = False
        if not vision_windows and video_path:
            vision_result = GameplayVisionAnalyzer(sample_every_seconds=sample_seconds).analyze_video(
                video_path=video_path,
                sample_every_seconds=sample_seconds,
                max_frames=240,
            )
            vision_windows = self._vision_windows(vision_result)
            sampled_from_video = bool(vision_windows)

        event_windows = self._event_windows(gameplay_event_result)
        phase_windows = self._phase_windows(round_phase_result)
        states: list[GameplayStateWindow] = []

        for vision in vision_windows:
            self._add_vision_states(states, vision, phase_windows, event_windows)

        for event in event_windows:
            self._add_event_states(states, event, vision_windows, phase_windows)

        for phase in phase_windows:
            self._add_phase_states(states, phase, vision_windows, event_windows)

        self._add_pre_action_context(states)
        self._add_dead_time_after_goal(states, vision_windows, phase_windows)
        self._add_scoreboard_like(states, vision_windows, phase_windows, event_windows)

        states.sort(key=lambda item: (item.start_seconds, item.end_seconds, item.state_type, item.window_id))
        skipped_reason = None if states else self._skipped_reason(vision_result, gameplay_event_result, round_phase_result)
        return GameplayStateResult(
            windows=states,
            engine=self.engine,
            skipped_reason=skipped_reason,
            metadata={
                "sample_seconds": sample_seconds,
                "sampled_from_video": sampled_from_video,
                "vision_windows": len(vision_windows),
                "event_windows": len(event_windows),
                "phase_windows": len(phase_windows),
            },
        )

    def _add_vision_states(
        self,
        states: list[GameplayStateWindow],
        vision: dict[str, Any],
        phase_windows: list[dict[str, Any]],
        event_windows: list[dict[str, Any]],
    ) -> None:
        activity = self._activity(vision)
        phase = self._phase_at(phase_windows, (vision["start_seconds"] + vision["end_seconds"]) / 2.0)
        event_types = self._event_types_at(event_windows, vision["start_seconds"], vision["end_seconds"])
        blocked = phase in _MENU_PHASES or "menu_or_idle" in event_types or "low_gameplay_value" in event_types

        if activity >= ACTION_THRESHOLD and not blocked:
            self._append(
                states,
                state_type="active_gameplay",
                start=vision["start_seconds"],
                end=vision["end_seconds"],
                score=max(activity, 0.55),
                confidence=0.58,
                motion=vision["motion_score"],
                scene=vision["scene_change_score"],
                activity=activity,
                reason="vision window has gameplay activity without wait phase",
                source_signals=[vision["window_id"], *event_types, phase or ""],
                metadata={"label": vision["label"], "action_score": vision["action_score"]},
            )

        if vision["motion_score"] >= ACTION_THRESHOLD or vision["action_score"] >= ACTION_THRESHOLD:
            self._append(
                states,
                state_type="high_motion_action",
                start=vision["start_seconds"],
                end=vision["end_seconds"],
                score=max(activity, 0.58),
                confidence=0.62,
                motion=vision["motion_score"],
                scene=vision["scene_change_score"],
                activity=activity,
                reason="high sampled frame motion/action",
                source_signals=[vision["window_id"]],
                metadata={"label": vision["label"], "action_score": vision["action_score"]},
            )

        low_motion = (
            vision["motion_score"] <= LOW_MOTION_THRESHOLD
            and vision["action_score"] <= LOW_MOTION_THRESHOLD + 0.02
            and vision["scene_change_score"] <= LOW_MOTION_THRESHOLD + 0.04
        )
        if low_motion and not (event_types & (_ACTION_EVENTS | _FLASH_EVENTS)):
            self._append(
                states,
                state_type="low_motion_wait",
                start=vision["start_seconds"],
                end=vision["end_seconds"],
                score=1.0 - max(activity, vision["scene_change_score"]),
                confidence=0.56,
                motion=vision["motion_score"],
                scene=vision["scene_change_score"],
                activity=activity,
                reason="low visual motion without action event",
                source_signals=[vision["window_id"], phase or "", *event_types],
                metadata={"label": vision["label"], "action_score": vision["action_score"]},
            )

        if vision["scene_change_score"] >= STRONG_SCENE_THRESHOLD and activity >= 0.12:
            self._append(
                states,
                state_type="possible_goal_or_flash",
                start=vision["start_seconds"],
                end=vision["end_seconds"],
                score=max(vision["scene_change_score"], activity),
                confidence=0.46,
                motion=vision["motion_score"],
                scene=vision["scene_change_score"],
                activity=activity,
                reason="strong visual scene change with activity",
                source_signals=[vision["window_id"]],
                metadata={"label": vision["label"], "from_vision_only": True},
            )

    def _add_event_states(
        self,
        states: list[GameplayStateWindow],
        event: dict[str, Any],
        vision_windows: list[dict[str, Any]],
        phase_windows: list[dict[str, Any]],
    ) -> None:
        visual = self._visual_summary(event["start_seconds"], event["end_seconds"], vision_windows)
        phase = self._phase_at(phase_windows, (event["start_seconds"] + event["end_seconds"]) / 2.0)
        event_type = event["event_type"]

        if event_type in _ACTION_EVENTS:
            self._append(
                states,
                state_type="high_motion_action",
                start=event["start_seconds"],
                end=event["end_seconds"],
                score=max(event["score"], visual["activity"], 0.6),
                confidence=max(event["confidence"], 0.58),
                reason="gameplay event indicates action burst",
                source_signals=[event["event_id"], event_type],
                metadata={"event_type": event_type},
                **visual,
            )
            if phase not in _MENU_PHASES:
                self._append(
                    states,
                    state_type="active_gameplay",
                    start=event["start_seconds"],
                    end=event["end_seconds"],
                    score=max(event["score"], visual["activity"], 0.58),
                    confidence=max(event["confidence"], 0.56),
                    reason="action event inside non-menu phase",
                    source_signals=[event["event_id"], event_type, phase or ""],
                    metadata={"event_type": event_type},
                    **visual,
                )

        if event_type in _FLASH_EVENTS:
            self._append(
                states,
                state_type="possible_goal_or_flash",
                start=event["start_seconds"],
                end=event["end_seconds"],
                score=max(event["score"], 0.65),
                confidence=max(event["confidence"], 0.58),
                reason="gameplay event indicates goal/save-like flash",
                source_signals=[event["event_id"], event_type],
                metadata={"event_type": event_type},
                **visual,
            )

        if event_type in _ROUND_END_EVENTS:
            self._append(
                states,
                state_type="round_end",
                start=event["start_seconds"],
                end=event["end_seconds"],
                score=max(event["score"], 0.62),
                confidence=max(event["confidence"], 0.56),
                reason="gameplay event indicates round-end dead time",
                source_signals=[event["event_id"], event_type],
                metadata={"event_type": event_type},
                **visual,
            )
            self._append(
                states,
                state_type="possible_dead_time_after_goal",
                start=event["start_seconds"],
                end=event["end_seconds"],
                score=max(event["score"], 0.62),
                confidence=max(event["confidence"], 0.54),
                reason="dead-time event after prior action context",
                source_signals=[event["event_id"], event_type],
                metadata={"event_type": event_type},
                **visual,
            )

        if event_type in _REPLAY_EVENTS:
            self._append(
                states,
                state_type="replay_like",
                start=event["start_seconds"],
                end=event["end_seconds"],
                score=max(event["score"], visual["scene_change_score"], 0.52),
                confidence=max(event["confidence"], 0.48),
                reason="event resembles replay or scene transition",
                source_signals=[event["event_id"], event_type],
                metadata={"event_type": event_type},
                **visual,
            )

        if event_type in _WAIT_EVENTS:
            state_type = "menu_wait" if event_type == "menu_or_idle" else "low_motion_wait"
            self._append(
                states,
                state_type=state_type,
                start=event["start_seconds"],
                end=event["end_seconds"],
                score=max(event["score"], 0.55),
                confidence=max(event["confidence"], 0.55),
                reason="event indicates low gameplay value or idle menu",
                source_signals=[event["event_id"], event_type],
                metadata={"event_type": event_type},
                **visual,
            )

    def _add_phase_states(
        self,
        states: list[GameplayStateWindow],
        phase: dict[str, Any],
        vision_windows: list[dict[str, Any]],
        event_windows: list[dict[str, Any]],
    ) -> None:
        visual = self._visual_summary(phase["start_seconds"], phase["end_seconds"], vision_windows)
        phase_type = phase["phase"]
        event_types = self._event_types_at(event_windows, phase["start_seconds"], phase["end_seconds"])

        if phase_type in _ACTIVE_PHASES:
            state_type = "active_gameplay" if phase_type == "active_round" else "possible_pre_action_context"
            self._append(
                states,
                state_type=state_type,
                start=phase["start_seconds"],
                end=phase["end_seconds"],
                score=max(phase["confidence"], visual["activity"], 0.55),
                confidence=max(phase["confidence"], 0.55),
                reason=f"round phase detector marked {phase_type}",
                source_signals=[phase_type, *event_types],
                metadata={"phase": phase_type},
                **visual,
            )

        if phase_type in _MENU_PHASES:
            self._append(
                states,
                state_type="menu_wait",
                start=phase["start_seconds"],
                end=phase["end_seconds"],
                score=max(phase["confidence"], 1.0 - visual["activity"], 0.58),
                confidence=max(phase["confidence"], 0.58),
                reason=f"round phase detector marked {phase_type}",
                source_signals=[phase_type, *event_types],
                metadata={"phase": phase_type},
                **visual,
            )

        if phase_type in _ROUND_END_PHASES:
            self._append(
                states,
                state_type="round_end",
                start=phase["start_seconds"],
                end=phase["end_seconds"],
                score=max(phase["confidence"], 0.6),
                confidence=max(phase["confidence"], 0.56),
                reason="round phase detector marked round_end",
                source_signals=[phase_type, *event_types],
                metadata={"phase": phase_type},
                **visual,
            )

        if phase_type in _REPLAY_PHASES:
            self._append(
                states,
                state_type="replay_like",
                start=phase["start_seconds"],
                end=phase["end_seconds"],
                score=max(phase["confidence"], visual["scene_change_score"], 0.58),
                confidence=max(phase["confidence"], 0.54),
                reason="round phase detector marked goal replay",
                source_signals=[phase_type, *event_types],
                metadata={"phase": phase_type},
                **visual,
            )

    def _add_pre_action_context(self, states: list[GameplayStateWindow]) -> None:
        triggers = [
            state for state in states
            if state.state_type in {"high_motion_action", "possible_goal_or_flash"}
        ]
        for trigger in triggers:
            start = round(max(0.0, trigger.start_seconds - 2.0), 3)
            end = trigger.start_seconds
            if end <= start:
                continue
            self._append(
                states,
                state_type="possible_pre_action_context",
                start=start,
                end=end,
                score=max(0.5, trigger.score * 0.8),
                confidence=max(0.45, trigger.confidence * 0.8),
                motion=trigger.motion_score,
                scene=trigger.scene_change_score,
                activity=trigger.visual_activity_score,
                reason="context window before high-action or flash state",
                source_signals=[trigger.window_id, trigger.state_type],
                metadata={"trigger_state": trigger.state_type, "trigger_start_seconds": trigger.start_seconds},
            )

    def _add_dead_time_after_goal(
        self,
        states: list[GameplayStateWindow],
        vision_windows: list[dict[str, Any]],
        phase_windows: list[dict[str, Any]],
    ) -> None:
        triggers = [
            state for state in states
            if state.state_type in {"possible_goal_or_flash", "round_end"}
        ]
        for trigger in triggers:
            start = round(trigger.end_seconds, 3)
            end = round(trigger.end_seconds + 5.0, 3)
            if end <= start:
                continue
            visual = self._visual_summary(start, end, vision_windows)
            has_wait_phase = any(
                phase["phase"] in (_MENU_PHASES | _ROUND_END_PHASES)
                and _overlap_seconds(start, end, phase["start_seconds"], phase["end_seconds"]) > 0.0
                for phase in phase_windows
            )
            if visual["motion_score"] > 0.10 and not has_wait_phase:
                continue
            self._append(
                states,
                state_type="possible_dead_time_after_goal",
                start=start,
                end=end,
                score=max(0.52, 1.0 - visual["activity"] if visual["samples"] else trigger.score * 0.75),
                confidence=max(0.44, trigger.confidence * 0.72),
                reason="low motion or wait phase shortly after goal/round-end state",
                source_signals=[trigger.window_id, trigger.state_type],
                metadata={"trigger_state": trigger.state_type, "trigger_end_seconds": trigger.end_seconds},
                **visual,
            )

    def _add_scoreboard_like(
        self,
        states: list[GameplayStateWindow],
        vision_windows: list[dict[str, Any]],
        phase_windows: list[dict[str, Any]],
        event_windows: list[dict[str, Any]],
    ) -> None:
        candidates = [
            state for state in states
            if state.state_type in {"round_end", "menu_wait", "low_motion_wait"}
        ]
        for candidate in candidates:
            visual = self._visual_summary(candidate.start_seconds, candidate.end_seconds, vision_windows)
            phase = self._phase_at(
                phase_windows,
                (candidate.start_seconds + candidate.end_seconds) / 2.0,
            )
            event_types = self._event_types_at(event_windows, candidate.start_seconds, candidate.end_seconds)
            if visual["samples"] and visual["motion_score"] > 0.09:
                continue
            if candidate.state_type == "low_motion_wait" and phase not in (_MENU_PHASES | _ROUND_END_PHASES):
                continue
            self._append(
                states,
                state_type="scoreboard_like",
                start=candidate.start_seconds,
                end=candidate.end_seconds,
                score=max(0.5, candidate.score * 0.85),
                confidence=max(0.42, candidate.confidence * 0.8),
                reason="stable low-motion wait/round-end surface",
                source_signals=[candidate.window_id, candidate.state_type, phase or "", *event_types],
                metadata={"derived_from": candidate.state_type},
                **visual,
            )

    def _vision_windows(self, result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, window in enumerate(self._iter_items(self._get(result, "windows", default=[]))):
            start, end = self._start_end(window)
            if end <= start:
                continue
            rows.append(
                {
                    "window_id": str(self._get(window, "window_id", default=f"vision_{index:06d}") or f"vision_{index:06d}"),
                    "start_seconds": start,
                    "end_seconds": end,
                    "motion_score": self._clamp(self._get(window, "motion_score", default=0.0)),
                    "action_score": self._clamp(self._get(window, "action_score", default=0.0)),
                    "scene_change_score": self._clamp(self._get(window, "scene_change_score", default=0.0)),
                    "label": str(self._get(window, "label", default="") or ""),
                }
            )
        return sorted(rows, key=lambda item: (item["start_seconds"], item["end_seconds"]))

    def _event_windows(self, result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, event in enumerate(self._iter_items(self._get(result, "windows", default=[]))):
            start, end = self._start_end(event)
            if end <= start:
                continue
            rows.append(
                {
                    "event_id": str(self._get(event, "event_id", default=f"event_{index:06d}") or f"event_{index:06d}"),
                    "start_seconds": start,
                    "end_seconds": end,
                    "event_type": str(self._get(event, "event_type", default="unknown") or "unknown"),
                    "score": self._clamp(self._get(event, "score", default=0.0)),
                    "confidence": self._clamp(self._get(event, "confidence", default=0.0)),
                }
            )
        return sorted(rows, key=lambda item: (item["start_seconds"], item["end_seconds"], item["event_type"]))

    def _phase_windows(self, result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for phase in self._iter_items(self._get(result, "windows", default=[])):
            start, end = self._start_end(phase)
            if end <= start:
                continue
            raw_phase = self._get(phase, "phase", default="unknown")
            phase_value = getattr(raw_phase, "value", raw_phase)
            rows.append(
                {
                    "start_seconds": start,
                    "end_seconds": end,
                    "phase": str(phase_value or "unknown"),
                    "confidence": self._clamp(self._get(phase, "confidence", default=0.0)),
                }
            )
        return sorted(rows, key=lambda item: (item["start_seconds"], item["end_seconds"], item["phase"]))

    def _visual_summary(
        self,
        start: float,
        end: float,
        vision_windows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        overlaps = [
            window for window in vision_windows
            if _overlap_seconds(start, end, window["start_seconds"], window["end_seconds"]) > 0.0
        ]
        if not overlaps:
            return {
                "motion": 0.0,
                "scene": 0.0,
                "activity": 0.0,
                "motion_score": 0.0,
                "scene_change_score": 0.0,
                "visual_activity_score": 0.0,
                "samples": 0,
            }
        motion = self._clamp(sum(window["motion_score"] for window in overlaps) / len(overlaps))
        scene = self._clamp(max(window["scene_change_score"] for window in overlaps))
        activity = self._clamp(max(self._activity(window) for window in overlaps))
        return {
            "motion": motion,
            "scene": scene,
            "activity": activity,
            "motion_score": motion,
            "scene_change_score": scene,
            "visual_activity_score": activity,
            "samples": len(overlaps),
        }

    def _append(
        self,
        states: list[GameplayStateWindow],
        *,
        state_type: str,
        start: float,
        end: float,
        score: float,
        confidence: float,
        reason: str,
        source_signals: list[str],
        metadata: dict[str, Any] | None = None,
        motion: float | None = None,
        scene: float | None = None,
        activity: float | None = None,
        motion_score: float | None = None,
        scene_change_score: float | None = None,
        visual_activity_score: float | None = None,
        samples: int | None = None,
    ) -> None:
        del samples
        if end <= start:
            return
        clean_sources = [signal for signal in source_signals if signal]
        states.append(
            GameplayStateWindow(
                window_id=f"gameplay_state_{len(states):06d}",
                start_seconds=start,
                end_seconds=end,
                state_type=state_type,
                score=score,
                confidence=confidence,
                motion_score=motion if motion is not None else (motion_score or 0.0),
                scene_change_score=scene if scene is not None else (scene_change_score or 0.0),
                visual_activity_score=activity if activity is not None else (visual_activity_score or 0.0),
                reason=reason,
                source_signals=clean_sources,
                metadata=metadata or {},
            )
        )

    def _activity(self, vision: dict[str, Any]) -> float:
        return self._clamp(
            max(
                vision["action_score"],
                (vision["motion_score"] * 0.75) + (vision["scene_change_score"] * 0.25),
                vision["scene_change_score"] * 0.85,
            )
        )

    def _phase_at(self, phase_windows: list[dict[str, Any]], seconds: float) -> str | None:
        for phase in phase_windows:
            if phase["start_seconds"] <= seconds < phase["end_seconds"]:
                return phase["phase"]
        return None

    def _event_types_at(
        self,
        event_windows: list[dict[str, Any]],
        start: float,
        end: float,
    ) -> set[str]:
        return {
            event["event_type"]
            for event in event_windows
            if _overlap_seconds(start, end, event["start_seconds"], event["end_seconds"]) > 0.0
        }

    def _iter_items(self, value: object) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, dict):
            return list(value.values())
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return list(value)
        return []

    def _get(self, item: object, *names: str, default: object = None) -> object:
        if isinstance(item, dict):
            for name in names:
                if name in item:
                    return item[name]
            return default
        for name in names:
            value = getattr(item, name, None)
            if value is not None:
                return value
        return default

    def _start_end(self, item: object) -> tuple[float, float]:
        start = max(0.0, self._safe_float(self._get(item, "start_seconds", "start_time", default=0.0)))
        end = max(start, self._safe_float(self._get(item, "end_seconds", "end_time", default=start), start))
        return round(start, 3), round(end, 3)

    def _safe_float(self, value: object, fallback: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _clamp(self, value: object, fallback: float = 0.0) -> float:
        return round(max(0.0, min(1.0, self._safe_float(value, fallback))), 3)

    def _skipped_reason(self, vision_result: object, event_result: object, phase_result: object) -> str:
        reasons = [
            str(self._get(result, "skipped_reason", default="") or "")
            for result in (vision_result, event_result, phase_result)
        ]
        reasons = [reason for reason in reasons if reason]
        return "; ".join(reasons) if reasons else "no gameplay state signals"


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))
