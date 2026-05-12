from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import core.scene_change_runner as runner_module
from core.scene_change_runner import (
    apply_scene_change_run_report_to_job,
    run_scene_change_for_job,
)
from models.job import Job
from models.scene_change import SceneChangePoint, SceneChangeResult
from models.scene_change_run import SceneChangeRunReport


def _touch_mp4(path: Path) -> Path:
    path.write_bytes(b"tiny fake mp4 placeholder\n")
    return path


def _base_job_dict(**overrides):
    data = {
        "job_id": "job_scene_change_smoke",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }
    data.update(overrides)
    return data


def _fake_scene_result(input_path: str) -> SceneChangeResult:
    return SceneChangeResult(
        status="ok",
        input_path=input_path,
        scene_changes=[
            SceneChangePoint(
                time_seconds=0.5,
                frame_index=5,
                scene_score=0.91,
                change_type="hard_scene_change",
                confidence=0.95,
                reason="smoke_test",
            ),
            SceneChangePoint(
                time_seconds=1.2,
                frame_index=12,
                scene_score=0.22,
                change_type="soft_transition",
                confidence=0.55,
                reason="smoke_test",
            ),
        ],
        scene_change_count=2,
        hard_change_count=1,
        soft_transition_count=1,
        false_positive_candidate_count=0,
        threshold=0.30,
        duration_seconds=2.0,
        recommendation="scene_changes_available",
        warnings=[],
        errors=[],
        metadata={"test": "fake_detector"},
    )


def test_scene_change_run_report_roundtrip() -> None:
    report = SceneChangeRunReport(
        status="ok",
        source_selection={"status": "selected"},
        selected_path="clip.mp4",
        selected_type="raw_video_path",
        scene_change_result={"status": "ok"},
        scene_changes=[
            {
                "time_seconds": 0.5,
                "scene_score": 0.91,
                "change_type": "hard_scene_change",
            }
        ],
        scene_change_count=1,
        hard_change_count=1,
        soft_transition_count=0,
        false_positive_candidate_count=0,
        threshold=0.30,
        duration_seconds=2.0,
        recommendation="scene_changes_available",
        warnings=["demo_warning"],
        errors=[],
        metadata={"kind": "roundtrip"},
    )

    loaded = SceneChangeRunReport.from_dict(report.to_dict())

    assert loaded.status == "ok"
    assert loaded.selected_path == "clip.mp4"
    assert loaded.selected_type == "raw_video_path"
    assert loaded.scene_change_count == 1
    assert loaded.hard_change_count == 1
    assert loaded.soft_transition_count == 0
    assert loaded.false_positive_candidate_count == 0
    assert loaded.recommendation == "scene_changes_available"
    assert loaded.metadata["kind"] == "roundtrip"


def test_run_scene_change_for_job_prefers_raw_video_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_video = _touch_mp4(tmp_path / "raw.mp4")
    fallback_video = _touch_mp4(tmp_path / "fallback.mp4")
    called = {"path": None}

    def fake_analyze_scene_changes(input_path, *args, **kwargs):
        called["path"] = str(input_path)
        return _fake_scene_result(str(input_path))

    monkeypatch.setattr(
        runner_module,
        "analyze_scene_changes",
        fake_analyze_scene_changes,
    )

    job = SimpleNamespace(
        raw_video_path=str(raw_video),
        preprocessing_manifest={"source_path": str(fallback_video)},
    )

    report = run_scene_change_for_job(job)

    assert report.status == "ok"
    assert report.selected_path == str(raw_video)
    assert report.selected_type == "raw_video_path"
    assert called["path"] == str(raw_video)
    assert report.scene_change_count == 2
    assert report.hard_change_count == 1
    assert report.soft_transition_count == 1


def test_run_scene_change_for_job_uses_preprocessing_manifest_source_path_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fallback_video = _touch_mp4(tmp_path / "fallback.mp4")
    called = {"path": None}

    def fake_analyze_scene_changes(input_path, *args, **kwargs):
        called["path"] = str(input_path)
        return _fake_scene_result(str(input_path))

    monkeypatch.setattr(
        runner_module,
        "analyze_scene_changes",
        fake_analyze_scene_changes,
    )

    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={"source_path": str(fallback_video)},
    )

    report = run_scene_change_for_job(job)

    assert report.status == "ok"
    assert report.selected_path == str(fallback_video)
    assert report.selected_type in {
        "preprocessing_manifest_source_path",
        "source_path",
        "preprocessed_source_path",
    }
    assert called["path"] == str(fallback_video)
    assert report.scene_change_count == 2


def test_run_scene_change_for_job_missing_source_safe() -> None:
    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={},
    )

    report = run_scene_change_for_job(job)

    assert report.status in {
        "skipped_no_video_source",
        "skipped_no_scene_change_source",
        "failed",
    }
    assert report.scene_change_count == 0
    assert report.selected_path in {None, ""}
    assert report.recommendation in {
        "no_video_source_available",
        "no_video_source",
        "retry_or_fix_video",
        "scene_detection_failed",
    }


def test_runner_handles_detector_failed(tmp_path: Path, monkeypatch) -> None:
    raw_video = _touch_mp4(tmp_path / "raw.mp4")

    def fake_analyze_scene_changes(input_path, *args, **kwargs):
        return SceneChangeResult(
            status="failed",
            input_path=str(input_path),
            scene_changes=[],
            scene_change_count=0,
            hard_change_count=0,
            soft_transition_count=0,
            false_positive_candidate_count=0,
            threshold=0.30,
            duration_seconds=None,
            recommendation="scene_detection_failed",
            warnings=[],
            errors=["ffmpeg_unavailable"],
            metadata={"test": "detector_failed"},
        )

    monkeypatch.setattr(
        runner_module,
        "analyze_scene_changes",
        fake_analyze_scene_changes,
    )

    job = SimpleNamespace(raw_video_path=str(raw_video), preprocessing_manifest={})

    report = run_scene_change_for_job(job)

    assert report.status == "failed"
    assert report.selected_path == str(raw_video)
    assert report.selected_type == "raw_video_path"
    assert report.scene_change_count == 0
    assert "ffmpeg_unavailable" in report.errors


def test_apply_scene_change_run_report_to_job_writes_all_fields() -> None:
    job = Job.from_dict(_base_job_dict())

    report = SceneChangeRunReport(
        status="ok",
        source_selection={"status": "selected"},
        selected_path="clip.mp4",
        selected_type="raw_video_path",
        scene_change_result={"status": "ok"},
        scene_changes=[
            {
                "time_seconds": 0.5,
                "scene_score": 0.91,
                "change_type": "hard_scene_change",
            },
            {
                "time_seconds": 1.2,
                "scene_score": 0.22,
                "change_type": "soft_transition",
            },
        ],
        scene_change_count=2,
        hard_change_count=1,
        soft_transition_count=1,
        false_positive_candidate_count=0,
        threshold=0.30,
        duration_seconds=2.0,
        recommendation="scene_changes_available",
        warnings=[],
        errors=[],
        metadata={"kind": "apply_to_job"},
    )

    apply_scene_change_run_report_to_job(job, report)

    assert job.scene_change_status == "ok"
    assert job.scene_change_selected_path == "clip.mp4"
    assert job.scene_change_selected_type == "raw_video_path"
    assert job.scene_change_result["status"] == "ok"
    assert len(job.scene_changes) == 2
    assert job.scene_change_count == 2
    assert job.scene_change_hard_count == 1
    assert job.scene_change_soft_count == 1
    assert job.scene_change_false_positive_candidate_count == 0
    assert job.scene_change_threshold == 0.30
    assert job.scene_change_duration_seconds == 2.0
    assert job.scene_change_recommendation == "scene_changes_available"
    assert job.scene_change_report["metadata"]["kind"] == "apply_to_job"


def test_job_from_dict_loads_old_jobs_without_scene_change_fields() -> None:
    old_job = Job.from_dict(_base_job_dict())

    assert old_job.scene_change_report == {}
    assert old_job.scene_change_status is None
    assert old_job.scene_change_selected_path is None
    assert old_job.scene_change_selected_type is None
    assert old_job.scene_change_result == {}
    assert old_job.scene_changes == []
    assert old_job.scene_change_count == 0
    assert old_job.scene_change_hard_count == 0
    assert old_job.scene_change_soft_count == 0
    assert old_job.scene_change_false_positive_candidate_count == 0
    assert old_job.scene_change_recommendation is None


def test_job_to_dict_contains_scene_change_fields() -> None:
    job = Job.from_dict(
        _base_job_dict(
            scene_change_status="ok",
            scene_change_selected_path="clip.mp4",
            scene_change_selected_type="raw_video_path",
            scene_change_count=1,
        )
    )

    data = job.to_dict()

    expected_fields = {
        "scene_change_report",
        "scene_change_status",
        "scene_change_selected_path",
        "scene_change_selected_type",
        "scene_change_result",
        "scene_changes",
        "scene_change_count",
        "scene_change_hard_count",
        "scene_change_soft_count",
        "scene_change_false_positive_candidate_count",
        "scene_change_threshold",
        "scene_change_duration_seconds",
        "scene_change_recommendation",
    }

    missing = expected_fields - set(data)
    assert not missing, f"Missing scene_change fields in Job.to_dict(): {missing}"

    assert data["scene_change_status"] == "ok"
    assert data["scene_change_selected_path"] == "clip.mp4"
    assert data["scene_change_selected_type"] == "raw_video_path"
    assert data["scene_change_count"] == 1


def _find_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found

    common = Path(r"D:\Tools\ffmpeg\bin\ffmpeg.exe")
    if common.exists():
        return str(common)

    return None


def test_real_ffmpeg_mini_video_scene_change_detection(tmp_path: Path) -> None:
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        pytest.skip("ffmpeg not available")

    video_path = tmp_path / "black_white_blue.mp4"

    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=64x64:d=0.6:r=10",
        "-f",
        "lavfi",
        "-i",
        "color=c=white:s=64x64:d=0.6:r=10",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=64x64:d=0.6:r=10",
        "-filter_complex",
        "[0:v][1:v][2:v]concat=n=3:v=1:a=0,format=yuv420p[v]",
        "-map",
        "[v]",
        str(video_path),
    ]

    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if completed.returncode != 0:
        pytest.skip(f"ffmpeg mini video creation failed: {completed.stderr[-500:]}")

    job = SimpleNamespace(raw_video_path=str(video_path), preprocessing_manifest={})

    report = run_scene_change_for_job(job)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_path == str(video_path)
    assert report.selected_type == "raw_video_path"
    assert report.scene_change_count >= 1


def test_scene_change_runner_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("models/scene_change_source.py"),
        Path("models/scene_change_run.py"),
        Path("core/scene_change_source_selector.py"),
        Path("core/scene_change_runner.py"),
        Path("tests/test_scene_change_source_selector_smoke.py"),
        Path("tests/test_scene_change_runner_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"