from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from core.focus_switch_engine import FocusSwitchEngine
from models.transcript_result import TranscriptSegment


FRIEND_REACTION_KEYWORDS = FocusSwitchEngine.FRIEND_REACTION_KEYWORDS


@dataclass(frozen=True)
class FriendReactionBeatConfig:
    min_call_pause_seconds: float = 0.5
    max_call_pause_seconds: float = 2.0


@dataclass(frozen=True)
class FriendReactionBeat:
    start: float
    end: float
    beat_type: str
    evidence: dict[str, Any] = field(default_factory=dict)
    ali_context_text: str = ""
    friend_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": round(float(self.start), 3),
            "end": round(float(self.end), 3),
            "beat_type": self.beat_type,
            "evidence": dict(self.evidence),
            "ali_context_text": self.ali_context_text,
            "friend_text": self.friend_text,
        }


def build(
    segments: list[TranscriptSegment],
    config: FriendReactionBeatConfig | None = None,
) -> list[FriendReactionBeat]:
    config = config or FriendReactionBeatConfig()
    clean_segments = sorted(
        [segment for segment in segments if _valid_segment(segment)],
        key=lambda segment: (float(segment.start_seconds), float(segment.end_seconds)),
    )

    beats: list[FriendReactionBeat] = []
    for index, segment in enumerate(clean_segments):
        if _speaker(segment) != "friend":
            continue

        keyword = _reaction_keyword(segment.text)
        if not keyword:
            continue

        ali_segment, ali_index, gap_seconds = _owner_call_pause_context(
            clean_segments,
            friend_index=index,
            config=config,
        )
        beats.append(
            _friend_reaction_beat(
                segment,
                index=index,
                keyword=keyword,
                ali_segment=ali_segment,
                ali_index=ali_index,
                gap_seconds=gap_seconds,
                config=config,
            )
        )

    return sorted(beats, key=lambda beat: (beat.start, beat.end, beat.beat_type))


def _friend_reaction_beat(
    segment: TranscriptSegment,
    *,
    index: int,
    keyword: str,
    ali_segment: TranscriptSegment | None,
    ali_index: int | None,
    gap_seconds: float | None,
    config: FriendReactionBeatConfig,
) -> FriendReactionBeat:
    beat_type = "friend_reaction_keyword"
    evidence: dict[str, Any] = {
        "pattern": beat_type,
        "keyword": keyword,
        "friend_segment_index": index,
    }
    ali_context_text = ""
    if ali_segment is not None and ali_index is not None and gap_seconds is not None:
        beat_type = "owner_call_pause_friend"
        evidence.update(
            {
                "pattern": beat_type,
                "gap_seconds": round(gap_seconds, 3),
                "ali_segment_index": ali_index,
                "min_call_pause_seconds": round(float(config.min_call_pause_seconds), 3),
                "max_call_pause_seconds": round(float(config.max_call_pause_seconds), 3),
            }
        )
        ali_context_text = _text(ali_segment)

    return FriendReactionBeat(
        start=round(float(segment.start_seconds), 3),
        end=round(float(segment.end_seconds), 3),
        beat_type=beat_type,
        evidence=evidence,
        ali_context_text=ali_context_text,
        friend_text=_text(segment),
    )


def _owner_call_pause_context(
    segments: list[TranscriptSegment],
    *,
    friend_index: int,
    config: FriendReactionBeatConfig,
) -> tuple[TranscriptSegment | None, int | None, float | None]:
    min_gap = max(0.0, float(config.min_call_pause_seconds))
    max_gap = max(min_gap, float(config.max_call_pause_seconds))
    friend_segment = segments[friend_index]
    friend_start = float(friend_segment.start_seconds)

    for index in range(friend_index - 1, -1, -1):
        candidate = segments[index]
        candidate_end = float(candidate.end_seconds)
        if candidate_end > friend_start:
            continue

        gap_seconds = round(friend_start - candidate_end, 3)
        if gap_seconds > max_gap:
            break

        if _speaker(candidate) != "ali":
            continue

        if gap_seconds < min_gap:
            continue

        if not _has_true_silence_gap(
            segments,
            ali_index=index,
            friend_index=friend_index,
            gap_start=candidate_end,
            gap_end=friend_start,
        ):
            return None, None, None

        return candidate, index, gap_seconds

    return None, None, None


def _has_true_silence_gap(
    segments: list[TranscriptSegment],
    *,
    ali_index: int,
    friend_index: int,
    gap_start: float,
    gap_end: float,
) -> bool:
    for index, segment in enumerate(segments):
        if index in (ali_index, friend_index):
            continue

        start = float(segment.start_seconds)
        end = float(segment.end_seconds)
        if start < gap_end and end > gap_start:
            return False

    return True


def _reaction_keyword(text: str) -> str | None:
    clean = str(text or "").lower()
    tokens = set(re.findall(r"[\w\u00c0-\u024f]+", clean, flags=re.UNICODE))
    for keyword in sorted(FRIEND_REACTION_KEYWORDS, key=len, reverse=True):
        low = str(keyword).lower()
        if len(low) <= 3:
            if low in tokens:
                return low
        elif low in clean or low in tokens:
            return low
    return None


def _valid_segment(segment: TranscriptSegment) -> bool:
    try:
        return float(segment.end_seconds) > float(segment.start_seconds)
    except (TypeError, ValueError):
        return False


def _speaker(segment: TranscriptSegment) -> str:
    return str(getattr(segment, "speaker", "") or "").strip().lower()


def _text(segment: TranscriptSegment) -> str:
    return str(getattr(segment, "text", "") or "").strip()
