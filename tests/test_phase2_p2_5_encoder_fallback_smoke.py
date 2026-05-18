from __future__ import annotations

from types import SimpleNamespace

import core.final_render_driver as frd
from core.final_render_driver import FinalRenderDriver


class _Report:
    def __init__(self, has_h264: bool, has_nvenc: bool, status: str = "ffmpeg_capability_ready"):
        self.has_h264 = has_h264
        self.has_nvenc = has_nvenc
        self.status = status


def test_p2_5_resolves_nvenc_when_capability_and_runtime_probe_pass(monkeypatch) -> None:
    driver = FinalRenderDriver()

    monkeypatch.setattr(frd, "resolve_ffmpeg_capabilities", lambda job: _Report(True, True))
    monkeypatch.setattr(driver, "_probe_video_encoder_runtime", lambda encoder: True)

    encoder = driver._resolve_video_encoder(SimpleNamespace(job_id="job_encoder_nvenc"))

    assert encoder["codec"] == "h264_nvenc"
    assert encoder["mode"] == "nvenc"
    assert encoder["ffmpeg_args"] == ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]
    assert encoder["fallback_reason"] is None


def test_p2_5_falls_back_to_libx264_when_nvenc_missing(monkeypatch) -> None:
    driver = FinalRenderDriver()

    monkeypatch.setattr(frd, "resolve_ffmpeg_capabilities", lambda job: _Report(True, False))

    encoder = driver._resolve_video_encoder(SimpleNamespace(job_id="job_encoder_cpu"))

    assert encoder["codec"] == "libx264"
    assert encoder["mode"] == "cpu_fallback"
    assert encoder["ffmpeg_args"] == ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]
    assert encoder["fallback_reason"] == "nvenc_not_available"


def test_p2_5_falls_back_to_libx264_when_nvenc_runtime_fails(monkeypatch) -> None:
    driver = FinalRenderDriver()

    monkeypatch.setattr(frd, "resolve_ffmpeg_capabilities", lambda job: _Report(True, True))
    monkeypatch.setattr(driver, "_probe_video_encoder_runtime", lambda encoder: False)

    encoder = driver._resolve_video_encoder(SimpleNamespace(job_id="job_encoder_runtime_fail"))

    assert encoder["codec"] == "libx264"
    assert encoder["mode"] == "cpu_fallback"
    assert encoder["fallback_reason"] == "nvenc_runtime_probe_failed"


def test_p2_5_final_render_driver_no_longer_hardcodes_context_to_nvenc() -> None:
    source = open("core/final_render_driver.py", encoding="utf-8").read()

    assert '"codec_video": "h264_nvenc"' not in source
    assert '"codec_video": video_encoder["codec"]' in source
    assert "video_encoder_mode" in source
    assert "video_encoder_fallback_reason" in source


import json
import subprocess
from pathlib import Path

import pytest

from core.ffmpeg_helper import get_ffmpeg_path
from models.edit_timeline import EditTimeline
from models.timeline_segment import TimelineSegment


def _make_p2_5_source(path: Path) -> None:
    ffmpeg = get_ffmpeg_path()
    cmd = [
        ffmpeg,
        "-y",
        "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=2",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


@pytest.mark.ffmpeg_integration
def test_p2_5_cpu_fallback_encoder_can_render_real_clip(tmp_path, monkeypatch) -> None:
    source_path = tmp_path / "p2_5_cpu_source.mp4"
    _make_p2_5_source(source_path)

    driver = FinalRenderDriver()

    monkeypatch.setattr(
        driver,
        "_resolve_video_encoder",
        lambda job: {
            "codec": "libx264",
            "mode": "cpu_fallback",
            "ffmpeg_args": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"],
            "resolver_status": "forced_test_cpu_fallback",
            "fallback_reason": "forced_test_cpu_fallback",
            "has_h264": True,
            "has_nvenc": False,
            "nvenc_runtime_ok": False,
        },
    )

    job = SimpleNamespace(
        job_id="job_p2_5_cpu_fallback",
        raw_video_path=str(source_path),
        profanity_censor_matches=[],
    )

    timeline = EditTimeline(
        timeline_id="timeline_p2_5_cpu_fallback",
        job_id=job.job_id,
        target_duration=1.0,
        selected_segments=[
            TimelineSegment(
                segment_id="seg_p2_5_cpu",
                job_id=job.job_id,
                candidate_id=None,
                start_time=0.25,
                end_time=1.25,
                segment_role="hook",
                selection_score=1.0,
            )
        ],
        hook_segment_id="seg_p2_5_cpu",
        peak_segment_ids=[],
        payoff_segment_id="seg_p2_5_cpu",
        timeline_score=1.0,
    )

    output_path = Path(
        driver.render(
            job=job,
            source_path=source_path,
            edit_timeline=timeline,
            output_dir=tmp_path,
        )
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 1000

    context_path = tmp_path / f"{job.job_id}_final_render_driver_context.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))

    assert context["codec_video"] == "libx264"
    assert context["video_encoder_mode"] == "cpu_fallback"
    assert context["video_encoder_fallback_reason"] == "forced_test_cpu_fallback"
