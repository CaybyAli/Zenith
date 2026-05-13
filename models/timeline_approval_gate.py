from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


TIMELINE_APPROVAL_STATUS_PENDING_REVIEW = "pending_review"
TIMELINE_APPROVAL_STATUS_APPROVED = "approved"
TIMELINE_APPROVAL_STATUS_REJECTED = "rejected"
TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES = "needs_manual_changes"
TIMELINE_APPROVAL_STATUS_BLOCKED = "blocked"
TIMELINE_APPROVAL_STATUS_FAILED = "failed"

TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW = "pending_review"
TIMELINE_APPROVAL_GATE_STATUS_APPROVED = "approved"
TIMELINE_APPROVAL_GATE_STATUS_BLOCKED = "blocked"
TIMELINE_APPROVAL_GATE_STATUS_FAILED = "failed"

TIMELINE_APPROVAL_REASON_MISSING_REVIEW_TIMELINE_PLAN = "missing_review_timeline_plan"
TIMELINE_APPROVAL_REASON_PENDING_HUMAN_REVIEW = "pending_human_review"
TIMELINE_APPROVAL_REASON_REJECTED_BY_REVIEW = "rejected_by_review"
TIMELINE_APPROVAL_REASON_NEEDS_MANUAL_CHANGES = "needs_manual_changes"
TIMELINE_APPROVAL_REASON_CONTINUITY_BLOCKED = (
    "continuity_blocked_items_require_manual_review"
)
TIMELINE_APPROVAL_REASON_CENSOR_REQUIRED = "censor_required_items_require_review"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_timeline_approval_gate_id() -> str:
    return f"timeline_approval_gate_{uuid.uuid4().hex[:12]}"


@dataclass
class TimelineApprovalGate:
    approval_gate_id: str = field(default_factory=new_timeline_approval_gate_id)
    job_id: str | None = None

    source_review_timeline_plan_id: str | None = None
    source_review_timeline_plan_status: str | None = None

    approval_status: str = TIMELINE_APPROVAL_STATUS_PENDING_REVIEW
    gate_status: str = TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW

    can_proceed_to_execution: bool = False
    can_render: bool = False
    requires_human_approval: bool = True

    total_items: int = 0
    review_required_count: int = 0
    protected_count: int = 0
    censor_required_count: int = 0
    continuity_blocked_count: int = 0

    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    safety_flags: list[str] = field(default_factory=list)

    approved_by: str | None = None
    approved_at: str | None = None

    rejected_by: str | None = None
    rejected_at: str | None = None

    manual_change_reason: str | None = None

    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_gate_id": self.approval_gate_id,
            "job_id": self.job_id,
            "source_review_timeline_plan_id": self.source_review_timeline_plan_id,
            "source_review_timeline_plan_status": self.source_review_timeline_plan_status,
            "approval_status": self.approval_status,
            "gate_status": self.gate_status,
            "can_proceed_to_execution": self.can_proceed_to_execution,
            "can_render": self.can_render,
            "requires_human_approval": self.requires_human_approval,
            "total_items": self.total_items,
            "review_required_count": self.review_required_count,
            "protected_count": self.protected_count,
            "censor_required_count": self.censor_required_count,
            "continuity_blocked_count": self.continuity_blocked_count,
            "blocking_reasons": list(self.blocking_reasons or []),
            "warnings": list(self.warnings or []),
            "safety_flags": list(self.safety_flags or []),
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "rejected_by": self.rejected_by,
            "rejected_at": self.rejected_at,
            "manual_change_reason": self.manual_change_reason,
            "created_at": self.created_at,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TimelineApprovalGate":
        data = data or {}

        return cls(
            approval_gate_id=str(
                data.get("approval_gate_id") or new_timeline_approval_gate_id()
            ),
            job_id=data.get("job_id"),
            source_review_timeline_plan_id=data.get("source_review_timeline_plan_id"),
            source_review_timeline_plan_status=data.get(
                "source_review_timeline_plan_status"
            ),
            approval_status=str(
                data.get("approval_status")
                or TIMELINE_APPROVAL_STATUS_PENDING_REVIEW
            ),
            gate_status=str(
                data.get("gate_status")
                or TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW
            ),
            can_proceed_to_execution=bool(
                data.get("can_proceed_to_execution", False)
            ),
            can_render=bool(data.get("can_render", False)),
            requires_human_approval=bool(
                data.get("requires_human_approval", True)
            ),
            total_items=int(data.get("total_items", 0) or 0),
            review_required_count=int(data.get("review_required_count", 0) or 0),
            protected_count=int(data.get("protected_count", 0) or 0),
            censor_required_count=int(data.get("censor_required_count", 0) or 0),
            continuity_blocked_count=int(
                data.get("continuity_blocked_count", 0) or 0
            ),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            warnings=list(data.get("warnings") or []),
            safety_flags=list(data.get("safety_flags") or []),
            approved_by=data.get("approved_by"),
            approved_at=data.get("approved_at"),
            rejected_by=data.get("rejected_by"),
            rejected_at=data.get("rejected_at"),
            manual_change_reason=data.get("manual_change_reason"),
            created_at=str(data.get("created_at") or utc_now_iso()),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class TimelineApprovalGateRunReport:
    status: str = TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW
    source: str = "timeline_approval_gate"

    timeline_approval_gate: TimelineApprovalGate | None = None

    approval_status: str = TIMELINE_APPROVAL_STATUS_PENDING_REVIEW
    gate_status: str = TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW

    can_proceed_to_execution: bool = False
    can_render: bool = False
    requires_human_approval: bool = True

    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "timeline_approval_gate": (
                self.timeline_approval_gate.to_dict()
                if self.timeline_approval_gate is not None
                else None
            ),
            "approval_status": self.approval_status,
            "gate_status": self.gate_status,
            "can_proceed_to_execution": self.can_proceed_to_execution,
            "can_render": self.can_render,
            "requires_human_approval": self.requires_human_approval,
            "blocking_reasons": list(self.blocking_reasons or []),
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "TimelineApprovalGateRunReport":
        data = data or {}

        gate_data = data.get("timeline_approval_gate")
        gate = (
            TimelineApprovalGate.from_dict(gate_data)
            if isinstance(gate_data, dict)
            else None
        )

        return cls(
            status=str(
                data.get("status")
                or TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW
            ),
            source=str(data.get("source") or "timeline_approval_gate"),
            timeline_approval_gate=gate,
            approval_status=str(
                data.get("approval_status")
                or TIMELINE_APPROVAL_STATUS_PENDING_REVIEW
            ),
            gate_status=str(
                data.get("gate_status")
                or TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW
            ),
            can_proceed_to_execution=bool(
                data.get("can_proceed_to_execution", False)
            ),
            can_render=bool(data.get("can_render", False)),
            requires_human_approval=bool(
                data.get("requires_human_approval", True)
            ),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        
        )
