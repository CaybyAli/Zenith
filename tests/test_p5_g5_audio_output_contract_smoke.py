
from types import SimpleNamespace
import subprocess

from core.final_render_driver import FinalRenderDriver
from core.shorts_render_driver import ShortsRenderDriver, VideoCodecChoice


def _values_after(cmd: list[str], option: str) -> list[str]:
    return [cmd[index + 1] for index, part in enumerate(cmd[:-1]) if part == option]


def test_p5_g5_longform_uses_raw_mixed_audio_and_outputs_48k_stereo(tmp_path, monkeypatch):
    source = tmp_path / "raw.mp4"
    raw_mixed = tmp_path / "raw_mixed_audio.mp4"
    temp_out = tmp_path / "segment.mp4"
    source.write_bytes(b"fake")
    raw_mixed.write_bytes(b"fake")

    captured = {}

    def fake_run(cmd, *args, **kwargs):
        captured["cmd"] = list(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    driver = FinalRenderDriver()
    monkeypatch.setattr(driver, "_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(subprocess, "run", fake_run)

    segment = SimpleNamespace(
        segment_id="seg_audio_contract",
        segment_role="hook",
        start_time=10.0,
        end_time=20.0,
        duration=10.0,
    )

    driver._extract_segment(
        source=source,
        segment=segment,
        filter_complex="[0:v]null[out]",
        out_label="[out]",
        temp_path=temp_out,
        video_encoder={"ffmpeg_args": ["-c:v", "libx264"]},
    )

    cmd = captured["cmd"]
    assert str(raw_mixed) in cmd
    assert "1:a:0?" in _values_after(cmd, "-map")
    assert _values_after(cmd, "-ar")[-1] == "48000"
    assert _values_after(cmd, "-ac")[-1] == "2"


def test_p5_g5_shorts_render_command_outputs_48k_stereo():
    helper = SimpleNamespace(
        get_ffmpeg_path=lambda: "ffmpeg",
        build_ffmpeg_cmd=lambda parts: list(parts),
    )
    resolver = SimpleNamespace(
        resolve_video_codec=lambda prefer_nvenc: VideoCodecChoice(
            encoder="libx264",
            uses_nvenc=False,
            probe_codec_names=("h264",),
        )
    )
    driver = ShortsRenderDriver(
        ffmpeg_helper=helper,
        ffmpeg_capability_resolver=resolver,
    )

    clip = SimpleNamespace(
        clip_index=1,
        source_start_time=1.0,
        source_end_time=4.0,
        reframe_plan=SimpleNamespace(ffmpeg_crop_filter="scale=1080:1920"),
        hook_score=0.0,
    )

    cmd = driver.build_render_command(
        clip=clip,
        source_video_path="raw.mp4",
        output_path="short.mp4",
        add_captions=False,
        transcript=None,
    )

    assert _values_after(cmd, "-ar")[-1] == "48000"
    assert _values_after(cmd, "-ac")[-1] == "2"

    audio_filters = _values_after(cmd, "-af")
    assert audio_filters
    assert "aresample=48000" in audio_filters[-1]
    assert "channel_layouts=stereo" in audio_filters[-1]
