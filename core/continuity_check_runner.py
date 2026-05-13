from __future__ import annotations

from typing import Any

from core.continuity_checker import run_continuity_check
from models.continuity_check import ContinuityCheckResult
from models.continuity_check_run import ContinuityCheckRunReport


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
        "continuity_check_result",
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


def _read_transition_decisions_from_job(job: Any) -> list[Any]:
    direct_items = _extract_list_from_container(
        _get_job_value(job, "transition_decision_decisions"),
        (
            "decisions",
            "transition_decision_decisions",
            "items",
            "results",
        ),
    )
    if direct_items:
        return direct_items

    report_items = _extract_list_from_container(
        _get_job_value(job, "transition_decision_report"),
        (
            "decisions",
            "transition_decision_decisions",
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


def _build_report_from_result(
    result: ContinuityCheckResult,
    metadata: dict[str, Any] | None = None,
) -> ContinuityCheckRunReport:
    result.refresh_counts()

    return ContinuityCheckRunReport(
        status=result.status,
        source="continuity_check",
        continuity_check_result=result,
        issues=list(result.issues),
        issue_count=result.issue_count,
        blocking_issue_count=result.blocking_issue_count,
        sentence_break_risk_count=result.sentence_break_risk_count,
        context_jump_risk_count=result.context_jump_risk_count,
        censor_context_risk_count=result.censor_context_risk_count,
        timing_issue_count=result.timing_issue_count,
        transition_conflict_count=result.transition_conflict_count,
        technical_issue_count=result.technical_issue_count,
        protected_context_count=result.protected_context_count,
        recommendation=result.recommendation,
        warnings=list(result.warnings or []),
        errors=list(result.errors or []),
        metadata={
            **dict(result.metadata or {}),
            **dict(metadata or {}),
        },
    )


def run_continuity_check_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> ContinuityCheckRunReport:
    run_metadata = dict(metadata or {})

    transition_decisions = _read_transition_decisions_from_job(job)
    cut_list_items = _read_cut_list_items_from_job(job)
    clip_duration_recommendations = _read_clip_duration_recommendations_from_job(job)
    unified_signals = _read_unified_signals_from_job(job)

    if not transition_decisions and not cut_list_items:
        result = run_continuity_check(
            transition_decisions=[],
            cut_list_items=[],
            clip_duration_recommendations=clip_duration_recommendations,
            unified_signals=unified_signals,
            metadata=run_metadata,
        )
        report = _build_report_from_result(result, metadata=run_metadata)
        report.status = "skipped_no_transition_decisions"
        report.recommendation = "continuity_check_skipped_no_inputs"
        return report

    try:
        result = run_continuity_check(
            transition_decisions=transition_decisions,
            cut_list_items=cut_list_items,
            clip_duration_recommendations=clip_duration_recommendations,
            unified_signals=unified_signals,
            metadata=run_metadata,
        )
        return _build_report_from_result(result, metadata=run_metadata)
    except Exception as exc:
        return ContinuityCheckRunReport(
            status="failed",
            source="continuity_check",
            continuity_check_result=None,
            issues=[],
            issue_count=0,
            recommendation="continuity_check_failed",
            warnings=[],
            errors=[str(exc)],
            metadata=run_metadata,
        )


def apply_continuity_check_run_report_to_job(
    job: Any,
    report: ContinuityCheckRunReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = ContinuityCheckRunReport.from_dict(report)

    report_dict = report.to_dict()
    issue_dicts = [issue.to_dict() for issue in report.issues]

    _set_job_value(job, "continuity_check_report", report_dict)
    _set_job_value(job, "continuity_check_status", report.status)
    _set_job_value(job, "continuity_check_issues", issue_dicts)
    _set_job_value(job, "continuity_check_issue_count", report.issue_count)
    _set_job_value(
        job,
        "continuity_check_blocking_issue_count",
        report.blocking_issue_count,
    )
    _set_job_value(
        job,
        "continuity_check_sentence_break_risk_count",
        report.sentence_break_risk_count,
    )
    _set_job_value(
        job,
        "continuity_check_context_jump_risk_count",
        report.context_jump_risk_count,
    )
    _set_job_value(
        job,
        "continuity_check_censor_context_risk_count",
        report.censor_context_risk_count,
    )
    _set_job_value(
        job,
        "continuity_check_timing_issue_count",
        report.timing_issue_count,
    )
    _set_job_value(
        job,
        "continuity_check_transition_conflict_count",
        report.transition_conflict_count,
    )
    _set_job_value(
        job,
        "continuity_check_technical_issue_count",
        report.technical_issue_count,
    )
    _set_job_value(
        job,
        "continuity_check_protected_context_count",
        report.protected_context_count,
    )
    _set_job_value(job, "continuity_check_recommendation", report.recommendation)

    return job
