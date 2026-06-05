from __future__ import annotations

from pathlib import Path

from core.caption_ass_builder import (
    ASS_HIGHLIGHT_GREEN,
    ASS_HIGHLIGHT_YELLOW,
    CaptionASSBuilder,
    CaptionGroup,
)
from core.shorts_caption_hygiene import apply_caption_display_hygiene
from core.shorts_transcript_caption_builder import build_sane_caption_words_from_transcript
from models.transcript_result import TranscriptResult, TranscriptSegment, TranscriptWord


def _word(
    text: str,
    start: float,
    end: float,
    *,
    speaker: str,
    audio_track: str,
) -> TranscriptWord:
    return TranscriptWord(
        text=text,
        start_seconds=start,
        end_seconds=end,
        probability=0.99,
        speaker=speaker,
        audio_track=audio_track,
    )


def _texts(words: list[TranscriptWord]) -> list[str]:
    return [word.text for word in words]


def test_friend_unique_word_inside_owner_region_is_kept() -> None:
    result = apply_caption_display_hygiene(
        [
            _word("ich", 1.00, 1.60, speaker="ali", audio_track="mic"),
            _word("links", 1.20, 1.42, speaker="friend", audio_track="discord"),
        ]
    )

    assert _texts(result.words) == ["ich", "links"]
    assert not [
        event
        for event in result.events
        if event.reason == "owner_overlap_priority" and event.word == "links"
    ]


def test_friend_duplicate_owner_word_inside_owner_region_is_removed() -> None:
    result = apply_caption_display_hygiene(
        [
            _word("ich", 1.00, 1.60, speaker="ali", audio_track="mic"),
            _word("ich", 1.20, 1.42, speaker="friend", audio_track="discord"),
        ]
    )

    kept = [
        (word.text, word.speaker, word.audio_track)
        for word in result.words
    ]
    assert kept == [("ich", "ali", "mic")]
    assert [
        event
        for event in result.events
        if event.reason == "owner_overlap_priority" and event.word == "ich"
    ]


def test_build_sane_caption_words_preserves_unique_friend_words() -> None:
    transcript = TranscriptResult(
        source_path="raw.mp4",
        language="de",
        engine="test",
        full_text="ich links",
        segments=[
            TranscriptSegment(
                start_seconds=1.00,
                end_seconds=1.60,
                text="ich",
                speaker="ali",
                audio_track="mic",
                words=[
                    _word("ich", 1.00, 1.60, speaker="ali", audio_track="mic"),
                ],
            ),
            TranscriptSegment(
                start_seconds=1.20,
                end_seconds=1.42,
                text="links",
                speaker="friend",
                audio_track="discord",
                words=[
                    _word("links", 1.20, 1.42, speaker="friend", audio_track="discord"),
                ],
            ),
        ],
    )

    result = build_sane_caption_words_from_transcript(
        transcript=transcript,
        clip_start_seconds=0.0,
        clip_end_seconds=3.0,
    )

    friend_words = [
        word
        for word in result.words
        if word.speaker == "friend" or word.audio_track == "discord"
    ]
    assert [word.text for word in friend_words] == ["links"]


def test_ass_builder_renders_friend_words_yellow(tmp_path: Path) -> None:
    ass_path = tmp_path / "friend_caption.ass"

    CaptionASSBuilder().generate_ass_file(
        caption_groups=[
            CaptionGroup(
                words=[
                    _word("links", 0.10, 0.50, speaker="friend", audio_track="discord"),
                ]
            )
        ],
        output_path=str(ass_path),
    )

    ass_text = ass_path.read_text(encoding="utf-8-sig")
    assert ASS_HIGHLIGHT_YELLOW in ass_text
    assert ASS_HIGHLIGHT_GREEN not in ass_text
