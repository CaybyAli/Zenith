from __future__ import annotations

import re
from typing import Any, Iterable


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_word_entries(raw_words: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []

    for item in raw_words or []:
        text = str(item.get("word") or item.get("text") or "").strip()
        if not text:
            continue

        start = _safe_float(item.get("start_seconds", item.get("start")))
        end = _safe_float(item.get("end_seconds", item.get("end")))
        if start is None or end is None:
            continue
        if end <= start:
            continue

        confidence = item.get("confidence", item.get("probability"))
        confidence_value = _safe_float(confidence) if confidence is not None else None

        words.append(
            {
                "word": text,
                "start_seconds": max(0.0, start),
                "end_seconds": max(0.0, end),
                "confidence": confidence_value,
            }
        )

    words.sort(key=lambda word: (word["start_seconds"], word["end_seconds"]))
    return words


def build_speech_segments(
    words: Iterable[dict[str, Any]],
    *,
    merge_gap: float = 0.3,
) -> list[dict[str, Any]]:
    if merge_gap < 0:
        raise ValueError("merge_gap must be >= 0")

    normalized_words = normalize_word_entries(words)
    if not normalized_words:
        return []

    segments: list[dict[str, Any]] = []
    current_start = normalized_words[0]["start_seconds"]
    current_end = normalized_words[0]["end_seconds"]
    current_words = [normalized_words[0]["word"]]

    for word in normalized_words[1:]:
        gap = word["start_seconds"] - current_end

        if gap < merge_gap:
            current_end = max(current_end, word["end_seconds"])
            current_words.append(word["word"])
            continue

        segments.append(
            {
                "start_seconds": round(current_start, 3),
                "end_seconds": round(current_end, 3),
                "duration_seconds": round(current_end - current_start, 3),
                "text": " ".join(current_words).strip(),
                "word_count": len(current_words),
            }
        )

        current_start = word["start_seconds"]
        current_end = word["end_seconds"]
        current_words = [word["word"]]

    segments.append(
        {
            "start_seconds": round(current_start, 3),
            "end_seconds": round(current_end, 3),
            "duration_seconds": round(current_end - current_start, 3),
            "text": " ".join(current_words).strip(),
            "word_count": len(current_words),
        }
    )

    return segments


def build_silence_gaps(
    speech_segments: Iterable[dict[str, Any]],
    *,
    min_gap: float = 0.0,
) -> list[dict[str, Any]]:
    if min_gap < 0:
        raise ValueError("min_gap must be >= 0")

    segments = sorted(
        list(speech_segments or []),
        key=lambda segment: float(segment.get("start_seconds", 0.0) or 0.0),
    )

    gaps: list[dict[str, Any]] = []
    for left, right in zip(segments, segments[1:]):
        left_end = _safe_float(left.get("end_seconds"))
        right_start = _safe_float(right.get("start_seconds"))

        if left_end is None or right_start is None:
            continue

        duration = right_start - left_end
        if duration <= min_gap:
            continue

        gaps.append(
            {
                "start_seconds": round(left_end, 3),
                "end_seconds": round(right_start, 3),
                "duration_seconds": round(duration, 3),
            }
        )

    return gaps


def speech_coverage_percent(
    speech_segments: Iterable[dict[str, Any]],
    *,
    media_duration_seconds: float,
) -> float:
    if media_duration_seconds <= 0:
        return 0.0

    total_speech = 0.0
    for segment in speech_segments or []:
        duration = _safe_float(segment.get("duration_seconds"))
        if duration is not None and duration > 0:
            total_speech += duration
            continue

        start = _safe_float(segment.get("start_seconds"))
        end = _safe_float(segment.get("end_seconds"))
        if start is not None and end is not None and end > start:
            total_speech += end - start

    return round((total_speech / media_duration_seconds) * 100.0, 3)


def _normalize_token(value: str) -> str:
    clean = value.strip().lower()
    clean = (
        clean.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    clean = re.sub(r"[^a-z0-9]+", "", clean)
    return clean


def find_phrase_occurrences(
    words: Iterable[dict[str, Any]],
    phrase: str,
    *,
    max_results: int = 3,
) -> list[list[dict[str, Any]]]:
    normalized_words = normalize_word_entries(words)
    phrase_tokens = [
        _normalize_token(part)
        for part in phrase.split()
        if _normalize_token(part)
    ]

    if not normalized_words or not phrase_tokens:
        return []

    indexed_tokens = [
        (_normalize_token(word["word"]), word)
        for word in normalized_words
        if _normalize_token(word["word"])
    ]

    matches: list[list[dict[str, Any]]] = []
    window_size = len(phrase_tokens)

    for index in range(0, len(indexed_tokens) - window_size + 1):
        candidate_tokens = [
            token for token, _word in indexed_tokens[index : index + window_size]
        ]

        if candidate_tokens == phrase_tokens:
            matches.append(
                [word for _token, word in indexed_tokens[index : index + window_size]]
            )

        if len(matches) >= max_results:
            break

    return matches
