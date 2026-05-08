from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.phase_2b_final_review_builder import Phase2BFinalReviewBuilder
from core.universal_boundary_evidence_reporter import UniversalBoundaryEvidenceReporter
from core.universal_moment_review_exporter import UniversalMomentReviewExporter
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment
from models.universal_boundary_evidence import UniversalBoundaryEvidenceReport
from models.universal_context_audit import UniversalContextAuditReport, UniversalSegmentContextAudit
from models.universal_moment_debug_report import UniversalMomentDebugReport, UniversalMomentSegmentDebug
from models.universal_moment_soft_decision import (
    UniversalMomentSegmentDecision,
    UniversalMomentSoftDecisionReport,
)


def _segment(segment_id: str, start: float, end: float) -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id="job_transcript_boundary_calibration",
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role="build",
        selection_score=0.7,
    )


def _transcript(*items: tuple[float, float, float | None]) -> TranscriptResult:
    return TranscriptResult(
        source_path="test.mp4",
        language="de",
        segments=[
            TranscriptSegment(
                start_seconds=start,
                end_seconds=end,
                text=f"speech {index}",
                confidence=confidence,
            )
            for index, (start, end, confidence) in enumerate(items, start=1)
        ],
        full_text="speech",
        engine="test",
    )


def _sentences(*items: tuple[float, float, float, float]) -> SentenceTimelineResult:
    return SentenceTimelineResult(
        sentences=[
            SentenceItem(
                sentence_id=f"sentence_{index}",
                text="sentence",
                start_seconds=start,
                end_seconds=end,
                duration_seconds=end - start,
                score=score,
                confidence=confidence,
                sentence_kind="normal",
            )
            for index, (start, end, score, confidence) in enumerate(items, start=1)
        ]
    )


def _audio(*items: tuple[float, float, float, float]) -> AudioRoleResult:
    return AudioRoleResult(
        windows=[
            AudioRoleWindow(
                window_id=f"audio_{index}",
                start_seconds=start,
                end_seconds=end,
                role_type="speech_active",
                score=score,
                confidence=confidence,
                reason="test speech",
            )
            for index, (start, end, score, confidence) in enumerate(items, start=1)
        ]
    )


def _context_with_warning(left: TimelineSegment, right: TimelineSegment) -> UniversalContextAuditReport:
    return UniversalContextAuditReport(
        job_id="job_transcript_boundary_calibration",
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
    *,
    transcript_result=None,
    sentence_timeline_result=None,
    audio_role_result=None,
    context_audit_report=None,
) -> UniversalBoundaryEvidenceReport:
    left = _segment("left", 0, 10)
    right = _segment("right", 10, 20)
    return UniversalBoundaryEvidenceReporter().build(
        job_id="job_transcript_boundary_calibration",
        timeline_segments=[left, right],
        transcript_result=transcript_result,
        sentence_timeline_result=sentence_timeline_result,
        audio_role_result=audio_role_result,
        context_audit_report=context_audit_report,
    )


def _final_review_for(boundary_report: UniversalBoundaryEvidenceReport) -> set[str]:
    left = _segment("left", 0, 10)
    right = _segment("right", 10, 20)
    context_report = _context_with_warning(left, right)
    debug_report = UniversalMomentDebugReport(
        job_id="job_transcript_boundary_calibration",
        segments=[
            UniversalMomentSegmentDebug(
                segment_id=segment.segment_id,
                segment_role=segment.segment_role,
                start_time=segment.start_time,
                end_time=segment.end_time,
                duration_seconds=segment.duration,
                avg_keep_score=0.76,
                avg_remove_score=0.05,
                avg_peak_score=0.4,
                avg_tension_score=0.45,
                has_keep_signal=True,
                professional_verdict="keep",
            )
            for segment in (left, right)
        ],
    )
    soft_report = UniversalMomentSoftDecisionReport(
        job_id="job_transcript_boundary_calibration",
        decisions=[
            UniversalMomentSegmentDecision(
                segment_id=segment.segment_id,
                segment_role=segment.segment_role,
                start_time=segment.start_time,
                end_time=segment.end_time,
                duration_seconds=segment.duration,
                soft_decision="safe_keep",
                keep_confidence=0.76,
                remove_confidence=0.05,
                conflict_score=0.1,
            )
            for segment in (left, right)
        ],
    )
    final_review = Phase2BFinalReviewBuilder().build(
        job_id="job_transcript_boundary_calibration",
        debug_report=debug_report,
        soft_decision_report=soft_report,
        context_audit_report=context_report,
        boundary_evidence_report=boundary_report,
    )
    return {item.human_review_priority for item in final_review.segments}


def test_empty_inputs_do_not_crash() -> None:
    report = UniversalBoundaryEvidenceReporter().build(
        job_id="job_transcript_boundary_calibration",
        timeline_segments=[],
    )
    assert report.total_boundaries == 0


def test_short_transcript_and_audio_mid_boundary_is_real_word_cut() -> None:
    report = _report_for(
        transcript_result=_transcript((9.0, 11.0, 0.92)),
        audio_role_result=_audio((9.6, 10.4, 0.9, 0.9)),
    )
    boundary = report.boundaries[0]
    assert boundary.speech_boundary_classification == "real_word_cut"
    assert boundary.priority == "real_high"


def test_plausible_sentence_mid_boundary_is_real_sentence_cut() -> None:
    report = _report_for(sentence_timeline_result=_sentences((8.0, 12.0, 0.85, 0.9)))
    boundary = report.boundaries[0]
    assert boundary.speech_boundary_classification == "real_sentence_cut"
    assert boundary.priority == "real_high"


def test_transcript_near_edge_is_not_real_word_cut() -> None:
    report = _report_for(transcript_result=_transcript((9.95, 11.2, 0.9)))
    boundary = report.boundaries[0]
    assert boundary.speech_boundary_classification in {"weak_speech_evidence", "likely_speech_cut"}
    assert boundary.speech_boundary_classification != "real_word_cut"


def test_broad_sentence_window_is_timestamp_uncertain() -> None:
    report = _report_for(sentence_timeline_result=_sentences((0.0, 30.0, 0.8, 0.9)))
    boundary = report.boundaries[0]
    assert boundary.speech_boundary_classification == "timestamp_uncertain"
    assert boundary.sentence_span_too_broad


def test_audio_only_near_edge_is_audio_only_near_edge() -> None:
    report = _report_for(audio_role_result=_audio((9.7, 10.3, 0.86, 0.88)))
    boundary = report.boundaries[0]
    assert boundary.speech_boundary_classification == "audio_only_near_edge"
    assert boundary.audio_only_risk


def test_weak_or_safe_evidence_is_not_high() -> None:
    weak_report = _report_for(transcript_result=_transcript((9.3, 9.5, 0.55)))
    safe_report = _report_for()
    assert weak_report.boundaries[0].speech_boundary_classification in {
        "weak_speech_evidence",
        "probably_safe",
    }
    assert safe_report.boundaries[0].speech_boundary_classification == "probably_safe"


def test_final_review_downgrades_timestamp_uncertain_to_medium() -> None:
    left = _segment("left", 0, 10)
    right = _segment("right", 10, 20)
    boundary_report = _report_for(
        sentence_timeline_result=_sentences((0.0, 30.0, 0.8, 0.9)),
        context_audit_report=_context_with_warning(left, right),
    )
    assert boundary_report.boundaries[0].speech_boundary_classification == "timestamp_uncertain"
    assert _final_review_for(boundary_report) == {"medium"}


def test_final_review_downgrades_safe_or_weak_to_low_or_none() -> None:
    left = _segment("left", 0, 10)
    right = _segment("right", 10, 20)
    boundary_report = _report_for(context_audit_report=_context_with_warning(left, right))
    assert boundary_report.boundaries[0].speech_boundary_classification == "probably_safe"
    assert _final_review_for(boundary_report) <= {"low", "none"}


def test_to_dict_from_dict_roundtrip() -> None:
    report = _report_for(
        transcript_result=_transcript((9.0, 11.0, 0.92)),
        audio_role_result=_audio((9.6, 10.4, 0.9, 0.9)),
    )
    roundtrip = UniversalBoundaryEvidenceReport.from_dict(report.to_dict())
    assert roundtrip.to_dict() == report.to_dict()


def test_markdown_contains_calibrated_speech_boundary_classification() -> None:
    boundary_report = _report_for(audio_role_result=_audio((9.7, 10.3, 0.86, 0.88)))
    debug_report = UniversalMomentDebugReport(
        job_id="job_transcript_boundary_calibration",
        segments=[
            UniversalMomentSegmentDebug(
                segment_id="left",
                segment_role="build",
                start_time=0.0,
                end_time=10.0,
                duration_seconds=10.0,
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
    assert "Speech Boundary Classification" in text
    assert "Calibrated Speech Risk Score" in text


def main() -> None:
    test_empty_inputs_do_not_crash()
    test_short_transcript_and_audio_mid_boundary_is_real_word_cut()
    test_plausible_sentence_mid_boundary_is_real_sentence_cut()
    test_transcript_near_edge_is_not_real_word_cut()
    test_broad_sentence_window_is_timestamp_uncertain()
    test_audio_only_near_edge_is_audio_only_near_edge()
    test_weak_or_safe_evidence_is_not_high()
    test_final_review_downgrades_timestamp_uncertain_to_medium()
    test_final_review_downgrades_safe_or_weak_to_low_or_none()
    test_to_dict_from_dict_roundtrip()
    test_markdown_contains_calibrated_speech_boundary_classification()
    print("TRANSCRIPT BOUNDARY CALIBRATION SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
