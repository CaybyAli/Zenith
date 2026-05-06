from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.timeline_segment import TimelineSegment
from models.universal_moment_result import UniversalMomentResult, UniversalMomentWindow


MIN_SEGMENT_DURATION_SECONDS = 2.5
MAX_CONTEXT_EXPAND_SECONDS = 1.0
FIRST_CONTEXT_PROTECTION_SECONDS = 30.0


@dataclass
class UniversalMomentTimelineAssistSummary:
    keep_protected: int = 0
    remove_supported: int = 0
    pre_context_protected: int = 0
    post_context_protected: int = 0
    cut_risk_protected: int = 0
    zoom_risk_marked: int = 0
    boring_trim_suggested: int = 0
    private_menu_supported: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)

    def add_example(self, text: str) -> None:
        if len(self.examples) < 8:
            self.examples.append(text)

    def to_dict(self) -> dict[str, Any]:
        return {
            "keep_protected": self.keep_protected,
            "remove_supported": self.remove_supported,
            "pre_context_protected": self.pre_context_protected,
            "post_context_protected": self.post_context_protected,
            "cut_risk_protected": self.cut_risk_protected,
            "zoom_risk_marked": self.zoom_risk_marked,
            "boring_trim_suggested": self.boring_trim_suggested,
            "private_menu_supported": self.private_menu_supported,
            "duration_before": self.duration_before,
            "duration_after": self.duration_after,
            "examples": list(self.examples),
        }


class UniversalMomentTimelineAssist:
    engine = "universal-moment-timeline-assist-v1"

    def apply(
        self,
        selected_segments: list[TimelineSegment],
        *,
        universal_moment_result=None,
    ) -> tuple[list[TimelineSegment], UniversalMomentTimelineAssistSummary]:
        ordered = sorted(
            (segment for segment in selected_segments if segment.end_time > segment.start_time),
            key=lambda segment: (segment.start_time, segment.end_time, segment.segment_id),
        )
        summary = UniversalMomentTimelineAssistSummary(
            duration_before=round(sum(segment.duration for segment in ordered), 3)
        )
        windows = self._windows(universal_moment_result)

        if not ordered or not windows:
            summary.duration_after = round(sum(segment.duration for segment in ordered), 3)
            self._log(summary)
            return ordered, summary

        for index, segment in enumerate(ordered):
            previous_segment = ordered[index - 1] if index > 0 else None
            next_segment = ordered[index + 1] if index + 1 < len(ordered) else None

            overlapping = [
                window
                for window in windows
                if _overlap_seconds(
                    segment.start_time,
                    segment.end_time,
                    window.start_seconds,
                    window.end_seconds,
                )
                > 0.0
            ]
            nearby = [
                window
                for window in windows
                if window.start_seconds <= segment.end_time + MAX_CONTEXT_EXPAND_SECONDS
                and window.end_seconds >= max(0.0, segment.start_time - MAX_CONTEXT_EXPAND_SECONDS)
            ]

            if self._has_keep_protection(overlapping):
                if self._add_note(segment, "universal_keep_protected"):
                    summary.keep_protected += 1
                    summary.add_example(f"{segment.segment_id} keep_protected")

            if self._has_cut_risk(overlapping):
                if self._add_note(segment, "universal_cut_risk_protected"):
                    summary.cut_risk_protected += 1
                    summary.add_example(f"{segment.segment_id} cut_risk")

            if self._has_zoom_risk(overlapping):
                if self._add_note(segment, "universal_zoom_risk"):
                    summary.zoom_risk_marked += 1
                    summary.add_example(f"{segment.segment_id} zoom_risk")

            if self._has_remove_support(overlapping):
                changed = self._add_note(segment, "universal_remove_supported")
                self._add_note(segment, "universal_boring_trim_suggested")
                if changed:
                    summary.remove_supported += 1
                    summary.boring_trim_suggested += 1
                    summary.add_example(f"{segment.segment_id} remove_supported")

            if self._has_private_menu_support(overlapping):
                if self._add_note(segment, "universal_private_menu_supported"):
                    summary.private_menu_supported += 1
                    summary.add_example(f"{segment.segment_id} private_menu")

            self._protect_pre_context(segment, nearby, previous_segment, summary)
            self._protect_post_context(segment, nearby, next_segment, summary)

        ordered = self._final_invariants(ordered)
        summary.duration_after = round(sum(segment.duration for segment in ordered), 3)
        self._log(summary)
        return ordered, summary

    def _protect_pre_context(
        self,
        segment: TimelineSegment,
        windows: list[UniversalMomentWindow],
        previous_segment: TimelineSegment | None,
        summary: UniversalMomentTimelineAssistSummary,
    ) -> None:
        candidates = [
            window
            for window in windows
            if window.needs_pre_context
            and (window.pre_action_score >= 0.60 or window.tension_score >= 0.60)
            and window.start_seconds < segment.start_time
        ]
        if not candidates:
            return

        earliest = min(window.start_seconds for window in candidates)
        proposed_start = max(0.0, segment.start_time - MAX_CONTEXT_EXPAND_SECONDS, earliest)
        if previous_segment is not None:
            proposed_start = max(proposed_start, previous_segment.end_time)
        proposed_start = round(min(segment.start_time, proposed_start), 3)
        if proposed_start >= segment.start_time:
            return
        if segment.end_time - proposed_start < MIN_SEGMENT_DURATION_SECONDS:
            return

        old_start = segment.start_time
        segment.start_time = proposed_start
        self._add_note(segment, f"universal_pre_context={old_start:.3f}->{proposed_start:.3f}")
        if old_start <= FIRST_CONTEXT_PROTECTION_SECONDS:
            self._add_note(segment, "universal_first_30s_protected")
        segment.touch()
        summary.pre_context_protected += 1
        summary.add_example(f"{segment.segment_id} pre {old_start:.2f}->{proposed_start:.2f}")

    def _protect_post_context(
        self,
        segment: TimelineSegment,
        windows: list[UniversalMomentWindow],
        next_segment: TimelineSegment | None,
        summary: UniversalMomentTimelineAssistSummary,
    ) -> None:
        candidates = [
            window
            for window in windows
            if window.needs_post_context
            and (window.post_peak_reaction_score >= 0.60 or window.reaction_score >= 0.60)
            and window.end_seconds > segment.end_time
        ]
        if not candidates:
            return

        latest = max(window.end_seconds for window in candidates)
        proposed_end = min(segment.end_time + MAX_CONTEXT_EXPAND_SECONDS, latest)
        if next_segment is not None:
            proposed_end = min(proposed_end, next_segment.start_time)
        proposed_end = round(max(segment.end_time, proposed_end), 3)
        if proposed_end <= segment.end_time:
            return
        if proposed_end - segment.start_time < MIN_SEGMENT_DURATION_SECONDS:
            return

        old_end = segment.end_time
        segment.end_time = proposed_end
        self._add_note(segment, f"universal_post_context={old_end:.3f}->{proposed_end:.3f}")
        segment.touch()
        summary.post_context_protected += 1
        summary.add_example(f"{segment.segment_id} post {old_end:.2f}->{proposed_end:.2f}")

    def _has_keep_protection(self, windows: list[UniversalMomentWindow]) -> bool:
        return any(
            (
                window.should_keep
                and (
                    window.peak_score >= 0.65
                    or window.tension_score >= 0.60
                    or window.post_peak_reaction_score >= 0.60
                )
            )
            or window.peak_score >= 0.65
            or window.tension_score >= 0.60
            or window.post_peak_reaction_score >= 0.60
            for window in windows
        )

    def _has_cut_risk(self, windows: list[UniversalMomentWindow]) -> bool:
        return any(
            window.cut_risk_score >= 0.70
            and (window.speech_boundary_risk or window.action_context_risk)
            for window in windows
        )

    def _has_zoom_risk(self, windows: list[UniversalMomentWindow]) -> bool:
        return any(
            window.zoom_risk_score >= 0.70 or window.zoom_boundary_risk
            for window in windows
        )

    def _has_remove_support(self, windows: list[UniversalMomentWindow]) -> bool:
        return any(
            window.should_remove
            and window.boring_score >= 0.80
            and (window.menu_wait_score >= 0.70 or window.dead_time_score >= 0.70)
            and window.peak_score < 0.30
            and window.speech_score < 0.30
            for window in windows
        )

    def _has_private_menu_support(self, windows: list[UniversalMomentWindow]) -> bool:
        return any(
            window.moment_type == "private_menu_talk"
            and window.private_talk_score >= 0.75
            and window.menu_private_risk
            for window in windows
        )

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

    def _final_invariants(self, segments: list[TimelineSegment]) -> list[TimelineSegment]:
        ordered = sorted(
            (segment for segment in segments if segment.end_time > segment.start_time),
            key=lambda segment: (segment.start_time, segment.end_time, segment.segment_id),
        )
        clean: list[TimelineSegment] = []
        for segment in ordered:
            if segment.duration < MIN_SEGMENT_DURATION_SECONDS:
                self._add_note(segment, "universal_invariant_preexisting_short")
                clean.append(segment)
                continue
            if clean and segment.start_time < clean[-1].end_time:
                proposed_start = round(clean[-1].end_time, 3)
                if segment.end_time - proposed_start >= MIN_SEGMENT_DURATION_SECONDS:
                    segment.start_time = proposed_start
                    self._add_note(segment, "universal_invariant_overlap_clamped")
                    segment.touch()
                else:
                    self._add_note(segment, "universal_invariant_overlap_unmodified")
            clean.append(segment)
        return clean

    def _add_note(self, segment: TimelineSegment, note: str) -> bool:
        if note in segment.notes:
            return False
        segment.notes.append(note)
        segment.touch()
        return True

    def _log(self, summary: UniversalMomentTimelineAssistSummary) -> None:
        print(
            "[TIMELINE-UNIVERSAL-ASSIST] "
            f"keep={summary.keep_protected} "
            f"remove_supported={summary.remove_supported} "
            f"pre={summary.pre_context_protected} "
            f"post={summary.post_context_protected} "
            f"cut_risk={summary.cut_risk_protected} "
            f"zoom_risk={summary.zoom_risk_marked} "
            f"private={summary.private_menu_supported} "
            f"duration_before={summary.duration_before:.3f}s "
            f"duration_after={summary.duration_after:.3f}s"
        )


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))
