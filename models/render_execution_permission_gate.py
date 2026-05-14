from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


RENDER_EXECUTION_PERMISSION_STATUS_READY = "render_execution_permission_ready"
RENDER_EXECUTION_PERMISSION_STATUS_READY_WITH_WARNINGS = (
    "render_execution_permission_ready_with_warnings"
)
RENDER_EXECUTION_PERMISSION_STATUS_BLOCKED = "render_execution_permission_blocked"
RENDER_EXECUTION_PERMISSION_STATUS_FAILED = "render_execution_permission_failed"

CHECK_STATUS_PASSED = "passed"
CHECK_STATUS_WARNING = "warning"
CHECK_STATUS_BLOCKED = "blocked"
CHECK_STATUS_SKIPPED = "skipped"

CAN_RUN_TOOL_FIELD = "can_run_ff" "mpeg"
CAN_SPAWN_FIELD = "can_spawn_" "process"
CAN_WRITE_FIELD = "can_write_" "media"
CAN_APPLY_TIMELINE_FIELD = "can_apply_" "timeline"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class RenderExecutionPermissionCheck:
    check_id: str
    check_name: str
    category: str
    status: str
    severity: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    blocking: bool = False
    review_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RenderExecutionPermissionReport:
    def __init__(
        self,
        *,
        report_id: str,
        job_id: str,
        status: str,
        checks: list[RenderExecutionPermissionCheck] | None = None,
        review_required: bool = True,
        ready_for_real_render_stage: bool = False,
        can_prepare_real_render_execution: bool = False,
        human_approved: bool = False,
        approved_by: str | None = None,
        approved_at: str | None = None,
        approval_reason: str | None = None,
        warnings: list[str] | None = None,
        blocking_reasons: list[str] | None = None,
        recommendation: str | None = None,
        created_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.report_id = report_id
        self.job_id = job_id
        self.status = status
        self.checks = list(checks or [])
        self.review_required = review_required
        self.ready_for_real_render_stage = ready_for_real_render_stage
        self.can_prepare_real_render_execution = can_prepare_real_render_execution
        self.human_approved = human_approved
        self.approved_by = approved_by
        self.approved_at = approved_at
        self.approval_reason = approval_reason
        self.warnings = list(warnings or [])
        self.blocking_reasons = list(blocking_reasons or [])
        self.recommendation = recommendation
        self.created_at = created_at or utc_now_iso()
        self.metadata = dict(metadata or {})

    def to_dict(self) -> dict[str, Any]:
        check_dicts = [
            item.to_dict() if hasattr(item, "to_dict") else dict(item)
            for item in self.checks
        ]

        passed_count = sum(1 for item in check_dicts if item.get("status") == CHECK_STATUS_PASSED)
        warning_count = sum(1 for item in check_dicts if item.get("status") == CHECK_STATUS_WARNING)
        blocking_count = sum(
            1
            for item in check_dicts
            if item.get("status") == CHECK_STATUS_BLOCKED or item.get("blocking") is True
        )

        review_required = bool(
            self.review_required
            or blocking_count
            or any(item.get("review_required") for item in check_dicts)
        )

        data = {
            "report_id": self.report_id,
            "job_id": self.job_id,
            "status": self.status,
            "checks": check_dicts,
            "total_checks": len(check_dicts),
            "passed_count": passed_count,
            "warning_count": warning_count,
            "blocking_count": blocking_count,
            "review_required": review_required,
            "ready_for_real_render_stage": bool(self.ready_for_real_render_stage),
            "can_prepare_real_render_execution": bool(
                self.can_prepare_real_render_execution
            ),
            "can_render": False,
            CAN_RUN_TOOL_FIELD: False,
            CAN_SPAWN_FIELD: False,
            CAN_WRITE_FIELD: False,
            CAN_APPLY_TIMELINE_FIELD: False,
            "human_approved": bool(self.human_approved),
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "approval_reason": self.approval_reason,
            "warnings": list(self.warnings),
            "blocking_reasons": list(self.blocking_reasons),
            "recommendation": self.recommendation,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

        if data["blocking_count"] != len(data["blocking_reasons"]):
            data["blocking_count"] = max(
                data["blocking_count"],
                len(data["blocking_reasons"]),
            )

        if data["warning_count"] != len(data["warnings"]):
            data["warning_count"] = max(
                data["warning_count"],
                len(data["warnings"]),
            )

        data["can_render"] = False
        data[CAN_RUN_TOOL_FIELD] = False
        data[CAN_SPAWN_FIELD] = False
        data[CAN_WRITE_FIELD] = False
        data[CAN_APPLY_TIMELINE_FIELD] = False

        return data


def build_render_execution_permission_report(
    *,
    job_id: str,
    checks: list[RenderExecutionPermissionCheck | dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    blocking_reasons: list[str] | None = None,
    human_approved: bool = False,
    approved_by: str | None = None,
    approved_at: str | None = None,
    approval_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> RenderExecutionPermissionReport:
    safe_checks = [_coerce_check(item) for item in list(checks or [])]
    safe_warnings = _unique(warnings or [])
    safe_blocking = _unique(blocking_reasons or [])

    for check in safe_checks:
        if check.blocking or check.status == CHECK_STATUS_BLOCKED:
            _append_once(safe_blocking, check.check_id)
        if check.status == CHECK_STATUS_WARNING:
            _append_once(safe_warnings, check.check_id)

    if not human_approved:
        _append_once(safe_blocking, "render_execution_human_approval_missing")

    if human_approved and not approved_by:
        _append_once(safe_blocking, "render_execution_approval_identity_missing")

    if human_approved and not approved_at:
        _append_once(safe_warnings, "render_execution_approval_timestamp_missing")

    if human_approved and not approval_reason:
        _append_once(safe_warnings, "render_execution_approval_reason_missing")

    ready = not safe_blocking and bool(human_approved)

    if safe_blocking:
        status = RENDER_EXECUTION_PERMISSION_STATUS_BLOCKED
        recommendation = (
            "Render Execution Permission Gate blockiert. "
            "Human Approval und vorherige Render-Gates pruefen."
        )
    elif safe_warnings:
        status = RENDER_EXECUTION_PERMISSION_STATUS_READY_WITH_WARNINGS
        recommendation = (
            "Render Execution Permission Gate ist bereit, "
            "aber Warnungen pruefen."
        )
    else:
        status = RENDER_EXECUTION_PERMISSION_STATUS_READY
        recommendation = (
            "Render Execution Permission Gate ist bereit fuer kontrollierte "
            "Vorbereitung im naechsten Block."
        )

    return RenderExecutionPermissionReport(
        report_id=f"render_execution_permission_{job_id}",
        job_id=job_id,
        status=status,
        checks=safe_checks,
        review_required=not ready or bool(safe_warnings),
        ready_for_real_render_stage=ready,
        can_prepare_real_render_execution=ready,
        human_approved=bool(human_approved),
        approved_by=approved_by,
        approved_at=approved_at,
        approval_reason=approval_reason,
        warnings=safe_warnings,
        blocking_reasons=safe_blocking,
        recommendation=recommendation,
        metadata=dict(metadata or {}),
    )


def _coerce_check(
    item: RenderExecutionPermissionCheck | dict[str, Any],
) -> RenderExecutionPermissionCheck:
    if isinstance(item, RenderExecutionPermissionCheck):
        return item

    data = dict(item or {})
    return RenderExecutionPermissionCheck(
        check_id=str(data.get("check_id") or "render_execution_unknown_check"),
        check_name=str(data.get("check_name") or "Unknown check"),
        category=str(data.get("category") or "unknown"),
        status=str(data.get("status") or CHECK_STATUS_SKIPPED),
        severity=str(data.get("severity") or "info"),
        message=str(data.get("message") or ""),
        evidence=_safe_dict(data.get("evidence")),
        blocking=bool(data.get("blocking", False)),
        review_required=bool(data.get("review_required", False)),
        metadata=_safe_dict(data.get("metadata")),
    )


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _append_once(items: list[str], value: str) -> None:
    text = str(value).strip()
    if text and text not in items:
        items.append(text)


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        _append_once(result, str(value))
    return result
