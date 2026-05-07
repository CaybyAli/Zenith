from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.phase_2b_final_review_builder import Phase2BFinalReviewBuilder
from core.universal_context_auditor import UniversalContextAuditor
from core.universal_moment_review_exporter import UniversalMomentReviewExporter
from models.phase_2b_final_review import Phase2BFinalReviewReport
from models.timeline_segment import TimelineSegment
from models.universal_context_audit import UniversalContextAuditReport, UniversalSegmentContextAudit
from models.universal_moment_debug_report import (
    UniversalMomentDebugReport,
    UniversalMomentSegmentDebug,
)
from models.universal_moment_result import UniversalMomentResult, UniversalMomentWindow
from models.universal_moment_soft_decision import (
    UniversalMomentSegmentDecision,
    UniversalMomentSoftDecisionReport,
)


def segment(segment_id: str, start: float, end: float, *, role: str = "bridge") -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id="job_z3",
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=0.5,
        source="smoke",
    )


def debug_segment(
    segment_id: str,
    start: float,
    end: float,
    *,
    role: str = "bridge",
    verdict: str = "unknown",
    keep: float = 0.0,
    remove: float = 0.0,
    peak: float = 0.0,
    tension: float = 0.0,
    post: float = 0.0,
    speech: float = 0.0,
    private: float = 0.0,
    boring: float = 0.0,
    cut: float = 0.0,
    zoom: float = 0.0,
    has_cut: bool = False,
) -> UniversalMomentSegmentDebug:
    return UniversalMomentSegmentDebug(
        segment_id=segment_id,
        segment_role=role,
        start_time=start,
        end_time=end,
        avg_keep_score=keep,
        avg_remove_score=remove,
        avg_peak_score=peak,
        avg_tension_score=tension,
        avg_post_reaction_score=post,
        avg_speech_score=speech,
        avg_private_talk_score=private,
        avg_boring_score=boring,
        avg_cut_risk_score=cut,
        avg_zoom_risk_score=zoom,
        has_keep_signal=keep >= 0.55,
        has_remove_signal=remove >= 0.55,
        has_cut_risk=has_cut,
        confirmed_cut_risk=has_cut,
        professional_verdict=verdict,
        professional_reason=f"{verdict}: smoke",
        diagnosis=[f"{verdict}: smoke"],
    )


def decision(
    segment_id: str,
    start: float,
    end: float,
    *,
    role: str = "bridge",
    soft_decision: str = "needs_human_review",
    keep: float = 0.0,
    remove: float = 0.0,
    conflict: float = 0.0,
) -> UniversalMomentSegmentDecision:
    return UniversalMomentSegmentDecision(
        segment_id=segment_id,
        segment_role=role,
        start_time=start,
        end_time=end,
        keep_confidence=keep,
        remove_confidence=remove,
        conflict_score=conflict,
        soft_decision=soft_decision,
        needs_human_review=soft_decision == "needs_human_review",
        can_trim_edges_later=soft_decision == "trim_edges_candidate",
        is_mixed_conflict=conflict >= 0.55,
        source_verdict="smoke",
    )


def moment_window(
    window_id: str,
    start: float,
    end: float,
    *,
    speech: float = 0.0,
    cut: float = 0.0,
    peak: float = 0.0,
    tension: float = 0.0,
    action: float = 0.0,
    speech_boundary: bool = False,
    action_boundary: bool = False,
    moment_type: str = "smoke",
) -> UniversalMomentWindow:
    return UniversalMomentWindow(
        window_id=window_id,
        start_seconds=start,
        end_seconds=end,
        speech_score=speech,
        cut_risk_score=cut,
        peak_score=peak,
        tension_score=tension,
        visual_action_score=action,
        gameplay_motion_score=action,
        speech_boundary_risk=speech_boundary,
        action_context_risk=action_boundary,
        moment_type=moment_type,
    )


def debug_report(*segments: UniversalMomentSegmentDebug) -> UniversalMomentDebugReport:
    return UniversalMomentDebugReport(job_id="job_z3", segments=list(segments))


def soft_report(*decisions: UniversalMomentSegmentDecision) -> UniversalMomentSoftDecisionReport:
    return UniversalMomentSoftDecisionReport(job_id="job_z3", decisions=list(decisions))


def context_report(*segments: UniversalSegmentContextAudit) -> UniversalContextAuditReport:
    return UniversalContextAuditReport(job_id="job_z3", segments=list(segments))


def build_context(
    timeline_segments: list[TimelineSegment],
    debug_segments: list[UniversalMomentSegmentDebug],
    decisions: list[UniversalMomentSegmentDecision],
    windows: list[UniversalMomentWindow] | None = None,
) -> UniversalContextAuditReport:
    return UniversalContextAuditor().build(
        job_id="job_z3",
        timeline_segments=timeline_segments,
        debug_report=debug_report(*debug_segments),
        soft_decision_report=soft_report(*decisions),
        universal_moment_result=UniversalMomentResult(windows=list(windows or [])),
    )


def by_id(report, segment_id: str):
    for segment_review in report.segments:
        if segment_review.segment_id == segment_id:
            return segment_review
    raise AssertionError(f"missing segment: {segment_id}")


def test_speech_inside_segment_not_at_edge_is_not_speech_cut_risk() -> None:
    timeline = [
        segment("speech_mid_left", 100.0, 110.0),
        segment("speech_mid_right", 110.0, 120.0),
    ]
    report = build_context(
        timeline,
        [
            debug_segment("speech_mid_left", 100.0, 110.0, speech=0.78, keep=0.45),
            debug_segment("speech_mid_right", 110.0, 120.0, speech=0.76, keep=0.45),
        ],
        [
            decision("speech_mid_left", 100.0, 110.0, keep=0.45),
            decision("speech_mid_right", 110.0, 120.0, keep=0.45),
        ],
        [
            moment_window("left_mid_speech", 104.0, 106.0, speech=0.82),
            moment_window("right_mid_speech", 114.0, 116.0, speech=0.80),
        ],
    )
    left = by_id(report, "speech_mid_left")
    right = by_id(report, "speech_mid_right")
    assert left.next_boundary_type != "speech_cut_risk"
    assert right.previous_boundary_type != "speech_cut_risk"


def test_speech_directly_at_edge_is_speech_cut_risk() -> None:
    timeline = [
        segment("speech_edge_left", 130.0, 140.0),
        segment("speech_edge_right", 140.0, 150.0),
    ]
    report = build_context(
        timeline,
        [
            debug_segment("speech_edge_left", 130.0, 140.0, speech=0.55, keep=0.45),
            debug_segment("speech_edge_right", 140.0, 150.0, speech=0.55, keep=0.45),
        ],
        [
            decision("speech_edge_left", 130.0, 140.0, keep=0.45),
            decision("speech_edge_right", 140.0, 150.0, keep=0.45),
        ],
        [
            moment_window("speech_edge", 139.55, 140.25, speech=0.68, cut=0.78, speech_boundary=True),
        ],
    )
    right = by_id(report, "speech_edge_right")
    assert right.previous_boundary_type == "speech_cut_risk"
    assert right.previous_boundary_risk


def test_peak_action_at_edge_is_action_cut_risk() -> None:
    timeline = [
        segment("action_edge_left", 160.0, 170.0),
        segment("action_edge_right", 170.0, 180.0),
    ]
    report = build_context(
        timeline,
        [
            debug_segment("action_edge_left", 160.0, 170.0, keep=0.45),
            debug_segment("action_edge_right", 170.0, 180.0, keep=0.45),
        ],
        [
            decision("action_edge_left", 160.0, 170.0, keep=0.45),
            decision("action_edge_right", 170.0, 180.0, keep=0.45),
        ],
        [
            moment_window(
                "action_edge",
                169.45,
                170.35,
                peak=0.68,
                tension=0.62,
                action=0.75,
                action_boundary=True,
                moment_type="peak_action",
            ),
        ],
    )
    right = by_id(report, "action_edge_right")
    assert right.previous_boundary_type == "action_cut_risk"
    assert right.previous_boundary_risk


def test_weak_protected_payoff_role_is_not_automatic_payoff_keep() -> None:
    timeline = [segment("weak_peak", 190.0, 200.0, role="peak")]
    report = build_context(
        timeline,
        [debug_segment("weak_peak", 190.0, 200.0, role="peak", keep=0.45, peak=0.20, post=0.10)],
        [decision("weak_peak", 190.0, 200.0, role="peak", soft_decision="needs_human_review", keep=0.45, conflict=0.42)],
    )
    weak_peak = by_id(report, "weak_peak")
    assert weak_peak.context_decision != "keep_as_payoff"
    assert "protected_role_without_strong_payoff_signal" in weak_peak.warnings


def test_edge_trim_diagnosis_requires_clean_nonprotected_nonfirst30_context() -> None:
    timeline = [
        segment("weak_prev", 210.0, 219.0),
        segment("edge_trim_candidate", 220.0, 230.0),
        segment("weak_next", 231.0, 240.0),
        segment("early_candidate", 10.0, 20.0),
        segment("protected_candidate", 250.0, 260.0, role="peak"),
    ]
    report = build_context(
        timeline,
        [
            debug_segment("early_candidate", 10.0, 20.0, private=0.65, remove=0.56),
            debug_segment("weak_prev", 210.0, 219.0, keep=0.56),
            debug_segment("edge_trim_candidate", 220.0, 230.0, private=0.64, remove=0.56, peak=0.10, tension=0.10),
            debug_segment("weak_next", 231.0, 240.0, keep=0.56),
            debug_segment("protected_candidate", 250.0, 260.0, role="peak", private=0.65, remove=0.56, peak=0.10),
        ],
        [
            decision("early_candidate", 10.0, 20.0, remove=0.56, conflict=0.40),
            decision("weak_prev", 210.0, 219.0, keep=0.56),
            decision("edge_trim_candidate", 220.0, 230.0, remove=0.56, conflict=0.40),
            decision("weak_next", 231.0, 240.0, keep=0.56),
            decision("protected_candidate", 250.0, 260.0, role="peak", remove=0.56, conflict=0.40),
        ],
    )
    edge = by_id(report, "edge_trim_candidate")
    early = by_id(report, "early_candidate")
    protected = by_id(report, "protected_candidate")
    assert edge.context_decision == "edge_trim_candidate"
    assert edge.can_consider_start_trim_later or edge.can_consider_end_trim_later
    assert early.context_decision != "edge_trim_candidate"
    assert protected.context_decision != "edge_trim_candidate"


def test_final_review_statuses_and_roundtrip() -> None:
    debug = debug_report(
        debug_segment("strong", 300.0, 310.0, role="peak", keep=0.82, peak=0.80),
        debug_segment("boundary", 320.0, 330.0, role="peak", keep=0.82, peak=0.80),
        debug_segment("review", 340.0, 350.0, keep=0.48, remove=0.52),
        debug_segment("edge", 360.0, 370.0, role="bridge", keep=0.46, remove=0.58, private=0.62),
    )
    soft = soft_report(
        decision("strong", 300.0, 310.0, role="peak", soft_decision="safe_keep", keep=0.82, remove=0.20),
        decision("boundary", 320.0, 330.0, role="peak", soft_decision="safe_keep", keep=0.82, remove=0.20),
        decision("review", 340.0, 350.0, soft_decision="needs_human_review", keep=0.48, remove=0.52, conflict=0.62),
        decision("edge", 360.0, 370.0, role="bridge", soft_decision="needs_human_review", keep=0.46, remove=0.58, conflict=0.40),
    )
    context = context_report(
        UniversalSegmentContextAudit(
            segment_id="strong",
            segment_role="peak",
            start_time=300.0,
            end_time=310.0,
            context_decision="keep_as_payoff",
            previous_boundary_type="clean",
            next_boundary_type="clean",
            context_conflict_score=0.20,
        ),
        UniversalSegmentContextAudit(
            segment_id="boundary",
            segment_role="peak",
            start_time=320.0,
            end_time=330.0,
            context_decision="keep_context_chain",
            previous_boundary_type="speech_cut_risk",
            next_boundary_type="clean",
            should_protect_previous_boundary=True,
            context_conflict_score=0.30,
        ),
        UniversalSegmentContextAudit(
            segment_id="review",
            segment_role="bridge",
            start_time=340.0,
            end_time=350.0,
            context_decision="needs_human_review",
            context_conflict_score=0.62,
        ),
        UniversalSegmentContextAudit(
            segment_id="edge",
            segment_role="bridge",
            start_time=360.0,
            end_time=370.0,
            context_decision="edge_trim_candidate",
            edge_trim_safety_score=0.60,
            can_consider_start_trim_later=True,
            context_conflict_score=0.40,
        ),
    )
    final = Phase2BFinalReviewBuilder().build(
        job_id="job_z3",
        debug_report=debug,
        soft_decision_report=soft,
        context_audit_report=context,
    )
    assert by_id(final, "strong").final_review_status == "strong_keep"
    assert by_id(final, "boundary").final_review_status == "keep_with_boundary_warning"
    assert by_id(final, "review").final_review_status == "review_needed"
    assert by_id(final, "edge").final_review_status == "possible_edge_trim_later"
    assert by_id(final, "boundary").human_review_priority == "high"
    assert by_id(final, "edge").human_review_priority == "high"
    assert Phase2BFinalReviewReport.from_dict(final.to_dict()).to_dict() == final.to_dict()

    with tempfile.TemporaryDirectory() as temp_dir:
        review_path = UniversalMomentReviewExporter().write_report(
            report=debug,
            output_dir=temp_dir,
            soft_decision_report=soft,
            context_audit_report=context,
            final_review_report=final,
        )
        markdown = review_path.read_text(encoding="utf-8")
    assert "## Phase 2.B Final Review Summary" in markdown
    assert "- Phase 2.B Final Review:" in markdown
    assert "  - Status: possible_edge_trim_later" in markdown


def main() -> None:
    test_speech_inside_segment_not_at_edge_is_not_speech_cut_risk()
    test_speech_directly_at_edge_is_speech_cut_risk()
    test_peak_action_at_edge_is_action_cut_risk()
    test_weak_protected_payoff_role_is_not_automatic_payoff_keep()
    test_edge_trim_diagnosis_requires_clean_nonprotected_nonfirst30_context()
    test_final_review_statuses_and_roundtrip()
    print("CONTEXT BOUNDARY CALIBRATION FINAL REVIEW SMOKE TEST PASSED")


def test_context_boundary_calibration_final_review_smoke() -> None:
    main()


if __name__ == "__main__":
    main()
