from core.audio_track_mapping_config import AudioTrackRole
from core.multispeaker_caption_transcript import (
    merge_caption_transcript_results,
    stamp_transcript_result_for_caption_track,
)
from models.transcript_result import TranscriptResult, TranscriptSegment, TranscriptWord


def _result(text: str, start: float, end: float) -> TranscriptResult:
    return TranscriptResult(
        source_path="sample.wav",
        language="de",
        engine="test",
        full_text=text,
        segments=[
            TranscriptSegment(
                start_seconds=start,
                end_seconds=end,
                text=text,
                words=[
                    TranscriptWord(
                        start_seconds=start,
                        end_seconds=end,
                        text=text,
                        probability=0.9,
                    )
                ],
            )
        ],
    )


def test_stamp_track_sets_owner_metadata_and_absolute_times() -> None:
    track = AudioTrackRole(
        role="owner",
        audio_track="mic",
        speaker="ali",
        ffmpeg_audio_index=0,
        transcribe_for_captions=True,
    )

    stamped = stamp_transcript_result_for_caption_track(
        _result("ich", 1.0, 1.4),
        track=track,
        clip_start_seconds=60.0,
        result_source_path="raw.mp4",
    )

    segment = stamped.segments[0]
    word = segment.words[0]

    assert segment.start_seconds == 61.0
    assert segment.end_seconds == 61.4
    assert segment.audio_track == "mic"
    assert segment.speaker == "ali"
    assert word.audio_track == "mic"
    assert word.speaker == "ali"


def test_merge_keeps_owner_before_friend_when_times_match() -> None:
    owner_track = AudioTrackRole("owner", "mic", "ali", 0, True)
    friend_track = AudioTrackRole("friend", "discord", "friend", 1, True)

    owner = stamp_transcript_result_for_caption_track(
        _result("owner", 0.0, 0.4),
        track=owner_track,
        clip_start_seconds=10.0,
        result_source_path="raw.mp4",
    )
    friend = stamp_transcript_result_for_caption_track(
        _result("friend", 0.0, 0.4),
        track=friend_track,
        clip_start_seconds=10.0,
        result_source_path="raw.mp4",
    )

    merged = merge_caption_transcript_results([friend, owner], source_path="raw.mp4")

    assert [segment.speaker for segment in merged.segments] == ["ali", "friend"]
    assert merged.segments[1].audio_track == "discord"
