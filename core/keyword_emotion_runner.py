from __future__ import annotations

from typing import Any

from core.keyword_emotion_scorer import score_keyword_emotions
from models.keyword_emotion import STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS
from models.keyword_emotion_run import KeywordEmotionRunReport


def _job_attr(job: Any, name: str) -> Any:
    if job is None:
        return None
    if isinstance(job, dict):
        return job.get(name)
    return getattr(job, name, None)


def run_keyword_emotion_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> KeywordEmotionRunReport:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    transcript_segments = _job_attr(job, "transcript_segments")
    transcript_source = _job_attr(job, "transcript_source_type")

    if not transcript_segments:
        return KeywordEmotionRunReport(
            status=STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
            transcript_source=transcript_source,
            recommendation="keyword_emotion_skipped_no_transcript",
            warnings=["no_transcript_segments_available"],
            metadata=safe_metadata,
        )

    result = score_keyword_emotions(
        transcript_segments,
        metadata={
            **safe_metadata,
            "transcript_source": transcript_source,
            "job_id": _job_attr(job, "job_id"),
        },
    )
    result_dict = result.to_dict()

    return KeywordEmotionRunReport(
        status=result.status,
        transcript_source=transcript_source,
        keyword_emotion_result=result_dict,
        matches=[match.to_dict() for match in result.matches],
        segment_scores=[score.to_dict() for score in result.segment_scores],
        match_count=result.match_count,
        segment_score_count=result.segment_score_count,
        hype_match_count=result.hype_match_count,
        frustration_match_count=result.frustration_match_count,
        shock_match_count=result.shock_match_count,
        laugh_match_count=result.laugh_match_count,
        question_match_count=result.question_match_count,
        high_value_segment_count=result.high_value_segment_count,
        recommendation=result.recommendation,
        warnings=list(result.warnings),
        errors=list(result.errors),
        metadata=safe_metadata,
    )


def apply_keyword_emotion_run_report_to_job(
    job: Any,
    report: KeywordEmotionRunReport,
) -> Any:
    report_dict = report.to_dict()

    job.keyword_emotion_report = report_dict
    job.keyword_emotion_status = report.status
    job.keyword_emotion_matches = list(report.matches)
    job.keyword_emotion_segment_scores = list(report.segment_scores)
    job.keyword_emotion_match_count = int(report.match_count or 0)
    job.keyword_emotion_segment_score_count = int(report.segment_score_count or 0)
    job.keyword_emotion_hype_match_count = int(report.hype_match_count or 0)
    job.keyword_emotion_frustration_match_count = int(
        report.frustration_match_count or 0
    )
    job.keyword_emotion_shock_match_count = int(report.shock_match_count or 0)
    job.keyword_emotion_laugh_match_count = int(report.laugh_match_count or 0)
    job.keyword_emotion_question_match_count = int(report.question_match_count or 0)
    job.keyword_emotion_high_value_segment_count = int(
        report.high_value_segment_count or 0
    )
    job.keyword_emotion_recommendation = report.recommendation

    if hasattr(job, "touch"):
        job.touch()

    return job
