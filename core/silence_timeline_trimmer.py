from __future__ import annotations

from dataclasses import dataclass, field

from models.highlight_candidate import HighlightCandidate
from models.timeline_segment import TimelineSegment


@dataclass
class SilenceTrimSummary:
    removed: int = 0
    trimmed_start: int = 0
    trimmed_end: int = 0
    skipped_middle: int = 0
    skipped_min_duration: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)


class SilenceTimelineTrimmer:
    def __init__(
        self,
        *,
        min_segment_duration: float = 2.0,
        edge_tolerance: float = 0.5,
        remove_overlap_ratio: float = 0.75,
    ) -> None:
        self.min_segment_duration = max(0.001, float(min_segment_duration))
        self.edge_tolerance = max(0.0, float(edge_tolerance))
        self.remove_overlap_ratio = max(0.0, min(1.0, float(remove_overlap_ratio)))

    def apply(
        self,
        segments: list[TimelineSegment],
        weak_zones: list[HighlightCandidate] | None,
    ) -> tuple[list[TimelineSegment], SilenceTrimSummary]:
        summary = SilenceTrimSummary(
            duration_before=round(sum(segment.duration for segment in segments), 3)
        )

        relevant_zones = [
            zone for zone in (weak_zones or [])
            if self._weak_kind(zone) in {"silence", "low_motion"}
            and zone.end_time > zone.start_time
        ]

        if not segments or not relevant_zones:
            summary.duration_after = summary.duration_before
            return segments, summary

        kept_segments: list[TimelineSegment] = []

        for segment in sorted(segments, key=lambda item: (item.start_time, item.end_time)):
            if self._trim_or_remove_segment(segment, relevant_zones, summary):
                kept_segments.append(segment)

        summary.duration_after = round(sum(segment.duration for segment in kept_segments), 3)
        return kept_segments, summary

    def _trim_or_remove_segment(
        self,
        segment: TimelineSegment,
        weak_zones: list[HighlightCandidate],
        summary: SilenceTrimSummary,
    ) -> bool:
        segment.start_time = round(max(0.0, segment.start_time), 3)
        if segment.end_time <= segment.start_time:
            segment.notes.append("silence_trim_skipped_invalid_duration")
            summary.skipped_min_duration += 1
            return True

        overlapping_zones = [
            zone for zone in weak_zones
            if self._overlap_seconds(
                segment.start_time,
                segment.end_time,
                zone.start_time,
                zone.end_time,
            ) > 0.0
        ]

        for zone in overlapping_zones:
            kind = self._weak_kind(zone)
            ratio = self._overlap_seconds(
                segment.start_time,
                segment.end_time,
                zone.start_time,
                zone.end_time,
            ) / max(0.001, segment.duration)
            if ratio >= self.remove_overlap_ratio:
                segment.notes.append(f"{kind}_removed_segment")
                summary.removed += 1
                self._add_example(
                    summary,
                    f"{segment.segment_id} removed {segment.start_time:.2f}-{segment.end_time:.2f}",
                )
                return False

        for zone in overlapping_zones:
            kind = self._weak_kind(zone)
            if self._is_start_edge(segment, zone):
                proposed_start = round(max(0.0, zone.end_time), 3)
                if segment.end_time - proposed_start >= self.min_segment_duration:
                    old_start = segment.start_time
                    segment.start_time = proposed_start
                    segment.notes.append(f"{kind}_trim_start={old_start:.3f}->{segment.start_time:.3f}")
                    segment.touch()
                    summary.trimmed_start += 1
                    self._add_example(
                        summary,
                        f"{segment.segment_id} start {old_start:.2f}->{segment.start_time:.2f}",
                    )
                else:
                    segment.notes.append(f"{kind}_skipped_min_duration")
                    summary.skipped_min_duration += 1

            if self._is_end_edge(segment, zone):
                proposed_end = round(zone.start_time, 3)
                if proposed_end - segment.start_time >= self.min_segment_duration:
                    old_end = segment.end_time
                    segment.end_time = proposed_end
                    segment.notes.append(f"{kind}_trim_end={old_end:.3f}->{segment.end_time:.3f}")
                    segment.touch()
                    summary.trimmed_end += 1
                    self._add_example(
                        summary,
                        f"{segment.segment_id} end {old_end:.2f}->{segment.end_time:.2f}",
                    )
                else:
                    segment.notes.append(f"{kind}_skipped_min_duration")
                    summary.skipped_min_duration += 1

            if self._is_middle_zone(segment, zone):
                note = f"{kind}_middle_skipped"
                if note not in segment.notes:
                    segment.notes.append(note)
                    summary.skipped_middle += 1

        segment.start_time = round(max(0.0, segment.start_time), 3)
        segment.end_time = round(segment.end_time, 3)
        if segment.end_time - segment.start_time < self.min_segment_duration:
            segment.notes.append("silence_trim_skipped_invalid_duration")
            summary.skipped_min_duration += 1

        return True

    def _is_start_edge(self, segment: TimelineSegment, zone: HighlightCandidate) -> bool:
        return (
            zone.start_time <= segment.start_time + self.edge_tolerance
            and segment.start_time < zone.end_time < segment.end_time
        )

    def _is_end_edge(self, segment: TimelineSegment, zone: HighlightCandidate) -> bool:
        return (
            zone.end_time >= segment.end_time - self.edge_tolerance
            and segment.start_time < zone.start_time < segment.end_time
        )

    def _is_middle_zone(self, segment: TimelineSegment, zone: HighlightCandidate) -> bool:
        return (
            segment.start_time + self.edge_tolerance < zone.start_time
            and zone.end_time < segment.end_time - self.edge_tolerance
        )

    def _weak_kind(self, zone: HighlightCandidate) -> str:
        text = " ".join([*zone.notes, *zone.signal_tags, zone.source or ""]).lower()
        if "low_motion" in text:
            return "low_motion"
        if "silence" in text:
            return "silence"
        return "weak"

    def _overlap_seconds(
        self,
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> float:
        return max(0.0, min(end_a, end_b) - max(start_a, start_b))

    def _add_example(self, summary: SilenceTrimSummary, example: str) -> None:
        if len(summary.examples) < 3:
            summary.examples.append(example)
