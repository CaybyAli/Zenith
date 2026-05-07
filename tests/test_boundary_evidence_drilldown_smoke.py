from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.phase_2b_final_review_builder import Phase2BFinalReviewBuilder
from core.universal_boundary_evidence_reporter import UniversalBoundaryEvidenceReporter
from core.universal_moment_review_exporter import UniversalMomentReviewExporter
from models.phase_2b_final_review import Phase2BFinalReviewReport
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment
from models.universal_boundary_evidence import UniversalBoundaryEvidenceReport
from models.universal_context_audit import UniversalContextAuditReport, UniversalSegmentContextAudit
from models.universal_moment_debug_report import UniversalMomentDebugReport, UniversalMomentSegmentDebug
from models.universal_moment_result import UniversalMomentResult, UniversalMomentWindow
from models.universal_moment_soft_decision import (
    UniversalMomentSegmentDecision,
    UniversalMomentSoftDecisionReport,
)


def _segment(segment_id: str, start: float, end: float, role: str = "build") -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id="job_boundary_evidence",
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=0.7,
    )


def _transcript(*items: tuple[float, float]) -> TranscriptResult:
    return TranscriptResult(
        source_path="test.mp4",
        language="de",
        segments=[
            TranscriptSegment(start_seconds=start, end_seconds=end, text=f"speech {index}")
            for index, (start, end) in enumerate(items, start=1)
        ],
        full_text="speech",
        engine="test",
    )


def _sentences(*items: tuple[float, float]) -> SentenceTimelineResult:
    return SentenceTimelineResult(
        sentences=[
            SentenceItem(
                sentence_id=f"sentence_{index}",
                text="sentence",
                start_seconds=start,
                end_seconds=end,
                duration_seconds=end - start,
                score=0.8,
                confidence=0.9,
                sentence_kind="normal",
            )
            for index, (start, end) in enumerate(items, start=1)
        ]
    )


def _moment(start: float, end: float, **scores) -> UniversalMomentWindow:
    return UniversalMomentWindow(
        window_id=f"w_{start}_{end}",
        start_seconds=start,
        end_seconds=end,
        duration_seconds=end - start,
        confidence=0.9,
        **scores,
    )


def _context_with_warning(left: TimelineSegment, right: TimelineSegment) -> UniversalContextAuditReport:
    return UniversalContextAuditReport(
        job_id="job_boundary_evidence",
        segments=[
            UniversalSegmentContextAudit(
                segment_id=left.segment_id,
                segment_role=left.segment_role,
                start_time=left.start_time,
                end_time=left.end_time,
                duration_seconds=left.duration,
                segment_index=0,
                next_segment_id=right.segment_id,
                context_decision="keep_context_chain",
                next_boundary_type="speech_cut_risk",
                next_boundary_risk=True,
                should_protect_next_boundary=True,
                context_conflict_score=0.2,
            ),
            UniversalSegmentContextAudit(
                segment_id=right.segment_id,
                segment_role=right.segment_role,
                start_time=right.start_time,
                end_time=right.end_time,
                duration_seconds=right.duration,
                segment_index=1,
                previous_segment_id=left.segment_id,
                context_decision="keep_context_chain",
                previous_boundary_type="speech_cut_risk",
                previous_boundary_risk=True,
                should_protect_previous_boundary=True,
                context_conflict_score=0.2,
            ),
        ],
    )


def _report_for(
    segments: list[TimelineSegment],
    *,
    transcript_result=None,
    sentence_timeline_result=None,
    universal_moment_result=None,
    context_audit_report=None,
) -> UniversalBoundaryEvidenceReport:
    return UniversalBoundaryEvidenceReporter().build(
        job_id="job_boundary_evidence",
        timeline_segments=segments,
        transcript_result=transcript_result,
        sentence_timeline_result=sentence_timeline_result,
        universal_moment_result=universal_moment_result,
        context_audit_report=context_audit_report,
    )


def test_empty_inputs_do_not_crash() -> None:
    report = _report_for([])
    assert report.total_boundaries == 0


def test_n_segments_create_n_minus_one_boundaries() -> None:
    report = _report_for([_segment("a", 0, 10), _segment("b", 10, 20), _segment("c", 20, 30)])
    assert report.total_boundaries == 2


def test_transcript_sentence_cross_boundary_is_real_speech_cut() -> None:
    left = _segment("left", 10, 20)
    right = _segment("right", 20, 30)
    report = _report_for(
        [left, right],
        transcript_result=_transcript((19.8, 20.2)),
        sentence_timeline_result=_sentences((19.7, 20.3)),
    )
    boundary = report.boundaries[0]
    assert boundary.boundary_type == "real_speech_cut_risk"
    assert boundary.priority == "real_high"


def test_speech_on_both_edges_without_cross_is_possible_speech_cut() -> None:
    left = _segment("left", 30, 40)
    right = _segment("right", 40.6, 50)
    report = _report_for(
        [left, right],
        transcript_result=_transcript((39.1, 39.4), (40.9, 41.1)),
    )
    boundary = report.boundaries[0]
    assert boundary.boundary_type == "possible_speech_cut_risk"
    assert boundary.priority == "medium"


def test_context_speech_warning_without_evidence_is_likely_false_positive() -> None:
    left = _segment("left", 50, 60)
    right = _segment("right", 60, 70)
    report = _report_for([left, right], context_audit_report=_context_with_warning(left, right))
    boundary = report.boundaries[0]
    assert boundary.boundary_type == "likely_false_positive"
    assert boundary.priority == "false_positive"


def test_peak_action_near_boundary_is_action_cut_risk() -> None:
    left = _segment("left", 70, 80)
    right = _segment("right", 80, 90)
    report = _report_for(
        [left, right],
        universal_moment_result=UniversalMomentResult(
            windows=[_moment(79.8, 80.1, peak_score=0.8, moment_type="peak_action")]
        ),
    )
    assert report.boundaries[0].boundary_type == "action_cut_risk"


def test_zoom_risk_near_boundary_is_zoom_cut_risk() -> None:
    left = _segment("left", 90, 100)
    right = _segment("right", 100, 110)
    report = _report_for(
        [left, right],
        universal_moment_result=UniversalMomentResult(
            windows=[_moment(99.8, 100.1, zoom_risk_score=0.8, zoom_boundary_risk=True)]
        ),
    )
    assert report.boundaries[0].boundary_type == "zoom_cut_risk"


def test_menu_to_action_is_menu_jump() -> None:
    left = _segment("left", 110, 120)
    right = _segment("right", 120, 130)
    report = _report_for(
        [left, right],
        universal_moment_result=UniversalMomentResult(
            windows=[
                _moment(119.5, 119.9, menu_wait_score=0.8),
                _moment(120.2, 120.4, visual_action_score=0.62),
            ]
        ),
    )
    assert report.boundaries[0].boundary_type == "menu_jump"


def test_boring_gap_is_boring_gap() -> None:
    left = _segment("left", 130, 140)
    right = _segment("right", 141, 150)
    report = _report_for(
        [left, right],
        universal_moment_result=UniversalMomentResult(
            windows=[_moment(139.5, 139.8, boring_score=0.8, dead_time_score=0.8)]
        ),
    )
    assert report.boundaries[0].boundary_type == "boring_gap"


def test_final_review_downgrades_false_positive_boundary_warning() -> None:
    left = _segment("left", 150, 160)
    right = _segment("right", 160, 170)
    context_report = _context_with_warning(left, right)
    boundary_report = _report_for([left, right], context_audit_report=context_report)
    debug_report = UniversalMomentDebugReport(
        job_id="job_boundary_evidence",
        segments=[
            UniversalMomentSegmentDebug(
                segment_id=segment.segment_id,
                segment_role=segment.segment_role,
                start_time=segment.start_time,
                end_time=segment.end_time,
                duration_seconds=segment.duration,
                avg_keep_score=0.75,
                avg_remove_score=0.1,
                avg_peak_score=0.35,
                avg_tension_score=0.45,
                has_keep_signal=True,
                professional_verdict="keep",
            )
            for segment in (left, right)
        ],
    )
    soft_report = UniversalMomentSoftDecisionReport(
        job_id="job_boundary_evidence",
        decisions=[
            UniversalMomentSegmentDecision(
                segment_id=segment.segment_id,
                segment_role=segment.segment_role,
                start_time=segment.start_time,
                end_time=segment.end_time,
                duration_seconds=segment.duration,
                soft_decision="safe_keep",
                keep_confidence=0.8,
                remove_confidence=0.1,
                conflict_score=0.1,
            )
            for segment in (left, right)
        ],
    )
    final_review = Phase2BFinalReviewBuilder().build(
        job_id="job_boundary_evidence",
        debug_report=debug_report,
        soft_decision_report=soft_report,
        context_audit_report=context_report,
        boundary_evidence_report=boundary_report,
    )
    assert final_review.high_priority_reviews == 0
    assert {item.human_review_priority for item in final_review.segments} <= {"low", "none"}


def test_markdown_contains_boundary_evidence_section() -> None:
    left = _segment("left", 170, 180)
    right = _segment("right", 180, 190)
    boundary_report = _report_for([left, right])
    debug_report = UniversalMomentDebugReport(
        job_id="job_boundary_evidence",
        segments=[
            UniversalMomentSegmentDebug(
                segment_id=left.segment_id,
                segment_role=left.segment_role,
                start_time=left.start_time,
                end_time=left.end_time,
                duration_seconds=left.duration,
            )
        ],
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = UniversalMomentReviewExporter().write_report(
            report=debug_report,
            output_dir=tmp,
            boundary_evidence_report=boundary_report,
        )
        text = Path(path).read_text(encoding="utf-8")
    assert "# Boundary Evidence" in text


def test_to_dict_from_dict_roundtrip() -> None:
    left = _segment("left", 190, 200)
    right = _segment("right", 200, 210)
    report = _report_for([left, right])
    roundtrip = UniversalBoundaryEvidenceReport.from_dict(report.to_dict())
    assert roundtrip.to_dict() == report.to_dict()


def main() -> None:
    test_empty_inputs_do_not_crash()
    test_n_segments_create_n_minus_one_boundaries()
    test_transcript_sentence_cross_boundary_is_real_speech_cut()
    test_speech_on_both_edges_without_cross_is_possible_speech_cut()
    test_context_speech_warning_without_evidence_is_likely_false_positive()
    test_peak_action_near_boundary_is_action_cut_risk()
    test_zoom_risk_near_boundary_is_zoom_cut_risk()
    test_menu_to_action_is_menu_jump()
    test_boring_gap_is_boring_gap()
    test_final_review_downgrades_false_positive_boundary_warning()
    test_markdown_contains_boundary_evidence_section()
    test_to_dict_from_dict_roundtrip()
    print("BOUNDARY EVIDENCE DRILLDOWN SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
