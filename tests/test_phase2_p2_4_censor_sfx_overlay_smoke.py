from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.ffmpeg_helper import get_ffmpeg_path
from core.final_render_driver import FinalRenderDriver
from models.edit_timeline import EditTimeline
from models.timeline_segment import TimelineSegment


def _segment(segment_id: str, start: float, end: float, role: str = "build") -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id="job_p2_4",
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=1.0,
    )


def test_p2_4_manifest_points_to_real_wav_assets() -> None:
    manifest_path = Path("assets/sfx/censor/censor_sfx_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["default"] == "quack"
    assert "No audio overlay is rendered" not in manifest_path.read_text(encoding="utf-8")

    for name in ("quack", "dolphin", "beep"):
        asset_path = Path(manifest["options"][name]["path"])
        assert asset_path.exists(), f"Missing censor asset: {asset_path}"
        assert asset_path.suffix.lower() == ".wav"
        assert asset_path.stat().st_size > 1000


def test_p2_4_mapping_drops_removed_segments_clamps_straddles_and_defaults_sfx() -> None:
    driver = FinalRenderDriver()
    segments = [
        _segment("seg_a", 10.0, 20.0, "hook"),
        _segment("seg_b", 30.0, 40.0, "payoff"),
    ]
    job = SimpleNamespace(
        job_id="job_p2_4",
        profanity_censor_matches=[
            {
                "match_id": "inside_a",
                "start_seconds": 12.0,
                "end_seconds": 13.0,
                "censor_required": True,
                "replacement_sfx": "dolphin",
                "timing_source": "word_timestamp",
            },
            {
                "match_id": "removed_gap",
                "start_seconds": 25.0,
                "end_seconds": 26.0,
                "censor_required": True,
                "replacement_sfx": "beep",
            },
            {
                "match_id": "straddle_a",
                "start_seconds": 19.75,
                "end_seconds": 20.50,
                "censor_required": True,
                "replacement_sfx": "beep",
            },
            {
                "match_id": "default_sfx",
                "start_seconds": 31.0,
                "end_seconds": 31.4,
                "censor_required": True,
                "replacement_sfx": None,
            },
        ],
    )

    events = driver._build_censor_sfx_events(job=job, segments=segments)

    assert [event["match_id"] for event in events] == [
        "inside_a",
        "straddle_a",
        "default_sfx",
    ]

    inside, straddle, default = events

    assert inside["final_start_seconds"] == 2.0
    assert inside["duration_seconds"] == 1.0
    assert inside["replacement_sfx"] == "dolphin"

    assert straddle["final_start_seconds"] == 9.75
    assert straddle["duration_seconds"] == 0.25
    assert straddle["source_start_seconds"] == 19.75
    assert straddle["source_end_seconds"] == 20.0
    assert straddle["replacement_sfx"] == "beep"

    assert default["final_start_seconds"] == 11.0
    assert default["replacement_sfx"] == "quack"


def test_p2_4_ffmpeg_mix_contract_is_non_normalizing_and_deterministic() -> None:
    source = Path("core/final_render_driver.py").read_text(encoding="utf-8")

    assert "amix=inputs=" in source
    assert "normalize=0:duration=first" in source
    assert "aresample=48000" in source
    assert "aformat=sample_fmts=fltp:channel_layouts=stereo" in source
    assert "anullsrc=r=48000:cl=stereo" in source
    assert "adelay=" in source


def _make_silent_source(path: Path) -> None:
    ffmpeg = get_ffmpeg_path()
    cmd = [
        ffmpeg,
        "-y",
        "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=30:d=4",
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000:d=4",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _mean_volume_db(video_path: Path, start: float, duration: float) -> float:
    ffmpeg = get_ffmpeg_path()
    cmd = [
        ffmpeg,
        "-ss", f"{start:.3f}",
        "-t", f"{duration:.3f}",
        "-i", str(video_path),
        "-vn",
        "-af", "volumedetect",
        "-f", "null",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = f"{result.stdout}\n{result.stderr}"

    for line in output.splitlines():
        if "mean_volume:" not in line:
            continue
        value = line.split("mean_volume:", 1)[1].strip().split(" ", 1)[0]
        if value == "-inf":
            return -999.0
        return float(value)

    raise AssertionError(f"mean_volume not found in ffmpeg output:\n{output[-1200:]}")


@pytest.mark.ffmpeg_integration
def test_p2_4_ffmpeg_overlay_adds_audio_energy_at_mapped_censor_time(tmp_path: Path) -> None:
    source_path = tmp_path / "silent_source.mp4"
    _make_silent_source(source_path)

    job = SimpleNamespace(
        job_id="job_p2_4_integration",
        raw_video_path=str(source_path),
        profanity_censor_matches=[
            {
                "match_id": "integration_quack",
                "start_seconds": 1.50,
                "end_seconds": 1.90,
                "censor_required": True,
                "replacement_sfx": "quack",
                "timing_source": "word_timestamp",
            }
        ],
    )

    timeline = EditTimeline(
        timeline_id="timeline_p2_4_integration",
        job_id=job.job_id,
        target_duration=2.0,
        selected_segments=[
            _segment("seg_integration", 1.0, 3.0, "hook"),
        ],
        hook_segment_id="seg_integration",
        peak_segment_ids=[],
        payoff_segment_id="seg_integration",
        timeline_score=1.0,
    )

    output_path = Path(
        FinalRenderDriver().render(
            job=job,
            source_path=source_path,
            edit_timeline=timeline,
            output_dir=tmp_path,
        )
    )

    assert output_path.exists()

    context_path = tmp_path / f"{job.job_id}_final_render_driver_context.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))

    assert context["censor_sfx_applied"] is True
    assert context["censor_sfx_events_count"] == 1
    assert context["censor_sfx_events"][0]["final_start_seconds"] == 0.5

    mean_volume = _mean_volume_db(output_path, start=0.50, duration=0.35)
    assert mean_volume > -55.0
