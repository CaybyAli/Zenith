from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Tuple

from models.engagement_span import (
    G7A_KEEP_RECOMMENDATIONS,
    ActivePlayEngagementResult,
    EngagementSpan,
)
from models.play_segment import PlaySegmentDetectionResult, PlaySignalWindow, clamp01


FORBIDDEN_G7A_TERMS = (
    "goal",
    "kickoff",
    "scoreboard",
    "round_end",
    "rocket_league",
    "fortnite",
    "minecraft",
    "league_of_legends",
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except Exception:
        return default
    if not math.isfinite(number):
        return default
    return number


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def assert_g7a_neutral_taxonomy() -> None:
    haystack = " ".join(G7A_KEEP_RECOMMENDATIONS).lower()
    leaked = [term for term in FORBIDDEN_G7A_TERMS if term in haystack]
    if leaked:
        raise AssertionError(f"forbidden G7a taxonomy terms leaked: {leaked}")


class ActivePlayEngagementClassifier:
    """Additive signal-only classifier inside active-play contexts.

    It does not replace G6 states.
    It does not use transcript/speech content.
    It does not render or cut anything.

    Honest boundary:
    - Can flag frozen/paused video.
    - Can flag sustained low signal engagement.
    - Cannot detect loud/moving private/off-content chatter. That belongs to G7b.
    """

    def __init__(
        self,
        *,
        low_engagement_threshold: float = 0.36,
        low_engagement_min_seconds: float = 4.0,
        frozen_min_seconds: float = 6.0,
        frozen_motion_max: float = 0.025,
        frozen_scene_change_max: float = 0.025,
        frozen_visual_stability_min: float = 0.985,
        active_context_gap_seconds: float = 12.0,
    ) -> None:
        assert_g7a_neutral_taxonomy()
        self.low_engagement_threshold = float(low_engagement_threshold)
        self.low_engagement_min_seconds = float(low_engagement_min_seconds)
        self.frozen_min_seconds = float(frozen_min_seconds)
        self.frozen_motion_max = float(frozen_motion_max)
        self.frozen_scene_change_max = float(frozen_scene_change_max)
        self.frozen_visual_stability_min = float(frozen_visual_stability_min)
        self.active_context_gap_seconds = float(active_context_gap_seconds)

    @property
    def thresholds(self) -> Dict[str, Any]:
        return {
            "low_engagement_threshold": self.low_engagement_threshold,
            "low_engagement_min_seconds": self.low_engagement_min_seconds,
            "frozen_min_seconds": self.frozen_min_seconds,
            "frozen_motion_max": self.frozen_motion_max,
            "frozen_scene_change_max": self.frozen_scene_change_max,
            "frozen_visual_stability_min": self.frozen_visual_stability_min,
            "active_context_gap_seconds": self.active_context_gap_seconds,
            "formula": (
                "engagement=0.34*motion+0.22*audio_activity+0.14*audio_peak+"
                "0.16*scene_change+0.14*visual_richness"
            ),
            "honesty_boundary": (
                "Signal-only. Does not classify loud or moving private/off-content speech; "
                "that requires G7b transcript analysis."
            ),
        }

    def engagement_score(self, window: PlaySignalWindow | Dict[str, Any]) -> float:
        data = self._window_to_row(window)
        motion = _safe_float(data.get("motion_score"))
        audio = _safe_float(data.get("audio_activity"))
        peak = _safe_float(data.get("audio_peak_score"))
        scene = _safe_float(data.get("scene_change_score"))
        richness = _safe_float(data.get("visual_richness"))

        score = (
            0.34 * motion
            + 0.22 * audio
            + 0.14 * peak
            + 0.16 * scene
            + 0.14 * richness
        )
        return clamp01(score)

    def classify(self, result: PlaySegmentDetectionResult) -> ActivePlayEngagementResult:
        warnings: List[str] = []

        if not getattr(result, "raw_windows", None):
            warnings.append("raw_windows_missing_run_g6_detector_with_include_raw_windows_true")
            return ActivePlayEngagementResult(
                video_path=str(result.video_path),
                analyzed_duration_seconds=float(result.analyzed_duration_seconds),
                window_seconds=float(result.window_seconds),
                thresholds=self.thresholds,
                active_contexts=[],
                spans=[],
                ratios=self._ratios([]),
                warnings=warnings,
            )

        contexts = self._active_contexts(result)
        rows: List[Dict[str, Any]] = []

        for context in contexts:
            context_rows = []
            for window in result.raw_windows:
                row = self._window_to_row(window)
                overlap = _overlap_seconds(
                    row["start_seconds"],
                    row["end_seconds"],
                    context["start_seconds"],
                    context["end_seconds"],
                )
                if overlap <= 0:
                    continue

                row["overlap_seconds"] = round(overlap, 3)
                row["parent_active_context"] = dict(context)
                row["engagement_score"] = round(self.engagement_score(row), 4)
                row["low_engagement_reasons"] = self.low_engagement_reasons(row)
                row["is_low_engagement_candidate"] = self._is_low_engagement_candidate(row)
                row["is_frozen_candidate"] = self._is_frozen_candidate(row)
                context_rows.append(row)

            rows.extend(self._assign_recommendations(context_rows))

        spans = self._consolidate_rows(rows)

        return ActivePlayEngagementResult(
            video_path=str(result.video_path),
            analyzed_duration_seconds=float(result.analyzed_duration_seconds),
            window_seconds=float(result.window_seconds),
            thresholds=self.thresholds,
            active_contexts=contexts,
            spans=spans,
            ratios=self._ratios(spans),
            warnings=warnings,
        )

    def _active_contexts(self, result: PlaySegmentDetectionResult) -> List[Dict[str, float]]:
        active_segments = [
            {
                "start_seconds": float(segment.start_seconds),
                "end_seconds": float(segment.end_seconds),
            }
            for segment in result.segments
            if segment.state == "active_play" and segment.end_seconds > segment.start_seconds
        ]
        active_segments.sort(key=lambda item: (item["start_seconds"], item["end_seconds"]))

        if not active_segments:
            return []

        contexts: List[Dict[str, float]] = [dict(active_segments[0])]

        for segment in active_segments[1:]:
            current = contexts[-1]
            gap = segment["start_seconds"] - current["end_seconds"]
            if gap <= self.active_context_gap_seconds:
                current["end_seconds"] = max(current["end_seconds"], segment["end_seconds"])
                current["bridged_gap_seconds"] = round(max(0.0, gap), 3)
            else:
                contexts.append(dict(segment))

        return [
            {
                "start_seconds": round(item["start_seconds"], 3),
                "end_seconds": round(item["end_seconds"], 3),
                "duration_seconds": round(item["end_seconds"] - item["start_seconds"], 3),
                **({"bridged_gap_seconds": item["bridged_gap_seconds"]} if "bridged_gap_seconds" in item else {}),
            }
            for item in contexts
            if item["end_seconds"] > item["start_seconds"]
        ]

    def _window_to_row(self, window: PlaySignalWindow | Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(window, dict):
            data = dict(window)
        else:
            data = window.to_dict()

        evidence = data.get("evidence") or {}
        data["visual_richness"] = _safe_float(evidence.get("visual_richness", data.get("visual_richness")), 0.0)
        data["active_score"] = _safe_float(evidence.get("active_score", data.get("active_score")), 0.0)
        data["idle_score"] = _safe_float(evidence.get("idle_score", data.get("idle_score")), 0.0)
        data["transition_score"] = _safe_float(evidence.get("transition_score", data.get("transition_score")), 0.0)
        return data

    def low_engagement_reasons(self, window: PlaySignalWindow | Dict[str, Any]) -> List[str]:
        data = self._window_to_row(window)

        motion = _safe_float(data.get("motion_score"))
        audio = _safe_float(data.get("audio_activity"))
        peak = _safe_float(data.get("audio_peak_score"))
        scene = _safe_float(data.get("scene_change_score"))
        stability = _safe_float(data.get("visual_stability"))
        richness = _safe_float(data.get("visual_richness"))
        score = self.engagement_score(data)

        reasons: List[str] = []

        if score <= self.low_engagement_threshold:
            reasons.append("low_composite_engagement")
        if motion <= 0.25:
            reasons.append("low_motion")
        if audio <= 0.22:
            reasons.append("low_audio_activity")
        if peak <= 0.35:
            reasons.append("low_audio_peak")
        if scene <= 0.20:
            reasons.append("low_scene_change")
        if scene <= 0.20 and stability >= 0.72:
            reasons.append("stable_low_scene_change")
        if richness <= 0.35:
            reasons.append("low_visual_richness")

        return reasons

    def _is_low_engagement_candidate(self, row: Dict[str, Any]) -> bool:
        if self._is_frozen_candidate(row):
            return False

        score = _safe_float(row.get("engagement_score", self.engagement_score(row)))
        reasons = row.get("low_engagement_reasons") or self.low_engagement_reasons(row)

        motion = _safe_float(row.get("motion_score"))
        audio = _safe_float(row.get("audio_activity"))
        peak = _safe_float(row.get("audio_peak_score"))
        scene = _safe_float(row.get("scene_change_score"))

        strict_low_bundle = (
            motion <= 0.25
            and audio <= 0.30
            and peak <= 0.35
            and scene <= 0.25
        )

        return (score <= self.low_engagement_threshold and len(reasons) >= 3) or strict_low_bundle

    def _is_frozen_candidate(self, row: Dict[str, Any]) -> bool:
        motion = _safe_float(row.get("motion_score"))
        scene = _safe_float(row.get("scene_change_score"))
        stability = _safe_float(row.get("visual_stability"))

        return (
            motion <= self.frozen_motion_max
            and scene <= self.frozen_scene_change_max
            and stability >= self.frozen_visual_stability_min
        )

    def _assign_recommendations(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = sorted(rows, key=lambda item: (item["start_seconds"], item["end_seconds"]))

        for row in rows:
            row["keep_recommendation"] = "keep_active"
            row["recommendation_confidence"] = round(max(0.52, min(0.95, 0.50 + row["engagement_score"] * 0.45)), 4)
            row["recommendation_reasons"] = ["high_or_sufficient_signal_keep_active"]

        self._mark_sustained_groups(
            rows,
            flag_key="is_frozen_candidate",
            recommendation="frozen_or_paused",
            min_seconds=self.frozen_min_seconds,
        )
        self._mark_sustained_groups(
            rows,
            flag_key="is_low_engagement_candidate",
            recommendation="trimmable_low_engagement",
            min_seconds=self.low_engagement_min_seconds,
        )

        return rows

    def _mark_sustained_groups(
        self,
        rows: List[Dict[str, Any]],
        *,
        flag_key: str,
        recommendation: str,
        min_seconds: float,
    ) -> None:
        current: List[Dict[str, Any]] = []

        def flush(group: List[Dict[str, Any]]) -> None:
            if not group:
                return
            duration = group[-1]["end_seconds"] - group[0]["start_seconds"]
            if duration < min_seconds:
                return

            for item in group:
                if recommendation == "frozen_or_paused":
                    item["keep_recommendation"] = recommendation
                    item["recommendation_confidence"] = 0.96
                    item["recommendation_reasons"] = [
                        "sustained_frozen_or_paused",
                        "near_zero_motion",
                        "near_zero_scene_change",
                        "near_identical_frames",
                    ]
                elif item.get("keep_recommendation") != "frozen_or_paused":
                    score = _safe_float(item.get("engagement_score"))
                    confidence = 0.62 + clamp01((self.low_engagement_threshold - score) / max(0.001, self.low_engagement_threshold)) * 0.28
                    item["keep_recommendation"] = recommendation
                    item["recommendation_confidence"] = round(confidence, 4)
                    item["recommendation_reasons"] = sorted(set(item.get("low_engagement_reasons") or []))

        for row in rows:
            if row.get("keep_recommendation") == "frozen_or_paused" and recommendation != "frozen_or_paused":
                if current:
                    flush(current)
                    current = []
                continue

            if bool(row.get(flag_key)):
                if current and abs(current[-1]["end_seconds"] - row["start_seconds"]) <= 0.01:
                    current.append(row)
                else:
                    if current:
                        flush(current)
                    current = [row]
            else:
                if current:
                    flush(current)
                    current = []

        if current:
            flush(current)

    def _consolidate_rows(self, rows: List[Dict[str, Any]]) -> List[EngagementSpan]:
        if not rows:
            return []

        rows = sorted(rows, key=lambda item: (item["start_seconds"], item["end_seconds"]))
        groups: List[List[Dict[str, Any]]] = []
        current: List[Dict[str, Any]] = [rows[0]]

        for row in rows[1:]:
            previous = current[-1]
            same_recommendation = row["keep_recommendation"] == previous["keep_recommendation"]
            same_context = row.get("parent_active_context") == previous.get("parent_active_context")
            touches = abs(previous["end_seconds"] - row["start_seconds"]) <= 0.01

            if same_recommendation and same_context and touches:
                current.append(row)
            else:
                groups.append(current)
                current = [row]

        groups.append(current)
        return [self._span_from_group(group) for group in groups]

    def _span_from_group(self, group: List[Dict[str, Any]]) -> EngagementSpan:
        start = float(group[0]["start_seconds"])
        end = float(group[-1]["end_seconds"])
        duration = max(0.0, end - start)

        def avg(key: str) -> float:
            values = [_safe_float(item.get(key)) for item in group]
            return round(sum(values) / len(values), 4) if values else 0.0

        source_counts: Dict[str, int] = {}
        for item in group:
            state = str(item.get("state") or "unknown")
            source_counts[state] = source_counts.get(state, 0) + 1

        reasons = sorted({reason for item in group for reason in item.get("recommendation_reasons", [])})
        warnings = sorted({warning for item in group for warning in item.get("warnings", [])})

        return EngagementSpan(
            start_seconds=start,
            end_seconds=end,
            duration_seconds=duration,
            keep_recommendation=str(group[0]["keep_recommendation"]),
            confidence=avg("recommendation_confidence"),
            reasons=reasons,
            evidence={
                "avg_engagement_score": avg("engagement_score"),
                "avg_motion_score": avg("motion_score"),
                "avg_audio_activity": avg("audio_activity"),
                "avg_audio_peak_score": avg("audio_peak_score"),
                "avg_scene_change_score": avg("scene_change_score"),
                "avg_visual_stability": avg("visual_stability"),
                "avg_visual_richness": avg("visual_richness"),
                "avg_active_score": avg("active_score"),
                "avg_idle_score": avg("idle_score"),
                "avg_transition_score": avg("transition_score"),
                "window_count": len(group),
                "honesty_boundary": (
                    "Signal-only recommendation. High-signal but private/off-content material "
                    "must remain keep_active until transcript-based G7b."
                ),
            },
            source_g6_state_counts=source_counts,
            parent_active_context=dict(group[0].get("parent_active_context") or {}),
            warnings=warnings,
        )

    def _ratios(self, spans: Iterable[EngagementSpan]) -> Dict[str, float]:
        items = list(spans)
        total = sum(max(0.0, float(item.duration_seconds)) for item in items)

        keep = sum(item.duration_seconds for item in items if item.keep_recommendation == "keep_active")
        low = sum(item.duration_seconds for item in items if item.keep_recommendation == "trimmable_low_engagement")
        frozen = sum(item.duration_seconds for item in items if item.keep_recommendation == "frozen_or_paused")

        return {
            "total_active_context_seconds": round(total, 3),
            "keep_active_seconds": round(keep, 3),
            "trimmable_low_engagement_seconds": round(low, 3),
            "frozen_or_paused_seconds": round(frozen, 3),
            "keep_active_share": round(keep / total, 4) if total > 0 else 0.0,
            "trimmable_low_engagement_share": round(low / total, 4) if total > 0 else 0.0,
            "frozen_or_paused_share": round(frozen / total, 4) if total > 0 else 0.0,
        }
