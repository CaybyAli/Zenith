from __future__ import annotations

from typing import Any

from core.timeline_safety_validator import TimelineSafetyValidator
from models.timeline_safety_validator import (
    TIMELINE_SAFETY_STATUS_FAILED,
    TimelineSafetyValidation,
    TimelineSafetyValidatorRunReport,
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


def run_timeline_safety_validator_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> TimelineSafetyValidatorRunReport:
    run_metadata = dict(metadata or {})

    try:
        validator = TimelineSafetyValidator()
        report = validator.validate(job)

        report.metadata = {
            **dict(report.metadata or {}),
            **run_metadata,
        }

        if report.timeline_safety_validation is not None:
            report.timeline_safety_validation.metadata = {
                **dict(report.timeline_safety_validation.metadata or {}),
                **run_metadata,
            }

        return report

    except Exception as exc:
        validation = TimelineSafetyValidation(
            job_id=_get_job_value(job, "job_id"),
            validation_status=TIMELINE_SAFETY_STATUS_FAILED,
            is_safe_for_future_execution=False,
            is_safe_for_render=False,
            requires_manual_review=True,
            blocking_errors=[TIMELINE_SAFETY_STATUS_FAILED],
            warnings=[],
            metadata={
                **run_metadata,
                "source": "timeline_safety_validator",
                "error": str(exc),
            },
        )

        return TimelineSafetyValidatorRunReport(
            status=TIMELINE_SAFETY_STATUS_FAILED,
            source="timeline_safety_validator",
            timeline_safety_validation=validation,
            validation_status=TIMELINE_SAFETY_STATUS_FAILED,
            is_safe_for_future_execution=False,
            is_safe_for_render=False,
            requires_manual_review=True,
            blocking_errors=list(validation.blocking_errors or []),
            warnings=[],
            errors=[str(exc)],
            metadata={
                **run_metadata,
                "source": "timeline_safety_validator",
            },
        )


def apply_timeline_safety_validator_run_report_to_job(
    job: Any,
    report: TimelineSafetyValidatorRunReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = TimelineSafetyValidatorRunReport.from_dict(report)

    report_dict = report.to_dict()
    validation_dict = (
        report.timeline_safety_validation.to_dict()
        if report.timeline_safety_validation is not None
        else {}
    )

    _set_job_value(job, "timeline_safety_validator_report", report_dict)
    _set_job_value(job, "timeline_safety_validator", validation_dict)

    _set_job_value(
        job,
        "timeline_safety_validation_status",
        report.validation_status,
    )
    _set_job_value(
        job,
        "timeline_is_safe_for_future_execution",
        report.is_safe_for_future_execution,
    )
    _set_job_value(
        job,
        "timeline_is_safe_for_render",
        False,
    )
    _set_job_value(
        job,
        "timeline_safety_requires_manual_review",
        report.requires_manual_review,
    )
    _set_job_value(
        job,
        "timeline_safety_blocking_errors",
        list(report.blocking_errors or []),
    )
    _set_job_value(
        job,
        "timeline_safety_warnings",
        list(report.warnings or []),
    )

    if report.timeline_safety_validation is None:
        return job

    validation = report.timeline_safety_validation

    _set_job_value(
        job,
        "timeline_safety_validation_id",
        validation.safety_validation_id,
    )
    _set_job_value(
        job,
        "timeline_safety_item_results",
        [
            item.to_dict()
            for item in list(validation.item_results or [])
        ],
    )
    _set_job_value(
        job,
        "timeline_safety_invalid_timing_count",
        validation.invalid_timing_count,
    )
    _set_job_value(
        job,
        "timeline_safety_overlap_count",
        validation.overlap_count,
    )
    _set_job_value(
        job,
        "timeline_safety_gap_count",
        validation.gap_count,
    )
    _set_job_value(
        job,
        "timeline_safety_protected_violation_count",
        validation.protected_violation_count,
    )
    _set_job_value(
        job,
        "timeline_safety_censor_violation_count",
        validation.censor_violation_count,
    )
    _set_job_value(
        job,
        "timeline_safety_continuity_violation_count",
        validation.continuity_violation_count,
    )
    _set_job_value(
        job,
        "timeline_safety_approval_violation_count",
        validation.approval_violation_count,
    )

    return job
