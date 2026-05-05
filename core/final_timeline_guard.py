from __future__ import annotations

from dataclasses import dataclass, field

from models.timeline_segment import TimelineSegment


MIN_SEGMENT_DURATION = 2.0
MIN_GAP_SECONDS = 0.15
OVERLAP_REMOVE_RATIO = 0.35
NEAR_DUPLICATE_GAP = 0.5


@dataclass
class FinalTimelineGuardSummary:
    backjumps_fixed: int = 0
    overlaps_removed: int = 0
    near_duplicates_removed: int = 0
    trimmed: int = 0
    removed: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)


class FinalTimelineGuard:
    def __init__(
        self,
        *,
        min_segment_duration: float = MIN_SEGMENT_DURATION,
        min_gap_seconds: float = MIN_GAP_SECONDS,
        overlap_remove_ratio: float = OVERLAP_REMOVE_RATIO,
        near_duplicate_gap: float = NEAR_DUPLICATE_GAP,
    ) -> None:
        self.min_segment_duration = max(0.001, float(min_segment_duration))
        self.min_gap_seconds = max(0.0, float(min_gap_seconds))
        self.overlap_remove_ratio = max(0.0, min(1.0, float(overlap_remove_ratio)))
        self.near_duplicate_gap = max(0.0, float(near_duplicate_gap))

    def apply(
        self,
        segments: list[TimelineSegment],
    ) -> tuple[list[TimelineSegment], FinalTimelineGuardSummary]:
        summary = FinalTimelineGuardSummary(
            duration_before=round(sum(segment.duration for segment in segments), 3)
        )
        pending = sorted(
            (segment for segment in segments if segment.end_time > segment.start_time),
            key=lambda segment: (segment.start_time, segment.end_time),
        )
        kept: list[TimelineSegment] = []

        for segment in pending:
            segment.start_time = round(max(0.0, segment.start_time), 3)
            segment.end_time = round(segment.end_time, 3)
            if segment.end_time - segment.start_time < self.min_segment_duration:
                segment.notes.append("final_guard_removed_too_short")
                summary.removed += 1
                self._add_example(summary, f"removed short {self._range(segment)}")
                continue

            while kept:
                previous = kept[-1]
                overlap_ratio = self._overlap_ratio(previous, segment)
                if overlap_ratio >= self.overlap_remove_ratio:
                    if segment.selection_score > previous.selection_score:
                        removed_previous = kept.pop()
                        removed_previous.notes.append(
                            f"final_guard_overlap_removed_by={segment.segment_id}"
                        )
                        summary.overlaps_removed += 1
                        summary.removed += 1
                        self._add_example(
                            summary,
                            f"removed overlap {self._range(removed_previous)} kept {segment.segment_id}",
                        )
                        continue

                    segment.notes.append(
                        f"final_guard_overlap_removed_by={previous.segment_id}"
                    )
                    summary.overlaps_removed += 1
                    summary.removed += 1
                    self._add_example(
                        summary,
                        f"removed overlap {self._range(segment)} kept {previous.segment_id}",
                    )
                    segment = None
                    break

                if self._is_near_duplicate(previous, segment):
                    if segment.selection_score > previous.selection_score:
                        removed_previous = kept.pop()
                        removed_previous.notes.append(
                            f"final_guard_near_duplicate_removed_by={segment.segment_id}"
                        )
                        summary.near_duplicates_removed += 1
                        summary.removed += 1
                        self._add_example(
                            summary,
                            f"removed near duplicate {removed_previous.segment_id} kept {segment.segment_id}",
                        )
                        continue

                    segment.notes.append(
                        f"final_guard_near_duplicate_removed_by={previous.segment_id}"
                    )
                    summary.near_duplicates_removed += 1
                    summary.removed += 1
                    self._add_example(
                        summary,
                        f"removed near duplicate {segment.segment_id} kept {previous.segment_id}",
                    )
                    segment = None
                    break

                required_start = round(previous.end_time + self.min_gap_seconds, 3)
                if segment.start_time < required_start:
                    old_start = segment.start_time
                    if segment.end_time - required_start >= self.min_segment_duration:
                        segment.start_time = required_start
                        segment.notes.append(
                            f"final_guard_backjump_trim={old_start:.3f}->{segment.start_time:.3f}"
                        )
                        summary.backjumps_fixed += 1
                        summary.trimmed += 1
                        self._add_example(
                            summary,
                            f"trimmed backjump {segment.segment_id} {old_start:.2f}->{segment.start_time:.2f}",
                        )
                        break

                    segment.notes.append(
                        f"final_guard_backjump_removed_after={previous.segment_id}"
                    )
                    summary.backjumps_fixed += 1
                    summary.removed += 1
                    self._add_example(
                        summary,
                        f"removed backjump {self._range(segment)} after {previous.segment_id}",
                    )
                    segment = None
                    break

                break

            if segment is None:
                continue

            segment.start_time = round(max(0.0, segment.start_time), 3)
            if segment.end_time - segment.start_time < self.min_segment_duration:
                segment.notes.append("final_guard_removed_too_short_after_trim")
                summary.removed += 1
                continue
            segment.touch()
            kept.append(segment)

        self._assign_final_roles(kept)
        summary.duration_after = round(sum(segment.duration for segment in kept), 3)
        return kept, summary

    def _assign_final_roles(self, segments: list[TimelineSegment]) -> None:
        if not segments:
            return
        for segment in segments:
            if segment.segment_role in {"hook", "payoff"}:
                segment.segment_role = "bridge"
        segments[0].segment_role = "hook"
        if len(segments) > 1:
            segments[-1].segment_role = "payoff"
        if not any(segment.segment_role == "peak" for segment in segments) and len(segments) > 2:
            peak = max(segments[1:-1], key=lambda segment: segment.selection_score)
            peak.segment_role = "peak"
        for segment in segments:
            segment.touch()

    def _is_near_duplicate(
        self,
        previous: TimelineSegment,
        current: TimelineSegment,
    ) -> bool:
        gap = current.start_time - previous.end_time
        if not (0.0 < gap < self.near_duplicate_gap):
            return False
        same_kind = self._candidate_kind(previous) == self._candidate_kind(current)
        similar_duration = abs(previous.duration - current.duration) <= 2.0
        similar_score = abs(previous.selection_score - current.selection_score) <= 0.08
        return same_kind or (similar_duration and similar_score)

    def _candidate_kind(self, segment: TimelineSegment) -> str:
        for note in segment.notes:
            if note.startswith("candidate_kind="):
                return note.split("=", 1)[1]
        return "unknown"

    def _overlap_ratio(self, left: TimelineSegment, right: TimelineSegment) -> float:
        overlap = max(0.0, min(left.end_time, right.end_time) - max(left.start_time, right.start_time))
        if overlap <= 0.0:
            return 0.0
        shorter = max(0.001, min(left.duration, right.duration))
        return overlap / shorter

    def _range(self, segment: TimelineSegment) -> str:
        return f"{segment.segment_id} {segment.start_time:.2f}-{segment.end_time:.2f}"

    def _add_example(self, summary: FinalTimelineGuardSummary, example: str) -> None:
        if len(summary.examples) < 3:
            summary.examples.append(example)
