from __future__ import annotations

from dataclasses import dataclass, field

from models.highlight_candidate import HighlightCandidate
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


MIN_VISIBLE_SEGMENT_DURATION = 2.5
PEAK_MICRO_ALLOWED_SCORE = 0.90
SPEECH_PRE_ROLL_SECONDS = 0.25
SPEECH_POST_ROLL_SECONDS = 0.35
SPEECH_NEAR_EDGE_SECONDS = 0.2
MIN_EDGE_SILENCE_TO_TRIM = 0.7
MAX_EDGE_TRIM_SECONDS = 2.5
MIN_GAP_SECONDS = 0.15


@dataclass
class FinalTimelineQualitySummary:
    micro_removed: int = 0
    peak_micro_allowed: int = 0
    speech_start_adjusted: int = 0
    speech_end_adjusted: int = 0
    silence_edge_trimmed: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)

    @property
    def speech_adjusted(self) -> int:
        return self.speech_start_adjusted + self.speech_end_adjusted


class FinalTimelineQualityGuard:
    def __init__(
        self,
        *,
        min_visible_segment_duration: float = MIN_VISIBLE_SEGMENT_DURATION,
        peak_micro_allowed_score: float = PEAK_MICRO_ALLOWED_SCORE,
        speech_pre_roll_seconds: float = SPEECH_PRE_ROLL_SECONDS,
        speech_post_roll_seconds: float = SPEECH_POST_ROLL_SECONDS,
        min_edge_silence_to_trim: float = MIN_EDGE_SILENCE_TO_TRIM,
        max_edge_trim_seconds: float = MAX_EDGE_TRIM_SECONDS,
        min_gap_seconds: float = MIN_GAP_SECONDS,
    ) -> None:
        self.min_visible_segment_duration = max(0.001, float(min_visible_segment_duration))
        self.peak_micro_allowed_score = max(0.0, min(1.0, float(peak_micro_allowed_score)))
        self.speech_pre_roll_seconds = max(0.0, float(speech_pre_roll_seconds))
        self.speech_post_roll_seconds = max(0.0, float(speech_post_roll_seconds))
        self.min_edge_silence_to_trim = max(0.0, float(min_edge_silence_to_trim))
        self.max_edge_trim_seconds = max(0.0, float(max_edge_trim_seconds))
        self.min_gap_seconds = max(0.0, float(min_gap_seconds))

    def apply(
        self,
        segments: list[TimelineSegment],
        transcript_result: TranscriptResult | None = None,
        weak_zones: list[HighlightCandidate] | None = None,
    ) -> tuple[list[TimelineSegment], FinalTimelineQualitySummary]:
        ordered = sorted(
            (segment for segment in segments if segment.end_time > segment.start_time),
            key=lambda segment: (segment.start_time, segment.end_time, segment.segment_id),
        )
        summary = FinalTimelineQualitySummary(
            duration_before=round(sum(segment.duration for segment in ordered), 3)
        )
        transcripts = self._transcript_segments(transcript_result)
        edge_zones = self._edge_zones(weak_zones)

        for index, segment in enumerate(ordered):
            previous = ordered[index - 1] if index > 0 else None
            next_segment = ordered[index + 1] if index + 1 < len(ordered) else None

            self._trim_silence_edges(segment, edge_zones, transcripts, summary)
            self._apply_speech_padding(segment, previous, next_segment, transcripts, summary)

            segment.start_time = round(max(0.0, segment.start_time), 3)
            segment.end_time = round(segment.end_time, 3)
            segment.touch()

        kept: list[TimelineSegment] = []
        for segment in ordered:
            if segment.duration < self.min_visible_segment_duration:
                if self._is_allowed_peak_micro(segment):
                    segment.notes.append("quality_peak_micro_allowed")
                    summary.peak_micro_allowed += 1
                    kept.append(segment)
                    continue

                segment.notes.append("quality_micro_removed")
                summary.micro_removed += 1
                self._add_example(summary, f"removed micro {self._range(segment)}")
                continue

            kept.append(segment)

        kept = self._drop_overlaps_after_removal(kept, summary)
        self._assign_final_roles(kept)
        self._assert_invariants(kept)
        summary.duration_after = round(sum(segment.duration for segment in kept), 3)
        return kept, summary

    def _trim_silence_edges(
        self,
        segment: TimelineSegment,
        weak_zones: list[HighlightCandidate],
        transcripts: list[TranscriptSegment],
        summary: FinalTimelineQualitySummary,
    ) -> None:
        if not weak_zones:
            return

        for zone in weak_zones:
            start_overlap = max(0.0, min(zone.end_time, segment.end_time) - segment.start_time)
            if zone.start_time <= segment.start_time + 0.1 and start_overlap >= self.min_edge_silence_to_trim:
                proposed_start = round(min(zone.end_time, segment.start_time + self.max_edge_trim_seconds), 3)
                if (
                    proposed_start > segment.start_time
                    and segment.end_time - proposed_start >= self.min_visible_segment_duration
                    and not self._range_has_speech(segment.start_time, proposed_start, transcripts)
                ):
                    old_start = segment.start_time
                    segment.start_time = proposed_start
                    segment.notes.append(
                        f"quality_silence_edge_trim_start={old_start:.3f}->{segment.start_time:.3f}"
                    )
                    summary.silence_edge_trimmed += 1
                    self._add_example(summary, f"{segment.segment_id} silence start {old_start:.2f}->{segment.start_time:.2f}")

            end_overlap = max(0.0, segment.end_time - max(zone.start_time, segment.start_time))
            if zone.end_time >= segment.end_time - 0.1 and end_overlap >= self.min_edge_silence_to_trim:
                proposed_end = round(max(zone.start_time, segment.end_time - self.max_edge_trim_seconds), 3)
                if (
                    proposed_end < segment.end_time
                    and proposed_end - segment.start_time >= self.min_visible_segment_duration
                    and not self._range_has_speech(proposed_end, segment.end_time, transcripts)
                ):
                    old_end = segment.end_time
                    segment.end_time = proposed_end
                    segment.notes.append(
                        f"quality_silence_edge_trim_end={old_end:.3f}->{segment.end_time:.3f}"
                    )
                    summary.silence_edge_trimmed += 1
                    self._add_example(summary, f"{segment.segment_id} silence end {old_end:.2f}->{segment.end_time:.2f}")

    def _apply_speech_padding(
        self,
        segment: TimelineSegment,
        previous: TimelineSegment | None,
        next_segment: TimelineSegment | None,
        transcripts: list[TranscriptSegment],
        summary: FinalTimelineQualitySummary,
    ) -> None:
        if not transcripts:
            return

        start_transcript = self._speech_at_or_near_start(segment.start_time, transcripts)
        if start_transcript is not None:
            preferred_start = round(max(0.0, start_transcript.start_seconds - self.speech_pre_roll_seconds), 3)
            previous_limit = (
                round(previous.end_time + self.min_gap_seconds, 3)
                if previous is not None
                else 0.0
            )
            if (
                preferred_start < segment.start_time
                and preferred_start >= previous_limit
                and segment.end_time - preferred_start >= self.min_visible_segment_duration
            ):
                old_start = segment.start_time
                segment.start_time = preferred_start
                segment.notes.append(
                    f"quality_speech_start_adjusted={old_start:.3f}->{segment.start_time:.3f}"
                )
                summary.speech_start_adjusted += 1
                self._add_example(summary, f"{segment.segment_id} speech start {old_start:.2f}->{segment.start_time:.2f}")

        end_transcript = self._speech_at_or_near_end(segment.end_time, transcripts)
        if end_transcript is not None:
            preferred_end = round(end_transcript.end_seconds + self.speech_post_roll_seconds, 3)
            next_limit = (
                round(next_segment.start_time - self.min_gap_seconds, 3)
                if next_segment is not None
                else None
            )
            if (
                preferred_end > segment.end_time
                and (next_limit is None or preferred_end <= next_limit)
                and preferred_end - segment.start_time >= self.min_visible_segment_duration
            ):
                old_end = segment.end_time
                segment.end_time = preferred_end
                segment.notes.append(
                    f"quality_speech_end_adjusted={old_end:.3f}->{segment.end_time:.3f}"
                )
                summary.speech_end_adjusted += 1
                self._add_example(summary, f"{segment.segment_id} speech end {old_end:.2f}->{segment.end_time:.2f}")

    def _drop_overlaps_after_removal(
        self,
        segments: list[TimelineSegment],
        summary: FinalTimelineQualitySummary,
    ) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []
        for segment in sorted(segments, key=lambda item: (item.start_time, item.end_time, item.segment_id)):
            if not kept:
                kept.append(segment)
                continue
            previous = kept[-1]
            required_start = round(previous.end_time + self.min_gap_seconds, 3)
            if segment.start_time >= required_start:
                kept.append(segment)
                continue
            if segment.end_time - required_start >= self.min_visible_segment_duration:
                old_start = segment.start_time
                segment.start_time = required_start
                segment.notes.append(f"quality_overlap_trim_start={old_start:.3f}->{segment.start_time:.3f}")
                kept.append(segment)
                continue
            segment.notes.append(f"quality_overlap_removed_after={previous.segment_id}")
            summary.micro_removed += 1
            self._add_example(summary, f"removed overlap-short {self._range(segment)}")
        return kept

    def _transcript_segments(self, transcript_result: TranscriptResult | None) -> list[TranscriptSegment]:
        if transcript_result is None:
            return []
        return sorted(
            (
                segment
                for segment in transcript_result.segments
                if segment.end_seconds > segment.start_seconds
            ),
            key=lambda segment: (segment.start_seconds, segment.end_seconds),
        )

    def _edge_zones(self, weak_zones: list[HighlightCandidate] | None) -> list[HighlightCandidate]:
        return sorted(
            [
                zone
                for zone in (weak_zones or [])
                if zone.end_time > zone.start_time and self._weak_kind(zone) in {"silence", "low_motion"}
            ],
            key=lambda zone: (zone.start_time, zone.end_time),
        )

    def _weak_kind(self, zone: HighlightCandidate) -> str:
        text = " ".join([*zone.notes, *zone.signal_tags, zone.source or ""]).lower()
        if "low_motion" in text:
            return "low_motion"
        if "silence" in text:
            return "silence"
        return "weak"

    def _speech_at_or_near_start(
        self,
        boundary: float,
        transcripts: list[TranscriptSegment],
    ) -> TranscriptSegment | None:
        for transcript in transcripts:
            if transcript.start_seconds < boundary < transcript.end_seconds:
                return transcript
            if 0.0 <= boundary - transcript.start_seconds <= SPEECH_NEAR_EDGE_SECONDS:
                return transcript
        return None

    def _speech_at_or_near_end(
        self,
        boundary: float,
        transcripts: list[TranscriptSegment],
    ) -> TranscriptSegment | None:
        for transcript in transcripts:
            if transcript.start_seconds < boundary < transcript.end_seconds:
                return transcript
            if 0.0 <= transcript.end_seconds - boundary <= SPEECH_NEAR_EDGE_SECONDS:
                return transcript
        return None

    def _range_has_speech(
        self,
        start: float,
        end: float,
        transcripts: list[TranscriptSegment],
    ) -> bool:
        return any(
            transcript.start_seconds < end and transcript.end_seconds > start
            for transcript in transcripts
        )

    def _is_allowed_peak_micro(self, segment: TimelineSegment) -> bool:
        return (
            segment.segment_role == "peak"
            and segment.selection_score >= self.peak_micro_allowed_score
            and self._has_peak_note(segment)
        )

    def _has_peak_note(self, segment: TimelineSegment) -> bool:
        text = " ".join(segment.notes).lower()
        return "peak" in text or "energy_boost" in text or "audio" in text

    def _assign_final_roles(self, segments: list[TimelineSegment]) -> None:
        if not segments:
            return
        for segment in segments:
            if segment.segment_role in {"hook", "payoff"}:
                segment.segment_role = "bridge"
        if not self._is_allowed_peak_micro(segments[0]):
            segments[0].segment_role = "hook"
        if len(segments) > 1 and not self._is_allowed_peak_micro(segments[-1]):
            segments[-1].segment_role = "payoff"
        if not any(segment.segment_role == "peak" for segment in segments) and len(segments) > 2:
            peak = max(segments[1:-1], key=lambda segment: segment.selection_score)
            peak.segment_role = "peak"
        for segment in segments:
            segment.touch()

    def _assert_invariants(self, segments: list[TimelineSegment]) -> None:
        previous_end: float | None = None
        seen_ids: set[str] = set()
        for segment in segments:
            if segment.segment_id in seen_ids:
                raise ValueError(f"Duplicate timeline segment id after quality guard: {segment.segment_id}")
            seen_ids.add(segment.segment_id)
            if segment.start_time < 0.0:
                raise ValueError(f"Negative segment start after quality guard: {segment.segment_id}")
            if segment.end_time <= segment.start_time:
                raise ValueError(f"Invalid segment duration after quality guard: {segment.segment_id}")
            if segment.duration < self.min_visible_segment_duration and not self._is_allowed_peak_micro(segment):
                raise ValueError(f"Micro segment after quality guard: {segment.segment_id}")
            if previous_end is not None and segment.start_time < previous_end:
                raise ValueError(f"Timeline overlap after quality guard: {segment.segment_id}")
            previous_end = segment.end_time

    def _range(self, segment: TimelineSegment) -> str:
        return f"{segment.segment_id} {segment.start_time:.2f}-{segment.end_time:.2f}"

    def _add_example(self, summary: FinalTimelineQualitySummary, example: str) -> None:
        if len(summary.examples) < 5:
            summary.examples.append(example)
