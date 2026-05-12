from __future__ import annotations

from pathlib import Path

import pytest

from core.face_reaction_analyzer import (
    analyze_face_reactions,
    build_face_reaction_segments,
    classify_face_reaction,
)
from models.face_reaction_analysis import (
    REACTION_EXPRESSIVE_CANDIDATE,
    REACTION_HYPE_CANDIDATE,
    REACTION_MOUTH_OPEN_CANDIDATE,
    REACTION_NEUTRAL_FACE,
    FaceReactionAnalysisResult,
    FaceReactionPoint,
    FaceReactionSegment,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _point(
    time_seconds: float,
    reaction_score: float,
    reaction_type: str = REACTION_HYPE_CANDIDATE,
) -> FaceReactionPoint:
    return FaceReactionPoint(
        time_seconds=time_seconds,
        frame_index=None,
        face_detected=True,
        face_count=1,
        primary_face_box={"x": 1, "y": 2, "width": 30, "height": 40},
        face_area_ratio=0.05,
        mouth_open_score=0.7,
        eye_open_score=0.6,
        expressiveness_score=0.8,
        reaction_type=reaction_type,
        reaction_score=reaction_score,
        confidence=0.8,
    )


def test_face_reaction_point_roundtrip():
    point = _point(1.5, 0.8, REACTION_MOUTH_OPEN_CANDIDATE)

    restored = FaceReactionPoint.from_dict(point.to_dict())

    assert restored.to_dict() == point.to_dict()


def test_face_reaction_segment_roundtrip():
    segment = FaceReactionSegment(
        start_seconds=1.0,
        end_seconds=2.0,
        duration_seconds=1.0,
        avg_reaction_score=0.7,
        max_reaction_score=0.9,
        avg_face_area_ratio=0.05,
        reaction_type=REACTION_HYPE_CANDIDATE,
        recommendation="review_high_face_reaction_candidate",
        metadata={"point_count": 2},
    )

    restored = FaceReactionSegment.from_dict(segment.to_dict())

    assert restored.to_dict() == segment.to_dict()


def test_face_reaction_analysis_result_roundtrip():
    point = _point(0.0, 0.75)
    segment = FaceReactionSegment(
        start_seconds=0.0,
        end_seconds=1.0,
        duration_seconds=1.0,
        avg_reaction_score=0.75,
        max_reaction_score=0.75,
        avg_face_area_ratio=0.05,
        reaction_type=REACTION_HYPE_CANDIDATE,
        recommendation="review_high_face_reaction_candidate",
    )
    result = FaceReactionAnalysisResult(
        status="ok",
        input_path="video.mp4",
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
        metadata={"source": "unit_test"},
    )

    restored = FaceReactionAnalysisResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_classify_face_reaction_neutral():
    assert (
        classify_face_reaction(
            face_detected=True,
            mouth_open_score=0.05,
            eye_open_score=0.20,
            expressiveness_score=0.10,
            reaction_score=0.15,
        )
        == REACTION_NEUTRAL_FACE
    )


def test_classify_face_reaction_mouth_open_candidate():
    assert (
        classify_face_reaction(
            face_detected=True,
            mouth_open_score=0.50,
            eye_open_score=0.20,
            expressiveness_score=0.20,
            reaction_score=0.30,
        )
        == REACTION_MOUTH_OPEN_CANDIDATE
    )


def test_classify_face_reaction_expressive_candidate():
    assert (
        classify_face_reaction(
            face_detected=True,
            mouth_open_score=0.20,
            eye_open_score=0.30,
            expressiveness_score=0.80,
            reaction_score=0.50,
        )
        == REACTION_EXPRESSIVE_CANDIDATE
    )


def test_classify_face_reaction_hype_candidate():
    assert (
        classify_face_reaction(
            face_detected=True,
            mouth_open_score=0.60,
            eye_open_score=0.40,
            expressiveness_score=0.70,
            reaction_score=0.75,
        )
        == REACTION_HYPE_CANDIDATE
    )


def test_segment_builder_detects_high_reaction_segment():
    points = [
        _point(0.0, 0.2, REACTION_NEUTRAL_FACE),
        _point(0.5, 0.80, REACTION_HYPE_CANDIDATE),
        _point(1.0, 0.90, REACTION_HYPE_CANDIDATE),
        _point(2.5, 0.1, REACTION_NEUTRAL_FACE),
    ]

    segments = build_face_reaction_segments(
        points,
        frame_sample_rate=2.0,
        high_reaction_threshold=0.55,
        min_reaction_segment_duration_seconds=0.5,
    )

    assert len(segments) == 1
    assert segments[0].max_reaction_score == 0.9
    assert segments[0].reaction_type == REACTION_HYPE_CANDIDATE


def test_missing_input_file_does_not_crash(tmp_path):
    missing_file = tmp_path / "missing_video.mp4"

    result = analyze_face_reactions(str(missing_file))

    assert result.status == "skipped_no_video_source"
    assert result.point_count == 0
    assert result.segment_count == 0
    assert result.warnings


def test_invalid_video_does_not_crash(tmp_path):
    invalid_video = tmp_path / "invalid_video.mp4"
    invalid_video.write_text("not a video", encoding="utf-8")

    result = analyze_face_reactions(str(invalid_video))

    assert result.status == "failed"
    assert result.point_count == 0
    assert result.segment_count == 0
    assert result.errors


def test_real_mini_video_face_reaction_if_opencv_available(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    video_path = tmp_path / "mini_face_reaction_test.avi"
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(video_path), fourcc, 10.0, (64, 64))

    if not writer.isOpened():
        pytest.skip("opencv_video_writer_unavailable")

    try:
        for index in range(20):
            frame = np.zeros((64, 64, 3), dtype=np.uint8)
            frame[:, : 4 + index] = 40 + index
            writer.write(frame)
    finally:
        writer.release()

    result = analyze_face_reactions(
        str(video_path),
        frame_sample_rate=2.0,
        resize_width=64,
        resize_height=64,
    )

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.point_count > 0


def test_new_face_reaction_foundation_files_do_not_have_bom():
    files = [
        REPO_ROOT / "models" / "face_reaction_analysis.py",
        REPO_ROOT / "core" / "face_reaction_analyzer.py",
        REPO_ROOT / "tests" / "test_face_reaction_analysis_foundation_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_new_face_reaction_foundation_files_end_with_newline():
    files = [
        REPO_ROOT / "models" / "face_reaction_analysis.py",
        REPO_ROOT / "core" / "face_reaction_analyzer.py",
        REPO_ROOT / "tests" / "test_face_reaction_analysis_foundation_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
