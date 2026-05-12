from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.stutter_detection_runner import (
    apply_stutter_detection_run_report_to_job,
    run_stutter_detection_for_job,
)
from models.job import Job
from models.stutter_detection import (
    CLASSIFICATION_DUPLICATE_FRAME_CANDIDATE,
    CLASSIFICATION_STUTTER_SEGMENT,
    StutterDetectionResult,
    StutterFramePoint,
    StutterSegment,
)
from models.stutter_detection_run import (
    STUTTER_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    STUTTER_RUN_STATUS_FAILED,
    STUTTER_RUN_STATUS_OK,
    STUTTER_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    StutterDetectionRunReport,
)
from models.stutter_detection_source import (
    STUTTER_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH,
    STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH,
    STUTTER_SOURCE_STATUS_SELECTED,
    StutterDetectionSourceSelection,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _fake_stutter_result(input_path: str) -> StutterDetectionResult:
    point = StutterFramePoint(
        time_seconds=0.1,
        frame_index=1,
        frame_hash="1" * 64,
        previous_frame_hash="1" * 64,
        duplicate_score=0.995,
        difference_score=0.005,
        is_duplicate_candidate=True,
        classification=CLASSIFICATION_DUPLICATE_FRAME_CANDIDATE,
        confidence=0.995,
    )
    segment = StutterSegment(
        start_seconds=0.0,
        end_seconds=0.5,
        duration_seconds=0.5,
        start_frame_index=1,
        end_frame_index=4,
        duplicate_frame_count=4,
        avg_duplicate_score=0.995,
        max_duplicate_score=0.999,
        classification=CLASSIFICATION_STUTTER_SEGMENT,
        recommendation="review_stutter_segment",
    )

    return StutterDetectionResult(
        status="ok",
        input_path=input_path,
        points=[point],
        segments=[segment],
        point_count=1,
        segment_count=1,
        duplicate_candidate_count=1,
        stutter_segment_count=1,
        freeze_segment_count=0,
        duration_seconds=1.0,
        frame_sample_rate=10.0,
        recommendation="review_stutter_segment",
        warnings=[],
        errors=[],
        metadata={"fake": True},
    )


def test_stutter_detection_run_report_roundtrip():
    source_selection = StutterDetectionSourceSelection(
        status=STUTTER_SOURCE_STATUS_SELECTED,
        selected_path="video.mp4",
        selected_type=STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH,
        checked_sources=[],
        source_exists=True,
        recommendation="run_stutter_detection",
    )
    stutter_result = _fake_stutter_result("video.mp4")

    report = StutterDetectionRunReport(
        status=STUTTER_RUN_STATUS_OK,
        source="stutter_detection_runner",
        source_selection=source_selection,
        selected_path="video.mp4",
        selected_type=STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH,
        stutter_detection_result=stutter_result,
        stutter_points=[point.to_dict() for point in stutter_result.points],
        stutter_segments=[
            segment.to_dict() for segment in stutter_result.segments
        ],
        point_count=1,
        segment_count=1,
        duplicate_candidate_count=1,
        stutter_segment_count=1,
        freeze_segment_count=0,
        duration_seconds=1.0,
        frame_sample_rate=10.0,
        recommendation="review_stutter_segment",
        warnings=[],
        errors=[],
        metadata={"unit": "test"},
    )

    restored = StutterDetectionRunReport.from_dict(report.to_dict())

    assert restored.to_dict() == report.to_dict()


def test_run_stutter_detection_for_job_uses_raw_video_path(tmp_path, monkeypatch):
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake video placeholder")

    calls = {}

    def fake_analyze_stutter_frames(input_path, **kwargs):
        calls["input_path"] = input_path
        return _fake_stutter_result(input_path)

    monkeypatch.setattr(
        "core.stutter_detection_runner.analyze_stutter_frames",
        fake_analyze_stutter_frames,
    )

    job = SimpleNamespace(raw_video_path=str(raw_video), preprocessing_manifest={})

    report = run_stutter_detection_for_job(job)

    assert report.status == STUTTER_RUN_STATUS_OK
    assert report.selected_path == str(raw_video)
    assert report.selected_type == STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH
    assert calls["input_path"] == str(raw_video)
    assert report.point_count == 1
    assert report.segment_count == 1


def test_run_stutter_detection_for_job_uses_preprocessing_manifest_fallback(
    tmp_path,
    monkeypatch,
):
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake video placeholder")

    calls = {}

    def fake_analyze_stutter_frames(input_path, **kwargs):
        calls["input_path"] = input_path
        return _fake_stutter_result(input_path)

    monkeypatch.setattr(
        "core.stutter_detection_runner.analyze_stutter_frames",
        fake_analyze_stutter_frames,
    )

    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={"source_path": str(source_video)},
    )

    report = run_stutter_detection_for_job(job)

    assert report.status == STUTTER_RUN_STATUS_OK
    assert report.selected_path == str(source_video)
    assert report.selected_type == STUTTER_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH
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

    report = run_stutter_detection_for_job(job)

    assert report.status == STUTTER_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE
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

    report = run_stutter_detection_for_job(job)

    assert report.status == STUTTER_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE
    assert report.selected_path == str(missing_raw)
    assert report.selected_type == STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH
    assert report.point_count == 0
    assert report.warnings


def test_analyzer_failed_is_handled_cleanly(tmp_path, monkeypatch):
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake video placeholder")

    def fake_failed_analyze_stutter_frames(input_path, **kwargs):
        return StutterDetectionResult(
            status="failed",
            input_path=input_path,
            points=[],
            segments=[],
            point_count=0,
            segment_count=0,
            duplicate_candidate_count=0,
            stutter_segment_count=0,
            freeze_segment_count=0,
            duration_seconds=None,
            frame_sample_rate=10.0,
            recommendation="stutter_detection_failed",
            warnings=[],
            errors=["fake_analyzer_failed"],
            metadata={},
        )

    monkeypatch.setattr(
        "core.stutter_detection_runner.analyze_stutter_frames",
        fake_failed_analyze_stutter_frames,
    )

    job = SimpleNamespace(raw_video_path=str(raw_video), preprocessing_manifest={})

    report = run_stutter_detection_for_job(job)

    assert report.status == STUTTER_RUN_STATUS_FAILED
    assert report.errors == ["fake_analyzer_failed"]
    assert report.point_count == 0
    assert report.segment_count == 0


def test_apply_stutter_detection_run_report_to_job_writes_all_fields():
    job = SimpleNamespace()
    stutter_result = _fake_stutter_result("video.mp4")
    source_selection = StutterDetectionSourceSelection(
        status=STUTTER_SOURCE_STATUS_SELECTED,
        selected_path="video.mp4",
        selected_type=STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH,
        checked_sources=[],
        source_exists=True,
        recommendation="run_stutter_detection",
    )
    report = StutterDetectionRunReport(
        status=STUTTER_RUN_STATUS_OK,
        source_selection=source_selection,
        selected_path="video.mp4",
        selected_type=STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH,
        stutter_detection_result=stutter_result,
        stutter_points=[point.to_dict() for point in stutter_result.points],
        stutter_segments=[
            segment.to_dict() for segment in stutter_result.segments
        ],
        point_count=1,
        segment_count=1,
        duplicate_candidate_count=1,
        stutter_segment_count=1,
        freeze_segment_count=0,
        duration_seconds=1.0,
        frame_sample_rate=10.0,
        recommendation="review_stutter_segment",
    )

    updated_job = apply_stutter_detection_run_report_to_job(job, report)

    assert updated_job.stutter_detection_status == STUTTER_RUN_STATUS_OK
    assert updated_job.stutter_detection_selected_path == "video.mp4"
    assert updated_job.stutter_detection_selected_type == STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH
    assert updated_job.stutter_detection_point_count == 1
    assert updated_job.stutter_detection_segment_count == 1
    assert updated_job.stutter_detection_duplicate_candidate_count == 1
    assert updated_job.stutter_detection_stutter_segment_count == 1
    assert updated_job.stutter_detection_freeze_segment_count == 0
    assert updated_job.stutter_detection_duration_seconds == 1.0
    assert updated_job.stutter_detection_frame_sample_rate == 10.0
    assert updated_job.stutter_detection_recommendation == "review_stutter_segment"
    assert updated_job.stutter_detection_points
    assert updated_job.stutter_detection_segments
    assert updated_job.stutter_detection_result
    assert updated_job.stutter_detection_report


def test_old_jobs_without_stutter_detection_fields_are_still_loadable():
    old_job_data = {
        "job_id": "old_job_without_stutter_detection",
        "job_type": "gaming",
        "channel_type": "gaming_main",
    }

    job = Job.from_dict(old_job_data)

    assert job.stutter_detection_report == {}
    assert job.stutter_detection_status is None
    assert job.stutter_detection_points == []
    assert job.stutter_detection_segments == []
    assert job.stutter_detection_point_count == 0
    assert job.stutter_detection_segment_count == 0


def test_job_to_dict_contains_stutter_detection_fields():
    job = Job.from_dict(
        {
            "job_id": "stutter_to_dict_job",
            "job_type": "gaming",
            "channel_type": "gaming_main",
        }
    )

    data = job.to_dict()

    required_fields = [
        "stutter_detection_report",
        "stutter_detection_status",
        "stutter_detection_selected_path",
        "stutter_detection_selected_type",
        "stutter_detection_result",
        "stutter_detection_points",
        "stutter_detection_segments",
        "stutter_detection_point_count",
        "stutter_detection_segment_count",
        "stutter_detection_duplicate_candidate_count",
        "stutter_detection_stutter_segment_count",
        "stutter_detection_freeze_segment_count",
        "stutter_detection_duration_seconds",
        "stutter_detection_frame_sample_rate",
        "stutter_detection_recommendation",
    ]

    for field_name in required_fields:
        assert field_name in data


def test_real_opencv_mini_video_stutter_runner(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    video_path = tmp_path / "runner_stutter_test.avi"

    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(video_path), fourcc, 10.0, (64, 64))

    if not writer.isOpened():
        pytest.skip("opencv_video_writer_unavailable")

    try:
        for _ in range(20):
            frame = np.zeros((64, 64, 3), dtype=np.uint8)
            writer.write(frame)
        for index in range(10):
            frame = np.zeros((64, 64, 3), dtype=np.uint8)
            frame[:, : index + 1] = 255
            writer.write(frame)
    finally:
        writer.release()

    job = SimpleNamespace(raw_video_path=str(video_path), preprocessing_manifest={})

    report = run_stutter_detection_for_job(job)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_path == str(video_path)
    assert report.selected_type == STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH
    assert report.point_count > 0
    assert report.duplicate_candidate_count > 0
    assert report.segment_count > 0


def test_new_stutter_runner_files_do_not_have_bom():
    files = [
        REPO_ROOT / "models" / "stutter_detection_run.py",
        REPO_ROOT / "core" / "stutter_detection_runner.py",
        REPO_ROOT / "models" / "job.py",
        REPO_ROOT / "tests" / "test_stutter_detection_runner_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_new_stutter_runner_files_end_with_newline():
    files = [
        REPO_ROOT / "models" / "stutter_detection_run.py",
        REPO_ROOT / "core" / "stutter_detection_runner.py",
        REPO_ROOT / "models" / "job.py",
        REPO_ROOT / "tests" / "test_stutter_detection_runner_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
