from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from models.transcript_result import TranscriptWord


OWNER_REGION_MERGE_GAP_SECONDS = 0.55
OWNER_REGION_PADDING_SECONDS = 0.12
OWNER_REGION_SUPPRESS_RATIO = 0.20
MIN_OWNER_REGION_OVERLAP_SECONDS = 0.02


@dataclass(frozen=True)
class CaptionHygieneEvent:
    reason: str
    word: str
    start_seconds: float
    end_seconds: float
    speaker: str
    audio_track: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "word": self.word,
            "start_seconds": round(float(self.start_seconds), 3),
            "end_seconds": round(float(self.end_seconds), 3),
            "speaker": self.speaker,
            "audio_track": self.audio_track,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class CaptionHygieneResult:
    words: list[TranscriptWord]
    events: list[CaptionHygieneEvent]


def apply_caption_display_hygiene(
    words: list[TranscriptWord],
    *,
    min_repeat_count: int = 4,
    max_seconds_per_token: float = 0.15,
) -> CaptionHygieneResult:
    ordered = sorted(
        list(words or []),
        key=lambda word: (
            float(getattr(word, "start_seconds", 0.0) or 0.0),
            _speaker_priority(word),
            float(getattr(word, "end_seconds", 0.0) or 0.0),
        ),
    )

    remove_indices: set[int] = set()
    events: list[CaptionHygieneEvent] = []

    owner_words = [word for word in ordered if _is_owner_word(word)]
    owner_regions = _build_owner_speech_regions(owner_words)

    # Wichtig:
    # Discord/Friend-W?rter innerhalb einer l?ngeren Owner-Sprachinsel werden ausgeblendet.
    # Das verhindert gelbe Echo-Captions, wenn Ali lange redet.
    for index, word in enumerate(ordered):
        if _is_owner_word(word):
            continue

        word_start = float(getattr(word, "start_seconds", 0.0) or 0.0)
        word_end = float(getattr(word, "end_seconds", 0.0) or 0.0)
        word_duration = max(0.001, word_end - word_start)
        word_center = word_start + (word_duration / 2.0)

        strongest_overlap = 0.0
        center_inside_owner_region = False

        for region_start, region_end in owner_regions:
            overlap = max(0.0, min(word_end, region_end) - max(word_start, region_start))
            strongest_overlap = max(strongest_overlap, overlap)

            if region_start <= word_center <= region_end:
                center_inside_owner_region = True

        overlap_ratio = strongest_overlap / word_duration

        word_token = _normalize_token(getattr(word, "text", ""))
        overlapping_owner_tokens = _overlapping_owner_tokens(word, owner_words)
        duplicates_owner_token = bool(word_token and word_token in overlapping_owner_tokens)

        if (
            duplicates_owner_token
            and strongest_overlap >= MIN_OWNER_REGION_OVERLAP_SECONDS
            and (
                overlap_ratio >= OWNER_REGION_SUPPRESS_RATIO
                or center_inside_owner_region
            )
        ):
            remove_indices.add(index)
            events.append(
                _event(
                    "owner_overlap_priority",
                    word,
                    (
                        "friend/secondary duplicate token lands inside owner speech island; "
                        f"owner display wins token={word_token!r} overlap={strongest_overlap:.3f}s "
                        f"ratio={overlap_ratio:.2f}"
                    ),
                )
            )

    # Rate hygiene: lokale schnelle Wiederholungs-Bursts filtern.
    run: list[tuple[int, TranscriptWord]] = []
    previous_token = ""

    def flush_run() -> None:
        nonlocal run
        if len(run) >= int(min_repeat_count):
            _mark_rapid_repeat_bursts(
                run=run,
                remove_indices=remove_indices,
                events=events,
                min_repeat_count=int(min_repeat_count),
                max_seconds_per_token=float(max_seconds_per_token),
            )
        run = []

    for index, word in enumerate(ordered):
        if index in remove_indices:
            continue

        token = _normalize_token(getattr(word, "text", ""))
        if not token:
            flush_run()
            previous_token = ""
            continue

        if token != previous_token:
            flush_run()
            run = [(index, word)]
            previous_token = token
        else:
            run.append((index, word))

    flush_run()

    kept = [
        word
        for index, word in enumerate(ordered)
        if index not in remove_indices
    ]

    return CaptionHygieneResult(words=kept, events=events)


def _overlapping_owner_tokens(
    word: TranscriptWord,
    owner_words: list[TranscriptWord],
) -> set[str]:
    word_start = float(getattr(word, "start_seconds", 0.0) or 0.0)
    word_end = float(getattr(word, "end_seconds", 0.0) or 0.0)

    tokens: set[str] = set()
    for owner_word in owner_words:
        owner_start = float(getattr(owner_word, "start_seconds", 0.0) or 0.0)
        owner_end = float(getattr(owner_word, "end_seconds", 0.0) or 0.0)

        overlap = max(0.0, min(word_end, owner_end) - max(word_start, owner_start))
        if overlap < MIN_OWNER_REGION_OVERLAP_SECONDS:
            continue

        token = _normalize_token(getattr(owner_word, "text", ""))
        if token:
            tokens.add(token)

    return tokens


def _build_owner_speech_regions(owner_words: list[TranscriptWord]) -> list[tuple[float, float]]:
    regions: list[tuple[float, float]] = []

    for word in sorted(owner_words, key=lambda item: float(getattr(item, "start_seconds", 0.0) or 0.0)):
        start = float(getattr(word, "start_seconds", 0.0) or 0.0)
        end = float(getattr(word, "end_seconds", 0.0) or 0.0)

        if end <= start:
            continue

        if not regions:
            regions.append((start, end))
            continue

        previous_start, previous_end = regions[-1]

        if start <= previous_end + OWNER_REGION_MERGE_GAP_SECONDS:
            regions[-1] = (previous_start, max(previous_end, end))
        else:
            regions.append((start, end))

    return [
        (
            max(0.0, start - OWNER_REGION_PADDING_SECONDS),
            end + OWNER_REGION_PADDING_SECONDS,
        )
        for start, end in regions
    ]


def _mark_rapid_repeat_bursts(
    *,
    run: list[tuple[int, TranscriptWord]],
    remove_indices: set[int],
    events: list[CaptionHygieneEvent],
    min_repeat_count: int,
    max_seconds_per_token: float,
) -> None:
    cursor = 0

    while cursor < len(run):
        best_end: int | None = None
        best_span = 0.0
        best_seconds_per_token = 999.0

        for end_index in range(cursor + min_repeat_count - 1, len(run)):
            first_word = run[cursor][1]
            last_word = run[end_index][1]

            span = max(
                0.0,
                float(getattr(last_word, "end_seconds", 0.0) or 0.0)
                - float(getattr(first_word, "start_seconds", 0.0) or 0.0),
            )
            count = end_index - cursor + 1
            seconds_per_token = span / max(1, count)

            if seconds_per_token < max_seconds_per_token:
                best_end = end_index
                best_span = span
                best_seconds_per_token = seconds_per_token

        if best_end is None:
            cursor += 1
            continue

        burst_count = best_end - cursor + 1
        for remove_pos in range(cursor + 1, best_end + 1):
            original_index, word = run[remove_pos]
            if original_index in remove_indices:
                continue

            remove_indices.add(original_index)
            events.append(
                _event(
                    "rapid_repeat_hallucination",
                    word,
                    (
                        f"same token repeated {burst_count}x in {best_span:.3f}s "
                        f"({best_seconds_per_token:.3f}s/token)"
                    ),
                )
            )

        cursor = best_end + 1


def _normalize_token(value: object) -> str:
    clean = str(value or "").strip().casefold()
    clean = re.sub(r"^[^\w????]+|[^\w????]+$", "", clean, flags=re.IGNORECASE)
    return clean


def _is_owner_word(word: TranscriptWord) -> bool:
    marker = f"{getattr(word, 'speaker', '')} {getattr(word, 'audio_track', '')}".casefold()
    return any(item in marker for item in ("ali", "owner", "mic", "hajar", "primary", "main"))


def _speaker_priority(word: TranscriptWord) -> int:
    return 0 if _is_owner_word(word) else 1


def _event(reason: str, word: TranscriptWord, detail: str) -> CaptionHygieneEvent:
    return CaptionHygieneEvent(
        reason=reason,
        word=str(getattr(word, "text", "") or ""),
        start_seconds=float(getattr(word, "start_seconds", 0.0) or 0.0),
        end_seconds=float(getattr(word, "end_seconds", 0.0) or 0.0),
        speaker=str(getattr(word, "speaker", "unknown") or "unknown"),
        audio_track=str(getattr(word, "audio_track", "unknown") or "unknown"),
        detail=detail,
    )
