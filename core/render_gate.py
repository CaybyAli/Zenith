from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, NamedTuple

from core.approval_store import read_job_approval


class RenderGateDecision(str, Enum):
    PASS = "pass"
    BLOCKED = "blocked"


class RenderGateResult(NamedTuple):
    decision: RenderGateDecision
    reason: str
    detail: dict[str, Any]


AUTO_APPROVE_ENV = "ZENITH_RENDER_GATE_AUTO_APPROVE"
AUTO_APPROVE_DEFAULT = "1"
_Key = tuple[str, str, str]


@dataclass(frozen=True)
class _GateStage:
    name: str
    block_reason: str
    status_key: _Key
    ready_key: _Key | None = None
    count_key: _Key | None = None
    reasons_key: _Key | None = None
    approval_key: _Key | None = None
    extra_keys: tuple[_Key, ...] = ()


_STAGES = (
    _GateStage(
        name="readiness",
        block_reason="readiness_not_ready",
        status_key=("render_readiness_status", "render_readiness_guard_report", "status"),
        ready_key=("render_readiness_ready_for_next_render_stage", "render_readiness_guard_report", "ready_for_next_render_stage"),
        count_key=("render_readiness_blocking_count", "render_readiness_guard_report", "blocking_count"),
        reasons_key=("render_readiness_blocking_reasons", "render_readiness_guard_report", "blocking_reasons"),
    ),
    _GateStage(
        name="plan",
        block_reason="plan_incomplete",
        status_key=("render_plan_status", "render_plan_report", "status"),
        ready_key=("render_plan_ready_for_renderer_contract", "render_plan_report", "ready_for_renderer_contract"),
        reasons_key=("render_plan_blocking_reasons", "render_plan_report", "blocking_reasons"),
    ),
    _GateStage(
        name="manifest",
        block_reason="manifest_not_ready",
        status_key=("render_asset_manifest_status", "render_asset_manifest_report", "status"),
        count_key=("render_asset_unsafe_path_count", "render_asset_manifest_report", "unsafe_path_count"),
        reasons_key=("render_asset_blocking_reasons", "render_asset_manifest_report", "blocking_reasons"),
    ),
    _GateStage(
        name="permission",
        block_reason="permission_denied",
        status_key=("render_execution_permission_status", "render_execution_permission_report", "status"),
        ready_key=("render_execution_ready_for_real_render_stage", "render_execution_permission_report", "ready_for_real_render_stage"),
        reasons_key=("render_execution_blocking_reasons", "render_execution_permission_report", "blocking_reasons"),
        approval_key=("render_execution_human_approved", "render_execution_permission_report", "human_approved"),
    ),
    _GateStage(
        name="verification",
        block_reason="verification_not_ready",
        status_key=("render_verification_contract_status", "render_verification_contract_report", "status"),
        count_key=("render_verification_blocked_check_count", "render_verification_contract_report", "blocked_check_count"),
        reasons_key=("render_verification_blocking_reasons", "render_verification_contract_report", "blocking_reasons"),
        extra_keys=(("render_verification_can_verify_smoke_output", "render_verification_contract_report", "can_verify_smoke_output"),),
    ),
)


def is_auto_approve_active() -> bool:
    return os.environ.get(AUTO_APPROVE_ENV, AUTO_APPROVE_DEFAULT) == "1"


def _get(job: Any, field: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(field, default)
    return getattr(job, field, default)


def _value(job: Any, key: _Key | None, default: Any = None) -> Any:
    if key is None:
        return default
    field, report_field, report_key = key
    direct_value = _get(job, field, None)
    if direct_value is not None:
        return direct_value
    report = _get(job, report_field, None)
    if isinstance(report, dict):
        return report.get(report_key, default)
    return default


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"1", "true", "yes", "y", "ready", "passed", "pass", "ok"}:
            return True
        if cleaned in {"0", "false", "no", "n", "failed", "blocked", "error"}:
            return False
    return bool(value)


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _as_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _has_final_quality_data(job: Any) -> bool:
    direct_fields = (
        "final_quality_status",
        "final_quality_can_render",
        "final_quality_can_execute_timeline",
        "final_quality_blocking_count",
        "final_quality_blocking_reasons",
        "final_quality_overall_score",
    )
    if any(_get(job, field, None) is not None for field in direct_fields):
        return True

    report = _get(job, "final_quality_report", None)
    return isinstance(report, dict) and bool(report)


def _final_quality_detail(job: Any) -> dict[str, Any]:
    if not _has_final_quality_data(job):
        return {"final_quality_present": False}

    return {
        "final_quality_present": True,
        "final_quality_status": _value(
            job,
            ("final_quality_status", "final_quality_report", "status"),
            "",
        ),
        "final_quality_can_render": _as_bool(
            _value(
                job,
                ("final_quality_can_render", "final_quality_report", "can_render"),
                None,
            )
        ),
        "final_quality_can_execute_timeline": _as_bool(
            _value(
                job,
                (
                    "final_quality_can_execute_timeline",
                    "final_quality_report",
                    "can_execute_timeline",
                ),
                None,
            )
        ),
        "final_quality_blocking_count": _as_int(
            _value(
                job,
                ("final_quality_blocking_count", "final_quality_report", "blocking_count"),
                0,
            )
        ),
        "final_quality_blocking_reasons": _as_list(
            _value(
                job,
                (
                    "final_quality_blocking_reasons",
                    "final_quality_report",
                    "blocking_reasons",
                ),
                [],
            )
        ),
        "final_quality_overall_score": _as_float(
            _value(
                job,
                (
                    "final_quality_overall_score",
                    "final_quality_report",
                    "overall_quality_score",
                ),
                0.0,
            )
        ),
    }


def _final_quality_blocked(detail: dict[str, Any]) -> bool:
    if not detail.get("final_quality_present"):
        return False

    if _bad_status(detail.get("final_quality_status")):
        return True

    if _as_int(detail.get("final_quality_blocking_count")) > 0:
        return True

    if _as_list(detail.get("final_quality_blocking_reasons")):
        return True

    if detail.get("final_quality_can_render") is not True:
        return True

    if detail.get("final_quality_can_execute_timeline") is not True:
        return True

    return False


def _bad_status(value: Any) -> bool:
    status = str(value or "").strip().lower()
    return bool(status) and any(
        marker in status
        for marker in ("failed", "blocked", "error", "denied", "not_ready")
    )


def _stage_detail(job: Any, stage: _GateStage) -> dict[str, Any]:
    detail = {stage.status_key[0]: _value(job, stage.status_key, "")}

    if stage.ready_key:
        detail[stage.ready_key[0]] = _as_bool(_value(job, stage.ready_key, None))
    if stage.count_key:
        detail[stage.count_key[0]] = _as_int(_value(job, stage.count_key, 0))
    if stage.reasons_key:
        detail[stage.reasons_key[0]] = _as_list(_value(job, stage.reasons_key, []))
    if stage.approval_key:
        detail[stage.approval_key[0]] = _as_bool(_value(job, stage.approval_key, False))
    for extra_key in stage.extra_keys:
        detail[extra_key[0]] = _as_bool(_value(job, extra_key, None))

    return detail


def _stage_blocked(stage: _GateStage, detail: dict[str, Any]) -> bool:
    status = detail.get(stage.status_key[0])
    ready = detail.get(stage.ready_key[0]) if stage.ready_key else None
    count = detail.get(stage.count_key[0], 0) if stage.count_key else 0
    reasons = detail.get(stage.reasons_key[0], []) if stage.reasons_key else []
    approved = detail.get(stage.approval_key[0]) if stage.approval_key else True

    if _bad_status(status) or _as_int(count) > 0 or _as_list(reasons):
        return True
    if ready is False:
        return True
    if stage.approval_key and approved is not True:
        return True
    return False


def evaluate_render_gate(job: Any) -> RenderGateResult:
    auto_approve = is_auto_approve_active()
    explicit_approval = read_job_approval(job)
    detail: dict[str, Any] = {
        "auto_approve_active": auto_approve,
        "auto_approve_env": AUTO_APPROVE_ENV,
        "explicit_job_approval": explicit_approval is not None,
    }

    if explicit_approval is not None:
        detail["explicit_approval"] = explicit_approval
        return RenderGateResult(
            RenderGateDecision.PASS,
            "explicitly_approved",
            detail,
        )
    first_block_reason: str | None = None
    first_block_stage: str | None = None
    first_block_detail: dict[str, Any] | None = None

    for stage in _STAGES:
        stage_detail = _stage_detail(job, stage)
        detail.update(stage_detail)

        if first_block_reason is None and _stage_blocked(stage, stage_detail):
            first_block_reason = stage.block_reason
            first_block_stage = stage.name
            first_block_detail = stage_detail

    final_quality_detail = _final_quality_detail(job)
    if final_quality_detail.get("final_quality_present"):
        detail.update(final_quality_detail)

        if first_block_reason is None and _final_quality_blocked(final_quality_detail):
            first_block_reason = "final_quality_not_renderable"
            first_block_stage = "final_quality"
            first_block_detail = final_quality_detail

    if first_block_reason:
        detail["would_block_reason"] = first_block_reason
        detail["would_block_stage"] = first_block_stage
        detail["would_block_detail"] = first_block_detail or {}

        if auto_approve:
            return RenderGateResult(
                RenderGateDecision.PASS,
                "auto_approve_override",
                detail,
            )

        return RenderGateResult(
            RenderGateDecision.BLOCKED,
            first_block_reason,
            detail,
        )

    return RenderGateResult(
        RenderGateDecision.PASS,
        "all_gates_passed",
        detail,
    )
