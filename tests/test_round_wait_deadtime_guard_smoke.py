from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.round_wait_deadtime_guard import RoundWaitDeadtimeGuard
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.timeline_segment import TimelineSegment


def _seg(seg_id: str, start: float, end: float, role: str = "bridge", score: float = 0.65) -> TimelineSegment:
    return TimelineSegment(
        segment_id=seg_id,
        job_id="job_round_wait_smoke",
        candidate_id=f"cand_{seg_id}",
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=score,
    )


def _indicator(indicator_type: str, start: float, end: float, polarity: str = "negative", score: float = 0.85) -> CutIndicator:
    return CutIndicator(
        indicator_id=f"ind_{indicator_type}_{start}",
        indicator_type=indicator_type,
        start_seconds=start,
        end_seconds=end,
        score=score,
        confidence=0.85,
        source="round_wait_smoke",
        reason="synthetic",
        polarity=polarity,
        channel_scope="all",
    )


def _silence(start: float, end: float) -> AudioRoleWindow:
    return AudioRoleWindow(
        window_id=f"silence_{start}",
        start_seconds=start,
        end_seconds=end,
        role_type="silence_or_dead_air",
        score=0.9,
        confidence=0.85,
        reason="synthetic silence",
    )


def _speech(start: float, end: float) -> AudioRoleWindow:
    return AudioRoleWindow(
        window_id=f"speech_{start}",
        start_seconds=start,
        end_seconds=end,
        role_type="speech_active",
        score=0.75,
        confidence=0.85,
        reason="synthetic neutral speech",
    )


def test_long_menu_bridge_removed() -> None:
    segments = [_seg("hook", 0, 5, "hook"), _seg("wait", 10, 40), _seg("payoff", 50, 55, "payoff")]
    indicators = CutIndicatorResult(indicators=[
        _indicator("menu_or_idle", 10, 40),
        _indicator("low_gameplay_value", 10, 40),
    ])

    result, summary = RoundWaitDeadtimeGuard().apply(segments, cut_indicator_result=indicators)
    assert "wait" not in [segment.segment_id for segment in result]
    assert summary.removed == 1
    print("  PASS: test_long_menu_bridge_removed")


def test_silence_filler_bridge_removed() -> None:
    segments = [_seg("wait", 100, 108)]
    indicators = CutIndicatorResult(indicators=[_indicator("filler_sentence", 100, 108)])
    audio = AudioRoleResult(windows=[_silence(100, 108)])

    result, summary = RoundWaitDeadtimeGuard().apply(
        segments,
        cut_indicator_result=indicators,
        audio_role_result=audio,
    )
    assert result == []
    assert summary.removed == 1
    print("  PASS: test_silence_filler_bridge_removed")


def test_high_action_protects_segment() -> None:
    segments = [_seg("action_bridge", 200, 215)]
    indicators = CutIndicatorResult(indicators=[
        _indicator("menu_or_idle", 200, 215),
        _indicator("high_action_burst", 206, 210, polarity="positive", score=0.9),
    ])

    result, summary = RoundWaitDeadtimeGuard().apply(segments, cut_indicator_result=indicators)
    assert [segment.segment_id for segment in result] == ["action_bridge"]
    assert summary.kept_action == 1
    print("  PASS: test_high_action_protects_segment")


def test_shout_protects_segment() -> None:
    segments = [_seg("shout_bridge", 300, 312)]
    indicators = CutIndicatorResult(indicators=[
        _indicator("low_gameplay_value", 300, 312),
        _indicator("shout_like_audio", 304, 306, polarity="positive", score=0.9),
    ])

    result, summary = RoundWaitDeadtimeGuard().apply(segments, cut_indicator_result=indicators)
    assert [segment.segment_id for segment in result] == ["shout_bridge"]
    assert summary.kept_action == 1
    print("  PASS: test_shout_protects_segment")


def test_menu_with_neutral_speech_removed() -> None:
    segments = [_seg("menu_talk", 400, 430)]
    indicators = CutIndicatorResult(indicators=[_indicator("menu_or_idle", 400, 430)])
    audio = AudioRoleResult(windows=[_speech(402, 424)])

    result, summary = RoundWaitDeadtimeGuard().apply(
        segments,
        cut_indicator_result=indicators,
        audio_role_result=audio,
    )
    assert result == []
    assert summary.removed == 1
    assert summary.menu_speech_ignored == 1
    print("  PASS: test_menu_with_neutral_speech_removed")


def test_menu_with_hook_or_shout_stays() -> None:
    segments = [_seg("menu_hook", 500, 530)]
    indicators = CutIndicatorResult(indicators=[
        _indicator("menu_or_idle", 500, 530),
        _indicator("hook_sentence", 512, 515, polarity="positive", score=0.9),
    ])

    result, summary = RoundWaitDeadtimeGuard().apply(segments, cut_indicator_result=indicators)
    assert [segment.segment_id for segment in result] == ["menu_hook"]
    assert summary.kept_action == 1
    assert result[0].start_time <= 512.0
    assert result[0].end_time >= 515.0
    print("  PASS: test_menu_with_hook_or_shout_stays")


def test_after_goal_tail_trimmed() -> None:
    segments = [_seg("goal_tail", 600, 610)]
    indicators = CutIndicatorResult(indicators=[_indicator("goal_or_save_like_flash", 602, 603, polarity="positive", score=0.9)])

    result, summary = RoundWaitDeadtimeGuard().apply(segments, cut_indicator_result=indicators)
    assert len(result) == 1
    assert result[0].end_time == 604.2
    assert summary.after_goal_tail_trimmed == 1
    print("  PASS: test_after_goal_tail_trimmed")


def test_protected_roles_never_removed_and_invariants() -> None:
    segments = [
        _seg("hook", 0, 8, "hook", 0.2),
        _seg("peak", 10, 18, "peak", 0.2),
        _seg("payoff", 20, 28, "payoff", 0.2),
    ]
    indicators = CutIndicatorResult(indicators=[
        _indicator("menu_or_idle", 0, 28),
        _indicator("low_gameplay_value", 0, 28),
    ])

    result, _ = RoundWaitDeadtimeGuard().apply(segments, cut_indicator_result=indicators)
    assert [segment.segment_id for segment in result] == ["hook", "peak", "payoff"]
    for index in range(len(result) - 1):
        assert result[index + 1].start_time >= result[index].end_time
    print("  PASS: test_protected_roles_never_removed_and_invariants")


def test_round_wait_deadtime_guard_smoke() -> None:
    test_long_menu_bridge_removed()
    test_silence_filler_bridge_removed()
    test_high_action_protects_segment()
    test_shout_protects_segment()
    test_menu_with_neutral_speech_removed()
    test_menu_with_hook_or_shout_stays()
    test_after_goal_tail_trimmed()
    test_protected_roles_never_removed_and_invariants()
    print("ROUND WAIT DEADTIME GUARD SMOKE TEST PASSED")


if __name__ == "__main__":
    test_round_wait_deadtime_guard_smoke()
