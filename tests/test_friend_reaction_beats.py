from models.transcript_result import TranscriptSegment

from core.friend_reaction_beats import FriendReactionBeatConfig, build


def test_build_detects_friend_reaction_keyword() -> None:
    beats = build(
        [
            TranscriptSegment(0.0, 1.0, "ich mache den call", speaker="ali"),
            TranscriptSegment(1.2, 2.0, "boah krass", speaker="friend"),
        ]
    )

    keyword_beats = [
        beat for beat in beats if beat.beat_type == "friend_reaction_keyword"
    ]

    assert len(keyword_beats) == 1
    assert keyword_beats[0].start == 1.2
    assert keyword_beats[0].end == 2.0
    assert keyword_beats[0].friend_text == "boah krass"
    assert keyword_beats[0].evidence["keyword"] == "krass"


def test_build_detects_owner_call_pause_friend_pattern() -> None:
    beats = build(
        [
            TranscriptSegment(0.0, 1.0, "warte kurz", speaker="ali"),
            TranscriptSegment(1.8, 2.4, "ich bin da", speaker="friend"),
        ]
    )

    call_pause_beats = [
        beat for beat in beats if beat.beat_type == "owner_call_pause_friend"
    ]

    assert len(call_pause_beats) == 1
    assert call_pause_beats[0].start == 0.0
    assert call_pause_beats[0].end == 2.4
    assert call_pause_beats[0].ali_context_text == "warte kurz"
    assert call_pause_beats[0].friend_text == "ich bin da"
    assert call_pause_beats[0].evidence["gap_seconds"] == 0.8


def test_build_respects_configured_call_pause_window() -> None:
    segments = [
        TranscriptSegment(0.0, 1.0, "warte kurz", speaker="ali"),
        TranscriptSegment(1.7, 2.4, "ich bin da", speaker="friend"),
    ]

    beats = build(
        segments,
        config=FriendReactionBeatConfig(
            min_call_pause_seconds=0.1,
            max_call_pause_seconds=0.4,
        ),
    )

    assert all(beat.beat_type != "owner_call_pause_friend" for beat in beats)
