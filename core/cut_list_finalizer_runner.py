from __future__ import annotations

from typing import Any

from core.cut_list_finalizer import finalize_cut_list
from models.final_cut_list import FinalCutListPlan
from models.final_cut_list_run import FinalCutListRunReport


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
        "final_cut_list_plan",
        "continuity_check_result",
        "transition_decision_plan",
        "clip_duration_plan",
        "cut_list_plan",
        "murch_scoring_result",
        "segment_classification_result",
        "unified_edit_signal_report",
        "result",
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


def _read_cut_list_items_from_job(job: Any) -> list[Any]:
    direct_items = _extract_list_from_container(
        _get_job_value(job, "cut_list_items"),
        ("items", "cut_list_items", "recommendations", "results"),
    )
    if direct_items:
        return direct_items

    return _extract_list_from_container(
        _get_job_value(job, "cut_list_report"),
        ("items", "cut_list_items", "recommendations", "results"),
    )


def _read_clip_duration_recommendations_from_job(job: Any) -> list[Any]:
    direct_items = _extract_list_from_container(
        _get_job_value(job, "clip_duration_recommendations"),
        ("recommendations", "clip_duration_recommendations", "items", "results"),
    )
    if direct_items:
        return direct_items

    return _extract_list_from_container(
        _get_job_value(job, "clip_duration_report"),
        ("recommendations", "clip_duration_recommendations", "items", "results"),
    )


def _read_transition_decisions_from_job(job: Any) -> list[Any]:
    direct_items = _extract_list_from_container(
        _get_job_value(job, "transition_decision_decisions"),
        ("decisions", "transition_decision_decisions", "items", "results"),
    )
    if direct_items:
        return direct_items

    return _extract_list_from_container(
        _get_job_value(job, "transition_decision_report"),
        ("decisions", "transition_decision_decisions", "items", "results"),
    )


def _read_continuity_issues_from_job(job: Any) -> list[Any]:
    direct_items = _extract_list_from_container(
        _get_job_value(job, "continuity_check_issues"),
        ("issues", "continuity_check_issues", "items", "results"),
    )
    if direct_items:
        return direct_items

    return _extract_list_from_container(
        _get_job_value(job, "continuity_check_report"),
        ("issues", "continuity_check_issues", "items", "results"),
    )


def _read_murch_scores_from_job(job: Any) -> list[Any]:
    direct_items = _extract_list_from_container(
        _get_job_value(job, "murch_scoring_segment_scores"),
        ("segment_scores", "murch_scoring_segment_scores", "scores", "items"),
    )
    if direct_items:
        return direct_items

    return _extract_list_from_container(
        _get_job_value(job, "murch_scoring_report"),
        ("segment_scores", "murch_scoring_segment_scores", "scores", "items"),
    )


def _read_segment_classifications_from_job(job: Any) -> list[Any]:
    direct_items = _extract_list_from_container(
        _get_job_value(job, "segment_classification_segments"),
        ("segments", "segment_classification_segments", "items", "results"),
    )
    if direct_items:
        return direct_items

    return _extract_list_from_container(
        _get_job_value(job, "segment_classification_report"),
        ("segments", "segment_classification_segments", "items", "results"),
    )


def _read_unified_signals_from_job(job: Any) -> list[Any]:
    direct_items = _extract_list_from_container(
        _get_job_value(job, "unified_edit_signals"),
        ("signals", "unified_edit_signals", "edit_signals", "items", "results"),
    )
    if direct_items:
        return direct_items

    return _extract_list_from_container(
        _get_job_value(job, "unified_edit_signal_report"),
        ("signals", "unified_edit_signals", "edit_signals", "items", "results"),
    )


def _build_report_from_plan(
    plan: FinalCutListPlan,
    metadata: dict[str, Any] | None = None,
) -> FinalCutListRunReport:
    plan.refresh_counts()

    return FinalCutListRunReport(
        status=plan.status,
        source="cut_list_finalizer",
        final_cut_list_plan=plan,
        final_items=list(plan.final_items),
        final_item_count=plan.final_item_count,
        final_keep_review_count=plan.final_keep_review_count,
        final_keep_high_value_count=plan.final_keep_high_value_count,
        final_trim_review_count=plan.final_trim_review_count,
        final_remove_review_count=plan.final_remove_review_count,
        final_protect_count=plan.final_protect_count,
        final_censor_keep_count=plan.final_censor_keep_count,
        final_technical_review_count=plan.final_technical_review_count,
        final_blocked_by_continuity_count=(
            plan.final_blocked_by_continuity_count
        ),
        final_unknown_review_count=plan.final_unknown_review_count,
        review_required_count=plan.review_required_count,
        blocking_issue_count=plan.blocking_issue_count,
        recommendation=plan.recommendation,
        warnings=list(plan.warnings or []),
        errors=list(plan.errors or []),
        metadata={
            **dict(plan.metadata or {}),
            **dict(metadata or {}),
        },
    )


def run_cut_list_finalization_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> FinalCutListRunReport:
    run_metadata = dict(metadata or {})

    cut_list_items = _read_cut_list_items_from_job(job)
    clip_duration_recommendations = _read_clip_duration_recommendations_from_job(job)
    transition_decisions = _read_transition_decisions_from_job(job)
    continuity_issues = _read_continuity_issues_from_job(job)
    murch_scores = _read_murch_scores_from_job(job)
    segment_classifications = _read_segment_classifications_from_job(job)
    unified_signals = _read_unified_signals_from_job(job)

    if not any(
        [
            cut_list_items,
            clip_duration_recommendations,
            transition_decisions,
            continuity_issues,
            murch_scores,
            segment_classifications,
            unified_signals,
        ]
    ):
        plan = finalize_cut_list(metadata=run_metadata)
        return _build_report_from_plan(plan, metadata=run_metadata)

    try:
        plan = finalize_cut_list(
            cut_list_items=cut_list_items,
            clip_duration_recommendations=clip_duration_recommendations,
            transition_decisions=transition_decisions,
            continuity_issues=continuity_issues,
            murch_scores=murch_scores,
            segment_classifications=segment_classifications,
            unified_signals=unified_signals,
            metadata=run_metadata,
        )
        return _build_report_from_plan(plan, metadata=run_metadata)
    except Exception as exc:
        return FinalCutListRunReport(
            status="failed",
            source="cut_list_finalizer",
            final_cut_list_plan=None,
            final_items=[],
            final_item_count=0,
            recommendation="cut_list_finalization_failed",
            warnings=[],
            errors=[str(exc)],
            metadata=run_metadata,
        )


def apply_cut_list_finalization_run_report_to_job(
    job: Any,
    report: FinalCutListRunReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = FinalCutListRunReport.from_dict(report)

    report_dict = report.to_dict()
    final_item_dicts = [item.to_dict() for item in report.final_items]

    _set_job_value(job, "final_cut_list_report", report_dict)
    _set_job_value(job, "final_cut_list_status", report.status)
    _set_job_value(job, "final_cut_list_items", final_item_dicts)
    _set_job_value(job, "final_cut_list_item_count", report.final_item_count)
    _set_job_value(
        job,
        "final_cut_list_keep_review_count",
        report.final_keep_review_count,
    )
    _set_job_value(
        job,
        "final_cut_list_keep_high_value_count",
        report.final_keep_high_value_count,
    )
    _set_job_value(
        job,
        "final_cut_list_trim_review_count",
        report.final_trim_review_count,
    )
    _set_job_value(
        job,
        "final_cut_list_remove_review_count",
        report.final_remove_review_count,
    )
    _set_job_value(job, "final_cut_list_protect_count", report.final_protect_count)
    _set_job_value(
        job,
        "final_cut_list_censor_keep_count",
        report.final_censor_keep_count,
    )
    _set_job_value(
        job,
        "final_cut_list_technical_review_count",
        report.final_technical_review_count,
    )
    _set_job_value(
        job,
        "final_cut_list_blocked_by_continuity_count",
        report.final_blocked_by_continuity_count,
    )
    _set_job_value(
        job,
        "final_cut_list_unknown_review_count",
        report.final_unknown_review_count,
    )
    _set_job_value(
        job,
        "final_cut_list_review_required_count",
        report.review_required_count,
    )
    _set_job_value(
        job,
        "final_cut_list_blocking_issue_count",
        report.blocking_issue_count,
    )
    _set_job_value(job, "final_cut_list_recommendation", report.recommendation)

    return job
