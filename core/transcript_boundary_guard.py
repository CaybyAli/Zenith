from __future__ import annotations

from dataclasses import dataclass, field

from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


@dataclass
class BoundaryAdjustmentSummary:
    adjusted_start: int = 0
    adjusted_end: int = 0
    skipped: int = 0
    examples: list[str] = field(default_factory=list)


class TranscriptBoundaryGuard:
    def __init__(
        self,
        *,
        max_shift_seconds: float = 2.0,
        min_segment_duration: float = 2.0,
    ) -> None:
        self.max_shift_seconds = max(0.0, float(max_shift_seconds))
        self.min_segment_duration = max(0.001, float(min_segment_duration))

    def apply(
        self,
        segments: list[TimelineSegment],
        transcript_result: TranscriptResult | None,
    ) -> BoundaryAdjustmentSummary:
        summary = BoundaryAdjustmentSummary()

        if transcript_result is None or not transcript_result.segments:
            return summary

        transcript_segments = sorted(
            transcript_result.segments,
            key=lambda segment: (segment.start_seconds, segment.end_seconds),
        )

        for segment in segments:
            self._adjust_segment(segment, transcript_segments, summary)

        return summary

    def _adjust_segment(
        self,
        segment: TimelineSegment,
        transcript_segments: list[TranscriptSegment],
        summary: BoundaryAdjustmentSummary,
    ) -> None:
        original_start = segment.start_time
        original_end = segment.end_time

        start_transcript = self._containing_transcript(segment.start_time, transcript_segments)
        if start_transcript is not None:
            proposed_start = max(0.0, start_transcript.start_seconds)
            shift = segment.start_time - proposed_start
            if shift <= self.max_shift_seconds and original_end - proposed_start >= self.min_segment_duration:
                segment.start_time = round(proposed_start, 3)
                segment.notes.append(
                    f"boundary_adjusted_start={original_start:.3f}->{segment.start_time:.3f}"
                )
                summary.adjusted_start += 1
                self._add_example(
                    summary,
                    f"{segment.segment_id} start {original_start:.2f}->{segment.start_time:.2f}",
                )
            else:
                segment.notes.append("boundary_skipped_start_no_safe_point")
                summary.skipped += 1

        end_transcript = self._containing_transcript(segment.end_time, transcript_segments)
        if end_transcript is not None:
            proposed_end = end_transcript.end_seconds
            shift = proposed_end - segment.end_time
            if shift <= self.max_shift_seconds and proposed_end - segment.start_time >= self.min_segment_duration:
                segment.end_time = round(proposed_end, 3)
                segment.notes.append(
                    f"boundary_adjusted_end={original_end:.3f}->{segment.end_time:.3f}"
                )
                summary.adjusted_end += 1
                self._add_example(
                    summary,
                    f"{segment.segment_id} end {original_end:.2f}->{segment.end_time:.2f}",
                )
            else:
                segment.notes.append("boundary_skipped_end_no_safe_point")
                summary.skipped += 1

        segment.start_time = round(max(0.0, segment.start_time), 3)
        if segment.end_time <= segment.start_time:
            segment.start_time = round(max(0.0, original_start), 3)
            segment.end_time = round(max(segment.start_time + self.min_segment_duration, original_end), 3)
            segment.notes.append("boundary_skipped_invalid_duration")
            summary.skipped += 1

    def _containing_transcript(
        self,
        time_seconds: float,
        transcript_segments: list[TranscriptSegment],
    ) -> TranscriptSegment | None:
        for transcript_segment in transcript_segments:
            if transcript_segment.start_seconds < time_seconds < transcript_segment.end_seconds:
                return transcript_segment
        return None

    def _add_example(self, summary: BoundaryAdjustmentSummary, example: str) -> None:
        if len(summary.examples) < 3:
            summary.examples.append(example)
