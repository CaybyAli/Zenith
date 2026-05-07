"""Smoke tests for UniversalSafeEdgeTrimApplier — QA6-Y"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.timeline_segment import TimelineSegment
from models.universal_moment_soft_decision import (
    UniversalMomentSegmentDecision,
    UniversalMomentSoftDecisionReport,
)
from models.universal_moment_result import UniversalMomentResult, UniversalMomentWindow
from core.universal_safe_edge_trim_applier import UniversalSafeEdgeTrimApplier


# ── helpers ──────────────────────────────────────────────────────────────────

def _seg(
    seg_id: str,
    start: float,
    end: float,
    role: str = "build",
    job_id: str = "j1",
) -> TimelineSegment:
    return TimelineSegment(
        segment_id=seg_id,
        job_id=job_id,
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=0.7,
    )


def _decision(
    seg_id: str,
    start: float,
    end: float,
    soft_decision: str = "trim_edges_candidate",
    *,
    can_trim_edges_later: bool = True,
    needs_human_review: bool = False,
    protect_pre_context: bool = False,
    protect_post_context: bool = False,
    boring_confidence: float = 0.70,
    private_confidence: float = 0.0,
    speech_confidence: float = 0.10,
    action_confidence: float = 0.10,
    segment_role: str = "build",
) -> UniversalMomentSegmentDecision:
    return UniversalMomentSegmentDecision(
        segment_id=seg_id,
        start_time=start,
        end_time=end,
        duration_seconds=end - start,
        segment_role=segment_role,
        soft_decision=soft_decision,
        can_trim_edges_later=can_trim_edges_later,
        needs_human_review=needs_human_review,
        protect_pre_context=protect_pre_context,
        protect_post_context=protect_post_context,
        boring_confidence=boring_confidence,
        private_confidence=private_confidence,
        speech_confidence=speech_confidence,
        action_confidence=action_confidence,
        keep_confidence=0.45,
        remove_confidence=0.45,
    )


def _report(*decisions: UniversalMomentSegmentDecision) -> UniversalMomentSoftDecisionReport:
    return UniversalMomentSoftDecisionReport(job_id="j1", decisions=list(decisions))


def _boring_window(start: float, end: float) -> UniversalMomentWindow:
    return UniversalMomentWindow(
        window_id=f"w_{start:.0f}",
        start_seconds=start,
        end_seconds=end,
        boring_score=0.80,
        menu_wait_score=0.75,
        peak_score=0.05,
        tension_score=0.05,
        speech_score=0.05,
        cut_risk_score=0.10,
        post_peak_reaction_score=0.05,
    )


def _speech_window(start: float, end: float) -> UniversalMomentWindow:
    return UniversalMomentWindow(
        window_id=f"ws_{start:.0f}",
        start_seconds=start,
        end_seconds=end,
        boring_score=0.20,
        speech_score=0.80,
        peak_score=0.10,
    )


def _peak_window(start: float, end: float) -> UniversalMomentWindow:
    return UniversalMomentWindow(
        window_id=f"wp_{start:.0f}",
        start_seconds=start,
        end_seconds=end,
        peak_score=0.80,
        tension_score=0.75,
        boring_score=0.05,
        speech_score=0.05,
    )


def _cut_risk_window(start: float, end: float) -> UniversalMomentWindow:
    return UniversalMomentWindow(
        window_id=f"wc_{start:.0f}",
        start_seconds=start,
        end_seconds=end,
        cut_risk_score=0.85,
        speech_score=0.70,
        speech_boundary_risk=True,
    )


def _result(*windows: UniversalMomentWindow) -> UniversalMomentResult:
    return UniversalMomentResult(windows=list(windows))


# ── test 1: empty inputs ─────────────────────────────────────────────────────

def test_empty_inputs():
    segs, summary = UniversalSafeEdgeTrimApplier().apply(
        [],
        soft_decision_report=None,
        universal_moment_result=None,
    )
    assert segs == []
    assert summary.trim_candidates_seen == 0
    assert summary.total_trimmed_seconds == 0.0
    print("  PASS: empty inputs do not crash")


# ── test 2: safe_keep not trimmed ─────────────────────────────────────────────

def test_safe_keep_not_trimmed():
    seg = _seg("s1", 60.0, 90.0)
    dec = _decision("s1", 60.0, 90.0, soft_decision="safe_keep")
    segs, summary = UniversalSafeEdgeTrimApplier().apply(
        [seg],
        soft_decision_report=_report(dec),
        universal_moment_result=_result(_boring_window(60.0, 62.0)),
    )
    assert segs[0].start_time == 60.0, "safe_keep start must not change"
    assert segs[0].end_time == 90.0, "safe_keep end must not change"
    assert summary.skipped_safe_keep >= 1
    assert summary.total_trimmed_seconds == 0.0
    print("  PASS: safe_keep not trimmed")


# ── test 3: needs_human_review not trimmed ────────────────────────────────────

def test_needs_human_review_not_trimmed():
    seg = _seg("s2", 60.0, 90.0)
    dec = _decision("s2", 60.0, 90.0, soft_decision="trim_edges_candidate", needs_human_review=True)
    segs, summary = UniversalSafeEdgeTrimApplier().apply(
        [seg],
        soft_decision_report=_report(dec),
        universal_moment_result=_result(_boring_window(60.0, 62.0)),
    )
    assert segs[0].start_time == 60.0
    assert segs[0].end_time == 90.0
    assert summary.skipped_human_review >= 1
    assert summary.total_trimmed_seconds == 0.0
    print("  PASS: needs_human_review not trimmed")


# ── test 4: boring start edge trimmed (max 0.75s) ─────────────────────────────

def test_boring_start_trimmed():
    seg = _seg("s3", 60.0, 90.0)
    dec = _decision("s3", 60.0, 90.0)
    boring_at_start = _boring_window(59.5, 62.0)
    segs, summary = UniversalSafeEdgeTrimApplier().apply(
        [seg],
        soft_decision_report=_report(dec),
        universal_moment_result=_result(boring_at_start),
    )
    trimmed = 60.0 + 0.75
    assert segs[0].start_time <= trimmed, f"start should be trimmed up to 0.75s, got {segs[0].start_time}"
    assert segs[0].start_time > 60.0, "start must actually move"
    assert segs[0].start_time - 60.0 <= 0.75 + 1e-6, "max trim 0.75s"
    assert summary.start_trimmed >= 1
    assert summary.total_trimmed_seconds <= 0.75 + 1e-6
    print(f"  PASS: boring start trimmed by {segs[0].start_time - 60.0:.3f}s")


# ── test 5: boring end edge trimmed (max 0.75s) ───────────────────────────────

def test_boring_end_trimmed():
    seg = _seg("s4", 60.0, 90.0)
    dec = _decision("s4", 60.0, 90.0)
    boring_at_end = _boring_window(89.0, 91.0)
    segs, summary = UniversalSafeEdgeTrimApplier().apply(
        [seg],
        soft_decision_report=_report(dec),
        universal_moment_result=_result(boring_at_end),
    )
    assert segs[0].end_time < 90.0, "end must actually shrink"
    assert 90.0 - segs[0].end_time <= 0.75 + 1e-6, "max trim 0.75s"
    assert summary.end_trimmed >= 1
    print(f"  PASS: boring end trimmed by {90.0 - segs[0].end_time:.3f}s")


# ── test 6: speech at edge blocks trim ───────────────────────────────────────

def test_speech_blocks_trim():
    seg = _seg("s5", 60.0, 90.0)
    dec = _decision("s5", 60.0, 90.0)
    speech_at_start = _speech_window(60.0, 62.0)
    segs, summary = UniversalSafeEdgeTrimApplier().apply(
        [seg],
        soft_decision_report=_report(dec),
        universal_moment_result=_result(speech_at_start),
    )
    assert segs[0].start_time == 60.0, "speech at start must block trim"
    assert summary.start_trimmed == 0
    print("  PASS: speech at edge blocks start trim")


# ── test 7: peak/tension at edge blocks trim ──────────────────────────────────

def test_action_peak_blocks_trim():
    seg = _seg("s6", 60.0, 90.0)
    dec = _decision("s6", 60.0, 90.0)
    peak_at_end = _peak_window(89.0, 91.0)
    segs, summary = UniversalSafeEdgeTrimApplier().apply(
        [seg],
        soft_decision_report=_report(dec),
        universal_moment_result=_result(peak_at_end),
    )
    assert segs[0].end_time == 90.0, "peak at end must block trim"
    assert summary.end_trimmed == 0
    print("  PASS: peak/tension at end edge blocks end trim")


# ── test 8: first 30s blocks start trim ──────────────────────────────────────

def test_first_30s_blocks_start_trim():
    seg = _seg("s7", 10.0, 40.0)
    dec = _decision("s7", 10.0, 40.0)
    boring = _boring_window(10.0, 12.0)
    segs, summary = UniversalSafeEdgeTrimApplier().apply(
        [seg],
        soft_decision_report=_report(dec),
        universal_moment_result=_result(boring),
    )
    assert segs[0].start_time == 10.0, "first 30s must block start trim"
    assert summary.start_trimmed == 0
    print("  PASS: first 30s blocks start trim")


# ── test 9: segment never trimmed below 2.5s ─────────────────────────────────

def test_never_below_min_duration():
    seg = _seg("s8", 60.0, 62.5)  # exactly 2.5s
    dec = _decision("s8", 60.0, 62.5)
    boring = _boring_window(60.0, 63.0)
    segs, summary = UniversalSafeEdgeTrimApplier().apply(
        [seg],
        soft_decision_report=_report(dec),
        universal_moment_result=_result(boring),
    )
    assert segs[0].duration >= 2.5 - 1e-6, f"min 2.5s violated: {segs[0].duration}"
    print(f"  PASS: segment duration maintained >= 2.5s ({segs[0].duration:.3f}s)")


# ── test 10: total trim budget <= 3.0s ────────────────────────────────────────

def test_total_trim_budget():
    segs = [_seg(f"seg{i}", 60.0 + i * 15.0, 60.0 + i * 15.0 + 12.0) for i in range(10)]
    decs = [_decision(f"seg{i}", 60.0 + i * 15.0, 60.0 + i * 15.0 + 12.0) for i in range(10)]
    windows = []
    for i in range(10):
        s = 60.0 + i * 15.0
        windows.append(_boring_window(s, s + 1.5))
        windows.append(_boring_window(s + 10.5, s + 12.5))

    out_segs, summary = UniversalSafeEdgeTrimApplier().apply(
        segs,
        soft_decision_report=_report(*decs),
        universal_moment_result=_result(*windows),
    )
    assert summary.total_trimmed_seconds <= 3.0 + 1e-6, (
        f"Total trim exceeded 3.0s: {summary.total_trimmed_seconds}"
    )
    print(f"  PASS: total trim {summary.total_trimmed_seconds:.3f}s <= 3.0s")


# ── test 11: final invariants (sorted, no overlaps, no backjumps) ─────────────

def test_final_invariants():
    segs = [
        _seg("s_a", 90.0, 110.0),
        _seg("s_b", 105.0, 125.0),  # overlap before trim
    ]
    decs = [
        _decision("s_a", 90.0, 110.0),
        _decision("s_b", 105.0, 125.0),
    ]
    out_segs, summary = UniversalSafeEdgeTrimApplier().apply(
        segs,
        soft_decision_report=_report(*decs),
        universal_moment_result=None,
    )
    for i in range(len(out_segs) - 1):
        assert out_segs[i].end_time <= out_segs[i + 1].start_time + 1e-6, "overlap detected"
        assert out_segs[i].start_time <= out_segs[i + 1].start_time, "backjump detected"
    print("  PASS: final invariants — sorted, no overlaps, no backjumps")


# ── test 12: cut_risk blocks trim ────────────────────────────────────────────

def test_cut_risk_blocks_trim():
    seg = _seg("s9", 60.0, 90.0)
    dec = _decision("s9", 60.0, 90.0)
    risk_at_start = _cut_risk_window(60.0, 62.0)
    segs, summary = UniversalSafeEdgeTrimApplier().apply(
        [seg],
        soft_decision_report=_report(dec),
        universal_moment_result=_result(risk_at_start),
    )
    assert segs[0].start_time == 60.0, "cut_risk at start must block trim"
    assert summary.start_trimmed == 0
    print("  PASS: cut_risk at edge blocks trim")


# ── run all ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_empty_inputs,
        test_safe_keep_not_trimmed,
        test_needs_human_review_not_trimmed,
        test_boring_start_trimmed,
        test_boring_end_trimmed,
        test_speech_blocks_trim,
        test_action_peak_blocks_trim,
        test_first_30s_blocks_start_trim,
        test_never_below_min_duration,
        test_total_trim_budget,
        test_final_invariants,
        test_cut_risk_blocks_trim,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as exc:
            print(f"  FAIL [{test.__name__}]: {exc}")
            failed += 1
        except Exception as exc:
            print(f"  ERROR [{test.__name__}]: {type(exc).__name__}: {exc}")
            failed += 1

    print()
    print(f"Results: {passed}/{len(tests)} passed, {failed} failed")
    if failed == 0:
        print()
        print("UNIVERSAL SAFE EDGE TRIM APPLIER SMOKE TEST PASSED")
    else:
        sys.exit(1)
