"""
ROUND LIFECYCLE GUARD SMOKE TEST
Tests for RoundLifecycleGuard (QA6-S).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.round_lifecycle_guard import RoundLifecycleGuard
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow
from models.round_phase_result import RoundPhase, RoundPhaseResult, RoundPhaseWindow
from models.timeline_segment import TimelineSegment

JOB_ID = "job_round_lifecycle_guard_smoke"
_IND_COUNTER = [0]


def _seg(seg_id: str, start: float, end: float, role: str = "bridge") -> TimelineSegment:
    return TimelineSegment(
        segment_id=seg_id,
        job_id=JOB_ID,
        candidate_id=f"cand_{seg_id}",
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=0.75,
    )


def _state(state_type: str, start: float, end: float, score: float = 0.9) -> GameplayStateWindow:
    return GameplayStateWindow(
        window_id=f"state_{state_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        state_type=state_type,
        score=score,
        confidence=score,
        motion_score=0.8 if state_type in {"active_gameplay", "high_motion_action"} else 0.04,
        scene_change_score=0.1,
        visual_activity_score=0.8 if state_type in {"active_gameplay", "high_motion_action"} else 0.04,
        reason="synthetic",
    )


def _states(*windows: GameplayStateWindow) -> GameplayStateResult:
    return GameplayStateResult(windows=list(windows))


def _phase(phase: RoundPhase, start: float, end: float, confidence: float = 0.9) -> RoundPhaseWindow:
    return RoundPhaseWindow(
        start_seconds=start,
        end_seconds=end,
        phase=phase,
        confidence=confidence,
    )


def _phases(*windows: RoundPhaseWindow) -> RoundPhaseResult:
    return RoundPhaseResult(windows=list(windows))


def _audio(role_type: str, start: float, end: float, score: float = 0.9) -> AudioRoleWindow:
    return AudioRoleWindow(
        window_id=f"audio_{role_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        role_type=role_type,
        score=score,
        confidence=score,
        reason="synthetic",
    )


def _audios(*windows: AudioRoleWindow) -> AudioRoleResult:
    return AudioRoleResult(windows=list(windows))


def _indicator(indicator_type: str, start: float, end: float, score: float = 0.9) -> CutIndicator:
    _IND_COUNTER[0] += 1
    negative_types = {"menu_or_idle", "low_gameplay_value", "round_end_dead_time", "silence_or_dead_air"}
    polarity = "negative" if indicator_type in negative_types else "positive"
    return CutIndicator(
        indicator_id=f"ind_{_IND_COUNTER[0]}",
        indicator_type=indicator_type,
        start_seconds=start,
        end_seconds=end,
        score=score,
        confidence=score,
        source="synthetic",
        reason="synthetic",
        polarity=polarity,
        channel_scope="all",
    )


def _indicators(*inds: CutIndicator) -> CutIndicatorResult:
    return CutIndicatorResult(indicators=list(inds))


def _guard() -> RoundLifecycleGuard:
    return RoundLifecycleGuard()


# =============================================================================
# Test 1: Menu speech after round-end is removed
# =============================================================================

def test_menu_speech_removed() -> None:
    """Segment dominated by menu_wait state must be removed."""
    segments = [
        _seg("s1", 0.0, 10.0, "hook"),    # active gameplay
        _seg("s2", 15.0, 50.0, "bridge"), # pure menu - should be removed
    ]
    states = _states(
        _state("active_gameplay", 0.0, 10.0),
        _state("menu_wait", 15.0, 50.0),
    )
    phases = _phases(
        _phase(RoundPhase.ACTIVE_ROUND, 0.0, 10.0),
        _phase(RoundPhase.MENU_WAIT, 15.0, 50.0),
    )

    out, summary = _guard().apply(
        segments,
        gameplay_state_result=states,
        round_phase_result=phases,
    )

    ids = [s.segment_id for s in out]
    assert "s2" not in ids, f"Menu-dominant segment s2 should have been removed, got ids={ids}"
    assert "s1" in ids, "Active segment s1 must be kept"
    assert summary.menu_removed >= 1, f"Expected menu_removed >= 1, got {summary.menu_removed}"
    print("  PASS test_menu_speech_removed")


# =============================================================================
# Test 2: True Round Start is shifted before first action/goal event
# =============================================================================

def test_true_round_start_shifted() -> None:
    """Segment starting in menu must have start shifted to first action."""
    segments = [
        _seg("s1", 100.0, 130.0, "hook"),
    ]
    states = _states(
        _state("menu_wait", 100.0, 111.0),
        _state("active_gameplay", 111.0, 130.0),
    )
    phases = _phases(
        _phase(RoundPhase.MENU_WAIT, 100.0, 111.0),
        _phase(RoundPhase.ACTIVE_ROUND, 111.0, 130.0),
    )

    out, summary = _guard().apply(
        segments,
        gameplay_state_result=states,
        round_phase_result=phases,
    )

    assert len(out) == 1, f"Expected 1 segment, got {len(out)}"
    seg = out[0]
    assert seg.start_time >= 110.5, (
        f"Start should be shifted to action area (>=110.5), got {seg.start_time}"
    )
    assert summary.round_start_shifted >= 1, (
        f"Expected round_start_shifted >= 1, got {summary.round_start_shifted}"
    )
    print("  PASS test_true_round_start_shifted")


# =============================================================================
# Test 3: Goal context protected — segment start expanded 2s before goal
# =============================================================================

def test_goal_context_protected_pre_goal() -> None:
    """Segment starting after a goal must be expanded to include pre-goal context."""
    segments = [
        _seg("s1", 30.0, 45.0, "build"),
    ]
    # Goal at 31.5, segment starts at 30 — should be expanded back to ~29.5
    states = _states(
        _state("active_gameplay", 28.0, 30.0),
        _state("possible_goal_or_flash", 31.5, 33.0),
        _state("active_gameplay", 33.0, 45.0),
    )
    indicators = _indicators(
        _indicator("possible_goal_or_flash", 31.5, 33.0),
    )

    out, summary = _guard().apply(
        segments,
        gameplay_state_result=states,
        cut_indicator_result=indicators,
    )

    assert len(out) == 1
    # Pre-goal protection: start should be at most goal_t - 2.0 = 29.5
    # Since segment started at 30, and goal is at 31.5, pre-goal protect = 31.5 - 2.0 = 29.5
    # Expansion should bring start to 29.5 (no previous segment to block)
    seg = out[0]
    assert seg.start_time <= 30.0, (
        f"Start should have been expanded to at most 30.0, got {seg.start_time}"
    )
    assert summary.pre_goal_expanded >= 1, (
        f"Expected pre_goal_expanded >= 1, got {summary.pre_goal_expanded}"
    )
    print("  PASS test_goal_context_protected_pre_goal")


# =============================================================================
# Test 4: Post-goal reaction (jubel) is protected and extended
# =============================================================================

def test_post_goal_reaction_protected() -> None:
    """Segment with goal near end must be extended to include post-goal reaction."""
    segments = [
        _seg("s1", 25.0, 34.0, "peak"),
    ]
    # Goal at 32.5, segment ends at 34 — post-goal protect = 32.5 + 2.0 = 34.5
    states = _states(
        _state("active_gameplay", 25.0, 32.0),
        _state("goal_or_save_like_flash", 32.5, 33.5),
    )
    indicators = _indicators(
        _indicator("goal_or_save_like_flash", 32.5, 33.5),
    )
    audios = _audios(
        _audio("shout_like_audio", 33.5, 36.0),
    )

    out, summary = _guard().apply(
        segments,
        gameplay_state_result=states,
        cut_indicator_result=indicators,
        audio_role_result=audios,
    )

    assert len(out) == 1
    seg = out[0]
    # Should extend to include shout (36.0) + 0.7 = 36.7
    assert seg.end_time > 34.0, (
        f"End should have been extended past 34.0 to include jubel, got {seg.end_time}"
    )
    assert summary.post_goal_extended >= 1, (
        f"Expected post_goal_extended >= 1, got {summary.post_goal_extended}"
    )
    print("  PASS test_post_goal_reaction_protected")


# =============================================================================
# Test 5: Boring silence gap is removed/trimmed
# =============================================================================

def test_boring_silence_removed() -> None:
    """Segment with no interesting content (no state, no speech, no action) is removed."""
    segments = [
        _seg("s1", 0.0, 10.0, "hook"),    # active
        _seg("s2", 35.0, 45.0, "bridge"), # no coverage at all = entirely boring, long enough
        _seg("s3", 60.0, 75.0, "payoff"), # active
    ]
    # s2 has no state/indicator coverage → entirely boring
    states = _states(
        _state("active_gameplay", 0.0, 10.0),
        _state("active_gameplay", 60.0, 75.0),
    )

    out, summary = _guard().apply(
        segments,
        gameplay_state_result=states,
    )

    ids = [s.segment_id for s in out]
    assert "s2" not in ids, f"Boring segment s2 should be removed, got ids={ids}"
    assert "s1" in ids, "s1 must be kept"
    assert "s3" in ids, "s3 must be kept"
    assert summary.boring_removed >= 1, (
        f"Expected boring_removed >= 1, got {summary.boring_removed}"
    )
    print("  PASS test_boring_silence_removed")


# =============================================================================
# Test 6: Pre-goal tension is NOT removed as boring
# =============================================================================

def test_pre_goal_tension_not_removed() -> None:
    """A segment that is 'boring' but precedes a goal by <2s must be kept."""
    segments = [
        _seg("s1", 27.0, 32.0, "build"),  # quiet but pre-goal
    ]
    # Goal at 30.5 — [28.5, 30.5] is protected pre-goal
    states = _states(
        _state("possible_goal_or_flash", 30.5, 32.0),
    )
    indicators = _indicators(
        _indicator("possible_goal_or_flash", 30.5, 32.0),
    )

    out, summary = _guard().apply(
        segments,
        gameplay_state_result=states,
        cut_indicator_result=indicators,
    )

    ids = [s.segment_id for s in out]
    assert "s1" in ids, (
        "Pre-goal tension segment s1 must NOT be removed as boring"
    )
    print("  PASS test_pre_goal_tension_not_removed")


# =============================================================================
# Test 7: Menu speech does NOT protect a menu segment
# =============================================================================

def test_menu_speech_does_not_protect() -> None:
    """Speech audio during menu_wait must not protect the segment from removal."""
    segments = [
        _seg("s1", 90.0, 130.0, "bridge"),
    ]
    states = _states(
        _state("menu_wait", 90.0, 130.0),
    )
    phases = _phases(
        _phase(RoundPhase.MENU_WAIT, 90.0, 130.0),
    )
    # Speech audio during menu — should NOT protect
    audios = _audios(
        _audio("speech_active", 95.0, 110.0),
    )

    out, summary = _guard().apply(
        segments,
        gameplay_state_result=states,
        round_phase_result=phases,
        audio_role_result=audios,
    )

    ids = [s.segment_id for s in out]
    assert "s1" not in ids, (
        "Menu segment s1 must be removed even if it contains speech audio"
    )
    assert summary.menu_removed >= 1, f"Expected menu_removed >= 1, got {summary.menu_removed}"
    print("  PASS test_menu_speech_does_not_protect")


# =============================================================================
# Test 8: Hook/Peak with real action is kept even in menu-adjacent context
# =============================================================================

def test_hook_peak_with_action_kept() -> None:
    """Hook/peak segment with real action must NOT be removed even if partially in menu."""
    segments = [
        _seg("s1", 50.0, 70.0, "hook"),
    ]
    states = _states(
        _state("menu_wait", 50.0, 58.0),
        _state("active_gameplay", 58.0, 70.0),  # strong action — keeps it
    )
    phases = _phases(
        _phase(RoundPhase.MENU_WAIT, 50.0, 58.0),
        _phase(RoundPhase.ACTIVE_ROUND, 58.0, 70.0),
    )

    out, summary = _guard().apply(
        segments,
        gameplay_state_result=states,
        round_phase_result=phases,
    )

    ids = [s.segment_id for s in out]
    assert "s1" in ids, "Hook segment s1 with real action must be kept"
    print("  PASS test_hook_peak_with_action_kept")


# =============================================================================
# Test 9: Final invariants — no overlaps, no backjumps, no micro segments
# =============================================================================

def test_final_invariants() -> None:
    """After all rules, output must have no overlaps, backjumps, or micro segments."""
    segments = [
        _seg("s1", 0.0, 10.0, "hook"),
        _seg("s2", 8.0, 15.0, "build"),   # overlaps with s1
        _seg("s3", 5.0, 9.0, "bridge"),   # backjump (starts before s2.end)
        _seg("s4", 20.0, 21.5, "bridge"), # too short (1.5s < 2.5s min)
        _seg("s5", 25.0, 35.0, "payoff"),
    ]
    states = _states(
        _state("active_gameplay", 0.0, 35.0),
    )

    out, summary = _guard().apply(
        segments,
        gameplay_state_result=states,
    )

    # Check no overlaps
    prev_end = -1.0
    for seg in out:
        assert seg.start_time >= prev_end - 0.01, (
            f"Overlap detected: seg {seg.segment_id} starts at {seg.start_time} "
            f"but prev ended at {prev_end}"
        )
        prev_end = seg.end_time

    # Check no backjumps in order
    times = [s.start_time for s in out]
    assert times == sorted(times), f"Backjump detected: times={times}"

    # s4 (1.5s) should be removed as micro (not a protected role)
    ids = [s.segment_id for s in out]
    assert "s4" not in ids, "Micro segment s4 (1.5s, bridge) must be removed"

    # s1 (hook) and s5 (payoff) must survive
    assert "s1" in ids, "Hook segment s1 must survive"
    assert "s5" in ids, "Payoff segment s5 must survive"

    print("  PASS test_final_invariants")


# =============================================================================
# Runner
# =============================================================================

if __name__ == "__main__":
    print("Running ROUND LIFECYCLE GUARD smoke tests...")
    test_menu_speech_removed()
    test_true_round_start_shifted()
    test_goal_context_protected_pre_goal()
    test_post_goal_reaction_protected()
    test_boring_silence_removed()
    test_pre_goal_tension_not_removed()
    test_menu_speech_does_not_protect()
    test_hook_peak_with_action_kept()
    test_final_invariants()
    print("\nROUND LIFECYCLE GUARD SMOKE TEST PASSED")
