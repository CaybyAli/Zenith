from __future__ import annotations

from models.transcript_result import TranscriptResult, TranscriptSegment, TranscriptWord


def _clean_word(value: object) -> str:
    return str(value or "").strip()


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


def build_caption_words_from_transcript(
    transcript: TranscriptResult,
    clip_start_seconds: float,
    clip_end_seconds: float,
    max_words: int = 9,
) -> tuple[list[str], dict[str, float]]:
    """
    Build caption words for one Shorts clip from transcript data.

    Returns:
        (words_in_clip_range, hook_score_by_word)
    """
    safe_max_words = max(0, int(max_words))
    if safe_max_words <= 0:
        return [], {}

    words: list[str] = []
    hook_score_by_word: dict[str, float] = {}

    for segment in transcript.segments or []:
        for word in segment.words or []:
            if not (
                float(clip_start_seconds)
                <= float(word.start_seconds)
                <= float(clip_end_seconds)
            ):
                continue

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
