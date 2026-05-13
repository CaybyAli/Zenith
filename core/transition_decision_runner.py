from __future__ import annotations

from typing import Any

from core.transition_decision_engine import build_transition_decision_plan
from models.transition_decision import TransitionDecisionPlan
from models.transition_decision_run import TransitionDecisionRunReport


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
        "transition_decision_plan",
        "clip_duration_plan",
        "cut_list_plan",
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


def _read_clip_duration_recommendations_from_job(job: Any) -> list[Any]:
    direct_items = _extract_list_from_container(
        _get_job_value(job, "clip_duration_recommendations"),
        (
            "recommendations",
            "clip_duration_recommendations",
            "items",
            "results",
        ),
    )
    if direct_items:
        return direct_items

    report_items = _extract_list_from_container(
        _get_job_value(job, "clip_duration_report"),
        (
            "recommendations",
            "clip_duration_recommendations",
            "items",
            "results",
        ),
    )
    if report_items:
        return report_items

    return []


def _read_cut_list_items_from_job(job: Any) -> list[Any]:
    direct_items = _extract_list_from_container(
        _get_job_value(job, "cut_list_items"),
        (
            "items",
            "cut_list_items",
            "recommendations",
            "results",
        ),
    )
    if direct_items:
        return direct_items

    report_items = _extract_list_from_container(
        _get_job_value(job, "cut_list_report"),
        (
            "items",
            "cut_list_items",
            "recommendations",
            "results",
        ),
    )
    if report_items:
        return report_items

    return []


def _read_unified_signals_from_job(job: Any) -> list[Any]:
    direct_items = _extract_list_from_container(
        _get_job_value(job, "unified_edit_signals"),
        (
            "signals",
            "unified_edit_signals",
            "items",
            "results",
        ),
    )
    if direct_items:
        return direct_items

    report_items = _extract_list_from_container(
        _get_job_value(job, "unified_edit_signal_report"),
        (
            "signals",
            "unified_edit_signals",
            "items",
            "results",
        ),
    )
    if report_items:
        return report_items

    return []


def _build_report_from_plan(
    plan: TransitionDecisionPlan,
    metadata: dict[str, Any] | None = None,
) -> TransitionDecisionRunReport:
    return TransitionDecisionRunReport(
        status=plan.status,
        source="transition_decision",
        transition_decision_plan=plan,
        decisions=list(plan.decisions),
        decision_count=plan.decision_count,
        hard_cut_review_count=plan.hard_cut_review_count,
        j_cut_review_count=plan.j_cut_review_count,
        l_cut_review_count=plan.l_cut_review_count,
        quick_fade_review_count=plan.quick_fade_review_count,
        no_cut_protect_count=plan.no_cut_protect_count,
        censor_safe_keep_count=plan.censor_safe_keep_count,
        technical_transition_review_count=plan.technical_transition_review_count,
        unknown_review_count=plan.unknown_review_count,
        recommendation=plan.recommendation,
        warnings=list(plan.warnings or []),
        errors=list(plan.errors or []),
        metadata={
            **dict(plan.metadata or {}),
            **dict(metadata or {}),
        },
    )


def run_transition_decision_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> TransitionDecisionRunReport:
    run_metadata = dict(metadata or {})

    clip_duration_recommendations = _read_clip_duration_recommendations_from_job(job)
    cut_list_items = _read_cut_list_items_from_job(job)
    unified_signals = _read_unified_signals_from_job(job)

    if not clip_duration_recommendations and not cut_list_items:
        plan = build_transition_decision_plan(
            clip_duration_recommendations=[],
            cut_list_items=[],
            unified_signals=unified_signals,
            metadata=run_metadata,
        )
        report = _build_report_from_plan(plan, metadata=run_metadata)
        report.status = "skipped_no_clip_duration_recommendations"
        report.recommendation = "transition_decision_skipped_no_inputs"
        return report

    try:
        plan = build_transition_decision_plan(
            clip_duration_recommendations=clip_duration_recommendations,
            cut_list_items=cut_list_items,
            unified_signals=unified_signals,
            metadata=run_metadata,
        )
        return _build_report_from_plan(plan, metadata=run_metadata)
    except Exception as exc:
        return TransitionDecisionRunReport(
            status="failed",
            source="transition_decision",
            transition_decision_plan=None,
            decisions=[],
            decision_count=0,
            recommendation="transition_decision_failed",
            warnings=[],
            errors=[str(exc)],
            metadata=run_metadata,
        )


def apply_transition_decision_run_report_to_job(
    job: Any,
    report: TransitionDecisionRunReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = TransitionDecisionRunReport.from_dict(report)

    report_dict = report.to_dict()
    decision_dicts = [decision.to_dict() for decision in report.decisions]

    _set_job_value(job, "transition_decision_report", report_dict)
    _set_job_value(job, "transition_decision_status", report.status)
    _set_job_value(job, "transition_decision_decisions", decision_dicts)
    _set_job_value(job, "transition_decision_count", report.decision_count)
    _set_job_value(
        job,
        "transition_decision_hard_cut_review_count",
        report.hard_cut_review_count,
    )
    _set_job_value(
        job,
        "transition_decision_j_cut_review_count",
        report.j_cut_review_count,
    )
    _set_job_value(
        job,
        "transition_decision_l_cut_review_count",
        report.l_cut_review_count,
    )
    _set_job_value(
        job,
        "transition_decision_quick_fade_review_count",
        report.quick_fade_review_count,
    )
    _set_job_value(
        job,
        "transition_decision_no_cut_protect_count",
        report.no_cut_protect_count,
    )
    _set_job_value(
        job,
        "transition_decision_censor_safe_keep_count",
        report.censor_safe_keep_count,
    )
    _set_job_value(
        job,
        "transition_decision_technical_review_count",
        report.technical_transition_review_count,
    )
    _set_job_value(
        job,
        "transition_decision_unknown_review_count",
        report.unknown_review_count,
    )
    _set_job_value(job, "transition_decision_recommendation", report.recommendation)

    return job
