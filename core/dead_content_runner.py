from __future__ import annotations

from typing import Any

from core.dead_content_detector import detect_dead_content
from models.dead_content import STATUS_SKIPPED_NO_INPUTS
from models.dead_content_run import DeadContentRunReport


def _job_attr(job: Any, name: str) -> Any:
    if job is None:
        return None
    if isinstance(job, dict):
        return job.get(name)
    return getattr(job, name, None)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict, str)):
        return bool(value)
    return True


def run_dead_content_detection_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> DeadContentRunReport:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    transcript_segments = _job_attr(job, "transcript_segments")
    sentence_boundary_report = _job_attr(job, "sentence_boundary_report")
    keyword_emotion_report = _job_attr(job, "keyword_emotion_report")
    interaction_classification_report = _job_attr(
        job,
        "interaction_classification_report",
    )
    filler_word_report = _job_attr(job, "filler_word_report")
    silence_classification_report = _job_attr(job, "silence_classification_report")
    if not silence_classification_report:
        silence_classification_report = {
            "classifications": _job_attr(job, "silence_classifications") or []
        }
    visual_energy_report = _job_attr(job, "visual_energy_report")
    screen_content_report = _job_attr(job, "screen_content_report")

    if not _has_value(transcript_segments):
        return DeadContentRunReport(
            status=STATUS_SKIPPED_NO_INPUTS,
            dead_content_result={},
            candidates=[],
            segment_scores=[],
            candidate_count=0,
            segment_score_count=0,
            recommendation="dead_content_skipped_no_inputs",
            warnings=["no_transcript_segments_available"],
            errors=[],
            metadata=safe_metadata,
        )

    result = detect_dead_content(
        job_or_sources=job,
        transcript_segments=transcript_segments,
        sentence_boundary_report=sentence_boundary_report,
        keyword_emotion_report=keyword_emotion_report,
        interaction_classification_report=interaction_classification_report,
        filler_word_report=filler_word_report,
        silence_classification_report=silence_classification_report,
        visual_energy_report=visual_energy_report,
        screen_content_report=screen_content_report,
        metadata={
            **safe_metadata,
            "job_id": _job_attr(job, "job_id"),
        },
    )

    return DeadContentRunReport(
        status=result.status,
        dead_content_result=result.to_dict(),
        candidates=[candidate.to_dict() for candidate in result.candidates],
        segment_scores=[score.to_dict() for score in result.segment_scores],
        candidate_count=result.candidate_count,
        segment_score_count=result.segment_score_count,
        dead_air_candidate_count=result.dead_air_candidate_count,
        low_value_candidate_count=result.low_value_candidate_count,
        filler_pause_candidate_count=result.filler_pause_candidate_count,
        loading_or_menu_candidate_count=result.loading_or_menu_candidate_count,
        private_or_meta_candidate_count=result.private_or_meta_candidate_count,
        protected_candidate_count=result.protected_candidate_count,
        high_confidence_candidate_count=result.high_confidence_candidate_count,
        recommendation=result.recommendation,
        warnings=list(result.warnings),
        errors=list(result.errors),
        metadata=safe_metadata,
    )


def apply_dead_content_run_report_to_job(
    job: Any,
    report: DeadContentRunReport,
) -> Any:
    report_dict = report.to_dict()

    job.dead_content_report = report_dict
    job.dead_content_status = report.status
    job.dead_content_candidates = list(report.candidates)
    job.dead_content_segment_scores = list(report.segment_scores)
    job.dead_content_candidate_count = int(report.candidate_count or 0)
    job.dead_content_segment_score_count = int(report.segment_score_count or 0)
    job.dead_content_dead_air_candidate_count = int(
        report.dead_air_candidate_count or 0
    )
    job.dead_content_low_value_candidate_count = int(
        report.low_value_candidate_count or 0
    )
    job.dead_content_filler_pause_candidate_count = int(
        report.filler_pause_candidate_count or 0
    )
    job.dead_content_loading_or_menu_candidate_count = int(
        report.loading_or_menu_candidate_count or 0
    )
    job.dead_content_private_or_meta_candidate_count = int(
        report.private_or_meta_candidate_count or 0
    )
    job.dead_content_protected_candidate_count = int(
        report.protected_candidate_count or 0
    )
    job.dead_content_high_confidence_candidate_count = int(
        report.high_confidence_candidate_count or 0
    )
    job.dead_content_recommendation = report.recommendation

    if hasattr(job, "touch"):
        job.touch()

    return job
