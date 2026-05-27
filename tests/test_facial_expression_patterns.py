from __future__ import annotations

from pathlib import Path

import pytest

from core.face_detector_mediapipe import (
    FaceDetectionPoint,
    FaceLandmarks,
    MediaPipeFaceDetector,
)
from core.facial_expression_analyzer import FacialExpression, FacialExpressionAnalyzer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_001_RAW = PROJECT_ROOT / "learning_corpus" / "pairs" / "pair_001" / "raw.mp4"


def _base_landmarks() -> list[tuple[float, float]]:
    points = [(0.5, 0.5) for _ in range(478)]
    points[0] = (0.4, 0.3)
    points[1] = (0.6, 0.7)

    points[61] = (0.45, 0.60)
    points[291] = (0.55, 0.60)
    points[13] = (0.50, 0.585)
    points[14] = (0.50, 0.600)

    points[33] = (0.42, 0.435)
    points[133] = (0.48, 0.435)
    points[159] = (0.45, 0.420)
    points[145] = (0.45, 0.440)

    points[362] = (0.52, 0.435)
    points[263] = (0.58, 0.435)
    points[386] = (0.55, 0.420)
    points[374] = (0.55, 0.440)

    points[105] = (0.45, 0.385)
    points[334] = (0.55, 0.385)
    points[70] = (0.43, 0.390)
    points[300] = (0.57, 0.390)

    for index in range(468, 473):
        points[index] = (0.45, 0.435)
    for index in range(473, 478):
        points[index] = (0.55, 0.435)

    return points


def _landmarks(points: list[tuple[float, float]]) -> FaceLandmarks:
    return FaceLandmarks(
        landmarks=points,
        bounding_box=(400, 300, 200, 400),
        confidence=1.0,
    )


def test_direct_gaze_pattern() -> None:
    expressions = FacialExpressionAnalyzer().analyze_landmarks(_landmarks(_base_landmarks()))

    assert FacialExpression.DIRECT_GAZE in expressions
    assert FacialExpression.NEUTRAL in expressions


def test_hand_on_mouth_pattern() -> None:
    points = _base_landmarks()
    points[61] = (0.495, 0.595)
    points[291] = (0.505, 0.595)
    points[13] = (0.50, 0.594)
    points[14] = (0.50, 0.598)

    expressions = FacialExpressionAnalyzer().analyze_landmarks(_landmarks(points))

    assert FacialExpression.HAND_ON_MOUTH in expressions


def test_eyebrow_raised_pattern() -> None:
    points = _base_landmarks()
    points[105] = (0.45, 0.350)
    points[334] = (0.55, 0.350)

    expressions = FacialExpressionAnalyzer().analyze_landmarks(_landmarks(points))

    assert FacialExpression.EYEBROW_RAISED in expressions


def test_surprise_pattern() -> None:
    points = _base_landmarks()
    points[13] = (0.50, 0.560)
    points[14] = (0.50, 0.615)
    points[159] = (0.45, 0.405)
    points[145] = (0.45, 0.445)
    points[386] = (0.55, 0.405)
    points[374] = (0.55, 0.445)

    expressions = FacialExpressionAnalyzer().analyze_landmarks(_landmarks(points))

    assert FacialExpression.SURPRISE in expressions


def test_frustration_pattern() -> None:
    points = _base_landmarks()
    points[70] = (0.49, 0.390)
    points[300] = (0.51, 0.390)
    points[13] = (0.50, 0.594)
    points[14] = (0.50, 0.599)

    expressions = FacialExpressionAnalyzer().analyze_landmarks(_landmarks(points))

    assert FacialExpression.FRUSTRATION in expressions


def test_mouth_open_yell_pattern() -> None:
    points = _base_landmarks()
    points[13] = (0.50, 0.545)
    points[14] = (0.50, 0.625)

    expressions = FacialExpressionAnalyzer().analyze_landmarks(_landmarks(points))

    assert FacialExpression.MOUTH_OPEN_YELL in expressions


def test_pair_001_expression_integration_has_multiple_patterns() -> None:
    if not PAIR_001_RAW.exists():
        pytest.skip("pair_001 raw.mp4 not available in this checkout")

    detector = MediaPipeFaceDetector(
        min_detection_confidence=0.2,
        facecam_region="auto",
    )
    try:
        face_points = detector.detect_in_video(
            str(PAIR_001_RAW),
            sample_rate_fps=1.0,
            max_samples=30,
        )
    finally:
        detector.close()

    expression_points = FacialExpressionAnalyzer().analyze_video(face_points)
    distinct = {
        expression
        for point in expression_points
        for expression in point.expressions
        if expression is not FacialExpression.NEUTRAL
    }

    assert len(distinct) >= 2
    distribution = FacialExpressionAnalyzer().distribution(expression_points)
    assert distribution["eyebrow_raised"] < 25.0


def test_video_baseline_suppresses_persistent_eyebrow_offset() -> None:
    points = _base_landmarks()
    points[105] = (0.45, 0.350)
    points[334] = (0.55, 0.350)
    face_points = [
        FaceDetectionPoint(
            timestamp=float(index),
            detected=True,
            landmarks=_landmarks(points),
        )
        for index in range(8)
    ]

    expression_points = FacialExpressionAnalyzer().analyze_video(face_points)

    assert all(
        FacialExpression.EYEBROW_RAISED not in point.expressions
        for point in expression_points
    )
    assert all(FacialExpression.NEUTRAL in point.expressions for point in expression_points)
