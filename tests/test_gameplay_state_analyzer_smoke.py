from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.gameplay_state_analyzer import GameplayStateAnalyzer
from models.gameplay_event_result import GameplayEventResult, GameplayEventWindow
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow
from models.gameplay_vision_result import GameplayVisionResult, GameplayVisionWindow
from models.round_phase_result import RoundPhase, RoundPhaseResult, RoundPhaseWindow


def _vision_window(
    start: float,
    end: float,
    motion: float,
    action: float,
    scene: float = 0.02,
    label: str = "synthetic",
) -> GameplayVisionWindow:
    return GameplayVisionWindow(
        start_seconds=start,
        end_seconds=end,
        motion_score=motion,
        action_score=action,
        scene_change_score=scene,
        label=label,
        reason="state smoke",
    )


def _vision(*windows: GameplayVisionWindow) -> GameplayVisionResult:
    return GameplayVisionResult(
        windows=list(windows),
        action_windows=[window for window in windows if window.action_score >= 0.12],
        average_action_score=0.2,
        max_action_score=max((window.action_score for window in windows), default=0.0),
    )


def _event(event_type: str, start: float, end: float, score: float = 0.8) -> GameplayEventWindow:
    return GameplayEventWindow(
        event_id=f"event_{event_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        event_type=event_type,
        score=score,
        confidence=0.7,
        reason="state smoke",
    )


def _events(*windows: GameplayEventWindow) -> GameplayEventResult:
    return GameplayEventResult(windows=list(windows))


def _phase(phase: RoundPhase, start: float, end: float, confidence: float = 0.72) -> RoundPhaseWindow:
    return RoundPhaseWindow(
        start_seconds=start,
        end_seconds=end,
        phase=phase,
        confidence=confidence,
        evidence={"source": "state smoke"},
    )


def _phases(*windows: RoundPhaseWindow) -> RoundPhaseResult:
    return RoundPhaseResult(windows=list(windows))


def _types(result: GameplayStateResult) -> list[str]:
    return [window.state_type for window in result.windows]


def _assert_valid(result: GameplayStateResult) -> None:
    assert result.total_windows == len(result.windows)
    assert result.state_counts == {
        state_type: _types(result).count(state_type)
        for state_type in set(_types(result))
    }
    assert 0.0 <= result.avg_score <= 1.0
    assert 0.0 <= result.max_score <= 1.0
    assert result.windows == sorted(
        result.windows,
        key=lambda item: (item.start_seconds, item.end_seconds, item.state_type, item.window_id),
    )
    for window in result.windows:
        assert window.end_seconds > window.start_seconds
        assert 0.0 <= window.score <= 1.0
        assert 0.0 <= window.confidence <= 1.0
        assert 0.0 <= window.motion_score <= 1.0
        assert 0.0 <= window.scene_change_score <= 1.0
        assert 0.0 <= window.visual_activity_score <= 1.0
        assert window.reason
        assert isinstance(window.source_signals, list)


def test_empty_inputs_do_not_crash() -> None:
    result = GameplayStateAnalyzer().analyze()
    assert result.windows == []
    assert result.total_windows == 0
    assert result.skipped_reason == "no gameplay state signals"
    _assert_valid(result)


def test_high_action_burst_creates_action_state() -> None:
    result = GameplayStateAnalyzer().analyze(
        gameplay_vision_result=_vision(_vision_window(10.0, 10.5, 0.28, 0.25)),
        gameplay_event_result=_events(_event("high_action_burst", 10.0, 10.5)),
    )
    assert "high_motion_action" in _types(result) or "active_gameplay" in _types(result)
    _assert_valid(result)


def test_goal_flash_creates_goal_or_flash_state() -> None:
    result = GameplayStateAnalyzer().analyze(
        gameplay_event_result=_events(_event("goal_or_save_like_flash", 20.0, 20.5)),
    )
    assert "possible_goal_or_flash" in _types(result)
    _assert_valid(result)


def test_round_end_dead_time_creates_round_end_state() -> None:
    result = GameplayStateAnalyzer().analyze(
        gameplay_event_result=_events(_event("round_end_dead_time", 30.0, 34.0)),
    )
    assert "round_end" in _types(result) or "possible_dead_time_after_goal" in _types(result)
    _assert_valid(result)


def test_round_phase_menu_wait_creates_menu_wait() -> None:
    result = GameplayStateAnalyzer().analyze(
        round_phase_result=_phases(_phase(RoundPhase.MENU_WAIT, 40.0, 48.0)),
    )
    assert "menu_wait" in _types(result)
    _assert_valid(result)


def test_round_phase_active_round_creates_active_gameplay() -> None:
    result = GameplayStateAnalyzer().analyze(
        round_phase_result=_phases(_phase(RoundPhase.ACTIVE_ROUND, 50.0, 58.0)),
    )
    assert "active_gameplay" in _types(result)
    _assert_valid(result)


def test_low_motion_without_action_creates_low_motion_wait() -> None:
    result = GameplayStateAnalyzer().analyze(
        gameplay_vision_result=_vision(_vision_window(60.0, 60.5, 0.02, 0.01)),
    )
    assert "low_motion_wait" in _types(result)
    _assert_valid(result)


def test_pre_action_context_is_created_before_strong_event() -> None:
    result = GameplayStateAnalyzer().analyze(
        gameplay_event_result=_events(_event("goal_or_save_like_flash", 70.0, 70.5)),
    )
    contexts = [
        window for window in result.windows
        if window.state_type == "possible_pre_action_context"
    ]
    assert contexts
    assert any(window.end_seconds <= 70.0 for window in contexts)
    _assert_valid(result)


def test_to_dict_from_dict_roundtrip() -> None:
    result = GameplayStateAnalyzer().analyze(
        gameplay_vision_result=_vision(_vision_window(80.0, 80.5, 0.3, 0.28, 0.2)),
        gameplay_event_result=_events(_event("high_action_burst", 80.0, 80.5, 1.4)),
        round_phase_result=_phases(_phase(RoundPhase.ACTIVE_ROUND, 79.0, 82.0, 1.4)),
    )
    roundtrip = GameplayStateResult.from_dict(result.to_dict())
    assert roundtrip.to_dict() == result.to_dict()
    assert roundtrip.state_counts == result.state_counts
    _assert_valid(roundtrip)


def test_window_model_clamps_scores_and_validates_time() -> None:
    window = GameplayStateWindow(
        window_id="bad_scores",
        start_seconds=10.0,
        end_seconds=9.0,
        state_type="active_gameplay",
        score=2.0,
        confidence=-1.0,
        motion_score=3.0,
        scene_change_score=-3.0,
        visual_activity_score=9.0,
        reason="clamp smoke",
    )
    assert window.end_seconds > window.start_seconds
    assert window.score == 1.0
    assert window.confidence == 0.0
    assert window.motion_score == 1.0
    assert window.scene_change_score == 0.0
    assert window.visual_activity_score == 1.0


def test_gameplay_state_analyzer_smoke() -> None:
    test_empty_inputs_do_not_crash()
    test_high_action_burst_creates_action_state()
    test_goal_flash_creates_goal_or_flash_state()
    test_round_end_dead_time_creates_round_end_state()
    test_round_phase_menu_wait_creates_menu_wait()
    test_round_phase_active_round_creates_active_gameplay()
    test_low_motion_without_action_creates_low_motion_wait()
    test_pre_action_context_is_created_before_strong_event()
    test_to_dict_from_dict_roundtrip()
    test_window_model_clamps_scores_and_validates_time()

    preview = GameplayStateAnalyzer().analyze(
        gameplay_vision_result=_vision(
            _vision_window(0.0, 0.5, 0.02, 0.01),
            _vision_window(1.0, 1.5, 0.26, 0.24, 0.18),
        ),
        gameplay_event_result=_events(
            _event("high_action_burst", 1.0, 1.5),
            _event("goal_or_save_like_flash", 2.0, 2.5),
            _event("round_end_dead_time", 3.0, 6.0),
        ),
        round_phase_result=_phases(
            _phase(RoundPhase.ACTIVE_ROUND, 0.0, 2.0),
            _phase(RoundPhase.ROUND_END, 3.0, 6.0),
            _phase(RoundPhase.MENU_WAIT, 6.0, 10.0),
        ),
    )
    print("GAMEPLAY STATE ANALYZER SMOKE TEST PASSED")
    print(f"total_windows={preview.total_windows}")
    print(f"state_counts={preview.state_counts}")
    print(f"avg_score={preview.avg_score}")
    print(f"max_score={preview.max_score}")
    print(f"engine={preview.engine}")


if __name__ == "__main__":
    test_gameplay_state_analyzer_smoke()
