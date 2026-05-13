from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW = "pending_review"
REVIEW_TIMELINE_PLAN_STATUS_SKIPPED_NO_FINAL_ITEMS = "skipped_no_final_items"
REVIEW_TIMELINE_PLAN_STATUS_FAILED = "failed"

REVIEW_TIMELINE_ACTION_KEEP_REVIEW = "keep_review"
REVIEW_TIMELINE_ACTION_TRIM_REVIEW = "trim_review"
REVIEW_TIMELINE_ACTION_REMOVE_REVIEW = "remove_review"
REVIEW_TIMELINE_ACTION_PROTECT = "protect"
REVIEW_TIMELINE_ACTION_CENSOR_KEEP = "censor_keep"
REVIEW_TIMELINE_ACTION_TECHNICAL_REVIEW = "technical_review"
REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY = "blocked_by_continuity"
REVIEW_TIMELINE_ACTION_UNKNOWN_REVIEW = "unknown_review"

REVIEW_TIMELINE_PROTECTION_NORMAL = "normal"
REVIEW_TIMELINE_PROTECTION_PROTECTED = "protected"
REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED = "censor_protected"
REVIEW_TIMELINE_PROTECTION_CONTINUITY_BLOCKED = "continuity_blocked"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_review_timeline_plan_id() -> str:
    return f"review_timeline_plan_{uuid.uuid4().hex[:12]}"


@dataclass
class ReviewTimelineItem:
    timeline_item_id: str
    source_segment_id: str | None = None

    start_seconds: float | None = None
    end_seconds: float | None = None

    source_start_seconds: float | None = None
    source_end_seconds: float | None = None
    duration_seconds: float = 0.0

    action: str = REVIEW_TIMELINE_ACTION_UNKNOWN_REVIEW
    final_decision: str = ""

    protection_status: str = REVIEW_TIMELINE_PROTECTION_NORMAL
    censor_sfx_required: bool = False
    continuity_blocked: bool = False

    review_required: bool = True
    review_reason: str = ""

    safety_flags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timeline_item_id": self.timeline_item_id,
            "source_segment_id": self.source_segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "source_start_seconds": self.source_start_seconds,
            "source_end_seconds": self.source_end_seconds,
            "duration_seconds": self.duration_seconds,
            "action": self.action,
            "final_decision": self.final_decision,
            "protection_status": self.protection_status,
            "censor_sfx_required": self.censor_sfx_required,
            "continuity_blocked": self.continuity_blocked,
            "review_required": self.review_required,
            "review_reason": self.review_reason,
            "safety_flags": list(self.safety_flags or []),
            "notes": list(self.notes or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ReviewTimelineItem":
        data = data or {}

        return cls(
            timeline_item_id=str(data.get("timeline_item_id") or ""),
            source_segment_id=data.get("source_segment_id"),
            start_seconds=data.get("start_seconds"),
            end_seconds=data.get("end_seconds"),
            source_start_seconds=data.get("source_start_seconds"),
            source_end_seconds=data.get("source_end_seconds"),
            duration_seconds=float(data.get("duration_seconds", 0.0) or 0.0),
            action=str(data.get("action") or REVIEW_TIMELINE_ACTION_UNKNOWN_REVIEW),
            final_decision=str(data.get("final_decision") or ""),
            protection_status=str(
                data.get("protection_status") or REVIEW_TIMELINE_PROTECTION_NORMAL
            ),
            censor_sfx_required=bool(data.get("censor_sfx_required", False)),
            continuity_blocked=bool(data.get("continuity_blocked", False)),
            review_required=bool(data.get("review_required", True)),
            review_reason=str(data.get("review_reason") or ""),
            safety_flags=list(data.get("safety_flags") or []),
            notes=list(data.get("notes") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class ReviewTimelinePlan:
    plan_id: str = field(default_factory=new_review_timeline_plan_id)
    job_id: str | None = None

    source_cut_list_id: str | None = None
    source_finalizer_run_id: str | None = None

    items: list[ReviewTimelineItem] = field(default_factory=list)

    total_items: int = 0
    total_duration_seconds: float = 0.0

    review_required_count: int = 0
    protected_count: int = 0
    censor_required_count: int = 0
    continuity_blocked_count: int = 0

    status: str = REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW
    recommendation: str = "review_timeline_plan_pending_review"

    created_at: str = field(default_factory=utc_now_iso)

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.total_items = len(self.items)
        self.total_duration_seconds = round(
            sum(float(item.duration_seconds or 0.0) for item in self.items),
            3,
        )
        self.review_required_count = sum(1 for item in self.items if item.review_required)
        self.protected_count = sum(
            1
            for item in self.items
            if item.protection_status
            in {
                REVIEW_TIMELINE_PROTECTION_PROTECTED,
                REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED,
            }
        )
        self.censor_required_count = sum(
            1 for item in self.items if item.censor_sfx_required
        )
        self.continuity_blocked_count = sum(
            1 for item in self.items if item.continuity_blocked
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()

        return {
            "plan_id": self.plan_id,
            "job_id": self.job_id,
            "source_cut_list_id": self.source_cut_list_id,
            "source_finalizer_run_id": self.source_finalizer_run_id,
            "items": [item.to_dict() for item in self.items],
            "total_items": self.total_items,
            "total_duration_seconds": self.total_duration_seconds,
            "review_required_count": self.review_required_count,
            "protected_count": self.protected_count,
            "censor_required_count": self.censor_required_count,
            "continuity_blocked_count": self.continuity_blocked_count,
            "status": self.status,
            "recommendation": self.recommendation,
            "created_at": self.created_at,
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ReviewTimelinePlan":
        data = data or {}

        plan = cls(
            plan_id=str(data.get("plan_id") or new_review_timeline_plan_id()),
            job_id=data.get("job_id"),
            source_cut_list_id=data.get("source_cut_list_id"),
            source_finalizer_run_id=data.get("source_finalizer_run_id"),
            items=[
                ReviewTimelineItem.from_dict(item)
                for item in data.get("items", []) or []
                if isinstance(item, dict)
            ],
            status=str(
                data.get("status") or REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW
            ),
            recommendation=str(
                data.get("recommendation") or "review_timeline_plan_pending_review"
            ),
            created_at=str(data.get("created_at") or utc_now_iso()),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
        plan.refresh_counts()
        return plan


@dataclass
class ReviewTimelinePlanRunReport:
    status: str = REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW
    source: str = "review_timeline_plan_builder"

    review_timeline_plan: ReviewTimelinePlan | None = None
    items: list[ReviewTimelineItem] = field(default_factory=list)

    total_items: int = 0
    total_duration_seconds: float = 0.0
    review_required_count: int = 0
    protected_count: int = 0
    censor_required_count: int = 0
    continuity_blocked_count: int = 0

    recommendation: str = "review_timeline_plan_pending_review"

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "review_timeline_plan": (
                self.review_timeline_plan.to_dict()
                if self.review_timeline_plan is not None
                else None
            ),
            "items": [item.to_dict() for item in self.items],
            "total_items": self.total_items,
            "total_duration_seconds": self.total_duration_seconds,
            "review_required_count": self.review_required_count,
            "protected_count": self.protected_count,
            "censor_required_count": self.censor_required_count,
            "continuity_blocked_count": self.continuity_blocked_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ReviewTimelinePlanRunReport":
        data = data or {}

        plan_data = data.get("review_timeline_plan")
        plan = (
            ReviewTimelinePlan.from_dict(plan_data)
            if isinstance(plan_data, dict)
            else None
        )

        items = [
            ReviewTimelineItem.from_dict(item)
            for item in data.get("items", []) or []
            if isinstance(item, dict)
        ]

        if not items and plan is not None:
            items = list(plan.items)

        return cls(
            status=str(
                data.get("status") or REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW
            ),
            source=str(data.get("source") or "review_timeline_plan_builder"),
            review_timeline_plan=plan,
            items=items,
            total_items=int(data.get("total_items", len(items)) or 0),
            total_duration_seconds=float(
                data.get("total_duration_seconds", 0.0) or 0.0
            ),
            review_required_count=int(data.get("review_required_count", 0) or 0),
            protected_count=int(data.get("protected_count", 0) or 0),
            censor_required_count=int(data.get("censor_required_count", 0) or 0),
            continuity_blocked_count=int(
                data.get("continuity_blocked_count", 0) or 0
            ),
            recommendation=str(
                data.get("recommendation")
                or "review_timeline_plan_pending_review"
            ),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
