from __future__ import annotations

from dataclasses import dataclass, field

from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


MAX_START_SHIFT_SECONDS = 2.5
MAX_END_SHIFT_SECONDS = 3.0
MIN_SEGMENT_DURATION = 2.0
MIN_GAP_SECONDS = 0.15


@dataclass
class FinalCutSafetySummary:
    adjusted_start: int = 0
    adjusted_end: int = 0
    skipped_start: int = 0
    skipped_end: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)

    @property
    def skipped(self) -> int:
        return self.skipped_start + self.skipped_end


class FinalCutSafetyGuard:
    def __init__(
        self,
        *,
        max_start_shift_seconds: float = MAX_START_SHIFT_SECONDS,
        max_end_shift_seconds: float = MAX_END_SHIFT_SECONDS,
        min_segment_duration: float = MIN_SEGMENT_DURATION,
        min_gap_seconds: float = MIN_GAP_SECONDS,
    ) -> None:
        self.max_start_shift_seconds = max(0.0, float(max_start_shift_seconds))
        self.max_end_shift_seconds = max(0.0, float(max_end_shift_seconds))
        self.min_segment_duration = max(0.001, float(min_segment_duration))
        self.min_gap_seconds = max(0.0, float(min_gap_seconds))

    def apply(
        self,
        segments: list[TimelineSegment],
        transcript_result: TranscriptResult | None,
    ) -> tuple[list[TimelineSegment], FinalCutSafetySummary]:
        ordered = sorted(
            (segment for segment in segments if segment.end_time > segment.start_time),
            key=lambda segment: (segment.start_time, segment.end_time, segment.segment_id),
        )
        summary = FinalCutSafetySummary(
            duration_before=round(sum(segment.duration for segment in ordered), 3)
        )

        if transcript_result is None or not transcript_result.segments:
            summary.duration_after = summary.duration_before
            return ordered, summary

        transcript_segments = sorted(
            (
                segment
                for segment in transcript_result.segments
                if segment.end_seconds > segment.start_seconds
            ),
            key=lambda segment: (segment.start_seconds, segment.end_seconds),
        )
        if not transcript_segments:
            summary.duration_after = summary.duration_before
            return ordered, summary

        for index, segment in enumerate(ordered):
            previous_segment = ordered[index - 1] if index > 0 else None
            next_segment = ordered[index + 1] if index + 1 < len(ordered) else None
            self._adjust_start(segment, previous_segment, transcript_segments, summary)
            self._adjust_end(segment, next_segment, transcript_segments, summary)
            segment.start_time = round(max(0.0, segment.start_time), 3)
            segment.end_time = round(segment.end_time, 3)
            segment.touch()

        self._assert_safe_order(ordered)
        summary.duration_after = round(sum(segment.duration for segment in ordered), 3)
        return ordered, summary

    def _adjust_start(
        self,
        segment: TimelineSegment,
        previous_segment: TimelineSegment | None,
        transcript_segments: list[TranscriptSegment],
        summary: FinalCutSafetySummary,
    ) -> None:
        transcript_segment = self._containing_transcript(segment.start_time, transcript_segments)
        if transcript_segment is None:
            return

        old_start = segment.start_time
        preferred_start = round(max(0.0, transcript_segment.start_seconds), 3)
        previous_limit = (
            round(previous_segment.end_time + self.min_gap_seconds, 3)
            if previous_segment is not None
            else 0.0
        )

        if (
            abs(old_start - preferred_start) <= self.max_start_shift_seconds
            and preferred_start >= previous_limit
            and segment.end_time - preferred_start >= self.min_segment_duration
        ):
            segment.start_time = preferred_start
            segment.notes.append(
                f"final_cut_safety_start={old_start:.3f}->{segment.start_time:.3f}"
            )
            summary.adjusted_start += 1
            self._add_example(
                summary,
                f"{segment.segment_id} start {old_start:.2f}->{segment.start_time:.2f}",
            )
            return

        segment.notes.append("final_cut_safety_start_skipped")
        summary.skipped_start += 1

    def _adjust_end(
        self,
        segment: TimelineSegment,
        next_segment: TimelineSegment | None,
        transcript_segments: list[TranscriptSegment],
        summary: FinalCutSafetySummary,
    ) -> None:
        transcript_segment = self._containing_transcript(segment.end_time, transcript_segments)
        if transcript_segment is None:
            return

        old_end = segment.end_time
        preferred_end = round(transcript_segment.end_seconds, 3)
        next_limit = (
            round(next_segment.start_time - self.min_gap_seconds, 3)
            if next_segment is not None
            else None
        )

        if (
            abs(preferred_end - old_end) <= self.max_end_shift_seconds
            and preferred_end - segment.start_time >= self.min_segment_duration
            and (next_limit is None or preferred_end <= next_limit)
        ):
            segment.end_time = preferred_end
            segment.notes.append(
                f"final_cut_safety_end={old_end:.3f}->{segment.end_time:.3f}"
            )
            summary.adjusted_end += 1
            self._add_example(
                summary,
                f"{segment.segment_id} end {old_end:.2f}->{segment.end_time:.2f}",
            )
            return

        fallback_end = round(transcript_segment.start_seconds, 3)
        if (
            fallback_end > segment.start_time
            and abs(old_end - fallback_end) <= self.max_end_shift_seconds
            and fallback_end - segment.start_time >= self.min_segment_duration
            and (next_limit is None or fallback_end <= next_limit)
        ):
            segment.end_time = fallback_end
            segment.notes.append(
                f"final_cut_safety_end_fallback={old_end:.3f}->{segment.end_time:.3f}"
            )
            summary.adjusted_end += 1
            summary.skipped_end += 1
            self._add_example(
                summary,
                f"{segment.segment_id} end fallback {old_end:.2f}->{segment.end_time:.2f}",
            )
            return

        segment.notes.append("final_cut_safety_end_skipped")
        summary.skipped_end += 1

    def _containing_transcript(
        self,
        time_seconds: float,
        transcript_segments: list[TranscriptSegment],
    ) -> TranscriptSegment | None:
        for transcript_segment in transcript_segments:
            if transcript_segment.start_seconds < time_seconds < transcript_segment.end_seconds:
                return transcript_segment
        return None

    def _assert_safe_order(self, segments: list[TimelineSegment]) -> None:
        previous_end: float | None = None
        seen_ids: set[str] = set()
        for segment in segments:
            if segment.segment_id in seen_ids:
                raise ValueError(f"Duplicate timeline segment id after cut safety: {segment.segment_id}")
            seen_ids.add(segment.segment_id)
            if segment.start_time < 0.0:
                raise ValueError(f"Negative timeline segment start after cut safety: {segment.segment_id}")
            if segment.end_time <= segment.start_time:
                raise ValueError(f"Invalid timeline segment duration after cut safety: {segment.segment_id}")
            if segment.end_time - segment.start_time < self.min_segment_duration:
                raise ValueError(f"Too short timeline segment after cut safety: {segment.segment_id}")
            if previous_end is not None and segment.start_time < previous_end:
                raise ValueError(f"Timeline overlap after cut safety: {segment.segment_id}")
            previous_end = segment.end_time

    def _add_example(self, summary: FinalCutSafetySummary, example: str) -> None:
        if len(summary.examples) < 5:
            summary.examples.append(example)
