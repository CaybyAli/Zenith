from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.face_reaction_runner import (
    apply_face_reaction_run_report_to_job,
    run_face_reaction_for_job,
)
from models.face_reaction_analysis import (
    REACTION_HYPE_CANDIDATE,
    FaceReactionAnalysisResult,
    FaceReactionPoint,
    FaceReactionSegment,
)
from models.face_reaction_run import (
    FACE_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    FACE_RUN_STATUS_FAILED,
    FACE_RUN_STATUS_OK,
    FACE_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    FaceReactionRunReport,
)
from models.face_reaction_source import (
    FACE_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH,
    FACE_SELECTED_TYPE_RAW_VIDEO_PATH,
    FACE_SOURCE_STATUS_SELECTED,
    FaceReactionSourceSelection,
)
from models.job import Job


REPO_ROOT = Path(__file__).resolve().parents[1]


def _fake_face_reaction_result(input_path: str) -> FaceReactionAnalysisResult:
    point = FaceReactionPoint(
        time_seconds=0.0,
        frame_index=0,
        face_detected=True,
        face_count=1,
        primary_face_box={"x": 1, "y": 2, "width": 20, "height": 30},
        face_area_ratio=0.05,
        mouth_open_score=0.7,
        eye_open_score=0.6,
        expressiveness_score=0.8,
        reaction_type=REACTION_HYPE_CANDIDATE,
        reaction_score=0.85,
        confidence=0.9,
    )
    segment = FaceReactionSegment(
        start_seconds=0.0,
        end_seconds=1.0,
        duration_seconds=1.0,
        avg_reaction_score=0.85,
        max_reaction_score=0.85,
        avg_face_area_ratio=0.05,
        reaction_type=REACTION_HYPE_CANDIDATE,
        recommendation="review_high_face_reaction_candidate",
    )

    return FaceReactionAnalysisResult(
        status="ok",
        input_path=input_path,
        points=[point],
        segments=[segment],
        point_count=1,
        segment_count=1,
        face_detected_point_count=1,
        reaction_candidate_count=1,
        high_reaction_segment_count=1,
        duration_seconds=1.0,
        frame_sample_rate=2.0,
        recommendation="review_face_reaction_candidates",
        warnings=[],
        errors=[],
        metadata={"fake": True},
    )


def test_face_reaction_run_report_roundtrip():
    source_selection = FaceReactionSourceSelection(
        status=FACE_SOURCE_STATUS_SELECTED,
        selected_path="video.mp4",
        selected_type=FACE_SELECTED_TYPE_RAW_VIDEO_PATH,
        checked_sources=[],
        source_exists=True,
        recommendation="run_face_reaction_analysis",
    )
    face_result = _fake_face_reaction_result("video.mp4")

    report = FaceReactionRunReport(
        status=FACE_RUN_STATUS_OK,
        source="face_reaction_runner",
        source_selection=source_selection,
        selected_path="video.mp4",
        selected_type=FACE_SELECTED_TYPE_RAW_VIDEO_PATH,
        face_reaction_result=face_result,
        face_reaction_points=[point.to_dict() for point in face_result.points],
        face_reaction_segments=[
            segment.to_dict() for segment in face_result.segments
        ],
        point_count=1,
        segment_count=1,
        face_detected_point_count=1,
        reaction_candidate_count=1,
        high_reaction_segment_count=1,
        duration_seconds=1.0,
        frame_sample_rate=2.0,
        recommendation="review_face_reaction_candidates",
        warnings=[],
        errors=[],
        metadata={"unit": "test"},
    )

    restored = FaceReactionRunReport.from_dict(report.to_dict())

    assert restored.to_dict() == report.to_dict()


def test_run_face_reaction_for_job_uses_raw_video_path(tmp_path, monkeypatch):
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake video placeholder")

    calls = {}

    def fake_analyze_face_reactions(input_path, **kwargs):
        calls["input_path"] = input_path
        return _fake_face_reaction_result(input_path)

    monkeypatch.setattr(
        "core.face_reaction_runner.analyze_face_reactions",
        fake_analyze_face_reactions,
    )

    job = SimpleNamespace(raw_video_path=str(raw_video), preprocessing_manifest={})

    report = run_face_reaction_for_job(job)

    assert report.status == FACE_RUN_STATUS_OK
    assert report.selected_path == str(raw_video)
    assert report.selected_type == FACE_SELECTED_TYPE_RAW_VIDEO_PATH
    assert calls["input_path"] == str(raw_video)
    assert report.point_count == 1
    assert report.segment_count == 1


def test_run_face_reaction_for_job_uses_preprocessing_manifest_fallback(
    tmp_path,
    monkeypatch,
):
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake video placeholder")

    calls = {}

    def fake_analyze_face_reactions(input_path, **kwargs):
        calls["input_path"] = input_path
        return _fake_face_reaction_result(input_path)

    monkeypatch.setattr(
        "core.face_reaction_runner.analyze_face_reactions",
        fake_analyze_face_reactions,
    )

    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={"source_path": str(source_video)},
    )

    report = run_face_reaction_for_job(job)

    assert report.status == FACE_RUN_STATUS_OK
    assert report.selected_path == str(source_video)
    assert report.selected_type == FACE_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH
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

    report = run_face_reaction_for_job(job)

    assert report.status == FACE_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE
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

    report = run_face_reaction_for_job(job)

    assert report.status == FACE_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE
    assert report.selected_path == str(missing_raw)
    assert report.selected_type == FACE_SELECTED_TYPE_RAW_VIDEO_PATH
    assert report.point_count == 0
    assert report.warnings


def test_analyzer_failed_is_handled_cleanly(tmp_path, monkeypatch):
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake video placeholder")

    def fake_failed_analyze_face_reactions(input_path, **kwargs):
        return FaceReactionAnalysisResult(
            status="failed",
            input_path=input_path,
            points=[],
            segments=[],
            point_count=0,
            segment_count=0,
            face_detected_point_count=0,
            reaction_candidate_count=0,
            high_reaction_segment_count=0,
            duration_seconds=None,
            frame_sample_rate=2.0,
            recommendation="face_reaction_analysis_failed",
            warnings=[],
            errors=["fake_analyzer_failed"],
            metadata={},
        )

    monkeypatch.setattr(
        "core.face_reaction_runner.analyze_face_reactions",
        fake_failed_analyze_face_reactions,
    )

    job = SimpleNamespace(raw_video_path=str(raw_video), preprocessing_manifest={})

    report = run_face_reaction_for_job(job)

    assert report.status == FACE_RUN_STATUS_FAILED
    assert report.errors == ["fake_analyzer_failed"]
    assert report.point_count == 0
    assert report.segment_count == 0


def test_apply_face_reaction_run_report_to_job_writes_all_fields():
    job = SimpleNamespace()
    face_result = _fake_face_reaction_result("video.mp4")
    source_selection = FaceReactionSourceSelection(
        status=FACE_SOURCE_STATUS_SELECTED,
        selected_path="video.mp4",
        selected_type=FACE_SELECTED_TYPE_RAW_VIDEO_PATH,
        checked_sources=[],
        source_exists=True,
        recommendation="run_face_reaction_analysis",
    )
    report = FaceReactionRunReport(
        status=FACE_RUN_STATUS_OK,
        source_selection=source_selection,
        selected_path="video.mp4",
        selected_type=FACE_SELECTED_TYPE_RAW_VIDEO_PATH,
        face_reaction_result=face_result,
        face_reaction_points=[point.to_dict() for point in face_result.points],
        face_reaction_segments=[
            segment.to_dict() for segment in face_result.segments
        ],
        point_count=1,
        segment_count=1,
        face_detected_point_count=1,
        reaction_candidate_count=1,
        high_reaction_segment_count=1,
        duration_seconds=1.0,
        frame_sample_rate=2.0,
        recommendation="review_face_reaction_candidates",
    )

    updated_job = apply_face_reaction_run_report_to_job(job, report)

    assert updated_job.face_reaction_status == FACE_RUN_STATUS_OK
    assert updated_job.face_reaction_selected_path == "video.mp4"
    assert updated_job.face_reaction_selected_type == FACE_SELECTED_TYPE_RAW_VIDEO_PATH
    assert updated_job.face_reaction_point_count == 1
    assert updated_job.face_reaction_segment_count == 1
    assert updated_job.face_reaction_detected_point_count == 1
    assert updated_job.face_reaction_candidate_count == 1
    assert updated_job.face_reaction_high_segment_count == 1
    assert updated_job.face_reaction_duration_seconds == 1.0
    assert updated_job.face_reaction_frame_sample_rate == 2.0
    assert updated_job.face_reaction_recommendation == "review_face_reaction_candidates"
    assert updated_job.face_reaction_points
    assert updated_job.face_reaction_segments
    assert updated_job.face_reaction_result
    assert updated_job.face_reaction_report


def test_old_jobs_without_face_reaction_fields_are_still_loadable():
    old_job_data = {
        "job_id": "old_job_without_face_reaction",
        "job_type": "gaming",
        "channel_type": "gaming_main",
    }

    job = Job.from_dict(old_job_data)

    assert job.face_reaction_report == {}
    assert job.face_reaction_status is None
    assert job.face_reaction_points == []
    assert job.face_reaction_segments == []
    assert job.face_reaction_point_count == 0
    assert job.face_reaction_segment_count == 0


def test_job_to_dict_contains_face_reaction_fields():
    job = Job.from_dict(
        {
            "job_id": "face_reaction_to_dict_job",
            "job_type": "gaming",
            "channel_type": "gaming_main",
        }
    )

    data = job.to_dict()

    required_fields = [
        "face_reaction_report",
        "face_reaction_status",
        "face_reaction_selected_path",
        "face_reaction_selected_type",
        "face_reaction_result",
        "face_reaction_points",
        "face_reaction_segments",
        "face_reaction_point_count",
        "face_reaction_segment_count",
        "face_reaction_detected_point_count",
        "face_reaction_candidate_count",
        "face_reaction_high_segment_count",
        "face_reaction_duration_seconds",
        "face_reaction_frame_sample_rate",
        "face_reaction_recommendation",
    ]

    for field_name in required_fields:
        assert field_name in data


def test_real_opencv_mini_video_face_reaction_runner(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    video_path = tmp_path / "runner_face_reaction_test.avi"

    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(video_path), fourcc, 10.0, (64, 64))

    if not writer.isOpened():
        pytest.skip("opencv_video_writer_unavailable")

    try:
        for index in range(20):
            frame = np.zeros((64, 64, 3), dtype=np.uint8)
            frame[index % 64 :, :] = 25
            writer.write(frame)
    finally:
        writer.release()

    job = SimpleNamespace(raw_video_path=str(video_path), preprocessing_manifest={})

    report = run_face_reaction_for_job(job)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_path == str(video_path)
    assert report.selected_type == FACE_SELECTED_TYPE_RAW_VIDEO_PATH
    assert report.point_count > 0


def test_new_face_reaction_runner_files_do_not_have_bom():
    files = [
        REPO_ROOT / "models" / "face_reaction_run.py",
        REPO_ROOT / "core" / "face_reaction_runner.py",
        REPO_ROOT / "models" / "job.py",
        REPO_ROOT / "tests" / "test_face_reaction_runner_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_new_face_reaction_runner_files_end_with_newline():
    files = [
        REPO_ROOT / "models" / "face_reaction_run.py",
        REPO_ROOT / "core" / "face_reaction_runner.py",
        REPO_ROOT / "models" / "job.py",
        REPO_ROOT / "tests" / "test_face_reaction_runner_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
