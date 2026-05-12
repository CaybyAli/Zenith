from __future__ import annotations

from typing import Any

from core.sentence_boundary_protector import analyze_sentence_boundaries
from models.sentence_boundary import STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS
from models.sentence_boundary_run import SentenceBoundaryRunReport


def _job_attr(job: Any, name: str) -> Any:
    if job is None:
        return None
    if isinstance(job, dict):
        return job.get(name)
    return getattr(job, name, None)


def run_sentence_boundary_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> SentenceBoundaryRunReport:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    transcript_segments = _job_attr(job, "transcript_segments")
    transcript_source = _job_attr(job, "transcript_source_type")

    if not transcript_segments:
        return SentenceBoundaryRunReport(
            status=STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
            transcript_source=transcript_source,
            recommendation="sentence_boundary_skipped_no_transcript",
            warnings=["no_transcript_segments_available"],
            metadata=safe_metadata,
        )

    result = analyze_sentence_boundaries(
        transcript_segments,
        metadata={
            **safe_metadata,
            "transcript_source": transcript_source,
            "job_id": _job_attr(job, "job_id"),
        },
    )
    result_dict = result.to_dict()

    return SentenceBoundaryRunReport(
        status=result.status,
        transcript_source=transcript_source,
        sentence_boundary_result=result_dict,
        boundaries=[boundary.to_dict() for boundary in result.boundaries],
        protection_zones=[zone.to_dict() for zone in result.protection_zones],
        boundary_count=result.boundary_count,
        protection_zone_count=result.protection_zone_count,
        complete_sentence_count=result.complete_sentence_count,
        open_fragment_count=result.open_fragment_count,
        question_count=result.question_count,
        open_question_count=result.open_question_count,
        safe_boundary_count=result.safe_boundary_count,
        unsafe_boundary_count=result.unsafe_boundary_count,
        recommendation=result.recommendation,
        warnings=list(result.warnings),
        errors=list(result.errors),
        metadata=safe_metadata,
    )


def apply_sentence_boundary_run_report_to_job(
    job: Any,
    report: SentenceBoundaryRunReport,
) -> Any:
    report_dict = report.to_dict()

    job.sentence_boundary_report = report_dict
    job.sentence_boundary_status = report.status
    job.sentence_boundary_boundaries = list(report.boundaries)
    job.sentence_boundary_protection_zones = list(report.protection_zones)
    job.sentence_boundary_boundary_count = int(report.boundary_count or 0)
    job.sentence_boundary_protection_zone_count = int(
        report.protection_zone_count or 0
    )
    job.sentence_boundary_complete_sentence_count = int(
        report.complete_sentence_count or 0
    )
    job.sentence_boundary_open_fragment_count = int(report.open_fragment_count or 0)
    job.sentence_boundary_question_count = int(report.question_count or 0)
    job.sentence_boundary_open_question_count = int(report.open_question_count or 0)
    job.sentence_boundary_safe_boundary_count = int(report.safe_boundary_count or 0)
    job.sentence_boundary_unsafe_boundary_count = int(
        report.unsafe_boundary_count or 0
    )
    job.sentence_boundary_recommendation = report.recommendation

    if hasattr(job, "touch"):
        job.touch()

    return job
