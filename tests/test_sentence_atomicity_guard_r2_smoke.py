from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.sentence_atomicity_guard import (
    FIRST_CONTEXT_PROTECTION_SECONDS,
    MAX_SEGMENT_COUNT_DROP,
    MAX_TOTAL_DURATION_DROP_RATIO,
    SentenceAtomicityGuard,
)
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow
from models.round_phase_result import RoundPhase, RoundPhaseResult, RoundPhaseWindow
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


JOB_ID = "job_r2_smoke"


def _seg(seg_id: str, start: float, end: float, role: str = "build") -> TimelineSegment:
    return TimelineSegment(
        segment_id=seg_id,
        job_id=JOB_ID,
        candidate_id=f"cand_{seg_id}",
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=0.75,
    )


def _sentence(sentence_id: str, start: float, end: float, text: str = "Hallo Welt das ist ein Test") -> SentenceItem:
    return SentenceItem(
        sentence_id=sentence_id,
        text=text,
        start_seconds=start,
        end_seconds=end,
        duration_seconds=round(end - start, 3),
        score=0.8,
        confidence=0.9,
        sentence_kind="normal",
    )


def _sentences(*items: SentenceItem) -> SentenceTimelineResult:
    return SentenceTimelineResult(sentences=list(items))


def _t(start: float, end: float, text: str = "Hallo Welt das ist ein Test") -> TranscriptSegment:
    return TranscriptSegment(start_seconds=start, end_seconds=end, text=text, confidence=0.9)


def _transcript(*segments: TranscriptSegment) -> TranscriptResult:
    return TranscriptResult(
        source_path="synthetic.mp4",
        language="de",
        segments=list(segments),
        full_text=" ".join(s.text for s in segments),
        engine="synthetic",
    )


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


def _indicator(indicator_type: str, start: float, end: float, score: float = 0.9) -> CutIndicator:
    negative_types = {"menu_or_idle", "low_gameplay_value", "round_end_dead_time", "silence_or_dead_air", "filler_sentence"}
    return CutIndicator(
        indicator_id=f"indicator_{indicator_type}_{start}",
        indicator_type=indicator_type,
        start_seconds=start,
        end_seconds=end,
        score=score,
        confidence=score,
        source="r2_smoke",
        reason="synthetic",
        polarity="negative" if indicator_type in negative_types else "positive",
        channel_scope="all",
    )


def _state(state_type: str, start: float, end: float, score: float = 0.9) -> GameplayStateWindow:
    return GameplayStateWindow(
        window_id=f"state_{state_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        state_type=state_type,
        score=score,
        confidence=score,
        motion_score=0.8 if state_type in {"active_gameplay", "high_motion_action", "possible_goal_or_flash"} else 0.05,
        scene_change_score=0.1,
        visual_activity_score=0.8 if state_type in {"active_gameplay", "high_motion_action", "possible_goal_or_flash"} else 0.05,
        reason="synthetic",
    )


def _states(*windows: GameplayStateWindow) -> GameplayStateResult:
    return GameplayStateResult(windows=list(windows))


def _assert_invariants(segments: list[TimelineSegment]) -> None:
    assert [s.start_time for s in segments] == sorted(s.start_time for s in segments), "not sorted"
    for i in range(len(segments) - 1):
        assert segments[i + 1].start_time >= segments[i].end_time, f"overlap at {i}"
    for s in segments:
        if s.segment_role not in {"hook", "peak", "payoff"}:
            assert s.duration >= 2.5, f"too short: {s.segment_id} {s.duration}"


# ---------------------------------------------------------------------------
# Test 1: First Context Protection
# ---------------------------------------------------------------------------
def test_first_context_protection() -> None:
    """Segment starting at 5s mid-sentence must NOT be killed (first 30s protection)."""
    # Segment 5s-10s, sentence spans 2s-8s → segment.start_time=5s is mid-sentence.
    # We use menu_wait to block _can_move_start expansion (boring_dominates).
    # After trim_past_source fails (remaining too short), kill path is reached.
    # First-context guard (start_time=5 < 30) must prevent the kill.
    result, summary = SentenceAtomicityGuard().apply(
        [
            _seg("prev", 0.0, 4.5),          # previous segment blocks expansion
            _seg("ctx", 5.0, 10.0),          # 5s duration; starts mid-sentence
        ],
        sentence_timeline_result=_sentences(_sentence("s1", 2.0, 8.0)),
        gameplay_state_result=_states(_state("menu_wait", 0.0, 5.5)),
    )
    ids = [s.segment_id for s in result]
    assert "ctx" in ids, (
        f"first-context segment was killed; remaining={ids} "
        f"first_context_kept={summary.first_context_kept}"
    )
    assert summary.first_context_kept >= 1, "first_context_kept must be >= 1"
    print("  [OK] test_first_context_protection")


# ---------------------------------------------------------------------------
# Test 2: Duration Budget
# ---------------------------------------------------------------------------
def test_duration_budget() -> None:
    """Guard may not remove more than 8% of total duration."""
    # Build a scenario: large background segment + 3 problematic segments each ~6s.
    # Each problematic segment starts mid-sentence, can't expand (previous blocks),
    # can't skip (too short after skip). No strong protection.
    # With duration_before ~138s: budget = 8% = ~11s.
    # First kill = 6s (within budget). Second kill = 12s > 11s → blocked.
    # So at most 1 of the 3 problematic segments may be removed.
    segments = [
        _seg("bg", 40.0, 160.0),             # 120s background; no speech nearby
        _seg("prob_a", 180.0, 186.0),        # 6s; sentence 177-184 → mid-sentence
        _seg("prob_b", 200.0, 206.0),        # 6s; sentence 197-204 → mid-sentence
        _seg("prob_c", 220.0, 226.0),        # 6s; sentence 217-224 → mid-sentence
    ]
    sentences_result = _sentences(
        _sentence("sa", 177.0, 184.0),
        _sentence("sb", 197.0, 204.0),
        _sentence("sc", 217.0, 224.0),
    )
    result, summary = SentenceAtomicityGuard().apply(segments, sentence_timeline_result=sentences_result)
    ids = [s.segment_id for s in result]
    prob_kept = sum(1 for seg_id in ("prob_a", "prob_b", "prob_c") if seg_id in ids)
    assert prob_kept >= 2, (
        f"duration budget should protect at least 2 of 3 problematic segments; "
        f"kept={ids} partial_removed={summary.sentence_partial_removed} "
        f"partial_kept_budget={summary.partial_kept_budget}"
    )
    _assert_invariants(result)
    print("  [OK] test_duration_budget")


# ---------------------------------------------------------------------------
# Test 3: Segment Count Budget
# ---------------------------------------------------------------------------
def test_segment_count_budget() -> None:
    """Guard may remove at most MAX_SEGMENT_COUNT_DROP=1 full segment."""
    # 5 problematic segments outside first-30s context, no protection.
    # Each 8s, spaced far apart (no previous blocking expansion... wait,
    # we need expansion to fail to reach the kill path).
    # Strategy: sentence spans 4s before+inside segment, so desired expansion
    # > MAX_SENTENCE_START_EXPAND (5s) → _can_move_start fails.
    # Then trim_past fails because segment.end - clean_start < MIN_SEGMENT_DURATION.
    # budget: duration_before = 5*8 = 40s, max_drop = 3.2s → can't kill any 8s segment!
    # We need a bigger total. Let's add a 200s background.
    # duration_before = 200 + 5*8 = 240s, budget = 19.2s. Can kill 2*8=16s, not 3*24.
    # But MAX_SEGMENT_COUNT_DROP=1 is stricter → only 1 kill allowed.
    segments = [
        _seg("big_bg", 0.0, 200.0),           # 200s no-speech background
        _seg("p1", 210.0, 218.0),             # 8s, sentence 202-215 → start mid-sentence
        _seg("p2", 230.0, 238.0),             # 8s, sentence 222-235 → start mid-sentence
        _seg("p3", 250.0, 258.0),             # 8s, sentence 242-255 → start mid-sentence
    ]
    sentences_result = _sentences(
        _sentence("ss1", 202.0, 215.0),       # sentence.start=202, segment.start=210 → in-sentence
        _sentence("ss2", 222.0, 235.0),
        _sentence("ss3", 242.0, 255.0),
    )
    # No previous segments block expansion for p1...p3 individually.
    # desired = max(0, 202-0.20)=201.8; segment.start=210, diff=8.2 > MAX_SENTENCE_START_EXPAND=5.0
    # → _can_move_start returns False (too far away).
    # trim_past: clean_start = 215+0.35=215.35; p1.end=218, 218-215.35=2.65>=2.5 → trim succeeds!
    # Hmm, trim would succeed. Let me use sentence that ends close to segment.end.
    # For trim to fail: segment.end - (sentence.end + 0.35) < 2.5
    # → sentence.end > segment.end - 2.85
    # p1 ends at 218 → sentence must end > 215.15 → use sentence ending at 216.
    segments2 = [
        _seg("big_bg", 0.0, 200.0),
        _seg("p1", 210.0, 218.0),
        _seg("p2", 230.0, 238.0),
        _seg("p3", 250.0, 258.0),
    ]
    sentences_result2 = _sentences(
        _sentence("ss1", 202.0, 216.0),       # ends at 216; trim_past: 216.35, 218-216.35=1.65<2.5 → FAIL
        _sentence("ss2", 222.0, 236.0),       # ends at 236; trim: 236.35, 238-236.35=1.65<2.5 → FAIL
        _sentence("ss3", 242.0, 256.0),       # ends at 256; trim: 256.35, 258-256.35=1.65<2.5 → FAIL
    )
    result, summary = SentenceAtomicityGuard().apply(segments2, sentence_timeline_result=sentences_result2)
    ids = [s.segment_id for s in result]
    prob_removed = sum(1 for seg_id in ("p1", "p2", "p3") if seg_id not in ids)
    assert prob_removed <= MAX_SEGMENT_COUNT_DROP, (
        f"segment count budget exceeded: removed={prob_removed} allowed={MAX_SEGMENT_COUNT_DROP} "
        f"remaining={ids} partial_kept_budget={summary.partial_kept_budget}"
    )
    _assert_invariants(result)
    print("  [OK] test_segment_count_budget")


# ---------------------------------------------------------------------------
# Test 4: Repair Before Remove
# ---------------------------------------------------------------------------
def test_repair_before_remove() -> None:
    """Partial sentence should be expanded (repaired) rather than removed."""
    # Segment at 40s-55s, sentence at 38s-44s.
    # No previous segment blocking expansion, no boring states.
    # _can_move_start should succeed → start moves to 37.8s.
    # Segment must NOT be killed.
    result, summary = SentenceAtomicityGuard().apply(
        [_seg("repair", 40.0, 55.0)],
        sentence_timeline_result=_sentences(_sentence("s1", 38.0, 44.0)),
    )
    assert result, "segment should not be removed (repair before remove)"
    assert result[0].start_time <= 38.0, (
        f"start should have been pulled to sentence start; got {result[0].start_time}"
    )
    assert summary.sentence_start_fixed >= 1, "sentence_start_fixed should be >= 1"
    assert summary.sentence_partial_removed == 0, "nothing should be removed"
    print("  [OK] test_repair_before_remove")


# ---------------------------------------------------------------------------
# Test 5: Clearly Bad Segment Still Removable (within budget)
# ---------------------------------------------------------------------------
def test_bad_segment_still_removable() -> None:
    """A segment with partial sentence + no protection + outside first 30s is removed (1st kill)."""
    # This verifies that R2 doesn't over-protect: one clearly bad segment should still be removable.
    # Segment at 100s-108s (8s), sentence 92s-104s.
    # Previous at 98s-100s blocks expansion (desired 91.8 < prev.end 100).
    # trim_past: clean_start = 104.35, remaining = 108-104.35=3.65 >= 2.5 → trim succeeds.
    # So this should be a partial removal (trim, not kill). That's acceptable.
    # Let's instead make it so trim also fails.
    # sentence ends at 107, trim: 107.35, 108-107.35=0.65 < 2.5 → trim fails → kill path.
    # No strong protection → would kill. Start_time=100 > 30 → first-context ok.
    # Budget: duration_before = 2 + 8 = 10s, budget = 0.8s → can't kill 8s segment!
    # Need bigger total. Use background segment.
    result, summary = SentenceAtomicityGuard().apply(
        [
            _seg("bg", 0.0, 180.0),           # 180s background → budget = 8% * 188 = 15s
            _seg("prev_blocker", 98.0, 100.0, role="build"),
            _seg("bad", 100.0, 108.0),        # 8s, sentence 92-107
        ],
        sentence_timeline_result=_sentences(_sentence("s1", 92.0, 107.0)),
    )
    # bg and prev_blocker have start_time=0, 98 → both < 30s for blocker? No, blocker starts at 98s > 30s.
    # bg: starts at 0 < 30. But bg doesn't have a mid-sentence start (no sentence overlaps 0).
    # bad: starts at 100 > 30. trim_past: sentence ends at 107, clean_start=107.35, 108-107.35=0.65<2.5 → fails.
    # Kill allowed (budget 188*0.08=15s > 8s → can kill). Check partial_removed or segment count.
    # Actually let's check: does bg have a sentence issue? No sentence near 0-180 range. Fine.
    # prob_removed = bad missing from result
    ids = [s.segment_id for s in result]
    assert "bad" not in ids or summary.sentence_partial_removed >= 1, (
        f"bad segment should have been removed or trimmed; ids={ids}"
    )
    _assert_invariants(result)
    print("  [OK] test_bad_segment_still_removable")


# ---------------------------------------------------------------------------
# Test 6: Hook / Peak Protected from Kill
# ---------------------------------------------------------------------------
def test_hook_peak_protected() -> None:
    """Hook and peak segments must not be killed even with partial sentence and no strong protection."""
    for role in ("hook", "peak", "payoff"):
        # Segment 50s-60s, sentence 45s-55s, start mid-sentence.
        # Previous at 49s blocks expansion (desired 44.8 < 49).
        # trim_past: sentence ends at 55, clean_start 55.35, 60-55.35=4.65>=2.5 → trim succeeds.
        # So role protection won't even be needed here because trim works.
        # Need trim to also fail. Sentence ending closer to segment end.
        # Sentence 45s-58s, clean_start=58.35, 60-58.35=1.65<2.5 → trim fails.
        # No strong protection → kill path. But role=hook/peak/payoff → protected!
        result, summary = SentenceAtomicityGuard().apply(
            [
                _seg("prev", 0.0, 49.0),
                _seg(f"protected_{role}", 50.0, 60.0, role=role),
            ],
            sentence_timeline_result=_sentences(_sentence("s1", 45.0, 58.0)),
        )
        ids = [s.segment_id for s in result]
        assert f"protected_{role}" in ids, (
            f"{role} segment was killed; remaining={ids} "
            f"partial_kept_budget={summary.partial_kept_budget}"
        )
        assert summary.partial_kept_budget >= 1, f"partial_kept_budget should be >= 1 for {role}"
    print("  [OK] test_hook_peak_protected")


# ---------------------------------------------------------------------------
# Test 7: Final Invariants
# ---------------------------------------------------------------------------
def test_final_invariants_r2() -> None:
    """After R2 processing, all output segments must satisfy timeline invariants."""
    result, _ = SentenceAtomicityGuard().apply(
        [
            _seg("hook", 0.0, 8.0, role="hook"),
            _seg("build1", 10.0, 20.0),
            _seg("build2", 22.0, 35.0),
            _seg("peak", 37.0, 47.0, role="peak"),
            _seg("payoff", 50.0, 60.0, role="payoff"),
        ],
        sentence_timeline_result=_sentences(
            _sentence("s1", 1.0, 6.0),
            _sentence("s2", 11.0, 18.0),
            _sentence("s3", 23.0, 33.0),
        ),
    )
    assert result, "should have segments after processing"
    _assert_invariants(result)
    print("  [OK] test_final_invariants_r2")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def test_sentence_atomicity_guard_r2_smoke() -> None:
    test_first_context_protection()
    test_duration_budget()
    test_segment_count_budget()
    test_repair_before_remove()
    test_bad_segment_still_removable()
    test_hook_peak_protected()
    test_final_invariants_r2()
    print("SENTENCE ATOMICITY R2 SMOKE TEST PASSED")


if __name__ == "__main__":
    test_sentence_atomicity_guard_r2_smoke()
