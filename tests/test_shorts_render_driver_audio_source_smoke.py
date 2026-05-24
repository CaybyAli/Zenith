from __future__ import annotations

from pathlib import Path

from core.audio_normalizer import AudioNormalizer
from core.power_profile import PowerProfile
from core.shorts_render_driver import ShortsRenderDriver, VideoCodecChoice
from models.shorts_clip import ShortsClip
from models.shorts_reframe_plan import ShortsReframePlan

JOB_ID = "job_shorts_audio_source_test"
FAKE_FFMPEG_BINARY = "fake_ffmpeg_binary"
TEST_VIDEO_ENCODER = "test_video_encoder"
TEST_PROBE_CODEC = "test_probe_codec"


class FakeFFmpegHelper:
    def get_ffmpeg_path(self) -> str:
        return FAKE_FFMPEG_BINARY

    def build_ffmpeg_cmd(self, parts: list[str]) -> list[str]:
        return list(parts)


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
        source_start_time=1.0,
        source_end_time=5.0,
        planned_duration=4.0,
        reframe_plan=ShortsReframePlan(
            layout_type="gameplay_centered",
            ffmpeg_crop_filter="crop=1080:1920:420:0",
        ),
        clip_index=0,
    )


def test_render_command_uses_raw_mixed_audio_when_available(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.mp4"
    raw_mixed_audio_path = tmp_path / "raw_mixed_audio.mp4"
    raw_path.touch()
    raw_mixed_audio_path.touch()

    command = _driver().build_render_command(
        clip=_clip(),
        source_video_path=str(raw_path),
        output_path=str(tmp_path / "short.mp4"),
        add_captions=False,
    )

    assert command.count("-i") == 2
    assert "-map" in command
    assert "0:v" in command
    assert "1:a" in command
    assert str(raw_mixed_audio_path) in command


def test_render_command_falls_back_to_raw_audio_when_mixed_file_missing(
    tmp_path: Path,
    caplog,
) -> None:
    raw_path = tmp_path / "raw.mp4"
    raw_path.touch()

    command = _driver().build_render_command(
        clip=_clip(),
        source_video_path=str(raw_path),
        output_path=str(tmp_path / "short.mp4"),
        add_captions=False,
    )

    assert command.count("-i") == 1
    assert "1:a" not in command
    assert "raw_mixed_audio.mp4 not found, falling back to raw.mp4 audio" in caplog.text
