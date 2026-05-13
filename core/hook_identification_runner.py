from __future__ import annotations

from typing import Any

from core.hook_identification_engine import identify_hook_candidates_for_job
from models.hook_identification import (
    HOOK_IDENTIFICATION_RECOMMENDATION_FAILED,
    HOOK_IDENTIFICATION_STATUS_FAILED,
    HookIdentificationReport,
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


def run_hook_identification_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> HookIdentificationReport:
    run_metadata = {
        "phase": "2B-37",
        "block": "block7_story_pacing",
        "review_only": True,
        "hook_identification_only": True,
        "media_unchanged": True,
        "no_execution_in_2b_37": True,
        "no_render_in_2b_37": True,
        "no_timeline_reorder_in_2b_37": True,
        **dict(metadata or {}),
    }

    try:
        return identify_hook_candidates_for_job(
            job,
            metadata=run_metadata,
        )
    except Exception as exc:
        report = HookIdentificationReport(
            job_id=_get_job_value(job, "job_id"),
            status=HOOK_IDENTIFICATION_STATUS_FAILED,
            selected_candidate=None,
            candidates=[],
            warnings=[],
            blocking_reasons=["hook_identification_failed"],
            recommendation=HOOK_IDENTIFICATION_RECOMMENDATION_FAILED,
            metadata={
                **run_metadata,
                "source": "hook_identification_runner",
                "error": str(exc),
            },
        )
        report.enforce_review_only()
        return report


def apply_hook_identification_run_report_to_job(
    job: Any,
    report: HookIdentificationReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = HookIdentificationReport.from_dict(report)

    report.enforce_review_only()
    report_dict = report.to_dict()
    candidate_dicts = [candidate.to_dict() for candidate in report.candidates]
    selected_candidate = (
        report.selected_candidate.to_dict()
        if report.selected_candidate is not None
        else None
    )

    _set_job_value(job, "hook_identification_report", report_dict)
    _set_job_value(job, "hook_identification", report_dict)
    _set_job_value(job, "hook_identification_status", report.status)
    _set_job_value(job, "hook_candidates", candidate_dicts)
    _set_job_value(job, "hook_selected_candidate", selected_candidate)
    _set_job_value(job, "hook_best_score", float(report.best_hook_score or 0.0))
    _set_job_value(job, "hook_review_required", True)
    _set_job_value(job, "hook_can_apply", False)
    _set_job_value(job, "hook_can_reorder_timeline", False)
    _set_job_value(job, "hook_can_render", False)
    _set_job_value(
        job,
        "hook_blocking_reasons",
        list(report.blocking_reasons or []),
    )
    _set_job_value(job, "hook_warnings", list(report.warnings or []))
    _set_job_value(job, "hook_recommendation", report.recommendation)

    if hasattr(job, "touch"):
        job.touch()

    return job
