from __future__ import annotations

from typing import Any

from core.cut_list_generator import generate_cut_list_plan
from models.cut_list import (
    CUT_LIST_STATUS_COMPLETED_WITH_WARNINGS,
    CUT_LIST_STATUS_FAILED,
    CUT_LIST_STATUS_SKIPPED_NO_SEGMENTS,
    CutListPlan,
)
from models.cut_list_run import CutListRunReport


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

    nested_result = data.get("result")
    if nested_result is not None:
        nested_data = _object_to_dict(nested_result)
        for key in keys:
            value = nested_data.get(key)
            if isinstance(value, list):
                return value

    return []


def _read_segment_classifications_from_job(job: Any) -> list[Any]:
    direct_segments = _extract_list_from_container(
        _get_job_value(job, "segment_classification_segments"),
        (
            "segments",
            "segment_classification_segments",
            "items",
            "results",
        ),
    )
    if direct_segments:
        return direct_segments

    report_segments = _extract_list_from_container(
        _get_job_value(job, "segment_classification_report"),
        (
            "segments",
            "segment_classification_segments",
            "items",
            "results",
        ),
    )
    if report_segments:
        return report_segments

    return []


def _read_murch_scores_from_job(job: Any) -> list[Any]:
    direct_scores = _extract_list_from_container(
        _get_job_value(job, "murch_scoring_segment_scores"),
        (
            "segment_scores",
            "murch_scoring_segment_scores",
            "scores",
            "items",
            "results",
        ),
    )
    if direct_scores:
        return direct_scores

    report_scores = _extract_list_from_container(
        _get_job_value(job, "murch_scoring_report"),
        (
            "segment_scores",
            "murch_scoring_segment_scores",
            "scores",
            "items",
            "results",
        ),
    )
    if report_scores:
        return report_scores

    return []


def _read_unified_signals_from_job(job: Any) -> list[Any]:
    direct_signals = _extract_list_from_container(
        _get_job_value(job, "unified_edit_signals"),
        (
            "signals",
            "unified_edit_signals",
            "edit_signals",
            "items",
            "results",
        ),
    )
    if direct_signals:
        return direct_signals

    report_signals = _extract_list_from_container(
        _get_job_value(job, "unified_edit_signal_report"),
        (
            "signals",
            "unified_edit_signals",
            "edit_signals",
            "items",
            "results",
        ),
    )
    if report_signals:
        return report_signals

    return []


def _build_report_from_plan(
    plan: CutListPlan,
    metadata: dict[str, Any] | None = None,
) -> CutListRunReport:
    plan.refresh_counts()

    return CutListRunReport(
        status=plan.status,
        source="cut_list_generator",
        cut_list_plan=plan,
        items=list(plan.items),
        item_count=plan.item_count,
        keep_count=plan.keep_count,
        review_keep_count=plan.review_keep_count,
        review_trim_count=plan.review_trim_count,
        review_remove_count=plan.review_remove_count,
        protect_count=plan.protect_count,
        censor_keep_count=plan.censor_keep_count,
        technical_review_count=plan.technical_review_count,
        unknown_review_count=plan.unknown_review_count,
        recommendation=plan.recommendation or "review_cut_list_candidates",
        warnings=list(plan.warnings or []),
        errors=list(plan.errors or []),
        metadata={
            **dict(plan.metadata or {}),
            **dict(metadata or {}),
        },
    )


def run_cut_list_generation_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> CutListRunReport:
    run_metadata = dict(metadata or {})
    segment_classifications = _read_segment_classifications_from_job(job)
    murch_scores = _read_murch_scores_from_job(job)
    unified_signals = _read_unified_signals_from_job(job)

    if not segment_classifications:
        plan = generate_cut_list_plan(
            segment_classifications=[],
            murch_scores=[],
            unified_signals=unified_signals,
            metadata=run_metadata,
        )
        report = _build_report_from_plan(plan, metadata=run_metadata)
        report.status = CUT_LIST_STATUS_SKIPPED_NO_SEGMENTS
        report.recommendation = "cut_list_skipped_no_segments"
        return report

    try:
        plan = generate_cut_list_plan(
            segment_classifications=segment_classifications,
            murch_scores=murch_scores,
            unified_signals=unified_signals,
            metadata=run_metadata,
        )
        report = _build_report_from_plan(plan, metadata=run_metadata)

        if not murch_scores:
            report.status = CUT_LIST_STATUS_COMPLETED_WITH_WARNINGS
            report.recommendation = "cut_list_generated_with_missing_murch_scores"
            if "missing_murch_scores_using_safe_fallback" not in report.warnings:
                report.warnings.append("missing_murch_scores_using_safe_fallback")

        return report
    except Exception as exc:
        return CutListRunReport(
            status=CUT_LIST_STATUS_FAILED,
            source="cut_list_generator",
            cut_list_plan=None,
            items=[],
            item_count=0,
            recommendation="cut_list_generation_failed",
            warnings=[],
            errors=[str(exc)],
            metadata=run_metadata,
        )


def apply_cut_list_run_report_to_job(
    job: Any,
    report: CutListRunReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = CutListRunReport.from_dict(report)

    report_dict = report.to_dict()
    item_dicts = [item.to_dict() for item in report.items]

    _set_job_value(job, "cut_list_report", report_dict)
    _set_job_value(job, "cut_list_status", report.status)
    _set_job_value(job, "cut_list_items", item_dicts)
    _set_job_value(job, "cut_list_item_count", report.item_count)
    _set_job_value(job, "cut_list_keep_count", report.keep_count)
    _set_job_value(job, "cut_list_review_keep_count", report.review_keep_count)
    _set_job_value(job, "cut_list_review_trim_count", report.review_trim_count)
    _set_job_value(job, "cut_list_review_remove_count", report.review_remove_count)
    _set_job_value(job, "cut_list_protect_count", report.protect_count)
    _set_job_value(job, "cut_list_censor_keep_count", report.censor_keep_count)
    _set_job_value(job, "cut_list_technical_review_count", report.technical_review_count)
    _set_job_value(job, "cut_list_unknown_review_count", report.unknown_review_count)
    _set_job_value(job, "cut_list_recommendation", report.recommendation)

    return job
