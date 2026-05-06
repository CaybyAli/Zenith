from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pre_action_context_guard import PreActionContextGuard
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.timeline_segment import TimelineSegment


def _seg(seg_id: str, start: float, end: float, role: str = "bridge") -> TimelineSegment:
    return TimelineSegment(
        segment_id=seg_id,
        job_id="job_pre_action_smoke",
        candidate_id=f"cand_{seg_id}",
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=0.8,
    )


def _indicator(indicator_type: str, start: float, end: float, score: float = 0.85) -> CutIndicator:
    return CutIndicator(
        indicator_id=f"ind_{indicator_type}_{start}",
        indicator_type=indicator_type,
        start_seconds=start,
        end_seconds=end,
        score=score,
        confidence=0.85,
        source="pre_action_smoke",
        reason="synthetic",
        polarity="positive",
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


def test_high_action_expands_start() -> None:
    segment = _seg("action", 10.0, 16.0)
    indicators = CutIndicatorResult(indicators=[_indicator("high_action_burst", 10.0, 12.0, score=0.7)])

    result, summary = PreActionContextGuard().apply([segment], cut_indicator_result=indicators)
    assert result[0].start_time == 8.0
    assert summary.action == 1
    print("  PASS: test_high_action_expands_start")


def test_goal_expands_one_second() -> None:
    segment = _seg("goal", 30.0, 36.0)
    indicators = CutIndicatorResult(indicators=[_indicator("goal_or_save_like_flash", 30.0, 31.0)])

    result, summary = PreActionContextGuard().apply([segment], cut_indicator_result=indicators)
    assert result[0].start_time == 26.0
    assert summary.goal == 1
    print("  PASS: test_goal_expands_one_second")


def test_strong_action_expands_two_seconds() -> None:
    segment = _seg("strong_action", 40.0, 47.0)
    indicators = CutIndicatorResult(indicators=[_indicator("high_action_burst", 40.0, 42.0, score=0.9)])

    result, summary = PreActionContextGuard().apply([segment], cut_indicator_result=indicators)
    assert result[0].start_time == 36.0
    assert summary.strong_action_context == 1
    print("  PASS: test_strong_action_expands_two_seconds")


def test_shout_expands_one_point_two_seconds() -> None:
    segment = _seg("shout", 50.0, 56.0)
    indicators = CutIndicatorResult(indicators=[_indicator("shout_like_audio", 50.0, 51.5)])

    result, summary = PreActionContextGuard().apply([segment], cut_indicator_result=indicators)
    assert result[0].start_time == 46.0
    assert summary.shout == 1
    print("  PASS: test_shout_expands_one_point_two_seconds")


def test_overlap_with_previous_prevented() -> None:
    previous = _seg("previous", 60.0, 69.6)
    current = _seg("current", 70.0, 77.0)
    indicators = CutIndicatorResult(indicators=[_indicator("shout_like_audio", 70.0, 71.0)])

    result, summary = PreActionContextGuard().apply([previous, current], cut_indicator_result=indicators)
    current_out = next(segment for segment in result if segment.segment_id == "current")
    previous_out = next(segment for segment in result if segment.segment_id == "previous")
    assert current_out.start_time >= previous_out.end_time + 0.15
    assert current_out.start_time == 70.0
    assert summary.expanded == 0
    assert "pre_action_context_skipped_min_backfill" in current_out.notes
    print("  PASS: test_overlap_with_previous_prevented")


def test_silence_blocks_expansion_and_segment_survives() -> None:
    segment = _seg("silent_before_action", 90.0, 98.0)
    indicators = CutIndicatorResult(indicators=[_indicator("high_action_burst", 90.0, 92.0)])
    audio = AudioRoleResult(windows=[_silence(88.8, 90.0)])

    result, summary = PreActionContextGuard().apply(
        [segment],
        cut_indicator_result=indicators,
        audio_role_result=audio,
    )
    assert len(result) == 1
    assert result[0].start_time == 90.0
    assert summary.skipped_silence == 1
    print("  PASS: test_silence_blocks_expansion_and_segment_survives")


def test_pre_action_context_guard_smoke() -> None:
    test_high_action_expands_start()
    test_goal_expands_one_second()
    test_strong_action_expands_two_seconds()
    test_shout_expands_one_point_two_seconds()
    test_overlap_with_previous_prevented()
    test_silence_blocks_expansion_and_segment_survives()
    print("PRE ACTION CONTEXT GUARD SMOKE TEST PASSED")


if __name__ == "__main__":
    test_pre_action_context_guard_smoke()
