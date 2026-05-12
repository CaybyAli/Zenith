from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.motion_analysis_runner import (
    apply_motion_analysis_run_report_to_job,
    run_motion_analysis_for_job,
)
from models.job import Job
from models.motion_analysis import (
    CLASSIFICATION_HIGH_MOTION,
    CLASSIFICATION_LOW_MOTION,
    CLASSIFICATION_STATIC,
    MotionAnalysisResult,
    MotionPoint,
    MotionSegment,
    STATUS_FAILED,
    STATUS_OK,
)
from models.motion_analysis_run import (
    MOTION_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    MOTION_RUN_STATUS_FAILED,
    MOTION_RUN_STATUS_OK,
    MOTION_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    MotionAnalysisRunReport,
)
from models.motion_analysis_source import (
    MOTION_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH,
    MOTION_SELECTED_TYPE_RAW_VIDEO_PATH,
    MOTION_SOURCE_STATUS_SELECTED,
    MotionAnalysisSourceSelection,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _fake_motion_result(input_path: str) -> MotionAnalysisResult:
    point = MotionPoint(
        time_seconds=0.0,
        frame_index=0,
        motion_score=0.0,
        raw_motion_value=0.0,
        classification=CLASSIFICATION_STATIC,
        confidence=1.0,
    )
    segment = MotionSegment(
        start_seconds=0.0,
        end_seconds=1.0,
        duration_seconds=1.0,
        avg_motion_score=0.0,
        max_motion_score=0.0,
        classification=CLASSIFICATION_LOW_MOTION,
        recommendation="none",
    )

    return MotionAnalysisResult(
        status=STATUS_OK,
        input_path=input_path,
        points=[point],
        segments=[segment],
        point_count=1,
        segment_count=1,
        low_motion_segment_count=1,
        high_motion_segment_count=0,
        dead_visual_candidate_count=0,
        duration_seconds=1.0,
        frame_sample_rate=2.0,
        recommendation="none",
        warnings=[],
        errors=[],
        metadata={"fake": True},
    )


def test_motion_analysis_run_report_roundtrip():
    source_selection = MotionAnalysisSourceSelection(
        status=MOTION_SOURCE_STATUS_SELECTED,
        selected_path="video.mp4",
        selected_type=MOTION_SELECTED_TYPE_RAW_VIDEO_PATH,
        checked_sources=[],
        source_exists=True,
        recommendation="run_motion_analysis",
    )
    motion_result = _fake_motion_result("video.mp4")

    report = MotionAnalysisRunReport(
        status=MOTION_RUN_STATUS_OK,
        source="motion_analysis_runner",
        source_selection=source_selection,
        selected_path="video.mp4",
        selected_type=MOTION_SELECTED_TYPE_RAW_VIDEO_PATH,
        motion_analysis_result=motion_result,
        motion_points=[point.to_dict() for point in motion_result.points],
        motion_segments=[segment.to_dict() for segment in motion_result.segments],
        point_count=1,
        segment_count=1,
        low_motion_segment_count=1,
        high_motion_segment_count=0,
        dead_visual_candidate_count=0,
        duration_seconds=1.0,
        frame_sample_rate=2.0,
        recommendation="none",
        warnings=[],
        errors=[],
        metadata={"unit": "test"},
    )

    restored = MotionAnalysisRunReport.from_dict(report.to_dict())

    assert restored.to_dict() == report.to_dict()


def test_run_motion_analysis_for_job_uses_raw_video_path(tmp_path, monkeypatch):
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake video placeholder")

    calls = {}

    def fake_analyze_motion(input_path, **kwargs):
        calls["input_path"] = input_path
        return _fake_motion_result(input_path)

    monkeypatch.setattr(
        "core.motion_analysis_runner.analyze_motion",
        fake_analyze_motion,
    )

    job = SimpleNamespace(raw_video_path=str(raw_video), preprocessing_manifest={})

    report = run_motion_analysis_for_job(job)

    assert report.status == MOTION_RUN_STATUS_OK
    assert report.selected_path == str(raw_video)
    assert report.selected_type == MOTION_SELECTED_TYPE_RAW_VIDEO_PATH
    assert calls["input_path"] == str(raw_video)
    assert report.point_count == 1
    assert report.segment_count == 1


def test_run_motion_analysis_for_job_uses_preprocessing_manifest_fallback(
    tmp_path,
    monkeypatch,
):
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake video placeholder")

    calls = {}

    def fake_analyze_motion(input_path, **kwargs):
        calls["input_path"] = input_path
        return _fake_motion_result(input_path)

    monkeypatch.setattr(
        "core.motion_analysis_runner.analyze_motion",
        fake_analyze_motion,
    )

    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={"source_path": str(source_video)},
    )

    report = run_motion_analysis_for_job(job)

    assert report.status == MOTION_RUN_STATUS_OK
    assert report.selected_path == str(source_video)
    assert report.selected_type == MOTION_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH
    assert calls["input_path"] == str(source_video)
    assert report.warnings


def test_missing_source_does_not_crash():
    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={},
        input_file=None,
        source_file=None,
        video_path=None,
        file_path=None,
    )

    report = run_motion_analysis_for_job(job)

    assert report.status == MOTION_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE
    assert report.selected_path is None
    assert report.point_count == 0
    assert report.segment_count == 0
    assert report.warnings


def test_missing_raw_source_is_blocked(tmp_path):
    missing_raw = tmp_path / "missing_raw.mp4"

    job = SimpleNamespace(
        raw_video_path=str(missing_raw),
        preprocessing_manifest={},
    )

    report = run_motion_analysis_for_job(job)

    assert report.status == MOTION_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE
    assert report.selected_path == str(missing_raw)
    assert report.selected_type == MOTION_SELECTED_TYPE_RAW_VIDEO_PATH
    assert report.point_count == 0
    assert report.warnings


def test_analyzer_failed_is_handled_cleanly(tmp_path, monkeypatch):
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake video placeholder")

    def fake_failed_analyze_motion(input_path, **kwargs):
        return MotionAnalysisResult(
            status=STATUS_FAILED,
            input_path=input_path,
            points=[],
            segments=[],
            point_count=0,
            segment_count=0,
            low_motion_segment_count=0,
            high_motion_segment_count=0,
            dead_visual_candidate_count=0,
            duration_seconds=None,
            frame_sample_rate=2.0,
            recommendation="review",
            warnings=[],
            errors=["fake_analyzer_failed"],
            metadata={},
        )

    monkeypatch.setattr(
        "core.motion_analysis_runner.analyze_motion",
        fake_failed_analyze_motion,
    )

    job = SimpleNamespace(raw_video_path=str(raw_video), preprocessing_manifest={})

    report = run_motion_analysis_for_job(job)

    assert report.status == MOTION_RUN_STATUS_FAILED
    assert report.errors == ["fake_analyzer_failed"]
    assert report.point_count == 0
    assert report.segment_count == 0


def test_apply_motion_analysis_run_report_to_job_writes_all_fields():
    job = SimpleNamespace()
    motion_result = _fake_motion_result("video.mp4")
    source_selection = MotionAnalysisSourceSelection(
        status=MOTION_SOURCE_STATUS_SELECTED,
        selected_path="video.mp4",
        selected_type=MOTION_SELECTED_TYPE_RAW_VIDEO_PATH,
        checked_sources=[],
        source_exists=True,
        recommendation="run_motion_analysis",
    )
    report = MotionAnalysisRunReport(
        status=MOTION_RUN_STATUS_OK,
        source_selection=source_selection,
        selected_path="video.mp4",
        selected_type=MOTION_SELECTED_TYPE_RAW_VIDEO_PATH,
        motion_analysis_result=motion_result,
        motion_points=[point.to_dict() for point in motion_result.points],
        motion_segments=[segment.to_dict() for segment in motion_result.segments],
        point_count=1,
        segment_count=1,
        low_motion_segment_count=1,
        high_motion_segment_count=0,
        dead_visual_candidate_count=0,
        duration_seconds=1.0,
        frame_sample_rate=2.0,
        recommendation="none",
    )

    updated_job = apply_motion_analysis_run_report_to_job(job, report)

    assert updated_job.motion_analysis_status == MOTION_RUN_STATUS_OK
    assert updated_job.motion_analysis_selected_path == "video.mp4"
    assert updated_job.motion_analysis_selected_type == MOTION_SELECTED_TYPE_RAW_VIDEO_PATH
    assert updated_job.motion_analysis_point_count == 1
    assert updated_job.motion_analysis_segment_count == 1
    assert updated_job.motion_analysis_low_motion_segment_count == 1
    assert updated_job.motion_analysis_high_motion_segment_count == 0
    assert updated_job.motion_analysis_dead_visual_candidate_count == 0
    assert updated_job.motion_analysis_duration_seconds == 1.0
    assert updated_job.motion_analysis_frame_sample_rate == 2.0
    assert updated_job.motion_analysis_recommendation == "none"
    assert updated_job.motion_analysis_points
    assert updated_job.motion_analysis_segments
    assert updated_job.motion_analysis_result
    assert updated_job.motion_analysis_report


def test_old_jobs_without_motion_fields_are_still_loadable():
    old_job_data = {
        "job_id": "old_job_without_motion",
        "job_type": "gaming",
        "channel_type": "gaming_main",
    }

    job = Job.from_dict(old_job_data)

    assert job.motion_analysis_report == {}
    assert job.motion_analysis_status is None
    assert job.motion_analysis_points == []
    assert job.motion_analysis_segments == []
    assert job.motion_analysis_point_count == 0
    assert job.motion_analysis_segment_count == 0


def test_job_to_dict_contains_motion_analysis_fields():
    job = Job.from_dict(
        {
            "job_id": "motion_to_dict_job",
            "job_type": "gaming",
            "channel_type": "gaming_main",
        }
    )

    data = job.to_dict()

    assert "motion_analysis_report" in data
    assert "motion_analysis_status" in data
    assert "motion_analysis_selected_path" in data
    assert "motion_analysis_selected_type" in data
    assert "motion_analysis_result" in data
    assert "motion_analysis_points" in data
    assert "motion_analysis_segments" in data
    assert "motion_analysis_point_count" in data
    assert "motion_analysis_segment_count" in data
    assert "motion_analysis_low_motion_segment_count" in data
    assert "motion_analysis_high_motion_segment_count" in data
    assert "motion_analysis_dead_visual_candidate_count" in data
    assert "motion_analysis_duration_seconds" in data
    assert "motion_analysis_frame_sample_rate" in data
    assert "motion_analysis_recommendation" in data


def test_real_opencv_mini_video_motion_runner(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    video_path = tmp_path / "runner_motion_test.avi"

    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(video_path), fourcc, 10.0, (64, 64))

    if not writer.isOpened():
        pytest.skip("opencv_video_writer_unavailable")

    try:
        for _ in range(20):
            frame = np.zeros((64, 64, 3), dtype=np.uint8)
            writer.write(frame)

        for index in range(20):
            frame = np.zeros((64, 64, 3), dtype=np.uint8)
            frame[:, : 10 + index] = 255
            writer.write(frame)
    finally:
        writer.release()

    job = SimpleNamespace(raw_video_path=str(video_path), preprocessing_manifest={})

    report = run_motion_analysis_for_job(job)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_path == str(video_path)
    assert report.selected_type == MOTION_SELECTED_TYPE_RAW_VIDEO_PATH
    assert report.point_count > 0
    assert report.segment_count > 0


def test_new_motion_runner_files_do_not_have_bom():
    files = [
        REPO_ROOT / "models" / "motion_analysis_run.py",
        REPO_ROOT / "core" / "motion_analysis_runner.py",
        REPO_ROOT / "models" / "job.py",
        REPO_ROOT / "tests" / "test_motion_analysis_runner_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_new_motion_runner_files_end_with_newline():
    files = [
        REPO_ROOT / "models" / "motion_analysis_run.py",
        REPO_ROOT / "core" / "motion_analysis_runner.py",
        REPO_ROOT / "models" / "job.py",
        REPO_ROOT / "tests" / "test_motion_analysis_runner_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
