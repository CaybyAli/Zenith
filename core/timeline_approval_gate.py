from __future__ import annotations

from typing import Any

from models.review_timeline_plan import REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW
from models.timeline_approval_gate import (
    TIMELINE_APPROVAL_GATE_STATUS_APPROVED,
    TIMELINE_APPROVAL_GATE_STATUS_BLOCKED,
    TIMELINE_APPROVAL_GATE_STATUS_FAILED,
    TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
    TIMELINE_APPROVAL_REASON_CENSOR_REQUIRED,
    TIMELINE_APPROVAL_REASON_CONTINUITY_BLOCKED,
    TIMELINE_APPROVAL_REASON_MISSING_REVIEW_TIMELINE_PLAN,
    TIMELINE_APPROVAL_REASON_NEEDS_MANUAL_CHANGES,
    TIMELINE_APPROVAL_REASON_PENDING_HUMAN_REVIEW,
    TIMELINE_APPROVAL_REASON_REJECTED_BY_REVIEW,
    TIMELINE_APPROVAL_STATUS_APPROVED,
    TIMELINE_APPROVAL_STATUS_BLOCKED,
    TIMELINE_APPROVAL_STATUS_FAILED,
    TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES,
    TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
    TIMELINE_APPROVAL_STATUS_REJECTED,
    TimelineApprovalGate,
    utc_now_iso,
)


_ALLOWED_APPROVAL_STATUSES = {
    TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
    TIMELINE_APPROVAL_STATUS_APPROVED,
    TIMELINE_APPROVAL_STATUS_REJECTED,
    TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES,
    TIMELINE_APPROVAL_STATUS_BLOCKED,
    TIMELINE_APPROVAL_STATUS_FAILED,
}


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


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_list(value: Any) -> list[str]:
    if not value:
        return []

    if isinstance(value, list):
        return [str(item) for item in value]

    if isinstance(value, tuple):
        return [str(item) for item in value]

    return [str(value)]


def _normal_approval_status(value: str | None) -> str:
    status = str(value or TIMELINE_APPROVAL_STATUS_PENDING_REVIEW).strip().lower()

    if status not in _ALLOWED_APPROVAL_STATUSES:
        return TIMELINE_APPROVAL_STATUS_PENDING_REVIEW

    return status


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def build_timeline_approval_gate(
    review_timeline_plan: Any | None = None,
    job_id: str | None = None,
    approval_status: str | None = None,
    approved_by: str | None = None,
    rejected_by: str | None = None,
    manual_change_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> TimelineApprovalGate:
    plan_data = _object_to_dict(review_timeline_plan)
    requested_status = _normal_approval_status(approval_status)

    gate = TimelineApprovalGate(
        job_id=job_id,
        approval_status=TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
        gate_status=TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
        can_proceed_to_execution=False,
        can_render=False,
        requires_human_approval=True,
        approved_by=None,
        approved_at=None,
        rejected_by=None,
        rejected_at=None,
        manual_change_reason=manual_change_reason,
        metadata={
            **dict(metadata or {}),
            "review_only": True,
            "approval_gate_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_33": True,
        },
    )

    if not plan_data:
        gate.approval_status = TIMELINE_APPROVAL_STATUS_BLOCKED
        gate.gate_status = TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
        _append_unique(
            gate.blocking_reasons,
            TIMELINE_APPROVAL_REASON_MISSING_REVIEW_TIMELINE_PLAN,
        )
        return gate

    gate.source_review_timeline_plan_id = plan_data.get("plan_id")
    gate.source_review_timeline_plan_status = str(
        plan_data.get("status") or REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW
    )

    gate.total_items = _safe_int(plan_data.get("total_items"), 0)
    gate.review_required_count = _safe_int(plan_data.get("review_required_count"), 0)
    gate.protected_count = _safe_int(plan_data.get("protected_count"), 0)
    gate.censor_required_count = _safe_int(plan_data.get("censor_required_count"), 0)
    gate.continuity_blocked_count = _safe_int(
        plan_data.get("continuity_blocked_count"),
        0,
    )

    gate.warnings.extend(_safe_list(plan_data.get("warnings")))
    gate.safety_flags.extend(_safe_list(plan_data.get("safety_flags")))

    if gate.protected_count > 0:
        _append_unique(gate.safety_flags, "protected_items_must_stay_preserved")

    if gate.continuity_blocked_count > 0:
        gate.approval_status = TIMELINE_APPROVAL_STATUS_BLOCKED
        gate.gate_status = TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
        _append_unique(gate.blocking_reasons, TIMELINE_APPROVAL_REASON_CONTINUITY_BLOCKED)
        return gate

    if requested_status == TIMELINE_APPROVAL_STATUS_REJECTED:
        gate.approval_status = TIMELINE_APPROVAL_STATUS_REJECTED
        gate.gate_status = TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
        gate.rejected_by = rejected_by
        gate.rejected_at = utc_now_iso()
        _append_unique(gate.blocking_reasons, TIMELINE_APPROVAL_REASON_REJECTED_BY_REVIEW)
        return gate

    if requested_status == TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES:
        gate.approval_status = TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES
        gate.gate_status = TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
        _append_unique(gate.blocking_reasons, TIMELINE_APPROVAL_REASON_NEEDS_MANUAL_CHANGES)
        return gate

    if requested_status == TIMELINE_APPROVAL_STATUS_BLOCKED:
        gate.approval_status = TIMELINE_APPROVAL_STATUS_BLOCKED
        gate.gate_status = TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
        _append_unique(gate.blocking_reasons, TIMELINE_APPROVAL_REASON_PENDING_HUMAN_REVIEW)
        return gate

    if requested_status == TIMELINE_APPROVAL_STATUS_FAILED:
        gate.approval_status = TIMELINE_APPROVAL_STATUS_FAILED
        gate.gate_status = TIMELINE_APPROVAL_GATE_STATUS_FAILED
        _append_unique(gate.blocking_reasons, TIMELINE_APPROVAL_STATUS_FAILED)
        return gate

    if gate.censor_required_count > 0:
        gate.approval_status = TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES
        gate.gate_status = TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
        _append_unique(gate.blocking_reasons, TIMELINE_APPROVAL_REASON_CENSOR_REQUIRED)
        _append_unique(gate.safety_flags, "censor_requires_later_human_approval")
        return gate

    if requested_status == TIMELINE_APPROVAL_STATUS_APPROVED:
        gate.approval_status = TIMELINE_APPROVAL_STATUS_APPROVED
        gate.gate_status = TIMELINE_APPROVAL_GATE_STATUS_APPROVED
        gate.can_proceed_to_execution = True
        gate.can_render = False
        gate.requires_human_approval = False
        gate.approved_by = approved_by
        gate.approved_at = utc_now_iso()
        gate.metadata["future_allowed_after_approval"] = True
        gate.metadata["can_render_in_2b_33"] = False
        return gate

    gate.approval_status = TIMELINE_APPROVAL_STATUS_PENDING_REVIEW
    gate.gate_status = TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW
    gate.can_proceed_to_execution = False
    gate.can_render = False
    gate.requires_human_approval = True
    _append_unique(gate.blocking_reasons, TIMELINE_APPROVAL_REASON_PENDING_HUMAN_REVIEW)
    return gate
