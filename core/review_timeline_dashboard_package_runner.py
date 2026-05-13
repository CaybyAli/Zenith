from __future__ import annotations

from typing import Any

from core.review_timeline_dashboard_package_builder import (
    ReviewTimelineDashboardPackageBuilder,
)
from models.review_timeline_dashboard_package import (
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED,
    ReviewTimelineDashboardPackage,
    ReviewTimelineDashboardPackageRunReport,
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


def run_review_timeline_dashboard_package_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> ReviewTimelineDashboardPackageRunReport:
    run_metadata = dict(metadata or {})

    try:
        builder = ReviewTimelineDashboardPackageBuilder()
        report = builder.build(job)

        report.metadata = {
            **dict(report.metadata or {}),
            **run_metadata,
        }

        if report.dashboard_package is not None:
            report.dashboard_package.metadata = {
                **dict(report.dashboard_package.metadata or {}),
                **run_metadata,
            }

        return report

    except Exception as exc:
        package = ReviewTimelineDashboardPackage(
            job_id=_get_job_value(job, "job_id"),
            package_status=REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED,
            review_status="failed",
            approval_status="failed",
            safety_status="failed",
            can_proceed_to_execution=False,
            can_render=False,
            is_safe_for_future_execution=False,
            is_safe_for_render=False,
            requires_manual_review=True,
            blocking_errors=[REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED],
            warnings=[],
            metadata={
                **run_metadata,
                "source": "review_timeline_dashboard_package_builder",
                "error": str(exc),
                "dashboard_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_35": True,
            },
        )

        return ReviewTimelineDashboardPackageRunReport(
            status=REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED,
            source="review_timeline_dashboard_package_builder",
            dashboard_package=package,
            review_status="failed",
            approval_status="failed",
            safety_status="failed",
            can_proceed_to_execution=False,
            can_render=False,
            requires_manual_review=True,
            warnings=[],
            blocking_errors=list(package.blocking_errors or []),
            errors=[str(exc)],
            metadata={
                **run_metadata,
                "source": "review_timeline_dashboard_package_builder",
            },
        )


def apply_review_timeline_dashboard_package_run_report_to_job(
    job: Any,
    report: ReviewTimelineDashboardPackageRunReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = ReviewTimelineDashboardPackageRunReport.from_dict(report)

    report_dict = report.to_dict()
    package_dict = (
        report.dashboard_package.to_dict()
        if report.dashboard_package is not None
        else {}
    )

    _set_job_value(job, "review_timeline_dashboard_package_report", report_dict)
    _set_job_value(job, "review_timeline_dashboard_package", package_dict)

    _set_job_value(
        job,
        "review_timeline_dashboard_package_status",
        report.status,
    )
    _set_job_value(
        job,
        "review_timeline_dashboard_review_status",
        report.review_status,
    )
    _set_job_value(
        job,
        "review_timeline_dashboard_approval_status",
        report.approval_status,
    )
    _set_job_value(
        job,
        "review_timeline_dashboard_safety_status",
        report.safety_status,
    )
    _set_job_value(
        job,
        "review_timeline_dashboard_can_proceed_to_execution",
        report.can_proceed_to_execution,
    )

    _set_job_value(
        job,
        "review_timeline_dashboard_can_render",
        False,
    )

    _set_job_value(
        job,
        "review_timeline_dashboard_requires_manual_review",
        report.requires_manual_review,
    )
    _set_job_value(
        job,
        "review_timeline_dashboard_warnings",
        list(report.warnings or []),
    )
    _set_job_value(
        job,
        "review_timeline_dashboard_blocking_errors",
        list(report.blocking_errors or []),
    )

    if report.dashboard_package is None:
        return job

    package = report.dashboard_package
    package.enforce_dashboard_only_safety()

    _set_job_value(
        job,
        "review_timeline_dashboard_package_id",
        package.dashboard_package_id,
    )
    _set_job_value(
        job,
        "review_timeline_dashboard_summary",
        dict(package.summary or {}),
    )
    _set_job_value(
        job,
        "review_timeline_dashboard_counters",
        dict(package.counters or {}),
    )
    _set_job_value(
        job,
        "review_timeline_dashboard_item_cards",
        [
            item_card.to_dict()
            for item_card in list(package.item_cards or [])
        ],
    )
    _set_job_value(
        job,
        "review_timeline_dashboard_approval_panel",
        dict(package.approval_panel or {}),
    )
    _set_job_value(
        job,
        "review_timeline_dashboard_safety_panel",
        dict(package.safety_panel or {}),
    )
    _set_job_value(
        job,
        "review_timeline_dashboard_actions",
        list(package.dashboard_actions or []),
    )

    _set_job_value(
        job,
        "review_timeline_dashboard_is_safe_for_future_execution",
        package.is_safe_for_future_execution,
    )
    _set_job_value(
        job,
        "review_timeline_dashboard_is_safe_for_render",
        False,
    )

    return job