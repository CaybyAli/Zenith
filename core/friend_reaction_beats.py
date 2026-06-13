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
        if keyword:
            beats.append(_friend_keyword_beat(segment, index=index, keyword=keyword))

    for index, ali_segment in enumerate(clean_segments):
        if _speaker(ali_segment) != "ali":
            continue

        friend_segment, friend_index, gap_seconds = _next_friend_after_pause(
            clean_segments,
            start_index=index + 1,
            ali_end=float(ali_segment.end_seconds),
            config=config,
        )
        if friend_segment is None or friend_index is None or gap_seconds is None:
            continue

        beats.append(
            FriendReactionBeat(
                start=round(float(ali_segment.start_seconds), 3),
                end=round(float(friend_segment.end_seconds), 3),
                beat_type="owner_call_pause_friend",
                evidence={
                    "pattern": "owner_call_pause_friend",
                    "gap_seconds": round(gap_seconds, 3),
                    "ali_segment_index": index,
                    "friend_segment_index": friend_index,
                    "min_call_pause_seconds": round(float(config.min_call_pause_seconds), 3),
                    "max_call_pause_seconds": round(float(config.max_call_pause_seconds), 3),
                },
                ali_context_text=_text(ali_segment),
                friend_text=_text(friend_segment),
            )
        )

    return sorted(beats, key=lambda beat: (beat.start, beat.end, beat.beat_type))


def _friend_keyword_beat(
    segment: TranscriptSegment,
    *,
    index: int,
    keyword: str,
) -> FriendReactionBeat:
    return FriendReactionBeat(
        start=round(float(segment.start_seconds), 3),
        end=round(float(segment.end_seconds), 3),
        beat_type="friend_reaction_keyword",
        evidence={
            "pattern": "friend_reaction_keyword",
            "keyword": keyword,
            "friend_segment_index": index,
        },
        friend_text=_text(segment),
    )


def _next_friend_after_pause(
    segments: list[TranscriptSegment],
    *,
    start_index: int,
    ali_end: float,
    config: FriendReactionBeatConfig,
) -> tuple[TranscriptSegment | None, int | None, float | None]:
    min_gap = max(0.0, float(config.min_call_pause_seconds))
    max_gap = max(min_gap, float(config.max_call_pause_seconds))

    for index in range(start_index, len(segments)):
        candidate = segments[index]
        if float(candidate.start_seconds) < ali_end:
            continue

        gap_seconds = round(float(candidate.start_seconds) - ali_end, 3)
        if gap_seconds > max_gap:
            return None, None, None

        if _speaker(candidate) != "friend":
            continue

        if gap_seconds < min_gap:
            continue

        return candidate, index, gap_seconds

    return None, None, None


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
