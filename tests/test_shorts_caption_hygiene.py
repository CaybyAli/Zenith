from core.shorts_caption_hygiene import apply_caption_display_hygiene
from models.transcript_result import TranscriptWord


def _word(
    text: str,
    start: float,
    end: float,
    *,
    speaker: str = "ali",
    audio_track: str = "mic",
) -> TranscriptWord:
    return TranscriptWord(
        text=text,
        start_seconds=start,
        end_seconds=end,
        probability=0.9,
        speaker=speaker,
        audio_track=audio_track,
    )


def test_rapid_pass_repeat_is_filtered_but_first_token_stays() -> None:
    words = [
        _word("Pass.", 0.00, 0.10),
        _word("Pass.", 0.12, 0.22),
        _word("Pass.", 0.24, 0.34),
        _word("Pass.", 0.36, 0.46),
        _word("Pass.", 0.48, 0.56),
    ]

    result = apply_caption_display_hygiene(words)

    assert [word.text for word in result.words] == ["Pass."]
    assert len(result.events) == 4
    assert {event.reason for event in result.events} == {"rapid_repeat_hallucination"}


def test_normal_nein_nein_nein_reaction_stays() -> None:
    words = [
        _word("nein", 0.00, 0.20),
        _word("nein", 0.33, 0.53),
        _word("nein", 0.66, 0.86),
    ]

    result = apply_caption_display_hygiene(words)

    assert [word.text for word in result.words] == ["nein", "nein", "nein"]
    assert result.events == []


def test_owner_word_suppresses_overlapping_friend_word() -> None:
    words = [
        _word("owner", 1.0, 1.5, speaker="ali", audio_track="mic"),
        _word("friend", 1.1, 1.4, speaker="friend", audio_track="discord"),
        _word("danach", 1.6, 1.9, speaker="friend", audio_track="discord"),
    ]

    result = apply_caption_display_hygiene(words)

    assert [word.text for word in result.words] == ["owner", "danach"]
    assert result.events[0].reason == "owner_overlap_priority"


def test_owner_speech_island_suppresses_false_discord_between_owner_words() -> None:
    from core.shorts_caption_hygiene import apply_caption_display_hygiene
    from models.transcript_result import TranscriptWord

    result = apply_caption_display_hygiene(
        [
            TranscriptWord(
                text="ich",
                start_seconds=0.0,
                end_seconds=1.0,
                speaker="ali",
                audio_track="mic",
            ),
            TranscriptWord(
                text="echo",
                start_seconds=1.15,
                end_seconds=1.25,
                speaker="friend",
                audio_track="discord",
            ),
            TranscriptWord(
                text="rede",
                start_seconds=1.4,
                end_seconds=2.0,
                speaker="ali",
                audio_track="mic",
            ),
        ]
    )

    assert [word.text for word in result.words] == ["ich", "rede"]
    assert any(event.reason == "owner_overlap_priority" for event in result.events)


def test_friend_after_owner_speech_island_stays_visible() -> None:
    from core.shorts_caption_hygiene import apply_caption_display_hygiene
    from models.transcript_result import TranscriptWord

    result = apply_caption_display_hygiene(
        [
            TranscriptWord(
                text="ich",
                start_seconds=0.0,
                end_seconds=1.0,
                speaker="ali",
                audio_track="mic",
            ),
            TranscriptWord(
                text="freund",
                start_seconds=2.0,
                end_seconds=2.3,
                speaker="friend",
                audio_track="discord",
            ),
        ]
    )

    assert [word.text for word in result.words] == ["ich", "freund"]
