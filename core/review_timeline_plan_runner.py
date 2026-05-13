from __future__ import annotations

from typing import Any

from core.review_timeline_plan_builder import build_review_timeline_plan
from models.review_timeline_plan import (
    REVIEW_TIMELINE_PLAN_STATUS_FAILED,
    REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW,
    REVIEW_TIMELINE_PLAN_STATUS_SKIPPED_NO_FINAL_ITEMS,
    ReviewTimelinePlan,
    ReviewTimelinePlanRunReport,
)


def _object_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    if hasattr(value, "to_dict"):
        try:
            converted = value.to_dict()
            if isinstance(converted, dict):
                return dict(converted)
        except Exception:
            return {}

    return {}


def _get_job_value(job: Any, key: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(key, default)

    return getattr(job, key, default)


def _set_job_value(job: Any, key: str, value: Any) -> None:
    if isinstance(job, dict):
        job[key] = value
        return

    setattr(job, key, value)


def _extract_list_from_container(container: Any, keys: tuple[str, ...]) -> list[Any]:
    if not container:
        return []

    if isinstance(container, list):
        return container

    if isinstance(container, tuple):
        return list(container)

    data = _object_to_dict(container)

    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value

    nested_names = (
        "review_timeline_plan",
        "final_cut_list_plan",
        "result",
        "plan",
    )

    for nested_name in nested_names:
        nested = data.get(nested_name)
        if nested is None:
            continue

        nested_data = _object_to_dict(nested)
        for key in keys:
            value = nested_data.get(key)
            if isinstance(value, list):
                return value

    return []


def _read_final_cut_list_items_from_job(job: Any) -> list[Any]:
    direct_items = _extract_list_from_container(
        _get_job_value(job, "final_cut_list_items"),
        ("final_items", "final_cut_list_items", "items", "results"),
    )
    if direct_items:
        return direct_items

    return _extract_list_from_container(
        _get_job_value(job, "final_cut_list_report"),
        ("final_items", "final_cut_list_items", "items", "results"),
    )


def _read_source_finalizer_run_id(job: Any) -> str | None:
    report = _object_to_dict(_get_job_value(job, "final_cut_list_report"))
    metadata = dict(report.get("metadata") or {})

    value = (
        report.get("run_id")
        or metadata.get("run_id")
        or metadata.get("source_finalizer_run_id")
    )

    return str(value) if value is not None else None


def _read_source_cut_list_id(job: Any) -> str | None:
    report = _object_to_dict(_get_job_value(job, "cut_list_report"))
    metadata = dict(report.get("metadata") or {})

    value = report.get("plan_id") or metadata.get("plan_id") or metadata.get("run_id")

    return str(value) if value is not None else None


def _build_report_from_plan(
    plan: ReviewTimelinePlan,
    metadata: dict[str, Any] | None = None,
) -> ReviewTimelinePlanRunReport:
    plan.refresh_counts()

    return ReviewTimelinePlanRunReport(
        status=plan.status,
        source="review_timeline_plan_builder",
        review_timeline_plan=plan,
        items=list(plan.items),
        total_items=plan.total_items,
        total_duration_seconds=plan.total_duration_seconds,
        review_required_count=plan.review_required_count,
        protected_count=plan.protected_count,
        censor_required_count=plan.censor_required_count,
        continuity_blocked_count=plan.continuity_blocked_count,
        recommendation=plan.recommendation,
        warnings=list(plan.warnings or []),
        errors=list(plan.errors or []),
        metadata={
            **dict(plan.metadata or {}),
            **dict(metadata or {}),
        },
    )


def run_review_timeline_plan_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> ReviewTimelinePlanRunReport:
    run_metadata = dict(metadata or {})

    final_items = _read_final_cut_list_items_from_job(job)
    job_id = _get_job_value(job, "job_id")
    source_finalizer_run_id = _read_source_finalizer_run_id(job)
    source_cut_list_id = _read_source_cut_list_id(job)

    try:
        plan = build_review_timeline_plan(
            final_cut_list_items=final_items,
            job_id=str(job_id) if job_id is not None else None,
            source_cut_list_id=source_cut_list_id,
            source_finalizer_run_id=source_finalizer_run_id,
            metadata=run_metadata,
        )

        report = _build_report_from_plan(plan, metadata=run_metadata)

        if not final_items:
            report.status = REVIEW_TIMELINE_PLAN_STATUS_SKIPPED_NO_FINAL_ITEMS
            report.recommendation = "review_timeline_plan_skipped_no_final_items"
            if "no_final_cut_list_items_available" not in report.warnings:
                report.warnings.append("no_final_cut_list_items_available")

        return report

    except Exception as exc:
        return ReviewTimelinePlanRunReport(
            status=REVIEW_TIMELINE_PLAN_STATUS_FAILED,
            source="review_timeline_plan_builder",
            review_timeline_plan=None,
            items=[],
            total_items=0,
            total_duration_seconds=0.0,
            review_required_count=0,
            protected_count=0,
            censor_required_count=0,
            continuity_blocked_count=0,
            recommendation="review_timeline_plan_failed",
            warnings=[],
            errors=[str(exc)],
            metadata=run_metadata,
        )


def apply_review_timeline_plan_run_report_to_job(
    job: Any,
    report: ReviewTimelinePlanRunReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = ReviewTimelinePlanRunReport.from_dict(report)

    report_dict = report.to_dict()
    plan_dict = (
        report.review_timeline_plan.to_dict()
        if report.review_timeline_plan is not None
        else {}
    )
    item_dicts = [item.to_dict() for item in report.items]

    _set_job_value(job, "review_timeline_plan_report", report_dict)
    _set_job_value(job, "review_timeline_plan", plan_dict)
    _set_job_value(job, "review_timeline_plan_status", report.status)
    _set_job_value(job, "review_timeline_plan_items", item_dicts)
    _set_job_value(job, "review_timeline_plan_item_count", report.total_items)
    _set_job_value(
        job,
        "review_timeline_plan_total_duration_seconds",
        report.total_duration_seconds,
    )
    _set_job_value(
        job,
        "review_timeline_plan_review_required_count",
        report.review_required_count,
    )
    _set_job_value(
        job,
        "review_timeline_plan_protected_count",
        report.protected_count,
    )
    _set_job_value(
        job,
        "review_timeline_plan_censor_required_count",
        report.censor_required_count,
    )
    _set_job_value(
        job,
        "review_timeline_plan_continuity_blocked_count",
        report.continuity_blocked_count,
    )
    _set_job_value(
        job,
        "review_timeline_plan_recommendation",
        report.recommendation,
    )

    if report.review_timeline_plan is not None:
        _set_job_value(
            job,
            "review_timeline_plan_id",
            report.review_timeline_plan.plan_id,
        )

    return job
