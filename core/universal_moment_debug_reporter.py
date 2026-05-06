from __future__ import annotations

from collections import Counter
from typing import Any

from models.timeline_segment import TimelineSegment
from models.universal_moment_debug_report import (
    ENGINE,
    UniversalMomentDebugReport,
    UniversalMomentSegmentDebug,
)
from models.universal_moment_result import UniversalMomentResult, UniversalMomentWindow


class UniversalMomentDebugReporter:
    engine = ENGINE

    def build(
        self,
        *,
        job_id: str,
        timeline_segments: list[TimelineSegment],
        universal_moment_result=None,
    ) -> UniversalMomentDebugReport:
        segments = sorted(
            [
                segment
                for segment in (timeline_segments or [])
                if getattr(segment, "end_time", 0.0) > getattr(segment, "start_time", 0.0)
            ],
            key=lambda segment: (segment.start_time, segment.end_time, segment.segment_id),
        )
        windows = self._windows(universal_moment_result)

        debug_segments = [
            self._build_segment_debug(segment, self._overlapping_windows(segment, windows))
            for segment in segments
        ]
        report = UniversalMomentDebugReport(
            job_id=str(job_id or ""),
            engine=self.engine,
            segments=debug_segments,
        )
        self._log(report)
        return report

    def _build_segment_debug(
        self,
        segment: TimelineSegment,
        windows: list[UniversalMomentWindow],
    ) -> UniversalMomentSegmentDebug:
        top_moment_types = self._moment_type_counts(windows)
        dominant_moment_type = next(iter(top_moment_types), "unknown")

        keep_scores = [
            max(
                window.peak_score,
                window.tension_score,
                window.post_peak_reaction_score,
                window.moment_score if window.should_keep else 0.0,
            )
            for window in windows
        ]
        remove_scores = [
            max(
                window.boring_score,
                window.menu_wait_score,
                window.dead_time_score,
                window.private_talk_score if window.should_remove else 0.0,
            )
            for window in windows
        ]

        has_keep_signal = any(
            window.should_keep
            or window.peak_score >= 0.65
            or window.tension_score >= 0.60
            or window.post_peak_reaction_score >= 0.60
            for window in windows
        )
        has_remove_signal = any(
            window.should_remove
            or window.boring_score >= 0.80
            or window.menu_wait_score >= 0.70
            or window.dead_time_score >= 0.70
            for window in windows
        )
        has_cut_risk = any(
            window.cut_risk_score >= 0.70
            or window.speech_boundary_risk
            or window.action_context_risk
            for window in windows
        )
        has_zoom_risk = any(
            window.zoom_risk_score >= 0.70 or window.zoom_boundary_risk
            for window in windows
        )
        has_private_menu_risk = any(
            window.private_talk_score >= 0.70
            or window.menu_private_risk
            or window.moment_type == "private_menu_talk"
            for window in windows
        )
        has_pre_context_need = any(window.needs_pre_context for window in windows)
        has_post_context_need = any(window.needs_post_context for window in windows)

        diagnosis = self._diagnosis(
            windows=windows,
            has_keep_signal=has_keep_signal,
            has_remove_signal=has_remove_signal,
            has_cut_risk=has_cut_risk,
            has_zoom_risk=has_zoom_risk,
            has_private_menu_risk=has_private_menu_risk,
            has_pre_context_need=has_pre_context_need,
            has_post_context_need=has_post_context_need,
        )

        return UniversalMomentSegmentDebug(
            segment_id=segment.segment_id,
            segment_role=segment.segment_role,
            start_time=segment.start_time,
            end_time=segment.end_time,
            duration_seconds=segment.duration,
            overlapping_windows=len(windows),
            dominant_moment_type=dominant_moment_type,
            top_moment_types=top_moment_types,
            avg_moment_score=self._avg(window.moment_score for window in windows),
            max_moment_score=self._max(window.moment_score for window in windows),
            avg_keep_score=self._avg(keep_scores),
            avg_remove_score=self._avg(remove_scores),
            avg_cut_risk_score=self._avg(window.cut_risk_score for window in windows),
            avg_zoom_risk_score=self._avg(window.zoom_risk_score for window in windows),
            avg_private_talk_score=self._avg(window.private_talk_score for window in windows),
            avg_boring_score=self._avg(window.boring_score for window in windows),
            avg_peak_score=self._avg(window.peak_score for window in windows),
            avg_tension_score=self._avg(window.tension_score for window in windows),
            avg_post_reaction_score=self._avg(window.post_peak_reaction_score for window in windows),
            has_keep_signal=has_keep_signal,
            has_remove_signal=has_remove_signal,
            has_cut_risk=has_cut_risk,
            has_zoom_risk=has_zoom_risk,
            has_private_menu_risk=has_private_menu_risk,
            has_pre_context_need=has_pre_context_need,
            has_post_context_need=has_post_context_need,
            segment_notes=list(getattr(segment, "notes", []) or []),
            universal_notes=self._universal_notes(segment, windows),
            diagnosis=diagnosis,
        )

    def _diagnosis(
        self,
        *,
        windows: list[UniversalMomentWindow],
        has_keep_signal: bool,
        has_remove_signal: bool,
        has_cut_risk: bool,
        has_zoom_risk: bool,
        has_private_menu_risk: bool,
        has_pre_context_need: bool,
        has_post_context_need: bool,
    ) -> list[str]:
        if not windows:
            return ["NO-SIGNAL: no overlapping universal moment windows"]

        diagnosis: list[str] = []
        if has_keep_signal:
            diagnosis.append("KEEP: peak/tension signal detected")
        if has_cut_risk:
            diagnosis.append("RISK: cut boundary may hit speech/action")
        if has_zoom_risk:
            diagnosis.append("RISK: zoom boundary risk")
        if has_remove_signal:
            diagnosis.append("REMOVE-CANDIDATE: boring/menu/dead-time signal")
        if has_private_menu_risk:
            diagnosis.append("PRIVATE: menu speech/private talk risk")
        if has_pre_context_need:
            diagnosis.append("CONTEXT: needs pre-action context")
        if has_post_context_need:
            diagnosis.append("CONTEXT: needs post-peak reaction")
        return diagnosis or ["INFO: universal moment windows overlap without dominant risk"]

    def _universal_notes(
        self,
        segment: TimelineSegment,
        windows: list[UniversalMomentWindow],
    ) -> list[str]:
        notes: list[str] = []
        for note in getattr(segment, "notes", []) or []:
            if str(note).startswith("universal_"):
                notes.append(str(note))
        for window in windows:
            for note in window.source_notes:
                notes.append(f"window:{window.window_id}:{note}")
            for signal in window.source_signals:
                notes.append(f"signal:{window.window_id}:{signal}")
        return self._dedupe(notes)

    def _moment_type_counts(self, windows: list[UniversalMomentWindow]) -> dict[str, int]:
        counter = Counter(str(window.moment_type or "unknown") for window in windows)
        return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))

    def _overlapping_windows(
        self,
        segment: TimelineSegment,
        windows: list[UniversalMomentWindow],
    ) -> list[UniversalMomentWindow]:
        return [
            window
            for window in windows
            if self._overlap_seconds(
                segment.start_time,
                segment.end_time,
                window.start_seconds,
                window.end_seconds,
            )
            > 0.0
        ]

    def _windows(self, universal_moment_result: object) -> list[UniversalMomentWindow]:
        if universal_moment_result is None:
            return []
        if isinstance(universal_moment_result, UniversalMomentResult):
            return [
                window
                for window in universal_moment_result.windows
                if window.end_seconds > window.start_seconds
            ]
        if isinstance(universal_moment_result, dict):
            return self._windows(UniversalMomentResult.from_dict(universal_moment_result))
        raw_windows = getattr(universal_moment_result, "windows", None)
        if raw_windows is None:
            return []

        parsed: list[UniversalMomentWindow] = []
        for window in raw_windows:
            if isinstance(window, UniversalMomentWindow):
                parsed.append(window)
            elif isinstance(window, dict):
                parsed.append(UniversalMomentWindow.from_dict(window))
        return sorted(
            (window for window in parsed if window.end_seconds > window.start_seconds),
            key=lambda window: (window.start_seconds, window.end_seconds, window.window_id),
        )

    def _avg(self, values: Any) -> float:
        clean = [self._clamp(value) for value in values]
        if not clean:
            return 0.0
        return self._clamp(sum(clean) / len(clean))

    def _max(self, values: Any) -> float:
        return self._clamp(max((self._clamp(value) for value in values), default=0.0))

    def _clamp(self, value: object, fallback: float = 0.0) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = fallback
        return round(max(0.0, min(1.0, numeric)), 3)

    def _overlap_seconds(self, start_a: float, end_a: float, start_b: float, end_b: float) -> float:
        return max(0.0, min(end_a, end_b) - max(start_a, start_b))

    def _dedupe(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            value = str(value)
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
            if len(result) >= 40:
                break
        return result

    def _log(self, report: UniversalMomentDebugReport) -> None:
        print(
            "[UNIVERSAL-MOMENT-DEBUG] "
            f"segments={report.total_segments} "
            f"keep={report.segments_with_keep_signal} "
            f"remove={report.segments_with_remove_signal} "
            f"cut_risk={report.segments_with_cut_risk} "
            f"zoom_risk={report.segments_with_zoom_risk} "
            f"private={report.segments_with_private_risk} "
            f"avg={report.avg_segment_moment_score}"
        )
