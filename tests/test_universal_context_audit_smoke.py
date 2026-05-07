from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.universal_context_auditor import UniversalContextAuditor
from core.universal_moment_review_exporter import UniversalMomentReviewExporter
from models.timeline_segment import TimelineSegment
from models.universal_context_audit import UniversalContextAuditReport
from models.universal_moment_debug_report import (
    UniversalMomentDebugReport,
    UniversalMomentSegmentDebug,
)
from models.universal_moment_result import UniversalMomentResult, UniversalMomentWindow
from models.universal_moment_soft_decision import (
    UniversalMomentSegmentDecision,
    UniversalMomentSoftDecisionReport,
)


def segment(
    segment_id: str,
    start: float,
    end: float,
    *,
    role: str = "bridge",
) -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id="job_context_audit",
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
    menu: float = 0.0,
    boring: float = 0.0,
    cut: float = 0.0,
    zoom: float = 0.0,
    has_keep: bool = False,
    has_remove: bool = False,
    has_private: bool = False,
    has_cut: bool = False,
    has_zoom: bool = False,
    has_pre: bool = False,
    has_post: bool = False,
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
        avg_menu_wait_score=menu,
        avg_boring_score=boring,
        avg_cut_risk_score=cut,
        avg_zoom_risk_score=zoom,
        raw_cut_risk_score=cut,
        has_keep_signal=has_keep,
        has_remove_signal=has_remove,
        has_private_menu_risk=has_private,
        has_cut_risk=has_cut,
        has_zoom_risk=has_zoom,
        has_pre_context_need=has_pre,
        has_post_context_need=has_post,
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
        source_verdict="smoke",
    )


def window(
    window_id: str,
    start: float,
    end: float,
    *,
    peak: float = 0.0,
    tension: float = 0.0,
    action: float = 0.0,
    speech: float = 0.0,
    private: float = 0.0,
    menu: float = 0.0,
    boring: float = 0.0,
    cut: float = 0.0,
    zoom: float = 0.0,
    speech_boundary: bool = False,
    action_boundary: bool = False,
) -> UniversalMomentWindow:
    return UniversalMomentWindow(
        window_id=window_id,
        start_seconds=start,
        end_seconds=end,
        peak_score=peak,
        tension_score=tension,
        visual_action_score=action,
        gameplay_motion_score=action,
        speech_score=speech,
        private_talk_score=private,
        menu_wait_score=menu,
        boring_score=boring,
        dead_time_score=boring,
        cut_risk_score=cut,
        zoom_risk_score=zoom,
        speech_boundary_risk=speech_boundary,
        action_context_risk=action_boundary,
        moment_type="smoke",
    )


def debug_report(*segments: UniversalMomentSegmentDebug) -> UniversalMomentDebugReport:
    return UniversalMomentDebugReport(job_id="job_context_audit", segments=list(segments))


def soft_report(*decisions: UniversalMomentSegmentDecision) -> UniversalMomentSoftDecisionReport:
    return UniversalMomentSoftDecisionReport(job_id="job_context_audit", decisions=list(decisions))


def moment_result(*windows: UniversalMomentWindow) -> UniversalMomentResult:
    return UniversalMomentResult(windows=list(windows))


def build_report(
    timeline_segments: list[TimelineSegment],
    debug_segments: list[UniversalMomentSegmentDebug],
    decisions: list[UniversalMomentSegmentDecision],
    windows: list[UniversalMomentWindow] | None = None,
) -> UniversalContextAuditReport:
    return UniversalContextAuditor().build(
        job_id="job_context_audit",
        timeline_segments=timeline_segments,
        debug_report=debug_report(*debug_segments),
        soft_decision_report=soft_report(*decisions),
        universal_moment_result=moment_result(*(windows or [])),
    )


def by_id(report: UniversalContextAuditReport, segment_id: str):
    for audit in report.segments:
        if audit.segment_id == segment_id:
            return audit
    raise AssertionError(f"missing context audit segment: {segment_id}")


def test_empty_inputs_do_not_crash() -> None:
    report = UniversalContextAuditor().build(
        job_id="job_empty",
        timeline_segments=[],
        debug_report=None,
        soft_decision_report=None,
        role_decision_audit_report=None,
        universal_moment_result=None,
    )
    assert report.total_segments == 0
    assert report.avg_context_conflict_score == 0.0


def test_previous_setup_current_peak_keeps_payoff() -> None:
    timeline = [
        segment("setup", 60.0, 70.0, role="build"),
        segment("payoff", 70.2, 80.0, role="peak"),
    ]
    report = build_report(
        timeline,
        [
            debug_segment("setup", 60.0, 70.0, role="build", keep=0.65, tension=0.66, has_pre=True),
            debug_segment("payoff", 70.2, 80.0, role="peak", keep=0.80, peak=0.82, post=0.60),
        ],
        [
            decision("setup", 60.0, 70.0, role="build", soft_decision="keep_dominant", keep=0.68),
            decision("payoff", 70.2, 80.0, role="peak", soft_decision="safe_keep", keep=0.82),
        ],
    )
    payoff = by_id(report, "payoff")
    assert payoff.previous_relation == "setup_context"
    assert payoff.context_decision == "keep_as_payoff"


def test_current_setup_next_peak_keeps_setup() -> None:
    timeline = [
        segment("setup", 90.0, 100.0, role="build"),
        segment("next_peak", 100.2, 110.0, role="peak"),
    ]
    report = build_report(
        timeline,
        [
            debug_segment("setup", 90.0, 100.0, role="build", keep=0.62, tension=0.64, has_pre=True),
            debug_segment("next_peak", 100.2, 110.0, role="peak", keep=0.82, peak=0.84, post=0.60),
        ],
        [
            decision("setup", 90.0, 100.0, role="build", soft_decision="needs_human_review", keep=0.60, conflict=0.35),
            decision("next_peak", 100.2, 110.0, role="peak", soft_decision="safe_keep", keep=0.84),
        ],
    )
    setup = by_id(report, "setup")
    assert setup.next_relation == "payoff_context"
    assert setup.context_decision == "keep_as_setup"


def test_private_menu_neighbors_create_block_candidate() -> None:
    timeline = [
        segment("private_prev", 120.0, 130.0, role="bridge"),
        segment("private_current", 130.0, 140.0, role="bridge"),
        segment("private_next", 140.0, 150.0, role="bridge"),
    ]
    report = build_report(
        timeline,
        [
            debug_segment("private_prev", 120.0, 130.0, private=0.68, menu=0.62, boring=0.50, remove=0.58, has_private=True),
            debug_segment("private_current", 130.0, 140.0, private=0.72, menu=0.66, boring=0.54, remove=0.62, has_private=True, has_remove=True),
            debug_segment("private_next", 140.0, 150.0, private=0.67, menu=0.63, boring=0.50, remove=0.57, has_private=True),
        ],
        [
            decision("private_prev", 120.0, 130.0, remove=0.58),
            decision("private_current", 130.0, 140.0, remove=0.62, conflict=0.42),
            decision("private_next", 140.0, 150.0, remove=0.57),
        ],
    )
    current = by_id(report, "private_current")
    assert current.previous_relation in {"menu_continuation", "private_talk_continuation"}
    assert current.next_relation in {"menu_continuation", "private_talk_continuation"}
    assert current.context_decision == "private_menu_block_candidate"


def test_boring_current_without_strong_neighbor_context_is_bridge_candidate() -> None:
    timeline = [
        segment("weak_prev", 160.0, 170.0, role="build"),
        segment("boring_current", 170.8, 180.0, role="bridge"),
        segment("weak_next", 180.8, 190.0, role="build"),
    ]
    report = build_report(
        timeline,
        [
            debug_segment("weak_prev", 160.0, 170.0, keep=0.22, remove=0.18, peak=0.12, tension=0.18),
            debug_segment("boring_current", 170.8, 180.0, remove=0.66, boring=0.72, peak=0.10, tension=0.14, has_remove=True),
            debug_segment("weak_next", 180.8, 190.0, keep=0.20, remove=0.16, peak=0.12, tension=0.16),
        ],
        [
            decision("weak_prev", 160.0, 170.0, soft_decision="needs_human_review", keep=0.22, remove=0.18),
            decision("boring_current", 170.8, 180.0, soft_decision="needs_human_review", keep=0.22, remove=0.66, conflict=0.36),
            decision("weak_next", 180.8, 190.0, soft_decision="needs_human_review", keep=0.20, remove=0.16),
        ],
    )
    current = by_id(report, "boring_current")
    assert current.previous_boundary_type == "clean"
    assert current.next_boundary_type == "clean"
    assert current.context_decision == "boring_bridge_candidate"


def test_speech_boundary_is_protected() -> None:
    timeline = [
        segment("speech_left", 200.0, 210.0, role="build"),
        segment("speech_right", 210.0, 220.0, role="bridge"),
    ]
    report = build_report(
        timeline,
        [
            debug_segment("speech_left", 200.0, 210.0, speech=0.70, keep=0.45),
            debug_segment("speech_right", 210.0, 220.0, speech=0.72, keep=0.45),
        ],
        [
            decision("speech_left", 200.0, 210.0, soft_decision="needs_human_review", keep=0.45),
            decision("speech_right", 210.0, 220.0, soft_decision="needs_human_review", keep=0.45),
        ],
        [
            window("speech_edge", 209.7, 210.3, speech=0.78, cut=0.76, speech_boundary=True),
        ],
    )
    right = by_id(report, "speech_right")
    assert right.previous_boundary_type == "speech_cut_risk"
    assert right.context_decision in {"boundary_protect", "keep_context_chain"}


def test_action_boundary_is_protected() -> None:
    timeline = [
        segment("action_left", 230.0, 240.0, role="build"),
        segment("action_right", 240.0, 250.0, role="bridge"),
    ]
    report = build_report(
        timeline,
        [
            debug_segment("action_left", 230.0, 240.0, keep=0.42, peak=0.22, tension=0.24),
            debug_segment("action_right", 240.0, 250.0, keep=0.42, peak=0.24, tension=0.22),
        ],
        [
            decision("action_left", 230.0, 240.0, soft_decision="needs_human_review", keep=0.42),
            decision("action_right", 240.0, 250.0, soft_decision="needs_human_review", keep=0.42),
        ],
        [
            window("action_edge", 239.7, 240.3, peak=0.82, tension=0.72, action=0.80, action_boundary=True),
        ],
    )
    right = by_id(report, "action_right")
    assert right.previous_boundary_type == "action_cut_risk"
    assert right.previous_boundary_risk


def test_first_30_seconds_sets_safety() -> None:
    timeline = [segment("early_bridge", 10.0, 20.0, role="bridge")]
    report = build_report(
        timeline,
        [debug_segment("early_bridge", 10.0, 20.0, remove=0.64, boring=0.68, has_remove=True)],
        [decision("early_bridge", 10.0, 20.0, soft_decision="needs_human_review", remove=0.64, conflict=0.36)],
    )
    early = by_id(report, "early_bridge")
    assert early.should_not_auto_remove
    assert "first_30s_context_protection" in early.warnings


def test_protected_roles_set_safety() -> None:
    timeline = [segment("protected_peak", 260.0, 270.0, role="peak")]
    report = build_report(
        timeline,
        [debug_segment("protected_peak", 260.0, 270.0, role="peak", peak=0.70, keep=0.72)],
        [decision("protected_peak", 260.0, 270.0, role="peak", soft_decision="safe_keep", keep=0.72)],
    )
    protected = by_id(report, "protected_peak")
    assert protected.should_not_auto_remove
    assert "protected_segment_role" in protected.warnings


def test_to_dict_from_dict_roundtrip() -> None:
    timeline = [
        segment("roundtrip_setup", 300.0, 310.0, role="build"),
        segment("roundtrip_peak", 310.2, 320.0, role="peak"),
    ]
    report = build_report(
        timeline,
        [
            debug_segment("roundtrip_setup", 300.0, 310.0, role="build", keep=0.64, tension=0.64),
            debug_segment("roundtrip_peak", 310.2, 320.0, role="peak", keep=0.82, peak=0.82),
        ],
        [
            decision("roundtrip_setup", 300.0, 310.0, role="build", soft_decision="needs_human_review", keep=0.64),
            decision("roundtrip_peak", 310.2, 320.0, role="peak", soft_decision="safe_keep", keep=0.82),
        ],
    )
    roundtrip = UniversalContextAuditReport.from_dict(report.to_dict())
    assert roundtrip.to_dict() == report.to_dict()


def test_review_markdown_contains_neighbor_context_audit() -> None:
    timeline = [
        segment("markdown_setup", 340.0, 350.0, role="build"),
        segment("markdown_peak", 350.2, 360.0, role="peak"),
    ]
    debug = debug_report(
        debug_segment("markdown_setup", 340.0, 350.0, role="build", keep=0.62, tension=0.64),
        debug_segment("markdown_peak", 350.2, 360.0, role="peak", keep=0.82, peak=0.84),
    )
    soft = soft_report(
        decision("markdown_setup", 340.0, 350.0, role="build", soft_decision="needs_human_review", keep=0.62),
        decision("markdown_peak", 350.2, 360.0, role="peak", soft_decision="safe_keep", keep=0.82),
    )
    context = UniversalContextAuditor().build(
        job_id="job_context_audit",
        timeline_segments=timeline,
        debug_report=debug,
        soft_decision_report=soft,
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        review_path = UniversalMomentReviewExporter().write_report(
            report=debug,
            output_dir=temp_dir,
            soft_decision_report=soft,
            context_audit_report=context,
        )
        markdown = review_path.read_text(encoding="utf-8")
    assert "## Neighbor Context Audit Summary" in markdown
    assert "- Neighbor Context Audit:" in markdown
    assert "  - Context Decision: keep_as_setup" in markdown


def main() -> None:
    test_empty_inputs_do_not_crash()
    test_previous_setup_current_peak_keeps_payoff()
    test_current_setup_next_peak_keeps_setup()
    test_private_menu_neighbors_create_block_candidate()
    test_boring_current_without_strong_neighbor_context_is_bridge_candidate()
    test_speech_boundary_is_protected()
    test_action_boundary_is_protected()
    test_first_30_seconds_sets_safety()
    test_protected_roles_set_safety()
    test_to_dict_from_dict_roundtrip()
    test_review_markdown_contains_neighbor_context_audit()
    print("UNIVERSAL CONTEXT AUDIT SMOKE TEST PASSED")


def test_universal_context_audit_smoke() -> None:
    main()


if __name__ == "__main__":
    main()
