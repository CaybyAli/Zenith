from __future__ import annotations

from core.audio_normalizer import AudioNormalizer
from core.power_profile import PowerProfile
from core.shorts_render_driver import (
    DEFAULT_SHORTS_CAPTION_WORDS,
    ShortsRenderDriver,
    VideoCodecChoice,
    build_caption_segments,
    _group_words_into_segments,
)
from models.shorts_clip import ShortsClip
from models.shorts_reframe_plan import ShortsReframePlan
from models.transcript_result import TranscriptResult, TranscriptSegment, TranscriptWord


JOB_ID = "job_transcript_caption_smoke"
SOURCE_VIDEO_NAME = "source.mp4"
FAKE_FFMPEG_BINARY = "fake_ffmpeg_binary"
TEST_VIDEO_ENCODER = "test_video_encoder"
TEST_PROBE_CODEC = "test_probe_codec"


class FakeFFmpegHelper:
    def get_ffmpeg_path(self) -> str:
        return FAKE_FFMPEG_BINARY

    def build_ffmpeg_cmd(self, parts: list[str]) -> list[str]:
        return list(parts)

    def run_ffmpeg(self, cmd: list[str]) -> None:
        return None


class FakeCodecResolver:
    def resolve_video_codec(self, prefer_nvenc: bool) -> VideoCodecChoice:
        return VideoCodecChoice(
            encoder=TEST_VIDEO_ENCODER,
            uses_nvenc=False,
            probe_codec_names=(TEST_PROBE_CODEC,),
        )


class MockTranscriptResult:
    def __init__(self, words: list[TranscriptWord]) -> None:
        self._words = list(words)
        self.segments = []

    def all_words(self) -> list[TranscriptWord]:
        return list(self._words)


def _driver() -> ShortsRenderDriver:
    return ShortsRenderDriver(
        ffmpeg_helper=FakeFFmpegHelper(),
        ffmpeg_capability_resolver=FakeCodecResolver(),
        audio_normalizer=AudioNormalizer(),
        power_profile=PowerProfile.BALANCED,
    )


def _clip() -> ShortsClip:
    return ShortsClip(
        source_job_id=JOB_ID,
        source_start_time=2.0,
        source_end_time=8.0,
        planned_duration=6.0,
        reframe_plan=ShortsReframePlan(
            layout_type="gameplay_centered",
            ffmpeg_crop_filter="crop=1080:1920:420:0",
        ),
        hook_score=0.8,
        llm_rationale="SHOULD NOT BE USED",
        clip_index=0,
    )


def _word(start: float, text: str, probability: float = 0.9) -> TranscriptWord:
    return TranscriptWord(
        start_seconds=start,
        end_seconds=start + 0.2,
        text=text,
        probability=probability,
    )


def _transcript_with_range_words() -> TranscriptResult:
    segments = [
        TranscriptSegment(
            start_seconds=0.0,
            end_seconds=4.0,
            text="zero one two three",
            words=[
                _word(0.0, "zero"),
                _word(1.0, "one"),
                _word(2.5, "alpha"),
                _word(3.5, "bravo"),
            ],
        ),
        TranscriptSegment(
            start_seconds=4.0,
            end_seconds=8.0,
            text="four five six seven",
            words=[
                _word(4.0, "charlie"),
                _word(5.0, "delta"),
                _word(6.0, "echo"),
                _word(7.0, "foxtrot"),
            ],
        ),
        TranscriptSegment(
            start_seconds=8.0,
            end_seconds=12.0,
            text="eight nine ten eleven",
            words=[
                _word(8.5, "outside_a"),
                _word(9.0, "outside_b"),
                _word(10.0, "outside_c"),
                _word(11.0, "outside_d"),
            ],
        ),
    ]
    return TranscriptResult(
        source_path="unit.mp4",
        language="de",
        segments=segments,
        full_text=" ".join(segment.text for segment in segments),
        engine="unit",
    )


def _transcript_outside_range() -> TranscriptResult:
    segments = [
        TranscriptSegment(
            start_seconds=20.0,
            end_seconds=30.0,
            text="outside only",
            words=[
                _word(20.0, "outside_one"),
                _word(22.0, "outside_two"),
                _word(24.0, "outside_three"),
            ],
        )
    ]
    return TranscriptResult(
        source_path="unit.mp4",
        language="de",
        segments=segments,
        full_text="outside only",
        engine="unit",
    )


def test_caption_filter_uses_transcript_words_in_clip_range() -> None:
    filter_text = _driver()._caption_filter(
        clip=_clip(),
        add_captions=True,
        transcript=_transcript_with_range_words(),
    )

    assert "ALPHA" in filter_text
    assert "BRAVO" in filter_text
    assert "CHARLIE" in filter_text
    assert "DELTA" in filter_text
    assert "SHOULD NOT BE USED" not in filter_text

    for default_word in DEFAULT_SHORTS_CAPTION_WORDS:
        assert default_word.upper() not in filter_text


def test_caption_filter_falls_back_to_default_words_without_transcript() -> None:
    filter_text = _driver()._caption_filter(
        clip=_clip(),
        add_captions=True,
        transcript=None,
    )

    for default_word in DEFAULT_SHORTS_CAPTION_WORDS:
        assert default_word.upper() in filter_text


def test_shorts_driver_passes_real_word_timestamps() -> None:
    words = [
        TranscriptWord(text="bruder", start_seconds=12.40, end_seconds=12.62),
        TranscriptWord(text="das", start_seconds=12.63, end_seconds=12.82),
        TranscriptWord(text="war", start_seconds=12.83, end_seconds=13.05),
        TranscriptWord(text="komplett", start_seconds=13.06, end_seconds=13.50),
        TranscriptWord(text="krank", start_seconds=13.51, end_seconds=13.90),
    ]
    clip = ShortsClip(
        source_job_id=JOB_ID,
        source_start_time=12.40,
        source_end_time=13.90,
        planned_duration=1.5,
        reframe_plan=ShortsReframePlan(
            layout_type="gameplay_centered",
            ffmpeg_crop_filter="crop=1080:1920:420:0",
        ),
    )
    transcript = MockTranscriptResult(words=words)

    segments = build_caption_segments(clip, transcript)

    assert len(segments) >= 2
    assert segments[0].words[0].text.upper() == "BRUDER"
    assert segments[0].words[0].start_seconds == 0.0
    assert segments[0].words[1].start_seconds == round(12.63 - 12.40, 3)
    assert all(
        word.start_seconds >= 0.0
        for segment in segments
        for word in segment.words
    )


def test_grouping_respects_max_words_and_chars() -> None:
    words = [
        TranscriptWord(text="DU", start_seconds=0.0, end_seconds=0.3),
        TranscriptWord(text="MUSST", start_seconds=0.3, end_seconds=0.7),
        TranscriptWord(text="AUCH", start_seconds=0.7, end_seconds=1.0),
        TranscriptWord(text="DATEN", start_seconds=1.0, end_seconds=1.4),
        TranscriptWord(text="ANALYSIEREN", start_seconds=1.4, end_seconds=2.1),
    ]

    segments = _group_words_into_segments(words)

    assert len(segments) == 3
    for segment in segments:
        assert len(segment.words) <= 3
        assert len(" ".join(word.text for word in segment.words)) <= 14
    assert segments[0].words[0].text.upper() == "DU"
    assert segments[1].words[0].text.upper() == "DATEN"


def test_grouping_does_not_render_stolen_phrase_as_one_long_block() -> None:
    words = [
        TranscriptWord(text="GEKLAUT?", start_seconds=0.0, end_seconds=0.3),
        TranscriptWord(text="JA.", start_seconds=0.3, end_seconds=0.6),
        TranscriptWord(text="ICH", start_seconds=0.6, end_seconds=0.9),
        TranscriptWord(text="HAB", start_seconds=0.9, end_seconds=1.2),
        TranscriptWord(text="FÜR", start_seconds=1.2, end_seconds=1.5),
    ]

    segments = _group_words_into_segments(words)
    segment_texts = [" ".join(word.text for word in segment.words) for segment in segments]

    assert "GEKLAUT? JA. ICH" not in segment_texts
    assert segment_texts[:2] == ["GEKLAUT? JA.", "ICH HAB FÜR"]
    assert all(len(text) <= 14 for text in segment_texts)


def test_shorts_driver_fallback_when_no_timestamps(caplog) -> None:
    transcript = TranscriptResult(
        source_path="unit.mp4",
        language="de",
        segments=[
            TranscriptSegment(
                start_seconds=0.0,
                end_seconds=1.0,
                text="test",
                words=[
                    TranscriptWord(
                        text="test",
                        start_seconds=None,
                        end_seconds=None,
                    )
                ],
            )
        ],
        full_text="test",
        engine="unit",
    )
    clip = ShortsClip(
        source_job_id=JOB_ID,
        source_start_time=0.0,
        source_end_time=1.0,
        planned_duration=1.0,
        reframe_plan=ShortsReframePlan(
            layout_type="gameplay_centered",
            ffmpeg_crop_filter="crop=1080:1920:420:0",
        ),
    )

    filter_text = _driver()._caption_filter(
        clip=clip,
        add_captions=True,
        transcript=transcript,
    )

    assert "No word-level timestamps available" in caplog.text
    assert "TEST" in filter_text
    assert "enable='between(t" not in filter_text


def test_caption_filter_falls_back_when_transcript_has_no_overlap() -> None:
    filter_text = _driver()._caption_filter(
        clip=_clip(),
        add_captions=True,
        transcript=_transcript_outside_range(),
    )

    for default_word in DEFAULT_SHORTS_CAPTION_WORDS:
        assert default_word.upper() in filter_text
