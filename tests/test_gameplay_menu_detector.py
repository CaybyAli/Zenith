from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from core.gameplay_menu_detector import GameplayMenuDetector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_001_RAW = PROJECT_ROOT / "learning_corpus" / "pairs" / "pair_001" / "raw.mp4"


def _menu_frame() -> np.ndarray:
    return np.full((90, 160, 3), 48, dtype=np.uint8)


def _gameplay_frame(index: int) -> np.ndarray:
    frame = np.zeros((90, 160, 3), dtype=np.uint8)
    frame[:, :, 0] = np.linspace(0, 255, 160, dtype=np.uint8)
    frame[:, :, 1] = (index * 32) % 255
    frame[:, :, 2] = np.linspace(255, 0, 90, dtype=np.uint8).reshape(90, 1)
    x = (index * 12) % 130
    cv2.rectangle(frame, (x, 20), (x + 30, 70), (255, 255, 255), -1)
    return frame


def test_static_menu_frames_score_as_menu() -> None:
    points = GameplayMenuDetector().detect_frames([_menu_frame() for _ in range(8)])

    assert points
    assert all(point.score <= 0.5 for point in points)
    assert all(point.is_gameplay is False for point in points)


def test_motion_and_color_frames_score_as_gameplay() -> None:
    frames = [_menu_frame() for _ in range(4)] + [_gameplay_frame(i) for i in range(8)]

    points = GameplayMenuDetector(game_profile="rocket_league").detect_frames(frames)

    menu_points = points[:4]
    gameplay_points = points[4:]
    assert sum(point.is_gameplay for point in menu_points) <= 1
    assert sum(point.is_gameplay for point in gameplay_points) >= 5
    assert any(point.signals["motion"] > 0.0 for point in gameplay_points)


def test_distribution_reports_gameplay_menu_percentages() -> None:
    detector = GameplayMenuDetector()
    points = detector.detect_frames([_menu_frame() for _ in range(5)] + [_gameplay_frame(i) for i in range(5)])

    distribution = detector.distribution(points)

    assert set(distribution) == {"gameplay", "menu"}
    assert round(sum(distribution.values()), 1) == 100.0


def test_pair_001_gameplay_menu_timeline_smoke() -> None:
    if not PAIR_001_RAW.exists():
        pytest.skip("pair_001 raw.mp4 not available in this checkout")

    points = GameplayMenuDetector().detect(
        str(PAIR_001_RAW),
        sample_rate_fps=1.0,
        max_samples=60,
    )
    distribution = GameplayMenuDetector().distribution(points)

    assert len(points) == 60
    assert round(sum(distribution.values()), 1) == 100.0
    assert all(0.0 <= point.score <= 1.0 for point in points)
    assert all({"motion", "audio_activity", "color_variance", "edge_density", "game_specific"} <= set(point.signals) for point in points)
