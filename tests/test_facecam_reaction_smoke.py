from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.facecam_reaction_analyzer import FacecamReactionAnalyzer
from models.facecam_reaction_result import FacecamReactionResult, FacecamReactionWindow


def make_flat_frame(value: int, size: int = 16) -> list[list[int]]:
    return [[value for _ in range(size)] for _ in range(size)]


def make_checker_frame(low: int = 20, high: int = 235, size: int = 16) -> list[list[int]]:
    return [
        [high if (row + col) % 2 == 0 else low for col in range(size)]
        for row in range(size)
    ]


def assert_valid_window(window: FacecamReactionWindow) -> None:
    assert window.start_seconds >= 0.0
    assert window.end_seconds > window.start_seconds
    assert 0.0 <= window.reaction_score <= 1.0
    assert 0.0 <= window.motion_score <= 1.0
    assert 0.0 <= window.expression_change_score <= 1.0
    assert isinstance(window.label, str)
    assert window.label
    assert isinstance(window.reason, str)


def test_empty_input_does_not_crash() -> None:
    analyzer = FacecamReactionAnalyzer()

    result = analyzer.analyze_frames([])

    assert isinstance(result, FacecamReactionResult)
    assert result.windows == []
    assert result.reaction_windows == []
    assert result.skipped_reason == "not enough facecam frames"
    assert result.average_reaction_score == 0.0
    assert result.max_reaction_score == 0.0
    assert result.engine == "facecam-reaction-analyzer-v1"


def test_calm_facecam_scores_low() -> None:
    analyzer = FacecamReactionAnalyzer()

    frames = [
        make_flat_frame(20),
        make_flat_frame(21),
        make_flat_frame(20),
    ]

    result = analyzer.analyze_frames(frames, fps=2.0)

    assert result.skipped_reason is None
    assert len(result.windows) == 2
    assert len(result.reaction_windows) == 0
    assert result.max_reaction_score < 0.05

    for window in result.windows:
        assert_valid_window(window)
        assert window.label == "calm_facecam"


def test_strong_facecam_reaction_scores_higher_than_calm() -> None:
    analyzer = FacecamReactionAnalyzer()

    calm_result = analyzer.analyze_frames(
        [
            make_flat_frame(20),
            make_flat_frame(21),
            make_flat_frame(20),
        ],
        fps=2.0,
    )

    strong_result = analyzer.analyze_frames(
        [
            make_flat_frame(20),
            make_flat_frame(235),
            make_checker_frame(20, 235),
        ],
        fps=2.0,
    )

    assert strong_result.skipped_reason is None
    assert len(strong_result.windows) == 2
    assert len(strong_result.reaction_windows) >= 1
    assert strong_result.max_reaction_score > calm_result.max_reaction_score
    assert strong_result.max_reaction_score >= 0.42

    labels = {window.label for window in strong_result.reaction_windows}
    assert "strong_facecam_reaction" in labels

    for window in strong_result.windows:
        assert_valid_window(window)


def test_audio_peak_can_boost_facecam_reaction_score() -> None:
    analyzer = FacecamReactionAnalyzer()

    frames = [
        make_flat_frame(20),
        make_flat_frame(80),
    ]

    without_audio = analyzer.analyze_frames(frames, fps=2.0)
    with_audio = analyzer.analyze_frames(frames, fps=2.0, audio_peak_times=[0.25])

    assert without_audio.skipped_reason is None
    assert with_audio.skipped_reason is None
    assert len(without_audio.windows) == 1
    assert len(with_audio.windows) == 1

    assert with_audio.max_reaction_score > without_audio.max_reaction_score
    assert "audio peak boost" in with_audio.windows[0].reason


def test_result_to_dict_contains_required_fields() -> None:
    analyzer = FacecamReactionAnalyzer()

    result = analyzer.analyze_frames(
        [
            make_flat_frame(20),
            make_flat_frame(235),
        ],
        fps=2.0,
    )

    data = result.to_dict()

    assert "windows" in data
    assert "reaction_windows" in data
    assert "average_reaction_score" in data
    assert "max_reaction_score" in data
    assert "engine" in data
    assert "skipped_reason" in data

    first_window = data["windows"][0]
    assert "start_seconds" in first_window
    assert "end_seconds" in first_window
    assert "reaction_score" in first_window
    assert "motion_score" in first_window
    assert "expression_change_score" in first_window
    assert "label" in first_window
    assert "reason" in first_window


if __name__ == "__main__":
    test_empty_input_does_not_crash()
    test_calm_facecam_scores_low()
    test_strong_facecam_reaction_scores_higher_than_calm()
    test_audio_peak_can_boost_facecam_reaction_score()
    test_result_to_dict_contains_required_fields()

    print("FACECAM REACTION SMOKE TEST PASSED")
