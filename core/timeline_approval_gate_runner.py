from __future__ import annotations

from typing import Any

from core.timeline_approval_gate import build_timeline_approval_gate
from models.timeline_approval_gate import (
    TIMELINE_APPROVAL_GATE_STATUS_FAILED,
    TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
    TimelineApprovalGate,
    TimelineApprovalGateRunReport,
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


def _read_review_timeline_plan_from_job(job: Any) -> dict[str, Any]:
    direct_plan = _object_to_dict(_get_job_value(job, "review_timeline_plan"))
    if direct_plan:
        return direct_plan

    report = _object_to_dict(_get_job_value(job, "review_timeline_plan_report"))
    nested_plan = _object_to_dict(report.get("review_timeline_plan"))
    if nested_plan:
        return nested_plan

    return {}


def _read_requested_approval_status(job: Any) -> str:
    value = (
        _get_job_value(job, "timeline_approval_requested_status")
        or _get_job_value(job, "timeline_approval_status")
        or TIMELINE_APPROVAL_STATUS_PENDING_REVIEW
    )

    return str(value)


def _build_report_from_gate(
    gate: TimelineApprovalGate,
    metadata: dict[str, Any] | None = None,
) -> TimelineApprovalGateRunReport:
    return TimelineApprovalGateRunReport(
        status=gate.gate_status,
        source="timeline_approval_gate",
        timeline_approval_gate=gate,
        approval_status=gate.approval_status,
        gate_status=gate.gate_status,
        can_proceed_to_execution=gate.can_proceed_to_execution,
        can_render=gate.can_render,
        requires_human_approval=gate.requires_human_approval,
        blocking_reasons=list(gate.blocking_reasons or []),
        warnings=list(gate.warnings or []),
        errors=[],
        metadata={
            **dict(gate.metadata or {}),
            **dict(metadata or {}),
        },
    )


def run_timeline_approval_gate_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> TimelineApprovalGateRunReport:
    run_metadata = dict(metadata or {})

    try:
        review_timeline_plan = _read_review_timeline_plan_from_job(job)

        gate = build_timeline_approval_gate(
            review_timeline_plan=review_timeline_plan,
            job_id=_get_job_value(job, "job_id"),
            approval_status=_read_requested_approval_status(job),
            approved_by=_get_job_value(job, "timeline_approved_by"),
            rejected_by=_get_job_value(job, "timeline_rejected_by"),
            manual_change_reason=_get_job_value(
                job,
                "timeline_manual_change_reason",
            ),
            metadata=run_metadata,
        )

        return _build_report_from_gate(gate, metadata=run_metadata)

    except Exception as exc:
        return TimelineApprovalGateRunReport(
            status=TIMELINE_APPROVAL_GATE_STATUS_FAILED,
            source="timeline_approval_gate",
            timeline_approval_gate=None,
            approval_status=TIMELINE_APPROVAL_GATE_STATUS_FAILED,
            gate_status=TIMELINE_APPROVAL_GATE_STATUS_FAILED,
            can_proceed_to_execution=False,
            can_render=False,
            requires_human_approval=True,
            blocking_reasons=[],
            warnings=[],
            errors=[str(exc)],
            metadata=run_metadata,
        )


def apply_timeline_approval_gate_run_report_to_job(
    job: Any,
    report: TimelineApprovalGateRunReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = TimelineApprovalGateRunReport.from_dict(report)

    report_dict = report.to_dict()
    gate_dict = (
        report.timeline_approval_gate.to_dict()
        if report.timeline_approval_gate is not None
        else {}
    )

    _set_job_value(job, "timeline_approval_gate_report", report_dict)
    _set_job_value(job, "timeline_approval_gate", gate_dict)

    _set_job_value(job, "timeline_approval_gate_status", report.gate_status)
    _set_job_value(job, "timeline_approval_status", report.approval_status)

    _set_job_value(
        job,
        "timeline_can_proceed_to_execution",
        report.can_proceed_to_execution,
    )
    _set_job_value(job, "timeline_can_render", report.can_render)
    _set_job_value(
        job,
        "timeline_requires_human_approval",
        report.requires_human_approval,
    )

    _set_job_value(
        job,
        "timeline_approval_blocking_reasons",
        list(report.blocking_reasons or []),
    )
    _set_job_value(
        job,
        "timeline_approval_warnings",
        list(report.warnings or []),
    )

    if report.timeline_approval_gate is not None:
        _set_job_value(
            job,
            "timeline_approval_gate_id",
            report.timeline_approval_gate.approval_gate_id,
        )

    return job
