from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.universal_moment_review_exporter import UniversalMomentReviewExporter
from core.universal_moment_soft_decision_builder import UniversalMomentSoftDecisionBuilder
from models.universal_moment_debug_report import (
    UniversalMomentDebugReport,
    UniversalMomentSegmentDebug,
)
from models.universal_moment_soft_decision import UniversalMomentSoftDecisionReport


SCORE_FIELDS = (
    "keep_confidence",
    "remove_confidence",
    "trim_confidence",
    "review_confidence",
    "conflict_score",
    "private_confidence",
    "boring_confidence",
    "action_confidence",
    "speech_confidence",
    "context_confidence",
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
    private: float = 0.0,
    boring: float = 0.0,
    cut: float = 0.0,
    zoom: float = 0.0,
    speech: float = 0.0,
    menu: float = 0.0,
    has_keep: bool = False,
    has_remove: bool = False,
    has_cut: bool = False,
    has_zoom: bool = False,
    has_private: bool = False,
    pre: bool = False,
    post_context: bool = False,
) -> UniversalMomentSegmentDebug:
    diagnosis = []
    if has_keep:
        diagnosis.append("KEEP: peak/tension signal detected")
    if has_remove:
        diagnosis.append("REMOVE-CANDIDATE: boring/menu/dead-time signal")
    if has_private:
        diagnosis.append("PRIVATE: menu speech/private talk risk")
    if has_cut:
        diagnosis.append("RISK: cut boundary may hit speech/action")
    if verdict == "mixed_conflict":
        diagnosis.append("MIXED_CONFLICT: keep and remove signals disagree")

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
        avg_private_talk_score=private,
        avg_boring_score=boring,
        avg_cut_risk_score=cut,
        avg_zoom_risk_score=zoom,
        raw_cut_risk_score=cut,
        avg_speech_score=speech,
        avg_menu_wait_score=menu,
        has_keep_signal=has_keep,
        has_remove_signal=has_remove,
        has_cut_risk=has_cut,
        has_zoom_risk=has_zoom,
        has_private_menu_risk=has_private,
        has_pre_context_need=pre,
        has_post_context_need=post_context,
        professional_verdict=verdict,
        professional_reason=f"{verdict}: test segment",
        diagnosis=diagnosis,
    )


def report(*segments: UniversalMomentSegmentDebug) -> UniversalMomentDebugReport:
    return UniversalMomentDebugReport(job_id="job_soft", segments=list(segments))


def build(*segments: UniversalMomentSegmentDebug) -> UniversalMomentSoftDecisionReport:
    return UniversalMomentSoftDecisionBuilder().build(
        job_id="job_soft",
        debug_report=report(*segments),
    )


def by_id(report: UniversalMomentSoftDecisionReport, segment_id: str):
    for decision in report.decisions:
        if decision.segment_id == segment_id:
            return decision
    raise AssertionError(f"missing soft decision: {segment_id}")


def assert_scores_clamped(report: UniversalMomentSoftDecisionReport) -> None:
    assert 0.0 <= report.avg_keep_confidence <= 1.0
    assert 0.0 <= report.avg_remove_confidence <= 1.0
    assert 0.0 <= report.avg_conflict_score <= 1.0
    for decision in report.decisions:
        for field in SCORE_FIELDS:
            value = getattr(decision, field)
            assert 0.0 <= value <= 1.0, f"{decision.segment_id}.{field}={value}"


def main() -> None:
    empty = UniversalMomentSoftDecisionBuilder().build(
        job_id="job_empty",
        debug_report=UniversalMomentDebugReport(job_id="job_empty"),
    )
    assert empty.total_segments == 0
    assert empty.avg_conflict_score == 0.0

    strong = build(
        debug_segment(
            "strong_peak",
            40.0,
            50.0,
            role="peak",
            verdict="keep_strong",
            keep=0.82,
            peak=0.84,
            tension=0.78,
            post=0.66,
            has_keep=True,
        )
    )
    strong_peak = by_id(strong, "strong_peak")
    assert strong_peak.soft_decision in {"safe_keep", "keep_dominant"}
    assert strong_peak.should_not_auto_remove

    remove = build(
        debug_segment(
            "private_boring",
            50.0,
            60.0,
            verdict="review_boring",
            remove=0.86,
            private=0.82,
            boring=0.88,
            menu=0.84,
            has_remove=True,
            has_private=True,
        )
    )
    private_boring = by_id(remove, "private_boring")
    assert private_boring.soft_decision == "remove_dominant"
    assert private_boring.should_not_auto_remove is False

    mixed = build(
        debug_segment(
            "mixed_keep_private",
            80.0,
            90.0,
            verdict="mixed_conflict",
            keep=0.72,
            remove=0.78,
            peak=0.70,
            tension=0.62,
            private=0.80,
            boring=0.50,
            menu=0.76,
            has_keep=True,
            has_remove=True,
            has_private=True,
        )
    )
    mixed_keep_private = by_id(mixed, "mixed_keep_private")
    assert mixed_keep_private.soft_decision in {"trim_edges_candidate", "needs_human_review"}
    assert mixed_keep_private.is_mixed_conflict

    cut_private = build(
        debug_segment(
            "cut_private",
            100.0,
            110.0,
            verdict="review_cut_risk",
            remove=0.72,
            private=0.78,
            boring=0.52,
            cut=0.82,
            menu=0.74,
            has_remove=True,
            has_private=True,
            has_cut=True,
        )
    )
    assert by_id(cut_private, "cut_private").soft_decision == "needs_human_review"

    first_30s = build(
        debug_segment(
            "first_30s_private",
            10.0,
            20.0,
            verdict="review_boring",
            remove=0.88,
            private=0.82,
            boring=0.86,
            has_remove=True,
            has_private=True,
        )
    )
    first_30s_private = by_id(first_30s, "first_30s_private")
    assert first_30s_private.soft_decision != "remove_dominant"
    assert first_30s_private.should_not_auto_remove
    assert "first_30s_context_protection" in first_30s_private.warnings

    protected = build(
        debug_segment(
            "protected_hook",
            70.0,
            80.0,
            role="hook",
            verdict="review_private_menu",
            remove=0.84,
            private=0.82,
            boring=0.76,
            has_remove=True,
            has_private=True,
        ),
        debug_segment(
            "protected_peak",
            90.0,
            100.0,
            role="peak",
            verdict="mixed_conflict",
            keep=0.66,
            remove=0.74,
            peak=0.62,
            private=0.76,
            has_keep=True,
            has_remove=True,
            has_private=True,
        ),
        debug_segment(
            "protected_payoff",
            110.0,
            120.0,
            role="payoff",
            verdict="review_boring",
            remove=0.84,
            boring=0.82,
            has_remove=True,
        ),
    )
    for segment_id in ("protected_hook", "protected_peak", "protected_payoff"):
        decision = by_id(protected, segment_id)
        assert decision.should_not_auto_remove
        assert decision.soft_decision != "remove_dominant"

    review_report = report(
        debug_segment(
            "review_export",
            130.0,
            140.0,
            verdict="mixed_conflict",
            keep=0.72,
            remove=0.76,
            peak=0.68,
            private=0.78,
            has_keep=True,
            has_remove=True,
            has_private=True,
        )
    )
    soft_report = UniversalMomentSoftDecisionBuilder().build(
        job_id="job_soft",
        debug_report=review_report,
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        review_path = UniversalMomentReviewExporter().write_report(
            report=review_report,
            output_dir=temp_dir,
            soft_decision_report=soft_report,
        )
        markdown = review_path.read_text(encoding="utf-8")
        assert "## Soft Decision Summary" in markdown
        assert "- Soft Decision:" in markdown
        assert "  - Decision:" in markdown
        assert "  - Conflict Score:" in markdown

    roundtrip = UniversalMomentSoftDecisionReport.from_dict(soft_report.to_dict())
    assert roundtrip.to_dict() == soft_report.to_dict()

    clamped = build(
        debug_segment(
            "clamped",
            150.0,
            160.0,
            verdict="mixed_conflict",
            keep=2.0,
            remove=2.0,
            peak=2.0,
            tension=-1.0,
            private=2.0,
            boring=2.0,
            cut=2.0,
            has_keep=True,
            has_remove=True,
            has_private=True,
            has_cut=True,
        )
    )
    assert_scores_clamped(clamped)
    assert_scores_clamped(soft_report)

    print("UNIVERSAL MOMENT SOFT DECISION SMOKE TEST PASSED")


def test_universal_moment_soft_decision_smoke() -> None:
    main()


if __name__ == "__main__":
    main()
