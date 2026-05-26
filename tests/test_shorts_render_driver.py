from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from core.audio_normalizer import AudioNormalizer
from core.ffmpeg_helper import get_ffmpeg_path, get_ffprobe_path
from core.power_profile import PowerProfile
from core.shorts_render_driver import (
    AAC_AUDIO_ENCODER,
    H264_PROBE_CODEC,
    SHORTS_MOVFLAGS,
    VideoCodecChoice,
    ShortsRenderDriver,
)
from models.shorts_clip import ShortsClip
from models.shorts_reframe_plan import ShortsReframePlan

JOB_ID = "job_shorts_render_driver_test"
SOURCE_VIDEO_NAME = "source.mp4"
RESOLVER_VIDEO_ENCODER = "resolver_video_encoder"
RESOLVER_PROBE_CODEC = "resolver_probe_codec"
FAKE_FFMPEG_BINARY = "fake_ffmpeg_binary"


class FakeFFmpegHelper:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.commands: list[list[str]] = []

    def get_ffmpeg_path(self) -> str:
        return FAKE_FFMPEG_BINARY

    def build_ffmpeg_cmd(self, parts: list[str]) -> list[str]:
        return list(parts)

    def run_ffmpeg(self, cmd: list[str]) -> None:
        self.commands.append(list(cmd))
        if self.should_fail:
            raise RuntimeError("fake_ffmpeg_failure")


class FakeCodecResolver:
    def __init__(self, encoder: str = RESOLVER_VIDEO_ENCODER, uses_nvenc: bool = False) -> None:
        self.encoder = encoder
        self.uses_nvenc = uses_nvenc
        self.called = False
        self.prefer_nvenc_values: list[bool] = []

    def resolve_video_codec(self, prefer_nvenc: bool) -> VideoCodecChoice:
        self.called = True
        self.prefer_nvenc_values.append(bool(prefer_nvenc))
        return VideoCodecChoice(
            encoder=self.encoder,
            uses_nvenc=self.uses_nvenc,
            probe_codec_names=(RESOLVER_PROBE_CODEC,),
        )


def _reframe_plan(filter_string: str = "crop=1080:1920:420:0") -> ShortsReframePlan:
    return ShortsReframePlan(
        layout_type="gameplay_centered",
        ffmpeg_crop_filter=filter_string,
    )


def _clip(clip_index: int = 2) -> ShortsClip:
    return ShortsClip(
        source_job_id=JOB_ID,
        source_start_time=1.25,
        source_end_time=8.75,
        planned_duration=7.5,
        reframe_plan=_reframe_plan(),
        hook_score=0.9,
        clip_index=clip_index,
    )


def _driver(
    *,
    helper: FakeFFmpegHelper | None = None,
    resolver: FakeCodecResolver | None = None,
    power_profile: str = PowerProfile.BALANCED,
) -> tuple[ShortsRenderDriver, FakeFFmpegHelper, FakeCodecResolver]:
    fake_helper = helper or FakeFFmpegHelper()
    fake_resolver = resolver or FakeCodecResolver()
    driver = ShortsRenderDriver(
        ffmpeg_helper=fake_helper,
        ffmpeg_capability_resolver=fake_resolver,
        audio_normalizer=AudioNormalizer(),
        power_profile=power_profile,
    )
    return driver, fake_helper, fake_resolver


def test_hwaccel_fallback_converts_gpu_stack_filter_to_cpu_filter() -> None:
    driver, _, _ = _driver()
    gpu_filter = (
        "[0:v]hwdownload,format=nv12,format=yuv420p,setsar=1,"
        "split=2[facecam_src][gameplay_src];"
        "[facecam_src]crop=1920:1080:0:0,"
        "hwupload_cuda,scale_cuda=1080:640:force_original_aspect_ratio=increase,"
        "hwdownload,format=yuv420p,"
        "crop=1080:640:10:0[facecam_block];"
        "[gameplay_src]crop=1920:1080:1850:0,"
        "hwupload_cuda,scale_cuda=1080:1280:force_original_aspect_ratio=increase,"
        "hwdownload,format=yuv420p,"
        "crop=1080:1280[gameplay_block];"
        "[facecam_block][gameplay_block]vstack=inputs=2[out]"
    )
    cmd = [
        "ffmpeg",
        "-hwaccel",
        "cuda",
        "-hwaccel_output_format",
        "cuda",
        "-i",
        "input.mp4",
        "-filter_complex",
        gpu_filter,
        "-map",
        "[out]",
        "out.mp4",
    ]

    fallback = driver._strip_hwaccel_from_cmd(cmd)
    fallback = driver._strip_hwdownload_from_cmd(fallback)

    assert "-hwaccel" not in fallback
    assert "-hwaccel_output_format" not in fallback

    filter_index = fallback.index("-filter_complex") + 1
    fallback_filter = fallback[filter_index]

    assert "hwupload_cuda" not in fallback_filter
    assert "scale_cuda" not in fallback_filter
    assert "hwdownload" not in fallback_filter
    assert fallback_filter.startswith("[0:v]setsar=1")
    assert "scale=1080:640:force_original_aspect_ratio=increase" in fallback_filter
    assert "scale=1080:1280:force_original_aspect_ratio=increase" in fallback_filter


@pytest.mark.ffmpeg_integration
class TestShortsRenderDriverCommand:
    def test_output_path_uses_job_id_and_clip_index(self, tmp_path: Path) -> None:
        driver, _, _ = _driver()
        clip = _clip(clip_index=3)

        output_path = driver.render_short(
            clip=clip,
            source_video_path=SOURCE_VIDEO_NAME,
            output_dir=str(tmp_path),
            job_id=JOB_ID,
        )

        assert output_path == str(tmp_path / f"{JOB_ID}_short_3.mp4")

    def test_command_contains_trim_arguments(self, tmp_path: Path) -> None:
        driver, helper, _ = _driver()
        clip = _clip()

        driver.render_short(clip, SOURCE_VIDEO_NAME, str(tmp_path), JOB_ID)

        command = helper.commands[0]
        assert "-ss" in command
        assert "-to" in command

    def test_command_contains_ffmpeg_thread_cap(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("ZENITH_FFMPEG_THREADS", "12")
        driver, helper, _ = _driver()

        driver.render_short(_clip(), SOURCE_VIDEO_NAME, str(tmp_path), JOB_ID)

        command = helper.commands[0]
        assert "-threads" in command
        assert command[command.index("-threads") + 1] == "12"

    def test_command_contains_reframe_filter(self, tmp_path: Path) -> None:
        driver, helper, _ = _driver()
        clip = _clip()

        driver.render_short(clip, SOURCE_VIDEO_NAME, str(tmp_path), JOB_ID)

        command_text = " ".join(helper.commands[0])
        assert clip.reframe_plan is not None
        assert clip.reframe_plan.ffmpeg_crop_filter in command_text

    def test_command_contains_faststart_movflags(self, tmp_path: Path) -> None:
        driver, helper, _ = _driver()

        driver.render_short(_clip(), SOURCE_VIDEO_NAME, str(tmp_path), JOB_ID)

        command = helper.commands[0]
        assert "-movflags" in command
        assert SHORTS_MOVFLAGS in command

    def test_command_contains_aac_audio_codec(self, tmp_path: Path) -> None:
        driver, helper, _ = _driver()

        driver.render_short(_clip(), SOURCE_VIDEO_NAME, str(tmp_path), JOB_ID)

        command = helper.commands[0]
        assert "-c:a" in command
        assert AAC_AUDIO_ENCODER in command

    def test_eco_uses_crf_23(self, tmp_path: Path) -> None:
        driver, helper, _ = _driver(power_profile=PowerProfile.ECO)

        driver.render_short(_clip(), SOURCE_VIDEO_NAME, str(tmp_path), JOB_ID)

        command = helper.commands[0]
        assert "-crf" in command
        assert "23" in command

    def test_performance_uses_crf_15(self, tmp_path: Path) -> None:
        driver, helper, _ = _driver(power_profile=PowerProfile.PERFORMANCE)

        driver.render_short(_clip(), SOURCE_VIDEO_NAME, str(tmp_path), JOB_ID)

        command = helper.commands[0]
        assert "-crf" in command
        assert "15" in command

    def test_performance_nvenc_uses_p7_preset(self, tmp_path: Path) -> None:
        resolver = FakeCodecResolver(encoder="h264_nvenc", uses_nvenc=True)
        driver, helper, _ = _driver(
            resolver=resolver,
            power_profile=PowerProfile.PERFORMANCE,
        )

        driver.render_short(_clip(), SOURCE_VIDEO_NAME, str(tmp_path), JOB_ID)

        command = helper.commands[0]
        assert "-preset" in command
        assert command[command.index("-preset") + 1] == "p7"
        assert "-cq" in command
        assert "15" in command

    def test_codec_is_resolved_via_codec_resolver(self, tmp_path: Path) -> None:
        resolver = FakeCodecResolver()
        driver, helper, resolver = _driver(resolver=resolver)

        driver.render_short(_clip(), SOURCE_VIDEO_NAME, str(tmp_path), JOB_ID)

        assert resolver.called is True
        assert RESOLVER_VIDEO_ENCODER in helper.commands[0]

    def test_run_ffmpeg_failure_sets_clip_status_failed(self, tmp_path: Path) -> None:
        helper = FakeFFmpegHelper(should_fail=True)
        driver, _, _ = _driver(helper=helper)
        clip = _clip()

        with pytest.raises(RuntimeError):
            driver.render_short(clip, SOURCE_VIDEO_NAME, str(tmp_path), JOB_ID)

        assert clip.status == "failed"


def _run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        shell=False,
        capture_output=True,
        text=True,
        check=False,
    )


def _moov_before_mdat(path: Path) -> bool:
    data = path.read_bytes()
    moov_index = data.find(b"moov")
    mdat_index = data.find(b"mdat")
    return moov_index != -1 and mdat_index != -1 and moov_index < mdat_index


@pytest.mark.shorts_render_integration
def test_real_shorts_render_outputs_vertical_mp4_with_audio_and_faststart(tmp_path: Path) -> None:
    ffmpeg_path = get_ffmpeg_path()
    ffprobe_path = get_ffprobe_path()

    source_path = tmp_path / "source_with_audio.mp4"
    output_dir = tmp_path / "out"

    create_source = [
        ffmpeg_path,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=1920x1080:r=60:d=10",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=48000:d=10",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        str(source_path),
    ]
    created = _run(create_source)
    if created.returncode != 0:
        pytest.skip(f"synthetic source creation failed: {created.stderr}")

    clip = ShortsClip(
        source_job_id=JOB_ID,
        source_start_time=0.0,
        source_end_time=8.0,
        planned_duration=8.0,
        reframe_plan=_reframe_plan("crop=1080:1920:420:0"),
        clip_index=0,
    )

    driver = ShortsRenderDriver(power_profile=PowerProfile.BALANCED)
    output_path = Path(
        driver.render_short(
            clip=clip,
            source_video_path=str(source_path),
            output_dir=str(output_dir),
            job_id=JOB_ID,
        )
    )

    ffprobe_cmd = [
        ffprobe_path,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(output_path),
    ]
    probed = _run(ffprobe_cmd)
    print("ffprobe command:", ffprobe_cmd)
    print("ffprobe stdout:", probed.stdout)
    print("ffprobe stderr:", probed.stderr)

    assert probed.returncode == 0

    payload = json.loads(probed.stdout)
    streams = payload.get("streams", [])
    video_stream = next(stream for stream in streams if stream.get("codec_type") == "video")
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]

    duration = float(payload.get("format", {}).get("duration", 0.0))
    assert 7.0 <= duration <= 9.0
    assert int(video_stream.get("width")) == 1080
    assert int(video_stream.get("height")) == 1920
    assert video_stream.get("codec_name") in driver.expected_probe_codec_names()
    assert H264_PROBE_CODEC in driver.expected_probe_codec_names()
    assert audio_streams
    assert _moov_before_mdat(output_path)
    assert clip.status == "rendered"
    assert clip.output_path == str(output_path)
