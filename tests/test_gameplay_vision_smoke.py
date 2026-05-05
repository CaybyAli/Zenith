from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.gameplay_vision_analyzer import GameplayVisionAnalyzer
from models.gameplay_vision_result import GameplayVisionResult, GameplayVisionWindow


def make_frame(value: int, width: int = 8, height: int = 6) -> list[list[int]]:
    return [[value for _ in range(width)] for _ in range(height)]


def make_moving_frame(offset: int, width: int = 8, height: int = 6) -> list[list[int]]:
    frame: list[list[int]] = []

    for y in range(height):
        row: list[int] = []
        for x in range(width):
            if (x + y + offset) % 3 == 0:
                row.append(255)
            elif (x * 2 + offset) % 5 == 0:
                row.append(180)
            else:
                row.append(20)
        frame.append(row)

    return frame


def assert_valid_window(window: GameplayVisionWindow) -> None:
    assert window.start_seconds >= 0
    assert window.end_seconds > window.start_seconds

    assert 0 <= window.motion_score <= 1
    assert 0 <= window.action_score <= 1
    assert 0 <= window.scene_change_score <= 1

    assert isinstance(window.label, str)
    assert window.label
    assert isinstance(window.reason, str)


def test_empty_input_does_not_crash() -> None:
    analyzer = GameplayVisionAnalyzer()

    result = analyzer.analyze_frames([])

    assert isinstance(result, GameplayVisionResult)
    assert result.windows == []
    assert result.action_windows == []
    assert result.average_action_score == 0
    assert result.max_action_score == 0
    assert result.skipped_reason == "not enough frames"


def test_calm_scene_scores_low() -> None:
    analyzer = GameplayVisionAnalyzer()

    calm_frames = [
        make_frame(40),
        make_frame(40),
        make_frame(41),
        make_frame(40),
    ]

    result = analyzer.analyze_frames(calm_frames, fps=2.0)

    assert len(result.windows) == 3
    assert len(result.action_windows) == 0
    assert result.max_action_score < 0.1
    assert result.average_action_score < 0.1

    for window in result.windows:
        assert_valid_window(window)
        assert window.label == "calm"


def test_action_scene_scores_higher_than_calm_scene() -> None:
    analyzer = GameplayVisionAnalyzer()

    calm_result = analyzer.analyze_frames(
        [
            make_frame(20),
            make_frame(20),
            make_frame(21),
            make_frame(20),
        ],
        fps=2.0,
    )

    action_result = analyzer.analyze_frames(
        [
            make_moving_frame(0),
            make_moving_frame(3),
            make_moving_frame(7),
            make_moving_frame(12),
        ],
        fps=2.0,
    )

    assert len(action_result.windows) == 3
    assert action_result.max_action_score > calm_result.max_action_score
    assert action_result.average_action_score > calm_result.average_action_score
    assert len(action_result.action_windows) >= 1

    labels = {window.label for window in action_result.windows}
    assert "action_candidate" in labels or "scene_change" in labels

    for window in action_result.windows:
        assert_valid_window(window)


def test_scene_change_is_detected() -> None:
    analyzer = GameplayVisionAnalyzer()

    result = analyzer.analyze_frames(
        [
            make_frame(0),
            make_frame(255),
            make_frame(0),
        ],
        fps=1.0,
    )

    assert len(result.windows) == 2
    assert len(result.action_windows) >= 1
    assert result.max_action_score >= 0.45

    scene_windows = [
        window
        for window in result.windows
        if window.scene_change_score >= 0.45
    ]

    assert scene_windows
    assert any(window.label == "scene_change" for window in scene_windows)
    assert any("large visual difference" in window.reason for window in scene_windows)

    for window in result.windows:
        assert_valid_window(window)


def main() -> None:
    test_empty_input_does_not_crash()
    test_calm_scene_scores_low()
    test_action_scene_scores_higher_than_calm_scene()
    test_scene_change_is_detected()

    analyzer = GameplayVisionAnalyzer()
    preview = analyzer.analyze_frames(
        [
            make_frame(0),
            make_frame(255),
            make_moving_frame(4),
            make_moving_frame(9),
        ],
        fps=2.0,
    )

    print("GAMEPLAY VISION SMOKE TEST PASSED")
    print(f"windows={len(preview.windows)}")
    print(f"action_windows={len(preview.action_windows)}")
    print(f"average_action_score={preview.average_action_score}")
    print(f"max_action_score={preview.max_action_score}")
    print(f"engine={preview.engine}")
    print(f"labels={[window.label for window in preview.windows]}")


if __name__ == "__main__":
    main()
