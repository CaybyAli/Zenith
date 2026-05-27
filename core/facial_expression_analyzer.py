from __future__ import annotations

import statistics
from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.face_detector_mediapipe import FaceDetectionPoint, FaceLandmarks


class FacialExpression(str, Enum):
    DIRECT_GAZE = "direct_gaze"
    HAND_ON_MOUTH = "hand_on_mouth"
    EYEBROW_RAISED = "eyebrow_raised"
    SURPRISE = "surprise"
    FRUSTRATION = "frustration"
    MOUTH_OPEN_YELL = "mouth_open_yell"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class FacialExpressionPoint:
    timestamp: float
    expressions: list[FacialExpression]
    confidence_by_expression: dict[FacialExpression, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "expressions": [expression.value for expression in self.expressions],
            "confidence_by_expression": {
                expression.value: confidence
                for expression, confidence in self.confidence_by_expression.items()
            },
        }


class FacialExpressionAnalyzer:
    def analyze_landmarks(self, landmarks: FaceLandmarks) -> list[FacialExpression]:
        return self._analyze_landmarks(landmarks, baseline=None)

    def _analyze_landmarks(
        self,
        landmarks: FaceLandmarks,
        baseline: dict[str, float] | None,
    ) -> list[FacialExpression]:
        metrics = self._metrics(landmarks)
        expressions: list[FacialExpression] = []

        if metrics["direct_gaze_score"] >= 0.72:
            expressions.append(FacialExpression.DIRECT_GAZE)

        if metrics["hand_on_mouth_score"] >= 0.25:
            expressions.append(FacialExpression.HAND_ON_MOUTH)

        if self._is_eyebrow_raised(metrics, baseline):
            expressions.append(FacialExpression.EYEBROW_RAISED)

        if metrics["surprise_score"] >= 0.25:
            expressions.append(FacialExpression.SURPRISE)

        if metrics["frustration_score"] >= 0.70:
            expressions.append(FacialExpression.FRUSTRATION)

        if metrics["mouth_open_yell_score"] >= 0.30:
            expressions.append(FacialExpression.MOUTH_OPEN_YELL)

        expressive = [
            expression
            for expression in expressions
            if expression is not FacialExpression.DIRECT_GAZE
        ]
        if not expressive:
            expressions.append(FacialExpression.NEUTRAL)

        return expressions

    def analyze_video(
        self,
        face_detection_points: list[FaceDetectionPoint],
    ) -> list[FacialExpressionPoint]:
        points: list[FacialExpressionPoint] = []
        baseline = self.calibrate_baseline(face_detection_points)
        for point in face_detection_points:
            if not point.detected or point.landmarks is None:
                points.append(
                    FacialExpressionPoint(
                        timestamp=point.timestamp,
                        expressions=[FacialExpression.NEUTRAL],
                        confidence_by_expression={FacialExpression.NEUTRAL: 1.0},
                    )
                )
                continue

            metrics = self._metrics(point.landmarks)
            expressions = self._analyze_landmarks(point.landmarks, baseline)
            confidence = self._confidence_map(expressions, metrics)
            points.append(
                FacialExpressionPoint(
                    timestamp=point.timestamp,
                    expressions=expressions,
                    confidence_by_expression=confidence,
                )
            )

        return points

    def calibrate_baseline(
        self,
        face_detection_points: list[FaceDetectionPoint],
        *,
        max_points: int = 30,
    ) -> dict[str, float]:
        brow_gaps: list[float] = []
        mouth_open_values: list[float] = []
        for point in face_detection_points:
            if not point.detected or point.landmarks is None:
                continue
            metrics = self._metrics(point.landmarks)
            brow_gaps.append(metrics["brow_gap"])
            mouth_open_values.append(metrics["mouth_open"])
            if len(brow_gaps) >= max_points:
                break

        if not brow_gaps:
            return {}

        return {
            "brow_gap_median": statistics.median(brow_gaps),
            "mouth_open_median": statistics.median(mouth_open_values),
        }

    def distribution(
        self,
        points: list[FacialExpressionPoint],
    ) -> dict[str, float]:
        if not points:
            return {expression.value: 0.0 for expression in FacialExpression}

        counts = {expression: 0 for expression in FacialExpression}
        for point in points:
            for expression in point.expressions:
                counts[expression] += 1

        total = float(len(points))
        return {
            expression.value: round((counts[expression] / total) * 100.0, 3)
            for expression in FacialExpression
        }

    def _confidence_map(
        self,
        expressions: list[FacialExpression],
        metrics: dict[str, float],
    ) -> dict[FacialExpression, float]:
        score_by_expression = {
            FacialExpression.DIRECT_GAZE: metrics["direct_gaze_score"],
            FacialExpression.HAND_ON_MOUTH: metrics["hand_on_mouth_score"],
            FacialExpression.EYEBROW_RAISED: metrics["eyebrow_raise_score"],
            FacialExpression.SURPRISE: metrics["surprise_score"],
            FacialExpression.FRUSTRATION: metrics["frustration_score"],
            FacialExpression.MOUTH_OPEN_YELL: metrics["mouth_open_yell_score"],
            FacialExpression.NEUTRAL: 1.0,
        }
        return {
            expression: round(max(0.0, min(1.0, score_by_expression[expression])), 3)
            for expression in expressions
        }

    def _metrics(self, landmarks: FaceLandmarks) -> dict[str, float]:
        points = landmarks.landmarks
        face_width, face_height = self._face_size(landmarks)

        mouth_open = self._distance(points, 13, 14) / face_height
        mouth_width = self._distance(points, 61, 291) / face_width

        left_eye_open = self._distance(points, 159, 145) / face_height
        right_eye_open = self._distance(points, 386, 374) / face_height
        eye_open = (left_eye_open + right_eye_open) / 2.0

        left_brow_gap = self._vertical_gap(points, 105, 159) / face_height
        right_brow_gap = self._vertical_gap(points, 334, 386) / face_height
        brow_gap = (left_brow_gap + right_brow_gap) / 2.0

        brow_inner_distance = self._distance(points, 70, 300) / face_width

        direct_gaze_score = self._direct_gaze_score(points, face_width)
        eyebrow_raise_score = _score_above(brow_gap, low=0.055, high=0.105)
        surprise_score = min(
            _score_above(eye_open, low=0.040, high=0.075),
            _score_above(mouth_open, low=0.045, high=0.090),
        )
        mouth_open_yell_score = _score_above(mouth_open, low=0.070, high=0.125)
        frustration_score = min(
            _score_below(brow_inner_distance, high=0.26, low=0.15),
            _score_below(mouth_open, high=0.035, low=0.010),
        )
        hand_on_mouth_score = min(
            _score_below(mouth_width, high=0.36, low=0.18),
            _score_below(mouth_open, high=0.025, low=0.006),
        )

        return {
            "mouth_open": mouth_open,
            "mouth_width": mouth_width,
            "eye_open": eye_open,
            "brow_gap": brow_gap,
            "brow_inner_distance": brow_inner_distance,
            "direct_gaze_score": direct_gaze_score,
            "hand_on_mouth_score": hand_on_mouth_score,
            "eyebrow_raise_score": eyebrow_raise_score,
            "surprise_score": surprise_score,
            "frustration_score": frustration_score,
            "mouth_open_yell_score": mouth_open_yell_score,
        }

    def _is_eyebrow_raised(
        self,
        metrics: dict[str, float],
        baseline: dict[str, float] | None,
    ) -> bool:
        if metrics["eyebrow_raise_score"] < 0.68:
            return False
        if not baseline or "brow_gap_median" not in baseline:
            return True

        baseline_gap = max(float(baseline.get("brow_gap_median", 0.0)), 1e-6)
        absolute_margin = 0.006
        relative_margin = 1.08
        return metrics["brow_gap"] >= max(
            baseline_gap * relative_margin,
            baseline_gap + absolute_margin,
        )

    def _direct_gaze_score(self, points: list[tuple[float, float]], face_width: float) -> float:
        if len(points) < 478:
            return 0.65

        left_iris_x = sum(points[index][0] for index in range(468, 473)) / 5.0
        right_iris_x = sum(points[index][0] for index in range(473, 478)) / 5.0
        left_center = (points[33][0] + points[133][0]) / 2.0
        right_center = (points[362][0] + points[263][0]) / 2.0
        offset = (
            abs(left_iris_x - left_center) + abs(right_iris_x - right_center)
        ) / max(face_width, 1e-6)
        return _score_below(offset, high=0.055, low=0.010)

    def _face_size(self, landmarks: FaceLandmarks) -> tuple[float, float]:
        box_width = max(1.0, float(landmarks.bounding_box[2]))
        box_height = max(1.0, float(landmarks.bounding_box[3]))
        # Landmarks are normalized; infer normalized box size from the points.
        xs = [point[0] for point in landmarks.landmarks]
        ys = [point[1] for point in landmarks.landmarks]
        width = max(max(xs) - min(xs), box_width / 10000.0, 1e-6)
        height = max(max(ys) - min(ys), box_height / 10000.0, 1e-6)
        return width, height

    def _distance(self, points: list[tuple[float, float]], left: int, right: int) -> float:
        if left >= len(points) or right >= len(points):
            return 0.0
        lx, ly = points[left]
        rx, ry = points[right]
        return ((lx - rx) ** 2 + (ly - ry) ** 2) ** 0.5

    def _vertical_gap(self, points: list[tuple[float, float]], upper: int, lower: int) -> float:
        if upper >= len(points) or lower >= len(points):
            return 0.0
        return max(0.0, points[lower][1] - points[upper][1])


def _score_above(value: float, *, low: float, high: float) -> float:
    if value <= low:
        return 0.0
    if value >= high:
        return 1.0
    return (value - low) / (high - low)


def _score_below(value: float, *, high: float, low: float) -> float:
    if value >= high:
        return 0.0
    if value <= low:
        return 1.0
    return (high - value) / (high - low)
