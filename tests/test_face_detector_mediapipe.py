from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from core.face_detector_mediapipe import MediaPipeFaceDetector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_001_RAW = PROJECT_ROOT / "learning_corpus" / "pairs" / "pair_001" / "raw.mp4"
MODEL_ASSET = PROJECT_ROOT / "assets" / "models" / "mediapipe" / "face_landmarker.task"


class Landmark:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class Result:
    def __init__(self) -> None:
        self.face_landmarks = [
            [Landmark(0.35 + (index % 10) * 0.01, 0.40 + (index % 12) * 0.01) for index in range(478)]
        ]


class FakeDetector(MediaPipeFaceDetector):
    def __init__(self) -> None:
        self.facecam_region = "right_half"
        self._api_mode = "fake"
        self.face_mesh = object()
        self._mp = object()

    def _detect_landmarks(self, rgb, timestamp: float):
        return Result()


def test_mediapipe_model_asset_is_local() -> None:
    assert MODEL_ASSET.exists()
    assert MODEL_ASSET.stat().st_size > 1_000_000


def test_detect_in_frame_returns_full_frame_normalized_landmarks() -> None:
    frame = np.zeros((1080, 3840, 3), dtype=np.uint8)
    point = FakeDetector().detect_in_frame(frame, timestamp=1.25)

    assert point.detected is True
    assert point.timestamp == 1.25
    assert point.landmarks is not None
    assert len(point.landmarks.landmarks) == 478
    assert all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in point.landmarks.landmarks)
    x, y, width, height = point.landmarks.bounding_box
    assert x >= 1920
    assert y >= 0
    assert width > 0
    assert height > 0


def test_pair_001_mediapipe_detection_rate_is_stable() -> None:
    if not PAIR_001_RAW.exists():
        pytest.skip("pair_001 raw.mp4 not available in this checkout")

    detector = MediaPipeFaceDetector(
        min_detection_confidence=0.2,
        facecam_region="auto",
    )
    try:
        points = detector.detect_in_video(
            str(PAIR_001_RAW),
            sample_rate_fps=1.0,
            max_samples=30,
        )
    finally:
        detector.close()

    assert len(points) == 30
    detected = sum(point.detected for point in points)
    assert detected / len(points) >= 0.95
    first_detected = next(point for point in points if point.detected)
    assert first_detected.landmarks is not None
    assert len(first_detected.landmarks.landmarks) >= 468
