from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, floor

from models.timeline_segment import TimelineSegment


@dataclass
class StoryTimelineSummary:
    duplicates_removed: int = 0
    near_duplicates_removed: int = 0
    hook_segment_id: str | None = None
    peak_segment_ids: list[str] = field(default_factory=list)
    payoff_segment_id: str | None = None
    bridge_count: int = 0
    build_count: int = 0
    examples: list[str] = field(default_factory=list)


class StoryTimelineOrganizer:
    def __init__(
        self,
        *,
        overlap_duplicate_ratio: float = 0.50,
        near_duplicate_gap_seconds: float = 1.0,
    ) -> None:
        self.overlap_duplicate_ratio = max(0.0, min(1.0, float(overlap_duplicate_ratio)))
        self.near_duplicate_gap_seconds = max(0.0, float(near_duplicate_gap_seconds))

    def apply(
        self,
        segments: list[TimelineSegment],
    ) -> tuple[list[TimelineSegment], StoryTimelineSummary]:
        summary = StoryTimelineSummary()
        deduped = self._remove_overlap_duplicates(segments, summary)
        deduped = self._remove_near_duplicates(deduped, summary)
        deduped = sorted(deduped, key=lambda segment: (segment.start_time, segment.end_time))
        self._assign_story_roles(deduped, summary)
        return deduped, summary

    def _remove_overlap_duplicates(
        self,
        segments: list[TimelineSegment],
        summary: StoryTimelineSummary,
    ) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []

        for segment in sorted(
            segments,
            key=lambda item: (-item.selection_score, item.start_time, item.end_time),
        ):
            duplicate = next(
                (
                    existing for existing in kept
                    if self._overlap_ratio(
                        segment.start_time,
                        segment.end_time,
                        existing.start_time,
                        existing.end_time,
                    ) >= self.overlap_duplicate_ratio
                ),
                None,
            )
            if duplicate is not None:
                segment.notes.append(
                    f"duplicate_removed_overlap_with={duplicate.segment_id}"
                )
                summary.duplicates_removed += 1
                self._add_example(
                    summary,
                    f"removed duplicate {segment.segment_id} "
                    f"{segment.start_time:.2f}-{segment.end_time:.2f} "
                    f"kept {duplicate.segment_id}",
                )
                continue

            kept.append(segment)

        return sorted(kept, key=lambda item: (item.start_time, item.end_time))

    def _remove_near_duplicates(
        self,
        segments: list[TimelineSegment],
        summary: StoryTimelineSummary,
    ) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []

        for segment in sorted(segments, key=lambda item: (item.start_time, item.end_time)):
            if not kept:
                kept.append(segment)
                continue

            previous = kept[-1]
            gap = segment.start_time - previous.end_time
            same_kind = self._candidate_kind(segment) == self._candidate_kind(previous)
            near_duplicate = 0.0 < gap < self.near_duplicate_gap_seconds and same_kind

            if not near_duplicate:
                kept.append(segment)
                continue

            winner, loser = (
                (segment, previous)
                if segment.selection_score > previous.selection_score
                else (previous, segment)
            )
            loser.notes.append(f"near_duplicate_removed_with={winner.segment_id}")
            summary.near_duplicates_removed += 1
            self._add_example(
                summary,
                f"removed near duplicate {loser.segment_id} "
                f"gap={gap:.2f}s kept {winner.segment_id}",
            )

            if winner is segment:
                kept[-1] = segment

        return kept

    def _assign_story_roles(
        self,
        segments: list[TimelineSegment],
        summary: StoryTimelineSummary,
    ) -> None:
        if not segments:
            return

        for segment in segments:
            segment.segment_role = "bridge"

        segments[0].segment_role = "hook"
        segments[0].notes.append("story_role=hook")
        summary.hook_segment_id = segments[0].segment_id

        if len(segments) == 1:
            summary.bridge_count = 0
            return

        segments[-1].segment_role = "payoff"
        segments[-1].notes.append("story_role=payoff")
        summary.payoff_segment_id = segments[-1].segment_id

        middle = segments[1:-1]
        if middle:
            peak_count = max(1, ceil(len(segments) * 0.20))
            peak_count = min(peak_count, len(middle))
            first_peak_candidate_index = max(1, floor(len(segments) * 0.35))
            eligible_middle = [
                segment for index, segment in enumerate(segments)
                if 0 < index < len(segments) - 1
                and index >= first_peak_candidate_index
            ] or middle
            peak_segments = sorted(
                eligible_middle,
                key=lambda segment: (-segment.selection_score, segment.start_time),
            )[:peak_count]
            peak_ids = {segment.segment_id for segment in peak_segments}
            first_peak_index = min(
                (
                    index for index, segment in enumerate(segments)
                    if segment.segment_id in peak_ids
                ),
                default=len(segments),
            )

            for index, segment in enumerate(segments[1:-1], start=1):
                if segment.segment_id in peak_ids:
                    segment.segment_role = "peak"
                    segment.notes.append("story_role=peak")
                    summary.peak_segment_ids.append(segment.segment_id)
                elif index < first_peak_index:
                    segment.segment_role = "build"
                    segment.notes.append("story_role=build")
                else:
                    segment.segment_role = "bridge"
                    segment.notes.append("story_role=bridge")

        summary.bridge_count = sum(
            segment.segment_role == "bridge" for segment in segments
        )
        summary.build_count = sum(
            segment.segment_role == "build" for segment in segments
        )

        for segment in segments:
            segment.touch()

    def _candidate_kind(self, segment: TimelineSegment) -> str:
        for note in segment.notes:
            if note.startswith("candidate_kind="):
                return note.split("=", 1)[1]
        return "unknown"

    def _overlap_ratio(
        self,
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> float:
        overlap_start = max(start_a, start_b)
        overlap_end = min(end_a, end_b)
        if overlap_end <= overlap_start:
            return 0.0
        overlap = overlap_end - overlap_start
        shorter = max(0.001, min(end_a - start_a, end_b - start_b))
        return overlap / shorter

    def _add_example(self, summary: StoryTimelineSummary, example: str) -> None:
        if len(summary.examples) < 3:
            summary.examples.append(example)
