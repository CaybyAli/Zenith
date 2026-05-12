from __future__ import annotations

from typing import Any

from core.content_value_calculator import calculate_content_value
from models.content_value import STATUS_SKIPPED_NO_INPUTS
from models.content_value_run import ContentValueRunReport


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


def run_content_value_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> ContentValueRunReport:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    transcript_segments = _job_attr(job, "transcript_segments")
    keyword_emotion_report = _job_attr(job, "keyword_emotion_report")
    interaction_classification_report = _job_attr(
        job,
        "interaction_classification_report",
    )
    sentence_boundary_report = _job_attr(job, "sentence_boundary_report")
    dead_content_report = _job_attr(job, "dead_content_report")
    filler_word_report = _job_attr(job, "filler_word_report")
    silence_classification_report = _job_attr(job, "silence_classification_report")
    if not silence_classification_report:
        silence_classification_report = {
            "classifications": _job_attr(job, "silence_classifications") or []
        }
    visual_energy_report = _job_attr(job, "visual_energy_report")
    face_reaction_report = _job_attr(job, "face_reaction_report")
    motion_analysis_report = _job_attr(job, "motion_analysis_report")
    screen_content_report = _job_attr(job, "screen_content_report")
    scene_change_report = _job_attr(job, "scene_change_report")
    energy_peak_report = _job_attr(job, "energy_peak_report")
    audio_normalization_report = _job_attr(job, "audio_normalization_report")
    stutter_detection_report = _job_attr(job, "stutter_detection_report")

    if not _has_value(transcript_segments):
        return ContentValueRunReport(
            status=STATUS_SKIPPED_NO_INPUTS,
            content_value_result={},
            segment_scores=[],
            segment_score_count=0,
            recommendation="content_value_skipped_no_inputs",
            warnings=["no_transcript_segments_available"],
            errors=[],
            metadata=safe_metadata,
        )

    result = calculate_content_value(
        job_or_sources=job,
        transcript_segments=transcript_segments,
        keyword_emotion_report=keyword_emotion_report,
        interaction_classification_report=interaction_classification_report,
        sentence_boundary_report=sentence_boundary_report,
        dead_content_report=dead_content_report,
        filler_word_report=filler_word_report,
        silence_classification_report=silence_classification_report,
        visual_energy_report=visual_energy_report,
        face_reaction_report=face_reaction_report,
        motion_analysis_report=motion_analysis_report,
        screen_content_report=screen_content_report,
        scene_change_report=scene_change_report,
        energy_peak_report=energy_peak_report,
        audio_normalization_report=audio_normalization_report,
        stutter_detection_report=stutter_detection_report,
        metadata={
            **safe_metadata,
            "job_id": _job_attr(job, "job_id"),
        },
    )

    return ContentValueRunReport(
        status=result.status,
        content_value_result=result.to_dict(),
        segment_scores=[score.to_dict() for score in result.segment_scores],
        segment_score_count=result.segment_score_count,
        high_value_count=result.high_value_count,
        mid_value_count=result.mid_value_count,
        low_value_count=result.low_value_count,
        protected_context_count=result.protected_context_count,
        hook_candidate_count=result.hook_candidate_count,
        technical_warning_count=result.technical_warning_count,
        avg_content_value_score=result.avg_content_value_score,
        max_content_value_score=result.max_content_value_score,
        min_content_value_score=result.min_content_value_score,
        recommendation=result.recommendation,
        warnings=list(result.warnings),
        errors=list(result.errors),
        metadata=safe_metadata,
    )


def apply_content_value_run_report_to_job(
    job: Any,
    report: ContentValueRunReport,
) -> Any:
    report_dict = report.to_dict()

    job.content_value_report = report_dict
    job.content_value_status = report.status
    job.content_value_segment_scores = list(report.segment_scores)
    job.content_value_segment_score_count = int(report.segment_score_count or 0)
    job.content_value_high_value_count = int(report.high_value_count or 0)
    job.content_value_mid_value_count = int(report.mid_value_count or 0)
    job.content_value_low_value_count = int(report.low_value_count or 0)
    job.content_value_protected_context_count = int(
        report.protected_context_count or 0
    )
    job.content_value_hook_candidate_count = int(
        report.hook_candidate_count or 0
    )
    job.content_value_technical_warning_count = int(
        report.technical_warning_count or 0
    )
    job.content_value_avg_score = float(report.avg_content_value_score or 0.0)
    job.content_value_max_score = float(report.max_content_value_score or 0.0)
    job.content_value_min_score = float(report.min_content_value_score or 0.0)
    job.content_value_recommendation = report.recommendation

    if hasattr(job, "touch"):
        job.touch()

    return job
