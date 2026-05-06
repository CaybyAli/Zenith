"""Smoke test — FINAL CUT SEAM GUARD

Proves that every protection rule fires correctly and that the final
invariants (sorted, no overlaps, no backjumps, no too-short segments)
are never violated.

Marker: FINAL CUT SEAM GUARD SMOKE TEST PASSED
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.final_cut_seam_guard import FinalCutSeamGuard
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult


# ── Factories ─────────────────────────────────────────────────────────────────

def _seg(seg_id: str, start: float, end: float, role: str = "build", score: float = 0.65) -> TimelineSegment:
    return TimelineSegment(
        segment_id=seg_id,
        job_id="test_job",
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=score,
    )


def _transcript_seg(start: float, end: float, text: str = "test") -> TranscriptSegment:
    return TranscriptSegment(start_seconds=start, end_seconds=end, text=text)


def _sentence(sid: str, start: float, end: float, text: str = "test sentence") -> SentenceItem:
    return SentenceItem(
        sentence_id=sid,
        text=text,
        start_seconds=start,
        end_seconds=end,
        duration_seconds=round(end - start, 3),
        score=0.7,
        confidence=0.9,
        sentence_kind="normal",
    )


def _indicator(iid: str, ind_type: str, start: float, end: float,
               polarity: str = "positive", score: float = 0.8) -> CutIndicator:
    return CutIndicator(
        indicator_id=iid,
        indicator_type=ind_type,
        start_seconds=start,
        end_seconds=end,
        score=score,
        confidence=0.8,
        source="test",
        reason="test",
        polarity=polarity,
        channel_scope="all",
    )


def _audio_window(wid: str, role_type: str, start: float, end: float, score: float = 0.8) -> AudioRoleWindow:
    return AudioRoleWindow(
        window_id=wid,
        start_seconds=start,
        end_seconds=end,
        role_type=role_type,
        score=score,
        confidence=0.8,
        reason="test",
    )


# ── Existing Tests ─────────────────────────────────────────────────────────────

def test_word_cut_start_protected() -> None:
    """Segment start falls inside a transcript word → pulled back by WORD_CUT_PROTECTION_SECONDS."""
    segments = [_seg("s1", 10.5, 20.0)]
    transcript = TranscriptResult(
        source_path="test", language=None,
        segments=[_transcript_seg(10.0, 11.0, "hello world")],
        full_text="hello world", engine="test",
    )
    result, summary = FinalCutSeamGuard().apply(segments, transcript_result=transcript)

    assert len(result) == 1
    # preferred = max(0, 10.0 - 0.25) = 9.75 < 10.5 → start pulled back
    assert result[0].start_time < 10.5, f"Expected start_time < 10.5, got {result[0].start_time}"
    assert summary.speech_start_adjusted >= 1
    print("  PASS: test_word_cut_start_protected")


def test_word_cut_end_protected() -> None:
    """Segment end falls inside a short transcript word → pushed forward (within cap)."""
    segments = [_seg("s1", 5.0, 14.5)]
    # transcript 14.0-14.9: expansion = (14.9+0.25)-14.5 = 0.65 < 1.20 cap → extend
    transcript = TranscriptResult(
        source_path="test", language=None,
        segments=[_transcript_seg(14.0, 14.9, "goodbye")],
        full_text="goodbye", engine="test",
    )
    result, summary = FinalCutSeamGuard().apply(segments, transcript_result=transcript)

    assert len(result) == 1
    # preferred = 14.9 + 0.25 = 15.15 > 14.5 → end pushed forward
    assert result[0].end_time > 14.5, f"Expected end_time > 14.5, got {result[0].end_time}"
    assert summary.speech_end_adjusted >= 1
    print("  PASS: test_word_cut_end_protected")


def test_mini_seam_fixed() -> None:
    """Gap between two segments < MIN_SEAM_GAP_SECONDS → second segment start pushed forward."""
    s1 = _seg("s1", 0.0, 10.0)
    s2 = _seg("s2", 10.05, 15.0)  # gap = 0.05 < 0.20 target
    result, summary = FinalCutSeamGuard().apply([s1, s2])

    assert summary.mini_seams_fixed >= 1
    s2_out = next(s for s in result if s.segment_id == "s2")
    # required_start = 10.0 + 0.20 = 10.20
    assert s2_out.start_time >= 10.15 - 0.001, f"Expected start_time >= 10.15, got {s2_out.start_time}"
    print("  PASS: test_mini_seam_fixed")


def test_reaction_context_expanded() -> None:
    """Reaction indicator just before segment start → start expanded backward."""
    segments = [_seg("s1", 10.0, 20.0)]
    indicators = CutIndicatorResult(
        indicators=[_indicator("i1", "goal_or_save_like_flash", 9.1, 9.5, "positive")],
    )
    result, summary = FinalCutSeamGuard().apply(segments, cut_indicator_result=indicators)

    assert summary.reaction_context_expanded >= 1
    assert result[0].start_time < 10.0, f"Expected start_time < 10.0, got {result[0].start_time}"
    print("  PASS: test_reaction_context_expanded")


def test_secondary_speech_protected() -> None:
    """Segment end falls inside a secondary-speech window → end extended past window."""
    segments = [_seg("s1", 5.0, 12.5)]
    audio = AudioRoleResult(
        windows=[_audio_window("w1", "secondary_speech_like", 12.0, 13.0)],
    )
    result, summary = FinalCutSeamGuard().apply(segments, audio_role_result=audio)

    assert summary.secondary_speech_protected >= 1
    # preferred_end = 13.0 + 0.35 = 13.35; cap = 12.5 + 1.00 = 13.5 → 13.35 OK
    assert result[0].end_time > 12.5, f"Expected end_time > 12.5, got {result[0].end_time}"
    print("  PASS: test_secondary_speech_protected")


def test_low_value_bridge_removed() -> None:
    """Long bridge with low score + no strong positive → removed; protected roles survive."""
    segments = [
        _seg("s1",  0.0,  5.0, role="hook",   score=0.9),
        _seg("s2",  6.0, 20.0, role="bridge",  score=0.3),  # > 8s, score < 0.62, no strong positive
        _seg("s3", 25.0, 35.0, role="payoff",  score=0.9),
    ]
    indicators = CutIndicatorResult(
        indicators=[_indicator("i1", "round_end_dead_time", 6.0, 20.0, "negative", 0.9)],
    )
    result, summary = FinalCutSeamGuard().apply(segments, cut_indicator_result=indicators)

    ids = [s.segment_id for s in result]
    assert summary.low_value_segments_removed >= 1
    assert "s2" not in ids, f"Expected s2 removed, got ids={ids}"
    assert "s1" in ids,     f"Expected hook s1 kept, got ids={ids}"
    assert "s3" in ids,     f"Expected payoff s3 kept, got ids={ids}"
    print("  PASS: test_low_value_bridge_removed")


def test_hook_peak_not_removed() -> None:
    """Hook and Peak roles are never pruned as low-value bridges regardless of score."""
    segments = [
        _seg("s1",  0.0, 20.0, role="hook", score=0.1),
        _seg("s2", 25.0, 45.0, role="peak", score=0.1),
    ]
    indicators = CutIndicatorResult(
        indicators=[_indicator("i1", "round_end_dead_time", 0.0, 50.0, "negative", 0.9)],
    )
    result, summary = FinalCutSeamGuard().apply(segments, cut_indicator_result=indicators)

    ids = [s.segment_id for s in result]
    assert "s1" in ids, f"Expected hook s1 kept (protected), got ids={ids}"
    assert "s2" in ids, f"Expected peak s2 kept (protected), got ids={ids}"
    print("  PASS: test_hook_peak_not_removed")


def test_final_invariants() -> None:
    """Sorted, no overlaps, no backjumps, no too-short non-protected segments."""
    segments = [
        _seg("s1",  0.0,  5.0, role="hook",   score=0.9),
        _seg("s2",  4.5, 12.0, role="build",   score=0.7),  # overlaps s1
        _seg("s3", 15.0, 20.0, role="peak",    score=0.85),
        _seg("s4", 11.0, 14.0, role="bridge",  score=0.6),  # out-of-order, overlaps s2
    ]
    result, _ = FinalCutSeamGuard().apply(segments)

    starts = [s.start_time for s in result]
    assert starts == sorted(starts), f"Result not sorted: {starts}"

    for i in range(len(result) - 1):
        gap = round(result[i + 1].start_time - result[i].end_time, 6)
        assert gap >= -0.001, (
            f"Overlap: {result[i].segment_id} ends {result[i].end_time}, "
            f"{result[i+1].segment_id} starts {result[i+1].start_time}"
        )

    protected = {"hook", "payoff", "peak"}
    for s in result:
        if s.segment_role not in protected:
            assert s.duration >= 2.5, (
                f"Segment {s.segment_id} too short: {s.duration}s (role={s.segment_role})"
            )

    print("  PASS: test_final_invariants")


def test_none_inputs_no_crash() -> None:
    """All optional inputs as None must not crash."""
    segments = [_seg("s1", 0.0, 5.0, role="hook", score=0.9)]
    result, summary = FinalCutSeamGuard().apply(
        segments,
        transcript_result=None,
        sentence_timeline_result=None,
        audio_role_result=None,
        cut_indicator_result=None,
    )
    assert len(result) >= 1
    print("  PASS: test_none_inputs_no_crash")


def test_empty_segments_no_crash() -> None:
    """Empty segment list must return empty list without crashing."""
    result, summary = FinalCutSeamGuard().apply([])
    assert result == []
    assert summary.duration_after == 0.0
    print("  PASS: test_empty_segments_no_crash")


# ── New Tests ──────────────────────────────────────────────────────────────────

def test_speech_end_expansion_capped_trim_back() -> None:
    """Segment end inside very long transcript → expansion > 1.20s cap → trim back before word."""
    segments = [_seg("s1", 5.0, 12.0)]
    # transcript 10.0-30.0: expansion = (30.25 - 12.0) = 18.25 > 1.20 → trim back to 10.0 - 0.25 = 9.75
    transcript = TranscriptResult(
        source_path="test", language=None,
        segments=[_transcript_seg(10.0, 30.0, "very long sentence")],
        full_text="very long sentence", engine="test",
    )
    result, summary = FinalCutSeamGuard().apply(segments, transcript_result=transcript)

    assert len(result) == 1
    assert result[0].end_time < 12.0, f"Expected end trimmed back, got {result[0].end_time}"
    assert summary.speech_end_trimmed_back >= 1
    assert summary.speech_end_adjusted == 0
    print("  PASS: test_speech_end_expansion_capped_trim_back")


def test_long_bridge_low_score_no_positive_removed() -> None:
    """Long bridge with score < 0.62 and no strong positive indicator → removed."""
    segments = [
        _seg("s1",   0.0,   5.0, role="hook",   score=0.9),
        _seg("s2", 100.0, 125.0, role="bridge",  score=0.60),  # 25s, score < 0.62
        _seg("s3", 130.0, 140.0, role="payoff",  score=0.9),
    ]
    # Only negative indicator, no strong positive
    indicators = CutIndicatorResult(
        indicators=[_indicator("i1", "round_end_dead_time", 100.0, 125.0, "negative", 0.8)],
    )
    result, summary = FinalCutSeamGuard().apply(segments, cut_indicator_result=indicators)

    ids = [s.segment_id for s in result]
    assert "s2" not in ids, f"Expected s2 removed (low score, no strong positive), got ids={ids}"
    assert summary.low_value_segments_removed >= 1
    print("  PASS: test_long_bridge_low_score_no_positive_removed")


def test_menu_dead_time_removed() -> None:
    """Bridge with menu/idle indicators and no strong positive → removed by menu pruner."""
    segments = [
        _seg("s1",   0.0,   5.0, role="hook",   score=0.9),
        _seg("s2", 200.0, 240.0, role="bridge",  score=0.65),  # 40s, score >= 0.62 (survives low_value pruner)
        _seg("s3", 245.0, 260.0, role="payoff",  score=0.9),
    ]
    indicators = CutIndicatorResult(
        indicators=[
            _indicator("i1", "menu_or_idle",      200.0, 240.0, "negative", 0.9),
            _indicator("i2", "low_gameplay_value", 200.0, 240.0, "negative", 0.9),
        ],
    )
    result, summary = FinalCutSeamGuard().apply(segments, cut_indicator_result=indicators)

    ids = [s.segment_id for s in result]
    assert "s2" not in ids, f"Expected s2 removed (menu/dead-time), got ids={ids}"
    assert summary.menu_dead_time_removed >= 1
    print("  PASS: test_menu_dead_time_removed")


def test_strong_action_bridge_kept() -> None:
    """Bridge with high_action_burst is kept even if menu/idle indicator also present."""
    segments = [
        _seg("s1",   0.0,   5.0, role="hook",   score=0.9),
        _seg("s2", 300.0, 320.0, role="bridge",  score=0.5),   # 20s, has action
        _seg("s3", 325.0, 335.0, role="payoff",  score=0.9),
    ]
    indicators = CutIndicatorResult(
        indicators=[
            _indicator("i1", "high_action_burst", 305.0, 315.0, "positive", 0.9),
            _indicator("i2", "menu_or_idle",      300.0, 320.0, "negative", 0.7),
        ],
    )
    result, summary = FinalCutSeamGuard().apply(segments, cut_indicator_result=indicators)

    ids = [s.segment_id for s in result]
    assert "s2" in ids, f"Expected s2 kept (has strong action), got ids={ids}"
    print("  PASS: test_strong_action_bridge_kept")


def test_mini_seam_small_gap_pushed_to_target() -> None:
    """Gap of 0.10s (< 0.20 target) is pushed forward to achieve target gap."""
    s1 = _seg("s1",  0.0, 10.0)
    s2 = _seg("s2", 10.10, 20.0)  # gap = 0.10 < MINI_SEAM_TARGET_GAP_SECONDS (0.20)
    result, summary = FinalCutSeamGuard().apply([s1, s2])

    assert summary.mini_seams_fixed >= 1
    s2_out = next(s for s in result if s.segment_id == "s2")
    # target = 10.0 + 0.20 = 10.20
    assert s2_out.start_time >= 10.20 - 0.001, f"Expected start >= 10.20, got {s2_out.start_time}"
    print("  PASS: test_mini_seam_small_gap_pushed_to_target")


def test_mini_seam_wide_threshold_detects_030() -> None:
    """Gap of 0.30s (< new 0.45 threshold, > old 0.15) is detected but not pushed if already >= 0.20."""
    s1 = _seg("s1",  0.0, 10.0)
    s2 = _seg("s2", 10.30, 20.0)  # gap = 0.30 → detected by new threshold; already >= 0.20 target
    result, summary = FinalCutSeamGuard().apply([s1, s2])

    # Gap 0.30 >= 0.20 target → no push needed
    s2_out = next(s for s in result if s.segment_id == "s2")
    assert s2_out.start_time == 10.30, f"Expected start unchanged at 10.30, got {s2_out.start_time}"
    # mini_seams_fixed should be 0 since no fix was applied
    assert summary.mini_seams_fixed == 0
    print("  PASS: test_mini_seam_wide_threshold_detects_030")


def test_speech_end_lock_extends_near_sentence_end() -> None:
    segments = [_seg("s1", 5.0, 12.8)]
    transcript = TranscriptResult(
        source_path="test",
        language=None,
        segments=[_transcript_seg(12.0, 13.4, "finish this thought")],
        full_text="finish this thought",
        engine="test",
    )

    result, summary = FinalCutSeamGuard().apply(segments, transcript_result=transcript)
    assert result[0].end_time >= 13.9
    assert summary.speech_end_locked >= 1
    print("  PASS: test_speech_end_lock_extends_near_sentence_end")


def test_shout_end_lock_extends_segment() -> None:
    segments = [_seg("s1", 20.0, 25.0)]
    indicators = CutIndicatorResult(
        indicators=[_indicator("i1", "shout_like_audio", 24.8, 25.5, "positive", 0.9)],
    )

    result, summary = FinalCutSeamGuard().apply(segments, cut_indicator_result=indicators)
    assert result[0].end_time >= 26.1
    assert summary.shout_end_locked >= 1
    print("  PASS: test_shout_end_lock_extends_segment")


def test_phrase_end_lock_protects_alles_gut() -> None:
    segments = [_seg("s1", 30.0, 34.5)]
    transcript = TranscriptResult(
        source_path="test",
        language=None,
        segments=[_transcript_seg(33.0, 35.0, "alles gut alles gut alles geplant")],
        full_text="alles gut alles gut alles geplant",
        engine="test",
    )

    result, summary = FinalCutSeamGuard().apply(segments, transcript_result=transcript)
    assert result[0].end_time >= 35.7
    assert summary.phrase_end_locked >= 1
    print("  PASS: test_phrase_end_lock_protects_alles_gut")


def test_speech_end_lock_long_expansion_still_trims_back() -> None:
    segments = [_seg("s1", 40.0, 45.0)]
    transcript = TranscriptResult(
        source_path="test",
        language=None,
        segments=[_transcript_seg(44.0, 60.0, "very long sentence")],
        full_text="very long sentence",
        engine="test",
    )

    result, summary = FinalCutSeamGuard().apply(segments, transcript_result=transcript)
    assert result[0].end_time < 45.0
    assert summary.speech_end_trimmed_back >= 1
    print("  PASS: test_speech_end_lock_long_expansion_still_trims_back")


def test_speech_end_lock_shifts_next_without_overlap() -> None:
    s1 = _seg("s1", 70.0, 75.0)
    s2 = _seg("s2", 75.4, 81.0)
    indicators = CutIndicatorResult(
        indicators=[_indicator("i1", "shout_like_audio", 74.8, 75.5, "positive", 0.9)],
    )

    result, summary = FinalCutSeamGuard().apply([s1, s2], cut_indicator_result=indicators)
    first = next(segment for segment in result if segment.segment_id == "s1")
    second = next(segment for segment in result if segment.segment_id == "s2")
    assert first.end_time >= 76.1
    assert second.start_time >= first.end_time + 0.15
    assert summary.shout_end_locked >= 1
    print("  PASS: test_speech_end_lock_shifts_next_without_overlap")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n=== FINAL CUT SEAM GUARD SMOKE TEST ===\n")

    tests = [
        test_none_inputs_no_crash,
        test_empty_segments_no_crash,
        test_word_cut_start_protected,
        test_word_cut_end_protected,
        test_mini_seam_fixed,
        test_reaction_context_expanded,
        test_secondary_speech_protected,
        test_low_value_bridge_removed,
        test_hook_peak_not_removed,
        test_final_invariants,
        # New tests
        test_speech_end_expansion_capped_trim_back,
        test_long_bridge_low_score_no_positive_removed,
        test_menu_dead_time_removed,
        test_strong_action_bridge_kept,
        test_mini_seam_small_gap_pushed_to_target,
        test_mini_seam_wide_threshold_detects_030,
        test_speech_end_lock_extends_near_sentence_end,
        test_shout_end_lock_extends_segment,
        test_phrase_end_lock_protects_alles_gut,
        test_speech_end_lock_long_expansion_still_trims_back,
        test_speech_end_lock_shifts_next_without_overlap,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as exc:
            import traceback
            print(f"  FAIL: {t.__name__}: {exc}")
            traceback.print_exc()
            failed += 1

    print(f"\n=== RESULTS: {passed} passed, {failed} failed ===")
    if failed == 0:
        print("\nFINAL CUT SEAM GUARD SMOKE TEST PASSED")
    else:
        print("\nFINAL CUT SEAM GUARD SMOKE TEST FAILED")
        sys.exit(1)
