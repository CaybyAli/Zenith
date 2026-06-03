from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from core.shorts_caption_hygiene import CaptionHygieneEvent, apply_caption_display_hygiene
from models.transcript_result import TranscriptResult, TranscriptSegment, TranscriptWord

LOGGER = logging.getLogger(__name__)
MIN_CAPTION_WORD_DURATION_SECONDS = 0.06


@dataclass(frozen=True)
class CaptionTimestampClampEvent:
    segment_index: int
    word_index: int
    word: str
    segment_start_seconds: float
    segment_end_seconds: float
    raw_start_seconds: float
    raw_end_seconds: float
    clamped_start_seconds: float
    clamped_end_seconds: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_index": self.segment_index,
            "word_index": self.word_index,
            "word": self.word,
            "segment_start_seconds": self.segment_start_seconds,
            "segment_end_seconds": self.segment_end_seconds,
            "raw_start_seconds": self.raw_start_seconds,
            "raw_end_seconds": self.raw_end_seconds,
            "clamped_start_seconds": self.clamped_start_seconds,
            "clamped_end_seconds": self.clamped_end_seconds,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class SaneCaptionWordResult:
    words: list[TranscriptWord] = field(default_factory=list)
    clamp_events: list[CaptionTimestampClampEvent] = field(default_factory=list)
    skipped_word_count: int = 0
    hygiene_events: list[CaptionHygieneEvent] = field(default_factory=list)

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "word_count": len(self.words),
            "clamped_word_timestamp_count": len(self.clamp_events),
            "skipped_word_count": self.skipped_word_count,
            "hygiene_removed_word_count": len(self.hygiene_events),
            "hygiene_events": [event.to_dict() for event in self.hygiene_events],
            "clamp_events": [event.to_dict() for event in self.clamp_events],
            "words": [word.to_dict() for word in self.words],
        }


def _clean_word(value: object) -> str:
    return str(value or "").strip()


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(max(float(value), float(lower)), float(upper))


def _word_score(word: TranscriptWord) -> float:
    if word.probability is None:
        return 0.5
    try:
        return float(word.probability)
    except (TypeError, ValueError):
        return 0.5


def _segment_overlaps_clip(
    segment: TranscriptSegment,
    clip_start_seconds: float,
    clip_end_seconds: float,
) -> bool:
    return (
        float(segment.end_seconds) > float(clip_start_seconds)
        and float(segment.start_seconds) < float(clip_end_seconds)
    )


def _clamp_reason(
    raw_start: float,
    raw_end: float,
    segment_start: float,
    segment_end: float,
) -> str:
    reasons: list[str] = []
    if raw_start < segment_start:
        reasons.append("start_before_segment")
    if raw_start > segment_end:
        reasons.append("start_after_segment")
    if raw_end < segment_start:
        reasons.append("end_before_segment")
    if raw_end > segment_end:
        reasons.append("end_after_segment")
    return "+".join(reasons) or "inside_segment"


def build_sane_caption_words_from_transcript(
    transcript: TranscriptResult,
    clip_start_seconds: float,
    clip_end_seconds: float,
) -> SaneCaptionWordResult:
    clip_start = _safe_float(clip_start_seconds)
    clip_end = _safe_float(clip_end_seconds)
    if clip_start is None or clip_end is None or clip_end <= clip_start:
        return SaneCaptionWordResult()

    caption_words: list[TranscriptWord] = []
    clamp_events: list[CaptionTimestampClampEvent] = []
    skipped_word_count = 0

    for segment_index, segment in enumerate(transcript.segments or []):
        segment_start = _safe_float(getattr(segment, "start_seconds", None))
        segment_end = _safe_float(getattr(segment, "end_seconds", None))
        if segment_start is None or segment_end is None or segment_end <= segment_start:
            continue
        if not _segment_overlaps_clip(segment, clip_start, clip_end):
            continue

        segment_audio_track = str(getattr(segment, "audio_track", "mic") or "mic")
        segment_speaker = str(getattr(segment, "speaker", "unknown") or "unknown")

        for word_index, word in enumerate(getattr(segment, "words", []) or []):
            text = _clean_word(getattr(word, "text", ""))
            raw_start = _safe_float(getattr(word, "start_seconds", None))
            raw_end = _safe_float(getattr(word, "end_seconds", None))
            raw_word_audio_track = getattr(word, "audio_track", None)
            raw_word_speaker = getattr(word, "speaker", None)

            word_audio_track = str(raw_word_audio_track or segment_audio_track)
            word_speaker = str(raw_word_speaker or segment_speaker)

            # Backwards compatibility:
            # Older TranscriptWord objects default to mic/unknown even when the
            # parent segment is discord/friend. In that case, inherit segment metadata.
            if word_audio_track == "mic" and segment_audio_track != "mic":
                word_audio_track = segment_audio_track
            if word_speaker == "unknown" and segment_speaker != "unknown":
                word_speaker = segment_speaker

            if raw_start is None or raw_end is None or not text:
                skipped_word_count += 1
                continue

            # Existing caption contract:
            # A word that starts exactly at the clip end still belongs to the clip.
            if raw_start == clip_end and raw_end > raw_start:
                caption_words.append(
                    TranscriptWord(
                        start_seconds=round(
                            max(0.0, (clip_end - clip_start) - MIN_CAPTION_WORD_DURATION_SECONDS),
                            3,
                        ),
                        end_seconds=round(clip_end - clip_start, 3),
                        text=text,
                        probability=getattr(word, "probability", None),
                        audio_track=word_audio_track,
                        speaker=word_speaker,
                    )
                )
                continue

            clamped_start = _clamp(raw_start, segment_start, segment_end)
            clamped_end = _clamp(raw_end, segment_start, segment_end)

            if clamped_start != raw_start or clamped_end != raw_end:
                clamp_events.append(
                    CaptionTimestampClampEvent(
                        segment_index=segment_index,
                        word_index=word_index,
                        word=text,
                        segment_start_seconds=round(segment_start, 3),
                        segment_end_seconds=round(segment_end, 3),
                        raw_start_seconds=round(raw_start, 3),
                        raw_end_seconds=round(raw_end, 3),
                        clamped_start_seconds=round(clamped_start, 3),
                        clamped_end_seconds=round(clamped_end, 3),
                        reason=_clamp_reason(raw_start, raw_end, segment_start, segment_end),
                    )
                )

            absolute_start = max(clamped_start, clip_start)
            absolute_end = min(clamped_end, clip_end)

            # Keep a word that touches the clip end boundary. Existing caption
            # tests expect this, and it avoids dropping the final spoken word.
            if absolute_end - absolute_start < MIN_CAPTION_WORD_DURATION_SECONDS:
                touches_clip_end = raw_start <= clip_end <= raw_end
                if touches_clip_end:
                    absolute_end = clip_end
                    absolute_start = max(
                        clip_start,
                        clip_end - MIN_CAPTION_WORD_DURATION_SECONDS,
                    )

            if absolute_end - absolute_start < MIN_CAPTION_WORD_DURATION_SECONDS:
                skipped_word_count += 1
                continue

            caption_words.append(
                TranscriptWord(
                    start_seconds=round(absolute_start - clip_start, 3),
                    end_seconds=round(absolute_end - clip_start, 3),
                    text=text,
                    probability=getattr(word, "probability", None),
                    audio_track=word_audio_track,
                    speaker=word_speaker,
                )
            )

    if clamp_events:
        LOGGER.warning(
            "shorts_caption_timestamp_clamped count=%s clip=%.3f-%.3f events=%s",
            len(clamp_events),
            clip_start,
            clip_end,
            [event.to_dict() for event in clamp_events],
        )

    hygiene_result = apply_caption_display_hygiene(caption_words)

    return SaneCaptionWordResult(
        words=hygiene_result.words,
        clamp_events=clamp_events,
        skipped_word_count=skipped_word_count,
        hygiene_events=hygiene_result.events,
    )


def build_caption_words_from_transcript(
    transcript: TranscriptResult,
    clip_start_seconds: float,
    clip_end_seconds: float,
    max_words: int = 9,
) -> tuple[list[str], dict[str, float]]:
    safe_max_words = max(0, int(max_words))
    if safe_max_words <= 0:
        return [], {}

    words: list[str] = []
    hook_score_by_word: dict[str, float] = {}

    sane_result = build_sane_caption_words_from_transcript(
        transcript=transcript,
        clip_start_seconds=clip_start_seconds,
        clip_end_seconds=clip_end_seconds,
    )
    for word in sane_result.words:
        clean = _clean_word(word.text)
        if not clean:
            continue
        words.append(clean)
        hook_score_by_word[clean.casefold()] = _word_score(word)
        if len(words) >= safe_max_words:
            return words, hook_score_by_word

    if words:
        return words, hook_score_by_word

    for segment in transcript.segments or []:
        if not _segment_overlaps_clip(segment, clip_start_seconds, clip_end_seconds):
            continue

        for raw_word in str(segment.text or "").split():
            clean = _clean_word(raw_word)
            if not clean:
                continue

            words.append(clean)
            hook_score_by_word[clean.casefold()] = 0.5

            if len(words) >= safe_max_words:
                return words, hook_score_by_word

    return words, hook_score_by_word
