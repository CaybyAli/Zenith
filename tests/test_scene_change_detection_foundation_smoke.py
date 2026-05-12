from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from core.scene_change_detector import (
    DEFAULT_SCENE_THRESHOLD,
    DEFAULT_SOFT_THRESHOLD,
    analyze_scene_changes,
    classify_scene_change,
    filter_or_mark_near_duplicates,
    parse_ffmpeg_duration_seconds,
    parse_ffmpeg_scene_output,
)
from models.scene_change import (
    CHANGE_TYPE_FLASH,
    CHANGE_TYPE_HARD,
    CHANGE_TYPE_SOFT,
    CHANGE_TYPE_UNKNOWN,
    SCENE_STATUS_COMPLETED_WITH_WARNINGS,
    SCENE_STATUS_FAILED,
    SCENE_STATUS_OK,
    SCENE_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    SceneChangePoint,
    SceneChangeResult,
)


SAMPLE_FFMPEG_OUTPUT = """
ffmpeg version 6.1 ...
  Duration: 00:00:01.50, start: 0.000000, bitrate: 250 kb/s
[Parsed_metadata_1 @ 0x000001] frame:5    pts:500     pts_time:0.5
[Parsed_metadata_1 @ 0x000001] lavfi.scene_score=0.987654
[Parsed_metadata_1 @ 0x000001] frame:10   pts:1000    pts_time:1
[Parsed_metadata_1 @ 0x000001] lavfi.scene_score=0.452100
[Parsed_metadata_1 @ 0x000001] frame:14   pts:1400    pts_time:1.4
[Parsed_metadata_1 @ 0x000001] lavfi.scene_score=0.205000
"""


def _ffmpeg_available() -> bool:
    if shutil.which("ffmpeg"):
        return True
    return Path(r"D:\Tools\ffmpeg\bin\ffmpeg.exe").exists()


def _ffmpeg_executable() -> str:
    candidate = shutil.which("ffmpeg")
    if candidate:
        return candidate
    fallback = Path(r"D:\Tools\ffmpeg\bin\ffmpeg.exe")
    if fallback.exists():
        return str(fallback)
    raise FileNotFoundError("ffmpeg unavailable")


def _build_color_test_video(target_path: Path) -> bool:
    if not _ffmpeg_available():
        return False

    ffmpeg = _ffmpeg_executable()
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-nostats",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=64x36:d=0.5:r=10",
        "-f",
        "lavfi",
        "-i",
        "color=c=white:s=64x36:d=0.5:r=10",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=64x36:d=0.5:r=10",
        "-filter_complex",
        "[0:v][1:v][2:v]concat=n=3:v=1:a=0,format=yuv420p",
        "-t",
        "1.5",
        str(target_path),
    ]

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

    return completed.returncode == 0 and target_path.exists()


def test_scene_change_point_roundtrip() -> None:
    point = SceneChangePoint(
        time_seconds=1.25,
        frame_index=42,
        scene_score=0.78,
        change_type=CHANGE_TYPE_HARD,
        confidence=0.82,
        is_false_positive_candidate=False,
        reason="ffmpeg_scene_score",
        metadata={"source": "unit"},
        warnings=["minor"],
        errors=[],
    )

    loaded = SceneChangePoint.from_dict(point.to_dict())

    assert loaded.time_seconds == 1.25
    assert loaded.frame_index == 42
    assert loaded.scene_score == 0.78
    assert loaded.change_type == CHANGE_TYPE_HARD
    assert loaded.confidence == 0.82
    assert loaded.is_false_positive_candidate is False
    assert loaded.reason == "ffmpeg_scene_score"
    assert loaded.metadata["source"] == "unit"
    assert loaded.warnings == ["minor"]
    assert loaded.errors == []


def test_scene_change_point_invalid_change_type_falls_back_to_unknown() -> None:
    point = SceneChangePoint(time_seconds=0.5)
    point.change_type = "totally_invalid_value"

    loaded = SceneChangePoint.from_dict(point.to_dict())

    assert loaded.change_type == CHANGE_TYPE_UNKNOWN


def test_scene_change_result_roundtrip() -> None:
    result = SceneChangeResult(
        status=SCENE_STATUS_OK,
        input_path="demo.mp4",
        scene_changes=[
            SceneChangePoint(
                time_seconds=0.5,
                frame_index=5,
                scene_score=0.9,
                change_type=CHANGE_TYPE_HARD,
                confidence=0.9,
            ),
            SceneChangePoint(
                time_seconds=1.0,
                frame_index=10,
                scene_score=0.22,
                change_type=CHANGE_TYPE_SOFT,
                confidence=0.4,
            ),
        ],
        scene_change_count=2,
        hard_change_count=1,
        soft_transition_count=1,
        false_positive_candidate_count=0,
        threshold=0.30,
        duration_seconds=1.5,
        recommendation="scene_changes_available",
        warnings=["a"],
        errors=[],
        metadata={"kind": "roundtrip"},
    )

    loaded = SceneChangeResult.from_dict(result.to_dict())

    assert loaded.status == SCENE_STATUS_OK
    assert loaded.input_path == "demo.mp4"
    assert loaded.scene_change_count == 2
    assert loaded.hard_change_count == 1
    assert loaded.soft_transition_count == 1
    assert loaded.false_positive_candidate_count == 0
    assert loaded.threshold == 0.30
    assert loaded.duration_seconds == 1.5
    assert loaded.recommendation == "scene_changes_available"
    assert len(loaded.scene_changes) == 2
    assert loaded.scene_changes[0].change_type == CHANGE_TYPE_HARD
    assert loaded.scene_changes[1].change_type == CHANGE_TYPE_SOFT
    assert loaded.metadata["kind"] == "roundtrip"


def test_scene_change_result_invalid_status_falls_back_to_failed() -> None:
    result = SceneChangeResult(status="weird", input_path="x.mp4")
    result.status = "weird"

    loaded = SceneChangeResult.from_dict(result.to_dict())

    assert loaded.status == SCENE_STATUS_FAILED


def test_parse_ffmpeg_scene_output_extracts_scores() -> None:
    points = parse_ffmpeg_scene_output(SAMPLE_FFMPEG_OUTPUT)

    assert len(points) == 3
    assert points[0]["frame_index"] == 5
    assert points[0]["time_seconds"] == 0.5
    assert pytest.approx(points[0]["scene_score"], rel=1e-3) == 0.987654
    assert points[1]["frame_index"] == 10
    assert points[1]["time_seconds"] == 1.0
    assert pytest.approx(points[1]["scene_score"], rel=1e-3) == 0.4521
    assert points[2]["frame_index"] == 14
    assert points[2]["time_seconds"] == 1.4
    assert pytest.approx(points[2]["scene_score"], rel=1e-3) == 0.205


def test_parse_ffmpeg_duration_extracts_seconds() -> None:
    duration = parse_ffmpeg_duration_seconds(SAMPLE_FFMPEG_OUTPUT)

    assert duration == pytest.approx(1.5, rel=1e-6)


def test_parse_ffmpeg_scene_output_handles_empty_text() -> None:
    assert parse_ffmpeg_scene_output("") == []
    assert parse_ffmpeg_scene_output("no scene info here\nrandom data") == []


def test_classify_hard_scene_change() -> None:
    assert (
        classify_scene_change(
            0.85,
            scene_threshold=DEFAULT_SCENE_THRESHOLD,
            soft_threshold=DEFAULT_SOFT_THRESHOLD,
        )
        == CHANGE_TYPE_HARD
    )


def test_classify_soft_transition() -> None:
    assert (
        classify_scene_change(
            0.22,
            scene_threshold=DEFAULT_SCENE_THRESHOLD,
            soft_threshold=DEFAULT_SOFT_THRESHOLD,
        )
        == CHANGE_TYPE_SOFT
    )


def test_classify_below_soft_returns_unknown() -> None:
    assert (
        classify_scene_change(
            0.05,
            scene_threshold=DEFAULT_SCENE_THRESHOLD,
            soft_threshold=DEFAULT_SOFT_THRESHOLD,
        )
        == CHANGE_TYPE_UNKNOWN
    )


def test_flash_or_explosion_candidate_is_marked() -> None:
    points = [
        SceneChangePoint(
            time_seconds=2.00,
            scene_score=0.95,
            change_type=CHANGE_TYPE_HARD,
            confidence=0.95,
        ),
        SceneChangePoint(
            time_seconds=2.20,
            scene_score=0.97,
            change_type=CHANGE_TYPE_HARD,
            confidence=0.97,
        ),
        SceneChangePoint(
            time_seconds=8.00,
            scene_score=0.55,
            change_type=CHANGE_TYPE_HARD,
            confidence=0.7,
        ),
    ]

    filtered = filter_or_mark_near_duplicates(
        points,
        min_distance_seconds=0.1,
        flash_neighbor_window_seconds=0.4,
        flash_threshold=0.85,
    )

    assert len(filtered) == 3
    flash_points = [p for p in filtered if p.change_type == CHANGE_TYPE_FLASH]
    assert len(flash_points) >= 1
    assert any(p.is_false_positive_candidate for p in filtered)
    isolated = [p for p in filtered if p.time_seconds == 8.00][0]
    assert isolated.change_type == CHANGE_TYPE_HARD
    assert isolated.is_false_positive_candidate is False


def test_filter_near_duplicates_collapses_within_min_distance() -> None:
    points = [
        SceneChangePoint(
            time_seconds=0.10,
            scene_score=0.40,
            change_type=CHANGE_TYPE_HARD,
        ),
        SceneChangePoint(
            time_seconds=0.15,
            scene_score=0.85,
            change_type=CHANGE_TYPE_HARD,
        ),
        SceneChangePoint(
            time_seconds=2.00,
            scene_score=0.50,
            change_type=CHANGE_TYPE_HARD,
        ),
    ]

    filtered = filter_or_mark_near_duplicates(
        points,
        min_distance_seconds=0.25,
        flash_neighbor_window_seconds=0.4,
        flash_threshold=0.99,
    )

    assert len(filtered) == 2
    assert filtered[0].time_seconds == 0.15
    assert filtered[1].time_seconds == 2.00


def test_analyze_scene_changes_missing_input_does_not_crash(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.mp4"

    result = analyze_scene_changes(missing)

    assert result.status == SCENE_STATUS_FAILED
    assert "input_file_missing" in result.errors
    assert result.scene_change_count == 0
    assert result.threshold == DEFAULT_SCENE_THRESHOLD


def test_analyze_scene_changes_unsupported_extension_skipped(tmp_path: Path) -> None:
    audio = tmp_path / "voice.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")

    result = analyze_scene_changes(audio)

    assert result.status == SCENE_STATUS_SKIPPED_NO_VIDEO_SOURCE
    assert result.scene_change_count == 0
    assert "unsupported_video_extension" in result.warnings
    assert result.recommendation == "no_video_source"


def test_analyze_scene_changes_ffmpeg_unavailable_does_not_crash(tmp_path: Path) -> None:
    fake_video = tmp_path / "fake_video.mp4"
    fake_video.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"\x00" * 64)

    bad_ffmpeg = tmp_path / "definitely_missing_ffmpeg.exe"

    result = analyze_scene_changes(
        fake_video,
        ffmpeg_path_override=str(bad_ffmpeg),
    )

    assert result.status == SCENE_STATUS_FAILED
    assert "ffmpeg_unavailable" in result.errors
    assert result.scene_change_count == 0


def test_analyze_scene_changes_real_video_when_ffmpeg_available(tmp_path: Path) -> None:
    if not _ffmpeg_available():
        pytest.skip("ffmpeg not available on this machine")

    test_video = tmp_path / "color_scenes.mp4"
    if not _build_color_test_video(test_video):
        pytest.skip("ffmpeg lavfi could not create a test video")

    result = analyze_scene_changes(
        test_video,
        scene_threshold=0.30,
        soft_threshold=0.18,
    )

    assert result.status in {SCENE_STATUS_OK, SCENE_STATUS_COMPLETED_WITH_WARNINGS}
    assert result.input_path == str(test_video)
    assert isinstance(result.scene_change_count, int)
    assert result.scene_change_count >= 1
    assert result.threshold == 0.30
    assert result.recommendation
    assert result.scene_change_count == len(result.scene_changes)
    assert result.hard_change_count + result.soft_transition_count >= 1


def test_analyze_scene_changes_result_has_required_fields(tmp_path: Path) -> None:
    missing = tmp_path / "missing.mp4"

    result = analyze_scene_changes(missing)
    payload = result.to_dict()

    for required_key in (
        "status",
        "input_path",
        "scene_changes",
        "scene_change_count",
        "hard_change_count",
        "soft_transition_count",
        "false_positive_candidate_count",
        "threshold",
        "duration_seconds",
        "recommendation",
        "warnings",
        "errors",
        "metadata",
    ):
        assert required_key in payload


def test_scene_change_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("models/scene_change.py"),
        Path("core/scene_change_detector.py"),
        Path("tests/test_scene_change_detection_foundation_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"
