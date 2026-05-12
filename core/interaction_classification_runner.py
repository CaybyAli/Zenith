from __future__ import annotations

from typing import Any

from core.interaction_classifier import classify_interactions
from models.interaction_classification import STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS
from models.interaction_classification_run import InteractionClassificationRunReport


def _job_attr(job: Any, name: str) -> Any:
    if job is None:
        return None
    if isinstance(job, dict):
        return job.get(name)
    return getattr(job, name, None)


def run_interaction_classification_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> InteractionClassificationRunReport:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    transcript_segments = _job_attr(job, "transcript_segments")
    transcript_source = _job_attr(job, "transcript_source_type")
    sentence_boundary_report = _job_attr(job, "sentence_boundary_report")
    keyword_emotion_report = _job_attr(job, "keyword_emotion_report")

    if not transcript_segments:
        return InteractionClassificationRunReport(
            status=STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
            transcript_source=transcript_source,
            recommendation="interaction_classification_skipped_no_transcript",
            warnings=["no_transcript_segments_available"],
            metadata=safe_metadata,
        )

    result = classify_interactions(
        transcript_segments=transcript_segments,
        sentence_boundary_report=sentence_boundary_report,
        keyword_emotion_report=keyword_emotion_report,
        metadata={
            **safe_metadata,
            "transcript_source": transcript_source,
            "job_id": _job_attr(job, "job_id"),
        },
    )
    result_dict = result.to_dict()

    return InteractionClassificationRunReport(
        status=result.status,
        transcript_source=transcript_source,
        interaction_classification_result=result_dict,
        points=[point.to_dict() for point in result.points],
        segment_classifications=[
            classification.to_dict()
            for classification in result.segment_classifications
        ],
        point_count=result.point_count,
        segment_classification_count=result.segment_classification_count,
        monologue_count=result.monologue_count,
        interaction_count=result.interaction_count,
        question_answer_count=result.question_answer_count,
        chat_reaction_count=result.chat_reaction_count,
        callout_count=result.callout_count,
        commentary_count=result.commentary_count,
        private_or_meta_count=result.private_or_meta_count,
        context_needed_count=result.context_needed_count,
        recommendation=result.recommendation,
        warnings=list(result.warnings),
        errors=list(result.errors),
        metadata=safe_metadata,
    )


def apply_interaction_classification_run_report_to_job(
    job: Any,
    report: InteractionClassificationRunReport,
) -> Any:
    report_dict = report.to_dict()

    job.interaction_classification_report = report_dict
    job.interaction_classification_status = report.status
    job.interaction_classification_points = list(report.points)
    job.interaction_classification_segments = list(report.segment_classifications)
    job.interaction_classification_point_count = int(report.point_count or 0)
    job.interaction_classification_segment_count = int(
        report.segment_classification_count or 0
    )
    job.interaction_classification_monologue_count = int(
        report.monologue_count or 0
    )
    job.interaction_classification_interaction_count = int(
        report.interaction_count or 0
    )
    job.interaction_classification_question_answer_count = int(
        report.question_answer_count or 0
    )
    job.interaction_classification_chat_reaction_count = int(
        report.chat_reaction_count or 0
    )
    job.interaction_classification_callout_count = int(report.callout_count or 0)
    job.interaction_classification_commentary_count = int(
        report.commentary_count or 0
    )
    job.interaction_classification_private_or_meta_count = int(
        report.private_or_meta_count or 0
    )
    job.interaction_classification_context_needed_count = int(
        report.context_needed_count or 0
    )
    job.interaction_classification_recommendation = report.recommendation

    if hasattr(job, "touch"):
        job.touch()

    return job
