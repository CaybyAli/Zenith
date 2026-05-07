from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.universal_moment_review_exporter import UniversalMomentReviewExporter
from core.universal_moment_soft_decision_builder import UniversalMomentSoftDecisionBuilder
from core.universal_role_decision_auditor import UniversalRoleDecisionAuditor
from models.universal_moment_debug_report import (
    UniversalMomentDebugReport,
    UniversalMomentSegmentDebug,
)
from models.universal_moment_soft_decision import (
    UniversalMomentSegmentDecision,
    UniversalMomentSoftDecisionReport,
)
from models.universal_role_decision_audit import UniversalRoleDecisionAuditReport


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
    private: float = 0.0,
    boring: float = 0.0,
    cut: float = 0.0,
    zoom: float = 0.0,
    has_keep: bool = False,
    has_remove: bool = False,
    has_private: bool = False,
    has_cut: bool = False,
    has_zoom: bool = False,
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
        avg_private_talk_score=private,
        avg_boring_score=boring,
        avg_cut_risk_score=cut,
        avg_zoom_risk_score=zoom,
        raw_cut_risk_score=cut,
        has_keep_signal=has_keep,
        has_remove_signal=has_remove,
        has_private_menu_risk=has_private,
        has_cut_risk=has_cut,
        has_zoom_risk=has_zoom,
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
    soft_decision: str = "unknown",
    keep: float = 0.0,
    remove: float = 0.0,
    trim: float = 0.0,
    review: float = 0.0,
    conflict: float = 0.0,
) -> UniversalMomentSegmentDecision:
    return UniversalMomentSegmentDecision(
        segment_id=segment_id,
        segment_role=role,
        start_time=start,
        end_time=end,
        keep_confidence=keep,
        remove_confidence=remove,
        trim_confidence=trim,
        review_confidence=review,
        conflict_score=conflict,
        soft_decision=soft_decision,
        can_trim_edges_later=soft_decision == "trim_edges_candidate",
        needs_human_review=soft_decision == "needs_human_review",
        source_verdict="smoke",
    )


def debug_report(*segments: UniversalMomentSegmentDebug) -> UniversalMomentDebugReport:
    return UniversalMomentDebugReport(job_id="job_role_audit", segments=list(segments))


def soft_report(*decisions: UniversalMomentSegmentDecision) -> UniversalMomentSoftDecisionReport:
    return UniversalMomentSoftDecisionReport(job_id="job_role_audit", decisions=list(decisions))


def by_id(report: UniversalRoleDecisionAuditReport, segment_id: str):
    for segment in report.segments:
        if segment.segment_id == segment_id:
            return segment
    raise AssertionError(f"missing audit segment: {segment_id}")


def main() -> None:
    empty = UniversalRoleDecisionAuditor().build(
        job_id="job_empty",
        debug_report=None,
        soft_decision_report=None,
    )
    assert empty.total_segments == 0
    assert empty.protected_trim_conflicts == 0

    protected_conflict = UniversalRoleDecisionAuditor().build(
        job_id="job_role_audit",
        debug_report=debug_report(
            debug_segment("protected_trim", 40.0, 50.0, role="hook", peak=0.62)
        ),
        soft_decision_report=soft_report(
            decision(
                "protected_trim",
                40.0,
                50.0,
                role="hook",
                soft_decision="trim_edges_candidate",
                keep=0.70,
                remove=0.60,
                trim=0.70,
                conflict=0.50,
            )
        ),
    )
    assert protected_conflict.protected_trim_conflicts == 1
    assert by_id(protected_conflict, "protected_trim").role_decision_alignment == "protected_trim_conflict"

    review_trim = UniversalRoleDecisionAuditor().build(
        job_id="job_role_audit",
        debug_report=debug_report(
            debug_segment(
                "review_private_bridge",
                70.0,
                80.0,
                role="bridge",
                verdict="review_boring",
                peak=0.20,
                tension=0.25,
                private=0.62,
                boring=0.67,
            )
        ),
        soft_decision_report=soft_report(
            decision(
                "review_private_bridge",
                70.0,
                80.0,
                role="bridge",
                soft_decision="needs_human_review",
                keep=0.52,
                remove=0.58,
                review=0.70,
                conflict=0.48,
            )
        ),
    )
    assert review_trim.review_maybe_trim == 1
    review_audit = by_id(review_trim, "review_private_bridge")
    assert review_audit.suggested_soft_decision == "consider_trim_edges"

    safe_keep = UniversalRoleDecisionAuditor().build(
        job_id="job_role_audit",
        debug_report=debug_report(
            debug_segment("safe_keep", 90.0, 100.0, role="peak", verdict="safe", peak=0.45)
        ),
        soft_decision_report=soft_report(
            decision(
                "safe_keep",
                90.0,
                100.0,
                role="peak",
                soft_decision="safe_keep",
                keep=0.72,
                remove=0.20,
            )
        ),
    )
    assert safe_keep.safe_keep_correct == 1

    aligned = UniversalRoleDecisionAuditor().build(
        job_id="job_role_audit",
        debug_report=debug_report(
            debug_segment(
                "aligned_trim",
                110.0,
                120.0,
                role="bridge",
                peak=0.20,
                tension=0.20,
                private=0.60,
                boring=0.63,
            )
        ),
        soft_decision_report=soft_report(
            decision(
                "aligned_trim",
                110.0,
                120.0,
                role="bridge",
                soft_decision="trim_edges_candidate",
                keep=0.52,
                remove=0.58,
                trim=0.62,
                conflict=0.44,
            )
        ),
    )
    assert aligned.aligned == 1
    assert by_id(aligned, "aligned_trim").role_decision_alignment == "aligned"

    roundtrip = UniversalRoleDecisionAuditReport.from_dict(aligned.to_dict())
    assert roundtrip.to_dict() == aligned.to_dict()

    with tempfile.TemporaryDirectory() as temp_dir:
        review_path = UniversalMomentReviewExporter().write_report(
            report=debug_report(
                debug_segment(
                    "review_private_bridge",
                    70.0,
                    80.0,
                    role="bridge",
                    verdict="review_boring",
                    peak=0.20,
                    tension=0.25,
                    private=0.62,
                    boring=0.67,
                )
            ),
            output_dir=temp_dir,
            soft_decision_report=soft_report(
                decision(
                    "review_private_bridge",
                    70.0,
                    80.0,
                    role="bridge",
                    soft_decision="needs_human_review",
                    keep=0.52,
                    remove=0.58,
                    review=0.70,
                    conflict=0.48,
                )
            ),
            role_decision_audit_report=review_trim,
        )
        markdown = review_path.read_text(encoding="utf-8")
        assert "## Role Decision Audit Summary" in markdown
        assert "- Role Decision Audit:" in markdown
        assert "  - Alignment: review_maybe_trim" in markdown

    protected_soft = UniversalMomentSoftDecisionBuilder().build(
        job_id="job_role_audit",
        debug_report=debug_report(
            debug_segment(
                "protected_peak",
                130.0,
                140.0,
                role="peak",
                verdict="mixed_conflict",
                keep=0.66,
                remove=0.74,
                peak=0.62,
                private=0.76,
                boring=0.45,
                has_keep=True,
                has_remove=True,
                has_private=True,
            )
        ),
    )
    protected_decision = protected_soft.decisions[0]
    assert protected_decision.soft_decision != "trim_edges_candidate"
    assert protected_decision.should_not_auto_remove

    bridge_soft = UniversalMomentSoftDecisionBuilder().build(
        job_id="job_role_audit",
        debug_report=debug_report(
            debug_segment(
                "bridge_mixed_private",
                150.0,
                160.0,
                role="bridge",
                verdict="review_boring",
                keep=0.52,
                remove=0.58,
                peak=0.25,
                tension=0.25,
                private=0.60,
                boring=0.60,
                has_remove=True,
            )
        ),
    )
    bridge_decision = bridge_soft.decisions[0]
    assert bridge_decision.soft_decision == "trim_edges_candidate"
    assert bridge_decision.can_trim_edges_later

    print("UNIVERSAL ROLE DECISION AUDIT SMOKE TEST PASSED")


def test_universal_role_decision_audit_smoke() -> None:
    main()


if __name__ == "__main__":
    main()
