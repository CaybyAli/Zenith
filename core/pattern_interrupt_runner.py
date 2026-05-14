from __future__ import annotations

from typing import Any

from core.pattern_interrupt_engine import build_pattern_interrupt_for_job
from models.pattern_interrupt import (
    PATTERN_INTERRUPT_RECOMMENDATION_FAILED,
    PATTERN_INTERRUPT_STATUS_FAILED,
    PatternInterruptReport,
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


def run_pattern_interrupt_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> PatternInterruptReport:
    run_metadata = {
        "phase": "2B-40",
        "block": "block7_story_pacing",
        "review_only": True,
        "pattern_interrupt_only": True,
        "media_unchanged": True,
        "no_execution_in_2b_40": True,
        "no_render_in_2b_40": True,
        "no_timeline_reorder_in_2b_40": True,
        "no_pattern_apply_in_2b_40": True,
        "no_zoom_insert_in_2b_40": True,
        "no_text_overlay_insert_in_2b_40": True,
        "no_sfx_insert_in_2b_40": True,
        **dict(metadata or {}),
    }

    try:
        return build_pattern_interrupt_for_job(
            job,
            metadata=run_metadata,
        )
    except Exception as exc:
        report = PatternInterruptReport(
            job_id=_get_job_value(job, "job_id"),
            status=PATTERN_INTERRUPT_STATUS_FAILED,
            windows=[],
            suggestions=[],
            warnings=[],
            blocking_reasons=["pattern_interrupt_failed"],
            recommendation=PATTERN_INTERRUPT_RECOMMENDATION_FAILED,
            metadata={
                **run_metadata,
                "source": "pattern_interrupt_runner",
                "error": str(exc),
            },
        )
        report.enforce_review_only()
        return report


def store_pattern_interrupt_run_report_to_job(
    job: Any,
    report: PatternInterruptReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = PatternInterruptReport.from_dict(report)

    report.enforce_review_only()
    report_dict = report.to_dict()
    windows = [window.to_dict() for window in report.windows]
    suggestions = [suggestion.to_dict() for suggestion in report.suggestions]

    _set_job_value(job, "pattern_interrupt_report", report_dict)
    _set_job_value(job, "pattern_interrupt", report_dict)
    _set_job_value(job, "pattern_interrupt_status", report.status)
    _set_job_value(job, "pattern_interrupt_windows", windows)
    _set_job_value(job, "pattern_interrupt_suggestions", suggestions)
    _set_job_value(job, "pattern_interrupt_total_windows", int(report.total_windows))
    _set_job_value(
        job,
        "pattern_interrupt_needed_count",
        int(report.interrupt_needed_count),
    )
    _set_job_value(
        job,
        "pattern_interrupt_monotony_score",
        float(report.monotony_score or 0.0),
    )
    _set_job_value(
        job,
        "pattern_interrupt_average_window_duration_seconds",
        float(report.average_window_duration_seconds or 0.0),
    )
    _set_job_value(
        job,
        "pattern_interrupt_recommended_count",
        int(report.recommended_interrupt_count),
    )
    _set_job_value(job, "pattern_interrupt_review_required", True)
    _set_job_value(job, "pattern_interrupt_can_apply", False)
    _set_job_value(job, "pattern_interrupt_can_insert_zoom", False)
    _set_job_value(job, "pattern_interrupt_can_insert_text_overlay", False)
    _set_job_value(job, "pattern_interrupt_can_insert_sfx", False)
    _set_job_value(job, "pattern_interrupt_can_reorder_timeline", False)
    _set_job_value(job, "pattern_interrupt_can_trim", False)
    _set_job_value(job, "pattern_interrupt_can_extend", False)
    _set_job_value(job, "pattern_interrupt_can_render", False)
    _set_job_value(
        job,
        "pattern_interrupt_blocking_reasons",
        list(report.blocking_reasons or []),
    )
    _set_job_value(job, "pattern_interrupt_warnings", list(report.warnings or []))
    _set_job_value(job, "pattern_interrupt_recommendation", report.recommendation)

    if hasattr(job, "touch"):
        job.touch()

    return job
