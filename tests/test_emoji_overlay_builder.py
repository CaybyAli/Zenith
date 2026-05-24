from __future__ import annotations

from core.emoji_overlay_builder import (
    EMOJI_OUTLINE_ALPHA,
    EMOJI_OUTLINE_BLUR,
    EMOJI_SIZE,
    EMOJI_X,
    EMOJI_Y,
    EmojiOverlayEvent,
    EmojiOverlayRenderer,
    EmojiOverlaySelector,
)
from models.transcript_result import TranscriptWord


def _word(text: str, start: float, end: float) -> TranscriptWord:
    return TranscriptWord(
        text=text,
        start_seconds=start,
        end_seconds=end,
        probability=0.9,
    )


def test_selector_chooses_matching_emojis_only_when_relevant() -> None:
    groups = [
        [_word("ich", 0.0, 0.2), _word("liebe", 0.2, 0.4), _word("dich", 0.4, 0.6)],
        [_word("neutral", 3.0, 3.2), _word("weiter", 3.2, 3.4)],
        [_word("haha", 10.0, 10.2), _word("was", 10.2, 10.4)],
        [_word("das", 20.0, 20.2), _word("war", 20.2, 20.4), _word("heftig", 20.4, 20.6)],
    ]

    events = EmojiOverlaySelector().select(groups, duration_seconds=60.0)

    assert [event.emoji for event in events] == ["heart", "laugh", "fire"]
    assert len(events) == 3


def test_selector_limits_to_three_emojis_per_short() -> None:
    groups = [
        [_word("liebe", 0.0, 0.2)],
        [_word("haha", 10.0, 10.2)],
        [_word("heftig", 20.0, 20.2)],
        [_word("warte", 30.0, 30.2)],
    ]

    events = EmojiOverlaySelector().select(groups, duration_seconds=60.0)

    assert len(events) == 3


def test_selector_keeps_minimum_distance_between_emojis() -> None:
    groups = [
        [_word("liebe", 0.0, 0.2)],
        [_word("haha", 2.0, 2.2)],
        [_word("heftig", 10.0, 10.2)],
    ]

    events = EmojiOverlaySelector().select(groups, duration_seconds=60.0)

    assert [event.emoji for event in events] == ["heart", "fire"]


def test_renderer_filter_contains_final_visual_position_and_outline() -> None:
    events = [
        EmojiOverlayEvent(
            emoji="fire",
            start_seconds=1.23,
            end_seconds=2.93,
            source_text="DAS WAR HEFTIG",
        )
    ]

    filter_complex = EmojiOverlayRenderer()._filter_complex(events)

    assert f"scale={EMOJI_SIZE}:{EMOJI_SIZE}:flags=lanczos" in filter_complex
    assert f"boxblur={EMOJI_OUTLINE_BLUR}:1" in filter_complex
    assert f"color=white@{EMOJI_OUTLINE_ALPHA}:s={EMOJI_SIZE}x{EMOJI_SIZE}" in filter_complex
    assert f"overlay=x={EMOJI_X}:y={EMOJI_Y}" in filter_complex
    assert "between(t,1.23,2.93)" in filter_complex

def test_final_emoji_position_is_bottom_centered_below_captions() -> None:
    # Final D7 safety rule:
    # Emoji must never cover caption text.
    # Captions live around y=1310/1385/1445, so sticker starts safely below.
    assert EMOJI_X == 447
    assert EMOJI_Y >= 1600

