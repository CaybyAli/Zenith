from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from core.ffmpeg_helper import get_ffmpeg_path
from core.music_apply_processor import (
    MusicApplyProcessor,
    build_music_apply_filter_complex,
    build_music_apply_ffmpeg_command,
)
from models.music_apply_segment import MusicApplySegment
from models.music_apply_timeline import MusicApplyTimeline


def _ffmpeg_or_skip() -> str:
    try:
        return get_ffmpeg_path()
    except FileNotFoundError as exc:
        pytest.skip(str(exc))


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr or completed.stdout


def _create_sample_video(output_path: Path) -> None:
    ffmpeg = _ffmpeg_or_skip()
    _run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=96x54:rate=10:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=48000:duration=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
    )


def _create_sample_music(output_path: Path) -> None:
    ffmpeg = _ffmpeg_or_skip()
    _run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=2",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    )


def _sample_timeline(music_path: Path) -> MusicApplyTimeline:
    return MusicApplyTimeline(
        timeline_id="timeline-001",
        job_id="job-001",
        channel_type="gaming_main",
        segments=[
            MusicApplySegment(
                segment_id="segment-001",
                job_id="job-001",
                asset_id="asset-001",
                cue_kind="intro_bed",
                source_file_path=str(music_path),
                video_start_time=0.25,
                video_end_time=1.75,
                music_offset_start=0.0,
                music_offset_end=1.5,
                music_level=-1.25,
                voice_priority=0.9,
                ducking_required=True,
                fade_in_seconds=0.1,
                fade_out_seconds=0.2,
            )
        ],
    )


def test_apply_passes_through_when_timeline_is_none(tmp_path):
    rendered_path = tmp_path / "rendered.mp4"

    result = MusicApplyProcessor().apply(
        rendered_video_path=rendered_path,
        music_application_plan=None,
        channel_type="gaming_main",
        music_apply_timeline=None,
    )

    assert result == {
        "music_applied": False,
        "output_video_path": str(rendered_path),
    }


def test_apply_passes_through_when_timeline_is_empty(tmp_path):
    rendered_path = tmp_path / "rendered.mp4"
    timeline = MusicApplyTimeline(
        timeline_id="timeline-empty",
        job_id="job-001",
        channel_type="gaming_main",
        segments=[],
    )

    result = MusicApplyProcessor().apply(
        rendered_video_path=rendered_path,
        music_application_plan=None,
        channel_type="gaming_main",
        music_apply_timeline=timeline,
    )

    assert result == {
        "music_applied": False,
        "output_video_path": str(rendered_path),
    }


def test_build_music_apply_command_contains_recipe_chain(tmp_path):
    rendered_path = tmp_path / "rendered.mp4"
    music_path = tmp_path / "music.wav"
    timeline = _sample_timeline(music_path)
    filter_complex = build_music_apply_filter_complex(timeline.segments)
    command = build_music_apply_ffmpeg_command(
        rendered_video_path=rendered_path,
        segments=timeline.segments,
        output_video_path=tmp_path / "rendered_music_applied.mp4",
        music_ducked_stem_path=tmp_path / "rendered_music_ducked_stem.flac",
    )

    assert "atrim=start=0:end=1.5,asetpts=PTS-STARTPTS,volume=-1.25dB" in filter_complex
    assert "afade=t=in:st=0:d=0.1" in filter_complex
    assert "afade=t=out:st=1.3:d=0.2" in filter_complex
    assert "adelay=250:all=1[musicSegment1]" in filter_complex
    assert "[musicbed]dynaudnorm=f=250:g=31:m=8:p=0.9,acompressor=threshold=0.05:ratio=6:attack=20:release=250:makeup=8[music_const]" in filter_complex
    assert "[music_const]volume=-34.0dB[music_bed]" in filter_complex
    assert "[music_bed][0:a]sidechaincompress=threshold=0.03:ratio=3:attack=150:release=700[music_ducked_prelimit]" in filter_complex
    assert "[music_ducked_prelimit]volume=13.0dB,alimiter=limit=0.06309573:attack=5:release=80:level=0,volume=-13.0dB[music_ducked]" in filter_complex
    assert "[0:a][music_ducked_mix]amix=inputs=2:duration=first:dropout_transition=0,volume=1.0[aout]" in filter_complex
    assert command[command.index("-c:v") + 1] == "copy"


def test_apply_non_empty_timeline_renders_music_mix_and_stem(tmp_path):
    rendered_path = tmp_path / "rendered.mp4"
    music_path = tmp_path / "music.wav"
    _create_sample_video(rendered_path)
    _create_sample_music(music_path)
    timeline = _sample_timeline(music_path)

    result = MusicApplyProcessor().apply(
        rendered_video_path=rendered_path,
        music_application_plan=None,
        channel_type="gaming_main",
        music_apply_timeline=timeline,
    )

    assert result["music_applied"] is True
    assert result["output_video_path"] == str(tmp_path / "rendered_music_applied.mp4")
    assert result["music_apply_timeline_id"] == "timeline-001"
    assert result["music_apply_segment_count"] == 1
    assert result["applied_music_segment_count"] == 1
    assert Path(result["output_video_path"]).exists()
    assert Path(result["music_ducked_stem_path"]).exists()
