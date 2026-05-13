from __future__ import annotations

from typing import Any

from core.profanity_censor_detector import detect_profanity_censor_candidates
from models.profanity_censor import STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS
from models.profanity_censor_run import ProfanityCensorRunReport


def _job_attr(job: Any, name: str) -> Any:
    if job is None:
        return None
    if isinstance(job, dict):
        return job.get(name)
    return getattr(job, name, None)


def run_profanity_censor_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> ProfanityCensorRunReport:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    transcript_segments = _job_attr(job, "transcript_segments")

    if not transcript_segments:
        return ProfanityCensorRunReport(
            status=STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
            profanity_censor_result={},
            matches=[],
            segment_results=[],
            match_count=0,
            severe_match_count=0,
            mild_match_count=0,
            censor_required_count=0,
            word_level_match_count=0,
            segment_fallback_match_count=0,
            recommendation="profanity_censor_skipped_no_transcript",
            warnings=["no_transcript_segments_available"],
            errors=[],
            metadata=safe_metadata,
        )

    result = detect_profanity_censor_candidates(
        transcript_segments,
        metadata={
            **safe_metadata,
            "job_id": _job_attr(job, "job_id"),
        },
    )

    return ProfanityCensorRunReport(
        status=result.status,
        profanity_censor_result=result.to_dict(),
        matches=[match.to_dict() for match in result.matches],
        segment_results=[
            segment_result.to_dict()
            for segment_result in result.segment_results
        ],
        match_count=result.match_count,
        severe_match_count=result.severe_match_count,
        mild_match_count=result.mild_match_count,
        censor_required_count=result.censor_required_count,
        word_level_match_count=result.word_level_match_count,
        segment_fallback_match_count=result.segment_fallback_match_count,
        recommendation=result.recommendation,
        warnings=list(result.warnings),
        errors=list(result.errors),
        metadata=safe_metadata,
    )


def apply_profanity_censor_run_report_to_job(
    job: Any,
    report: ProfanityCensorRunReport,
) -> Any:
    report_dict = report.to_dict()

    job.profanity_censor_report = report_dict
    job.profanity_censor_status = report.status
    job.profanity_censor_matches = list(report.matches)
    job.profanity_censor_segment_results = list(report.segment_results)
    job.profanity_censor_match_count = int(report.match_count or 0)
    job.profanity_censor_severe_match_count = int(
        report.severe_match_count or 0
    )
    job.profanity_censor_mild_match_count = int(report.mild_match_count or 0)
    job.profanity_censor_required_count = int(
        report.censor_required_count or 0
    )
    job.profanity_censor_word_level_match_count = int(
        report.word_level_match_count or 0
    )
    job.profanity_censor_segment_fallback_match_count = int(
        report.segment_fallback_match_count or 0
    )
    job.profanity_censor_recommendation = report.recommendation

    if hasattr(job, "touch"):
        job.touch()

    return job
