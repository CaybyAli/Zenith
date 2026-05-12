from __future__ import annotations

from pathlib import Path

import pytest

from core.motion_analyzer import (
    analyze_motion,
    build_motion_points,
    build_motion_segments,
    classify_motion_score,
)
from models.motion_analysis import (
    CLASSIFICATION_DEAD_VISUAL_CANDIDATE,
    CLASSIFICATION_HIGH_MOTION,
    CLASSIFICATION_LOW_MOTION,
    CLASSIFICATION_MEDIUM_MOTION,
    CLASSIFICATION_STATIC,
    MotionAnalysisResult,
    MotionPoint,
    MotionSegment,
    RECOMMENDATION_REVIEW_OR_TRIM_DEAD_VISUAL,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_SKIPPED_NO_VIDEO_SOURCE,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_motion_point_to_dict_from_dict_roundtrip():
    point = MotionPoint(
        time_seconds=1.5,
        frame_index=12,
        motion_score=0.25,
        raw_motion_value=0.25,
        classification=CLASSIFICATION_MEDIUM_MOTION,
        confidence=0.9,
        metadata={"source": "test"},
        warnings=["minor_warning"],
        errors=[],
    )

    restored = MotionPoint.from_dict(point.to_dict())

    assert restored.to_dict() == point.to_dict()


def test_motion_segment_to_dict_from_dict_roundtrip():
    segment = MotionSegment(
        start_seconds=0.0,
        end_seconds=3.0,
        duration_seconds=3.0,
        avg_motion_score=0.01,
        max_motion_score=0.02,
        classification=CLASSIFICATION_DEAD_VISUAL_CANDIDATE,
        recommendation=RECOMMENDATION_REVIEW_OR_TRIM_DEAD_VISUAL,
        metadata={"point_count": 6},
        warnings=[],
        errors=[],
    )

    restored = MotionSegment.from_dict(segment.to_dict())

    assert restored.to_dict() == segment.to_dict()


def test_motion_analysis_result_to_dict_from_dict_roundtrip():
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
        classification=CLASSIFICATION_STATIC,
        recommendation="none",
    )
    result = MotionAnalysisResult(
        status=STATUS_OK,
        input_path="test.mp4",
        points=[point],
        segments=[segment],
        point_count=1,
        segment_count=1,
        low_motion_segment_count=0,
        high_motion_segment_count=0,
        dead_visual_candidate_count=0,
        duration_seconds=1.0,
        frame_sample_rate=2.0,
        recommendation="none",
        warnings=[],
        errors=[],
        metadata={"source": "unit_test"},
    )

    restored = MotionAnalysisResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_classify_motion_score_detects_static():
    assert classify_motion_score(0.0) == CLASSIFICATION_STATIC
    assert classify_motion_score(0.019) == CLASSIFICATION_STATIC


def test_classify_motion_score_detects_low_motion():
    assert classify_motion_score(0.05) == CLASSIFICATION_LOW_MOTION


def test_classify_motion_score_detects_medium_motion():
    assert classify_motion_score(0.20) == CLASSIFICATION_MEDIUM_MOTION


def test_classify_motion_score_detects_high_motion():
    assert classify_motion_score(0.50) == CLASSIFICATION_HIGH_MOTION


def test_build_motion_segments_detects_dead_visual_candidate():
    points = build_motion_points(
        raw_motion_values=[0.0, 0.01, 0.02, 0.01],
        frame_sample_rate=1.0,
        low_motion_threshold=0.08,
        high_motion_threshold=0.35,
    )

    segments = build_motion_segments(
        points=points,
        frame_sample_rate=1.0,
        dead_visual_min_duration_seconds=3.0,
    )

    assert len(segments) == 1
    assert segments[0].classification == CLASSIFICATION_DEAD_VISUAL_CANDIDATE
    assert segments[0].recommendation == RECOMMENDATION_REVIEW_OR_TRIM_DEAD_VISUAL


def test_missing_input_file_does_not_crash(tmp_path):
    missing_file = tmp_path / "missing_video.mp4"

    result = analyze_motion(str(missing_file))

    assert result.status == STATUS_SKIPPED_NO_VIDEO_SOURCE
    assert result.point_count == 0
    assert result.segment_count == 0
    assert result.warnings


def test_invalid_video_does_not_crash(tmp_path):
    invalid_video = tmp_path / "invalid_video.mp4"
    invalid_video.write_text("this is not a real video", encoding="utf-8")

    result = analyze_motion(str(invalid_video))

    assert result.status == STATUS_FAILED
    assert result.point_count == 0
    assert result.segment_count == 0
    assert result.errors


def test_real_mini_video_motion_analysis_if_opencv_available(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    video_path = tmp_path / "mini_motion_test.avi"

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

    result = analyze_motion(
        str(video_path),
        frame_sample_rate=2.0,
        low_motion_threshold=0.08,
        high_motion_threshold=0.35,
    )

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.point_count > 0
    assert result.segment_count > 0


def test_new_files_do_not_have_bom():
    files = [
        REPO_ROOT / "models" / "motion_analysis.py",
        REPO_ROOT / "core" / "motion_analyzer.py",
        REPO_ROOT / "tests" / "test_motion_analysis_foundation_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_new_files_end_with_newline():
    files = [
        REPO_ROOT / "models" / "motion_analysis.py",
        REPO_ROOT / "core" / "motion_analyzer.py",
        REPO_ROOT / "tests" / "test_motion_analysis_foundation_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
