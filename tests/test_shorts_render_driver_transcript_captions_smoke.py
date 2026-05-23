from __future__ import annotations

from core.audio_normalizer import AudioNormalizer
from core.power_profile import PowerProfile
from core.shorts_render_driver import (
    DEFAULT_SHORTS_CAPTION_WORDS,
    ShortsRenderDriver,
    VideoCodecChoice,
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

    assert "alpha" in filter_text
    assert "bravo" in filter_text
    assert "charlie" in filter_text
    assert "delta" in filter_text
    assert "SHOULD NOT BE USED" not in filter_text

    for default_word in DEFAULT_SHORTS_CAPTION_WORDS:
        assert default_word not in filter_text


def test_caption_filter_falls_back_to_default_words_without_transcript() -> None:
    filter_text = _driver()._caption_filter(
        clip=_clip(),
        add_captions=True,
        transcript=None,
    )

    for default_word in DEFAULT_SHORTS_CAPTION_WORDS:
        assert default_word in filter_text


def test_caption_filter_falls_back_when_transcript_has_no_overlap() -> None:
    filter_text = _driver()._caption_filter(
        clip=_clip(),
        add_captions=True,
        transcript=_transcript_outside_range(),
    )

    for default_word in DEFAULT_SHORTS_CAPTION_WORDS:
        assert default_word in filter_text
