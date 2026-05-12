from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.screen_content_runner import (
    apply_screen_content_run_report_to_job,
    run_screen_content_classification_for_job,
)
from models.job import Job
from models.screen_content_classification import (
    SCREEN_TYPE_BLACK_SCREEN,
    SCREEN_TYPE_GAMEPLAY,
    SCREEN_TYPE_LOADING,
    ScreenContentClassificationResult,
    ScreenContentPoint,
    ScreenContentSegment,
)
from models.screen_content_run import (
    SCREEN_CONTENT_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    SCREEN_CONTENT_RUN_STATUS_FAILED,
    SCREEN_CONTENT_RUN_STATUS_OK,
    SCREEN_CONTENT_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    ScreenContentRunReport,
)
from models.screen_content_source import (
    SCREEN_CONTENT_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH,
    SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH,
    SCREEN_CONTENT_SOURCE_STATUS_SELECTED,
    ScreenContentSourceSelection,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _fake_screen_content_result(input_path: str) -> ScreenContentClassificationResult:
    point = ScreenContentPoint(
        time_seconds=0.0,
        frame_index=0,
        screen_type=SCREEN_TYPE_GAMEPLAY,
        confidence=0.8,
        brightness_score=0.45,
        saturation_score=0.50,
        edge_density_score=0.20,
        motion_context_score=0.10,
        text_like_region_score=0.05,
        ui_density_score=0.10,
        is_review_candidate=False,
    )
    segment = ScreenContentSegment(
        start_seconds=0.0,
        end_seconds=1.0,
        duration_seconds=1.0,
        screen_type=SCREEN_TYPE_GAMEPLAY,
        avg_confidence=0.8,
        max_confidence=0.8,
        point_count=2,
        recommendation="keep_content_context",
    )

    return ScreenContentClassificationResult(
        status="ok",
        input_path=input_path,
        points=[point],
        segments=[segment],
        point_count=1,
        segment_count=1,
        gameplay_segment_count=1,
        menu_segment_count=0,
        loading_segment_count=0,
        scoreboard_segment_count=0,
        death_screen_segment_count=0,
        victory_screen_segment_count=0,
        black_screen_segment_count=0,
        duration_seconds=1.0,
        frame_sample_rate=2.0,
        recommendation="keep_content_context",
        warnings=[],
        errors=[],
        metadata={"fake": True},
    )


def test_screen_content_run_report_roundtrip():
    source_selection = ScreenContentSourceSelection(
        status=SCREEN_CONTENT_SOURCE_STATUS_SELECTED,
        selected_path="video.mp4",
        selected_type=SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH,
        checked_sources=[],
        source_exists=True,
        recommendation="run_screen_content_classification",
    )
    screen_content_result = _fake_screen_content_result("video.mp4")

    report = ScreenContentRunReport(
        status=SCREEN_CONTENT_RUN_STATUS_OK,
        source="screen_content_runner",
        source_selection=source_selection,
        selected_path="video.mp4",
        selected_type=SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH,
        screen_content_result=screen_content_result,
        screen_content_points=[point.to_dict() for point in screen_content_result.points],
        screen_content_segments=[
            segment.to_dict() for segment in screen_content_result.segments
        ],
        point_count=1,
        segment_count=1,
        gameplay_segment_count=1,
        menu_segment_count=0,
        loading_segment_count=0,
        scoreboard_segment_count=0,
        death_screen_segment_count=0,
        victory_screen_segment_count=0,
        black_screen_segment_count=0,
        duration_seconds=1.0,
        frame_sample_rate=2.0,
        recommendation="keep_content_context",
        warnings=[],
        errors=[],
        metadata={"unit": "test"},
    )

    restored = ScreenContentRunReport.from_dict(report.to_dict())

    assert restored.to_dict() == report.to_dict()


def test_run_screen_content_for_job_uses_raw_video_path(tmp_path, monkeypatch):
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake video placeholder")

    calls = {}

    def fake_classify_screen_content(input_path, **kwargs):
        calls["input_path"] = input_path
        return _fake_screen_content_result(input_path)

    monkeypatch.setattr(
        "core.screen_content_runner.classify_screen_content",
        fake_classify_screen_content,
    )

    job = SimpleNamespace(raw_video_path=str(raw_video), preprocessing_manifest={})

    report = run_screen_content_classification_for_job(job)

    assert report.status == SCREEN_CONTENT_RUN_STATUS_OK
    assert report.selected_path == str(raw_video)
    assert report.selected_type == SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH
    assert calls["input_path"] == str(raw_video)
    assert report.point_count == 1
    assert report.segment_count == 1


def test_run_screen_content_for_job_uses_preprocessing_manifest_fallback(
    tmp_path,
    monkeypatch,
):
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake video placeholder")

    calls = {}

    def fake_classify_screen_content(input_path, **kwargs):
        calls["input_path"] = input_path
        return _fake_screen_content_result(input_path)

    monkeypatch.setattr(
        "core.screen_content_runner.classify_screen_content",
        fake_classify_screen_content,
    )

    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={"source_path": str(source_video)},
    )

    report = run_screen_content_classification_for_job(job)

    assert report.status == SCREEN_CONTENT_RUN_STATUS_OK
    assert report.selected_path == str(source_video)
    assert report.selected_type == SCREEN_CONTENT_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH
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

    report = run_screen_content_classification_for_job(job)

    assert report.status == SCREEN_CONTENT_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE
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

    report = run_screen_content_classification_for_job(job)

    assert report.status == SCREEN_CONTENT_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE
    assert report.selected_path == str(missing_raw)
    assert report.selected_type == SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH
    assert report.point_count == 0
    assert report.warnings


def test_classifier_failed_is_handled_cleanly(tmp_path, monkeypatch):
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake video placeholder")

    def fake_failed_classify_screen_content(input_path, **kwargs):
        return ScreenContentClassificationResult(
            status="failed",
            input_path=input_path,
            points=[],
            segments=[],
            point_count=0,
            segment_count=0,
            gameplay_segment_count=0,
            menu_segment_count=0,
            loading_segment_count=0,
            scoreboard_segment_count=0,
            death_screen_segment_count=0,
            victory_screen_segment_count=0,
            black_screen_segment_count=0,
            duration_seconds=None,
            frame_sample_rate=2.0,
            recommendation="screen_content_classification_failed",
            warnings=[],
            errors=["fake_classifier_failed"],
            metadata={},
        )

    monkeypatch.setattr(
        "core.screen_content_runner.classify_screen_content",
        fake_failed_classify_screen_content,
    )

    job = SimpleNamespace(raw_video_path=str(raw_video), preprocessing_manifest={})

    report = run_screen_content_classification_for_job(job)

    assert report.status == SCREEN_CONTENT_RUN_STATUS_FAILED
    assert report.errors == ["fake_classifier_failed"]
    assert report.point_count == 0
    assert report.segment_count == 0


def test_apply_screen_content_run_report_to_job_writes_all_fields():
    job = SimpleNamespace()
    screen_content_result = _fake_screen_content_result("video.mp4")
    source_selection = ScreenContentSourceSelection(
        status=SCREEN_CONTENT_SOURCE_STATUS_SELECTED,
        selected_path="video.mp4",
        selected_type=SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH,
        checked_sources=[],
        source_exists=True,
        recommendation="run_screen_content_classification",
    )
    report = ScreenContentRunReport(
        status=SCREEN_CONTENT_RUN_STATUS_OK,
        source_selection=source_selection,
        selected_path="video.mp4",
        selected_type=SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH,
        screen_content_result=screen_content_result,
        screen_content_points=[point.to_dict() for point in screen_content_result.points],
        screen_content_segments=[
            segment.to_dict() for segment in screen_content_result.segments
        ],
        point_count=1,
        segment_count=1,
        gameplay_segment_count=1,
        menu_segment_count=0,
        loading_segment_count=0,
        scoreboard_segment_count=0,
        death_screen_segment_count=0,
        victory_screen_segment_count=0,
        black_screen_segment_count=0,
        duration_seconds=1.0,
        frame_sample_rate=2.0,
        recommendation="keep_content_context",
    )

    updated_job = apply_screen_content_run_report_to_job(job, report)

    assert updated_job.screen_content_status == SCREEN_CONTENT_RUN_STATUS_OK
    assert updated_job.screen_content_selected_path == "video.mp4"
    assert updated_job.screen_content_selected_type == SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH
    assert updated_job.screen_content_point_count == 1
    assert updated_job.screen_content_segment_count == 1
    assert updated_job.screen_content_gameplay_segment_count == 1
    assert updated_job.screen_content_menu_segment_count == 0
    assert updated_job.screen_content_loading_segment_count == 0
    assert updated_job.screen_content_scoreboard_segment_count == 0
    assert updated_job.screen_content_death_screen_segment_count == 0
    assert updated_job.screen_content_victory_screen_segment_count == 0
    assert updated_job.screen_content_black_screen_segment_count == 0
    assert updated_job.screen_content_duration_seconds == 1.0
    assert updated_job.screen_content_frame_sample_rate == 2.0
    assert updated_job.screen_content_recommendation == "keep_content_context"
    assert updated_job.screen_content_points
    assert updated_job.screen_content_segments
    assert updated_job.screen_content_result
    assert updated_job.screen_content_report


def test_old_jobs_without_screen_content_fields_are_still_loadable():
    old_job_data = {
        "job_id": "old_job_without_screen_content",
        "job_type": "gaming",
        "channel_type": "gaming_main",
    }

    job = Job.from_dict(old_job_data)

    assert job.screen_content_report == {}
    assert job.screen_content_status is None
    assert job.screen_content_points == []
    assert job.screen_content_segments == []
    assert job.screen_content_point_count == 0
    assert job.screen_content_segment_count == 0


def test_job_to_dict_contains_screen_content_fields():
    job = Job.from_dict(
        {
            "job_id": "screen_content_to_dict_job",
            "job_type": "gaming",
            "channel_type": "gaming_main",
        }
    )

    data = job.to_dict()

    required_fields = [
        "screen_content_report",
        "screen_content_status",
        "screen_content_selected_path",
        "screen_content_selected_type",
        "screen_content_result",
        "screen_content_points",
        "screen_content_segments",
        "screen_content_point_count",
        "screen_content_segment_count",
        "screen_content_gameplay_segment_count",
        "screen_content_menu_segment_count",
        "screen_content_loading_segment_count",
        "screen_content_scoreboard_segment_count",
        "screen_content_death_screen_segment_count",
        "screen_content_victory_screen_segment_count",
        "screen_content_black_screen_segment_count",
        "screen_content_duration_seconds",
        "screen_content_frame_sample_rate",
        "screen_content_recommendation",
    ]

    for field_name in required_fields:
        assert field_name in data


def test_real_opencv_mini_video_screen_content_runner(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    video_path = tmp_path / "runner_screen_content_test.avi"

    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(video_path), fourcc, 10.0, (64, 64))

    if not writer.isOpened():
        pytest.skip("opencv_video_writer_unavailable")

    try:
        for _ in range(8):
            writer.write(np.zeros((64, 64, 3), dtype=np.uint8))
        for index in range(12):
            frame = np.zeros((64, 64, 3), dtype=np.uint8)
            frame[:, :] = (30, 120, 40)
            cv2.circle(frame, (16 + index, 32), 10, (40, 220, 90), -1)
            writer.write(frame)
    finally:
        writer.release()

    job = SimpleNamespace(raw_video_path=str(video_path), preprocessing_manifest={})

    report = run_screen_content_classification_for_job(
        job,
        frame_sample_rate=2.0,
        resize_width=64,
        resize_height=64,
    )

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_path == str(video_path)
    assert report.selected_type == SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH
    assert report.point_count > 0
    assert report.segment_count > 0


def test_new_screen_content_runner_files_do_not_have_bom():
    files = [
        REPO_ROOT / "models" / "screen_content_run.py",
        REPO_ROOT / "core" / "screen_content_runner.py",
        REPO_ROOT / "models" / "job.py",
        REPO_ROOT / "tests" / "test_screen_content_runner_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_new_screen_content_runner_files_end_with_newline():
    files = [
        REPO_ROOT / "models" / "screen_content_run.py",
        REPO_ROOT / "core" / "screen_content_runner.py",
        REPO_ROOT / "models" / "job.py",
        REPO_ROOT / "tests" / "test_screen_content_runner_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
