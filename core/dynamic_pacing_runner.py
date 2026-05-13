from __future__ import annotations

from typing import Any

from core.dynamic_pacing_engine import build_dynamic_pacing_for_job
from models.dynamic_pacing import (
    DYNAMIC_PACING_RECOMMENDATION_FAILED,
    DYNAMIC_PACING_STATUS_FAILED,
    DynamicPacingReport,
)


def _get_job_value(job: Any, key: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(key, default)
    return getattr(job, key, default)


def _set_job_value(job: Any, key: str, value: Any) -> None:
    if isinstance(job, dict):
        job[key] = value
        return
    setattr(job, key, value)


def run_dynamic_pacing_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> DynamicPacingReport:
    run_metadata = {
        "phase": "2B-39",
        "block": "block7_story_pacing",
        "review_only": True,
        "dynamic_pacing_only": True,
        "media_unchanged": True,
        "no_execution_in_2b_39": True,
        "no_render_in_2b_39": True,
        "no_timeline_reorder_in_2b_39": True,
        "no_pacing_apply_in_2b_39": True,
        "no_split_merge_trim_extend_in_2b_39": True,
        **dict(metadata or {}),
    }

    try:
        return build_dynamic_pacing_for_job(
            job,
            metadata=run_metadata,
        )
    except Exception as exc:
        report = DynamicPacingReport(
            job_id=_get_job_value(job, "job_id"),
            status=DYNAMIC_PACING_STATUS_FAILED,
            pacing_segments=[],
            suggestions=[],
            warnings=[],
            blocking_reasons=["dynamic_pacing_failed"],
            recommendation=DYNAMIC_PACING_RECOMMENDATION_FAILED,
            metadata={
                **run_metadata,
                "source": "dynamic_pacing_runner",
                "error": str(exc),
            },
        )
        report.enforce_review_only()
        return report


def apply_dynamic_pacing_run_report_to_job(
    job: Any,
    report: DynamicPacingReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = DynamicPacingReport.from_dict(report)

    report.enforce_review_only()
    report_dict = report.to_dict()
    pacing_segments = [segment.to_dict() for segment in report.pacing_segments]
    suggestions = [suggestion.to_dict() for suggestion in report.suggestions]

    _set_job_value(job, "dynamic_pacing_report", report_dict)
    _set_job_value(job, "dynamic_pacing", report_dict)
    _set_job_value(job, "dynamic_pacing_status", report.status)
    _set_job_value(job, "dynamic_pacing_segments", pacing_segments)
    _set_job_value(job, "dynamic_pacing_suggestions", suggestions)
    _set_job_value(
        job,
        "dynamic_pacing_average_cut_rate",
        float(report.average_cut_rate or 0.0),
    )
    _set_job_value(
        job,
        "dynamic_pacing_target_cut_rate_range",
        dict(report.target_cut_rate_range or {}),
    )
    _set_job_value(
        job,
        "dynamic_pacing_match_score",
        float(report.pacing_match_score or 0.0),
    )
    _set_job_value(
        job,
        "dynamic_pacing_monotony_score",
        float(report.monotony_score or 0.0),
    )
    _set_job_value(
        job,
        "dynamic_pacing_breathing_room_score",
        float(report.breathing_room_score or 0.0),
    )
    _set_job_value(job, "dynamic_pacing_fast_run_count", int(report.fast_run_count))
    _set_job_value(job, "dynamic_pacing_slow_run_count", int(report.slow_run_count))
    _set_job_value(job, "dynamic_pacing_review_required", True)
    _set_job_value(job, "dynamic_pacing_can_apply", False)
    _set_job_value(job, "dynamic_pacing_can_split_clips", False)
    _set_job_value(job, "dynamic_pacing_can_merge_clips", False)
    _set_job_value(job, "dynamic_pacing_can_trim", False)
    _set_job_value(job, "dynamic_pacing_can_extend", False)
    _set_job_value(job, "dynamic_pacing_can_reorder_timeline", False)
    _set_job_value(job, "dynamic_pacing_can_render", False)
    _set_job_value(
        job,
        "dynamic_pacing_blocking_reasons",
        list(report.blocking_reasons or []),
    )
    _set_job_value(job, "dynamic_pacing_warnings", list(report.warnings or []))
    _set_job_value(job, "dynamic_pacing_recommendation", report.recommendation)

    if hasattr(job, "touch"):
        job.touch()

    return job
