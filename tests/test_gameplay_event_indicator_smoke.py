from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.cut_indicator_builder import CutIndicatorBuilder
from core.gameplay_event_indicator_builder import GameplayEventIndicatorBuilder
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.edit_signal import EditSignal
from models.energy_curve_result import EnergyCurvePoint, EnergyCurveResult
from models.gameplay_vision_result import GameplayVisionResult, GameplayVisionWindow


JOB_ID = "job_gameplay_event_indicator_smoke"


def _signal(signal_id: str, signal_type: str, start: float, end: float, strength: float) -> EditSignal:
    return EditSignal(
        signal_id=signal_id,
        job_id=JOB_ID,
        start_time=start,
        end_time=end,
        signal_type=signal_type,
        strength=strength,
        confidence=0.8,
        source="gameplay_event_smoke",
    )


def _vision() -> GameplayVisionResult:
    calm = GameplayVisionWindow(0.0, 1.0, 0.02, 0.02, 0.01, "calm", "low")
    action_a = GameplayVisionWindow(1.2, 2.0, 0.20, 0.20, 0.14, "action_candidate", "action")
    action_b = GameplayVisionWindow(2.4, 3.2, 0.22, 0.21, 0.13, "action_candidate", "action")
    action_c = GameplayVisionWindow(3.6, 4.4, 0.24, 0.22, 0.14, "action_candidate", "action")
    scene = GameplayVisionWindow(5.0, 5.8, 0.18, 0.16, 0.24, "scene_change", "scene")
    later_action = GameplayVisionWindow(10.2, 11.0, 0.20, 0.19, 0.12, "action_candidate", "action after low")
    windows = [calm, action_a, action_b, action_c, scene, later_action]
    return GameplayVisionResult(
        windows=windows,
        action_windows=[action_a, action_b, action_c, scene, later_action],
        average_action_score=0.16,
        max_action_score=0.22,
    )


def _energy() -> EnergyCurveResult:
    point = EnergyCurvePoint(
        point_id="energy_peak_smoke",
        job_id=JOB_ID,
        start_seconds=1.0,
        end_seconds=4.5,
        energy_score=0.9,
        signal_count=2,
        source_signal_ids=["sig_audio_peak"],
    )
    return EnergyCurveResult(
        curve_id="curve_gameplay_event_smoke",
        job_id=JOB_ID,
        points=[point],
        peak_points=[point],
        average_energy=0.6,
        max_energy=0.9,
    )


def _audio_roles() -> AudioRoleResult:
    return AudioRoleResult(
        windows=[
            AudioRoleWindow(
                window_id="audio_group_reaction",
                start_seconds=2.0,
                end_seconds=3.0,
                role_type="group_reaction_like",
                score=0.72,
                confidence=0.62,
                reason="group smoke",
                source_signal_ids=["sig_audio_peak"],
            )
        ],
        engine="audio-role-indicator-builder-v1",
    )


def test_empty_inputs_do_not_crash() -> None:
    result = GameplayEventIndicatorBuilder().build()

    assert result.windows == []
    assert result.event_counts == {}
    assert result.skipped_reason == "no gameplay event windows"


def test_gameplay_event_indicator_smoke() -> None:
    result = GameplayEventIndicatorBuilder().build(
        gameplay_vision_result=_vision(),
        energy_curve_result=_energy(),
        edit_signals=[
            _signal("sig_audio_peak", "audio_peak", 1.0, 2.0, 0.8),
            _signal("sig_low_after", "low_motion_zone", 6.0, 8.5, 0.1),
            _signal("sig_silence_after", "silence_zone", 8.6, 10.0, 0.1),
            _signal("sig_low_before_action", "low_motion_zone", 9.2, 10.0, 0.1),
            _signal("sig_long_idle", "silence_zone", 20.0, 24.0, 0.1),
        ],
        audio_role_result=_audio_roles(),
        channel_type="gaming_main",
    )

    event_counts = result.event_counts
    event_types = [window.event_type for window in result.windows]

    assert event_counts["high_action_burst"] >= 4
    assert event_counts["sustained_action"] >= 1
    assert event_counts["scene_change_moment"] >= 1
    assert event_counts["goal_or_save_like_flash"] >= 1
    assert event_counts["round_end_dead_time"] >= 1
    assert event_counts["kickoff_like"] >= 1
    assert event_counts.get("menu_or_idle", 0) + event_counts.get("low_gameplay_value", 0) >= 1

    payload = result.to_dict()
    assert payload["engine"] == GameplayEventIndicatorBuilder.engine
    assert payload["event_counts"] == event_counts
    assert payload["windows"]

    indicator_result = CutIndicatorBuilder().build(gameplay_event_result=result)
    indicator_types = [indicator.indicator_type for indicator in indicator_result.indicators]
    assert "high_action_burst" in indicator_types
    assert "round_end_dead_time" in indicator_types
    assert "low_gameplay_value" in indicator_types or "menu_or_idle" in indicator_types
    assert any(
        indicator.indicator_type == "high_action_burst" and indicator.polarity == "positive"
        for indicator in indicator_result.indicators
    )
    assert any(
        indicator.indicator_type == "round_end_dead_time" and indicator.polarity == "negative"
        for indicator in indicator_result.indicators
    )

    print("GAMEPLAY EVENT INDICATOR SMOKE TEST PASSED")
    print(f"total_windows={len(result.windows)}")
    print(f"event_counts={event_counts}")
    print(f"indicator_types={sorted(set(indicator_types))}")
    print(f"event_types={sorted(set(event_types))}")


if __name__ == "__main__":
    test_empty_inputs_do_not_crash()
    test_gameplay_event_indicator_smoke()
