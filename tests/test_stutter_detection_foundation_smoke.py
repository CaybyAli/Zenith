from __future__ import annotations

from pathlib import Path

import pytest

from core.stutter_detector import (
    analyze_stutter_frames,
    build_stutter_segments,
    classify_stutter_point,
)
from models.stutter_detection import (
    CLASSIFICATION_DUPLICATE_FRAME_CANDIDATE,
    CLASSIFICATION_FREEZE_SEGMENT,
    CLASSIFICATION_NORMAL_FRAME,
    CLASSIFICATION_STUTTER_SEGMENT,
    StutterDetectionResult,
    StutterFramePoint,
    StutterSegment,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _duplicate_point(time_seconds: float, frame_index: int) -> StutterFramePoint:
    return StutterFramePoint(
        time_seconds=time_seconds,
        frame_index=frame_index,
        frame_hash="1" * 64,
        previous_frame_hash="1" * 64,
        duplicate_score=0.995,
        difference_score=0.005,
        is_duplicate_candidate=True,
        classification=CLASSIFICATION_DUPLICATE_FRAME_CANDIDATE,
        confidence=0.995,
    )


def test_stutter_frame_point_roundtrip():
    point = _duplicate_point(1.0, 10)

    restored = StutterFramePoint.from_dict(point.to_dict())

    assert restored.to_dict() == point.to_dict()


def test_stutter_segment_roundtrip():
    segment = StutterSegment(
        start_seconds=1.0,
        end_seconds=1.5,
        duration_seconds=0.5,
        start_frame_index=10,
        end_frame_index=14,
        duplicate_frame_count=4,
        avg_duplicate_score=0.995,
        max_duplicate_score=0.999,
        classification=CLASSIFICATION_STUTTER_SEGMENT,
        recommendation="review_stutter_segment",
        metadata={"point_count": 4},
    )

    restored = StutterSegment.from_dict(segment.to_dict())

    assert restored.to_dict() == segment.to_dict()


def test_stutter_detection_result_roundtrip():
    point = _duplicate_point(0.1, 1)
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
    result = StutterDetectionResult(
        status="ok",
        input_path="video.mp4",
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
        metadata={"source": "unit_test"},
    )

    restored = StutterDetectionResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_classify_stutter_point_normal():
    assert (
        classify_stutter_point(
            duplicate_score=0.50,
            difference_score=0.50,
        )
        == CLASSIFICATION_NORMAL_FRAME
    )


def test_classify_stutter_point_duplicate_candidate():
    assert (
        classify_stutter_point(
            duplicate_score=0.995,
            difference_score=0.005,
        )
        == CLASSIFICATION_DUPLICATE_FRAME_CANDIDATE
    )


def test_build_stutter_segments_detects_stutter_after_four_duplicate_frames():
    points = [
        _duplicate_point(0.1, 1),
        _duplicate_point(0.2, 2),
        _duplicate_point(0.3, 3),
        _duplicate_point(0.4, 4),
    ]

    segments = build_stutter_segments(
        points,
        frame_sample_rate=10.0,
        min_duplicate_frames_for_stutter=4,
        min_stutter_duration_seconds=0.13,
    )

    assert len(segments) == 1
    assert segments[0].classification == CLASSIFICATION_STUTTER_SEGMENT
    assert segments[0].duplicate_frame_count == 4
    assert segments[0].recommendation == "review_stutter_segment"


def test_build_stutter_segments_detects_freeze_segment_for_long_static_block():
    points = [_duplicate_point(index / 10.0, index) for index in range(1, 13)]

    segments = build_stutter_segments(
        points,
        frame_sample_rate=10.0,
        min_duplicate_frames_for_stutter=4,
        min_stutter_duration_seconds=0.13,
    )

    assert len(segments) == 1
    assert segments[0].classification == CLASSIFICATION_FREEZE_SEGMENT
    assert segments[0].duplicate_frame_count == 12
    assert segments[0].recommendation == "review_freeze_segment"


def test_missing_input_file_does_not_crash(tmp_path):
    missing_file = tmp_path / "missing_video.mp4"

    result = analyze_stutter_frames(str(missing_file))

    assert result.status == "skipped_no_video_source"
    assert result.point_count == 0
    assert result.segment_count == 0
    assert result.warnings


def test_invalid_video_does_not_crash(tmp_path):
    invalid_video = tmp_path / "invalid_video.mp4"
    invalid_video.write_text("not a video", encoding="utf-8")

    result = analyze_stutter_frames(str(invalid_video))

    assert result.status == "failed"
    assert result.point_count == 0
    assert result.segment_count == 0
    assert result.errors


def test_real_mini_video_stutter_detection_if_opencv_available(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    video_path = tmp_path / "mini_stutter_test.avi"
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

    result = analyze_stutter_frames(
        str(video_path),
        frame_sample_rate=10.0,
        resize_width=64,
        resize_height=64,
    )

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.point_count > 0
    assert result.duplicate_candidate_count > 0
    assert result.segment_count > 0


def test_new_stutter_foundation_files_do_not_have_bom():
    files = [
        REPO_ROOT / "models" / "stutter_detection.py",
        REPO_ROOT / "core" / "stutter_detector.py",
        REPO_ROOT / "tests" / "test_stutter_detection_foundation_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_new_stutter_foundation_files_end_with_newline():
    files = [
        REPO_ROOT / "models" / "stutter_detection.py",
        REPO_ROOT / "core" / "stutter_detector.py",
        REPO_ROOT / "tests" / "test_stutter_detection_foundation_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
