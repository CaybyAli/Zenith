from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

from models.gameplay_event_result import GameplayEventResult, GameplayEventWindow


class GameplayEventIndicatorBuilder:
    engine = "gameplay-event-indicator-builder-v1"

    def _make_event_id(self, event_type: str) -> str:
        return f"gameplay_event_{event_type}_{uuid.uuid4().hex[:12]}"

    def _safe_float(self, value: object, fallback: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _clamp(self, value: object, fallback: float = 0.0) -> float:
        return round(max(0.0, min(1.0, self._safe_float(value, fallback))), 3)

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

    def _overlaps(self, left: dict[str, Any], right: dict[str, Any], tolerance: float = 0.0) -> bool:
        return (
            left["start_seconds"] <= right["end_seconds"] + tolerance
            and left["end_seconds"] >= right["start_seconds"] - tolerance
        )

    def _append(
        self,
        events: list[GameplayEventWindow],
        *,
        event_type: str,
        start_seconds: float,
        end_seconds: float,
        score: object,
        confidence: object,
        reason: str,
        source_window_ids: list[str] | None = None,
        source_signal_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        events.append(
            GameplayEventWindow(
                event_id=self._make_event_id(event_type),
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                event_type=event_type,
                score=self._clamp(score),
                confidence=self._clamp(confidence),
                reason=reason,
                source_window_ids=source_window_ids or [],
                source_signal_ids=source_signal_ids or [],
                metadata=metadata or {},
            )
        )

    def _vision_windows(self, gameplay_vision_result: object) -> list[dict[str, Any]]:
        windows = self._get(gameplay_vision_result, "windows", default=[])
        rows: list[dict[str, Any]] = []
        for index, window in enumerate(self._iter_items(windows)):
            start, end = self._start_end(window)
            if end <= start:
                continue
            rows.append(
                {
                    "window_id": f"vision_{index:06d}",
                    "start_seconds": start,
                    "end_seconds": end,
                    "motion_score": self._clamp(self._get(window, "motion_score", default=0.0)),
                    "action_score": self._clamp(self._get(window, "action_score", default=0.0)),
                    "scene_change_score": self._clamp(self._get(window, "scene_change_score", default=0.0)),
                    "label": str(self._get(window, "label", default="") or ""),
                }
            )
        return sorted(rows, key=lambda item: (item["start_seconds"], item["end_seconds"]))

    def _signals(self, edit_signals: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for signal in self._iter_items(edit_signals):
            signal_type = str(self._get(signal, "signal_type", "kind", "type", default="") or "")
            start, end = self._start_end(signal)
            if end <= start:
                continue
            rows.append(
                {
                    "signal_id": str(self._get(signal, "signal_id", default="")),
                    "signal_type": signal_type,
                    "start_seconds": start,
                    "end_seconds": end,
                    "strength": self._clamp(self._get(signal, "strength", "score", default=0.0)),
                }
            )
        return sorted(rows, key=lambda item: (item["start_seconds"], item["end_seconds"], item["signal_type"]))

    def _energy_peaks(self, energy_curve_result: object) -> list[dict[str, Any]]:
        peak_ids = {
            self._get(point, "point_id", default=None)
            for point in self._iter_items(self._get(energy_curve_result, "peak_points", default=[]))
        }
        rows: list[dict[str, Any]] = []
        for point in self._iter_items(self._get(energy_curve_result, "points", default=[])):
            energy_score = self._clamp(self._get(point, "energy_score", default=0.0))
            point_id = self._get(point, "point_id", default=None)
            if energy_score < 0.65 and point_id not in peak_ids:
                continue
            start, end = self._start_end(point)
            rows.append(
                {
                    "point_id": str(point_id or ""),
                    "start_seconds": start,
                    "end_seconds": end,
                    "energy_score": energy_score,
                    "source_signal_ids": list(self._get(point, "source_signal_ids", default=[]) or []),
                }
            )
        return rows

    def _audio_roles(self, audio_role_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for window in self._iter_items(self._get(audio_role_result, "windows", default=[])):
            start, end = self._start_end(window)
            rows.append(
                {
                    "window_id": str(self._get(window, "window_id", default="")),
                    "start_seconds": start,
                    "end_seconds": end,
                    "role_type": str(self._get(window, "role_type", default="") or ""),
                    "score": self._clamp(self._get(window, "score", default=0.0)),
                    "source_signal_ids": list(self._get(window, "source_signal_ids", default=[]) or []),
                }
            )
        return rows

    def _speech_windows(self, sentence_timeline_result: object, audio_roles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = [
            role for role in audio_roles
            if role["role_type"] in {"speech_active", "laugh_like_audio", "shout_like_audio", "group_reaction_like"}
        ]
        for sentence in self._iter_items(self._get(sentence_timeline_result, "sentences", default=[])):
            start, end = self._start_end(sentence)
            rows.append(
                {
                    "start_seconds": start,
                    "end_seconds": end,
                    "role_type": str(self._get(sentence, "sentence_kind", default="sentence") or "sentence"),
                }
            )
        return rows

    def _add_action_events(
        self,
        events: list[GameplayEventWindow],
        vision_windows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        high_actions: list[dict[str, Any]] = []
        for window in vision_windows:
            is_high = (
                window["action_score"] >= 0.18
                or (window["action_score"] >= 0.12 and window["scene_change_score"] >= 0.12)
            )
            if is_high:
                high_actions.append(window)
                score = self._clamp(max(window["action_score"] * 2.6, window["scene_change_score"] * 1.8, 0.55))
                self._append(
                    events,
                    event_type="high_action_burst",
                    start_seconds=window["start_seconds"],
                    end_seconds=window["end_seconds"],
                    score=score,
                    confidence=0.68 if window["action_score"] >= 0.18 else 0.58,
                    reason="high gameplay action score",
                    source_window_ids=[window["window_id"]],
                    metadata={
                        "action_score": window["action_score"],
                        "motion_score": window["motion_score"],
                        "scene_change_score": window["scene_change_score"],
                        "label": window["label"],
                    },
                )

            if window["label"] == "scene_change" or window["scene_change_score"] >= 0.18:
                self._append(
                    events,
                    event_type="scene_change_moment",
                    start_seconds=window["start_seconds"],
                    end_seconds=window["end_seconds"],
                    score=max(window["scene_change_score"], window["action_score"]),
                    confidence=0.62,
                    reason="visual scene change",
                    source_window_ids=[window["window_id"]],
                    metadata={"label": window["label"], "scene_change_score": window["scene_change_score"]},
                )

        return high_actions

    def _add_sustained_action(
        self,
        events: list[GameplayEventWindow],
        high_actions: list[dict[str, Any]],
    ) -> None:
        cluster: list[dict[str, Any]] = []
        for window in high_actions:
            if not cluster or window["start_seconds"] - cluster[-1]["end_seconds"] <= 1.0:
                cluster.append(window)
                continue
            self._flush_action_cluster(events, cluster)
            cluster = [window]
        self._flush_action_cluster(events, cluster)

    def _flush_action_cluster(
        self,
        events: list[GameplayEventWindow],
        cluster: list[dict[str, Any]],
    ) -> None:
        if not cluster:
            return
        start = cluster[0]["start_seconds"]
        end = cluster[-1]["end_seconds"]
        if end - start < 3.0:
            return
        avg_action = sum(window["action_score"] for window in cluster) / len(cluster)
        max_action = max(window["action_score"] for window in cluster)
        self._append(
            events,
            event_type="sustained_action",
            start_seconds=start,
            end_seconds=end,
            score=self._clamp((avg_action * 1.6) + (max_action * 1.2), 0.65),
            confidence=0.72,
            reason="clustered gameplay action windows",
            source_window_ids=[window["window_id"] for window in cluster],
            metadata={"cluster_size": len(cluster), "avg_action_score": round(avg_action, 3), "max_action_score": max_action},
        )

    def _add_flash_events(
        self,
        events: list[GameplayEventWindow],
        high_actions: list[dict[str, Any]],
        energy_peaks: list[dict[str, Any]],
        audio_roles: list[dict[str, Any]],
    ) -> None:
        reaction_roles = [
            role for role in audio_roles
            if role["role_type"] in {"shout_like_audio", "group_reaction_like", "laugh_like_audio"}
        ]
        for action in high_actions:
            nearby_energy = [point for point in energy_peaks if self._overlaps(action, point, tolerance=1.5)]
            nearby_reactions = [role for role in reaction_roles if self._overlaps(action, role, tolerance=1.5)]
            if not nearby_energy and not nearby_reactions:
                continue
            score = max(
                0.65,
                min(0.90, (action["action_score"] * 1.8) + (0.12 if nearby_energy else 0.0) + (0.15 if nearby_reactions else 0.0)),
            )
            self._append(
                events,
                event_type="goal_or_save_like_flash",
                start_seconds=action["start_seconds"],
                end_seconds=action["end_seconds"],
                score=score,
                confidence=0.62 if nearby_reactions else 0.50,
                reason="action burst near energy/audio reaction",
                source_window_ids=[action["window_id"], *[role["window_id"] for role in nearby_reactions]],
                source_signal_ids=[
                    signal_id
                    for point in nearby_energy
                    for signal_id in point.get("source_signal_ids", [])
                ],
                metadata={
                    "nearby_energy_peaks": len(nearby_energy),
                    "nearby_reaction_roles": len(nearby_reactions),
                    "action_score": action["action_score"],
                },
            )

    def _add_low_value_events(
        self,
        events: list[GameplayEventWindow],
        signals: list[dict[str, Any]],
        high_actions: list[dict[str, Any]],
        energy_peaks: list[dict[str, Any]],
        speech_windows: list[dict[str, Any]],
        vision_windows: list[dict[str, Any]],
    ) -> None:
        low_signals = [signal for signal in signals if signal["signal_type"] in {"silence_zone", "low_motion_zone"}]
        peakish = [*high_actions, *energy_peaks, *[s for s in signals if s["signal_type"] in {"audio_peak", "motion_peak"}]]
        for signal in low_signals:
            duration = signal["end_seconds"] - signal["start_seconds"]
            if duration <= 0:
                continue
            had_peak_before = any(
                item["end_seconds"] <= signal["start_seconds"]
                and signal["start_seconds"] - item["end_seconds"] <= 5.0
                for item in peakish
            )
            if had_peak_before and duration >= 1.5:
                self._append(
                    events,
                    event_type="round_end_dead_time",
                    start_seconds=signal["start_seconds"],
                    end_seconds=signal["end_seconds"],
                    score=min(0.90, 0.60 + duration / 10.0),
                    confidence=0.58,
                    reason="low activity after action peak",
                    source_signal_ids=[signal["signal_id"]],
                    metadata={"signal_type": signal["signal_type"], "duration_seconds": round(duration, 3)},
                )

            has_speech = any(self._overlaps(signal, speech, tolerance=0.5) for speech in speech_windows)
            has_action = any(self._overlaps(signal, action, tolerance=0.5) for action in high_actions)
            if duration >= 2.0 and not has_speech and not has_action:
                event_type = "menu_or_idle" if signal["signal_type"] == "low_motion_zone" else "low_gameplay_value"
                self._append(
                    events,
                    event_type=event_type,
                    start_seconds=signal["start_seconds"],
                    end_seconds=signal["end_seconds"],
                    score=min(0.90, 0.60 + duration / 12.0),
                    confidence=0.65,
                    reason="low gameplay/audio value",
                    source_signal_ids=[signal["signal_id"]],
                    metadata={"signal_type": signal["signal_type"], "duration_seconds": round(duration, 3)},
                )

        scene_changes = [window for window in vision_windows if window["label"] == "scene_change" or window["scene_change_score"] >= 0.18]
        for scene in scene_changes:
            previous_action = any(
                action["end_seconds"] <= scene["start_seconds"]
                and scene["start_seconds"] - action["end_seconds"] <= 5.0
                for action in high_actions
            )
            next_low = any(
                low["start_seconds"] >= scene["end_seconds"]
                and low["start_seconds"] - scene["end_seconds"] <= 5.0
                for low in low_signals
            )
            if previous_action and next_low:
                self._append(
                    events,
                    event_type="replay_like_moment",
                    start_seconds=scene["start_seconds"],
                    end_seconds=scene["end_seconds"],
                    score=0.56,
                    confidence=0.48,
                    reason="scene change after peak with lower activity",
                    source_window_ids=[scene["window_id"]],
                    metadata={"scene_change_score": scene["scene_change_score"]},
                )

        for action in high_actions:
            previous_low = [
                low for low in low_signals
                if low["end_seconds"] <= action["start_seconds"]
                and action["start_seconds"] - low["end_seconds"] <= 2.0
            ]
            if previous_low:
                self._append(
                    events,
                    event_type="kickoff_like",
                    start_seconds=action["start_seconds"],
                    end_seconds=action["end_seconds"],
                    score=max(0.45, min(0.70, action["action_score"] * 2.0)),
                    confidence=0.48,
                    reason="low activity followed by gameplay action",
                    source_window_ids=[action["window_id"]],
                    source_signal_ids=[previous_low[-1]["signal_id"]],
                    metadata={"action_score": action["action_score"]},
                )

    def build(
        self,
        *,
        gameplay_vision_result: object = None,
        energy_curve_result: object = None,
        edit_signals: object = None,
        audio_role_result: object = None,
        sentence_timeline_result: object = None,
        channel_type: object = "gaming_main",
    ) -> GameplayEventResult:
        del channel_type
        vision_windows = self._vision_windows(gameplay_vision_result)
        signals = self._signals(edit_signals)
        energy_peaks = self._energy_peaks(energy_curve_result)
        audio_roles = self._audio_roles(audio_role_result)
        speech_windows = self._speech_windows(sentence_timeline_result, audio_roles)

        events: list[GameplayEventWindow] = []
        high_actions = self._add_action_events(events, vision_windows)
        self._add_sustained_action(events, high_actions)
        self._add_flash_events(events, high_actions, energy_peaks, audio_roles)
        self._add_low_value_events(events, signals, high_actions, energy_peaks, speech_windows, vision_windows)

        events.sort(key=lambda event: (event.start_seconds, event.end_seconds, event.event_type))
        return GameplayEventResult(
            windows=events,
            engine=self.engine,
            skipped_reason="no gameplay event windows" if not events else None,
        )
