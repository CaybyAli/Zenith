from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY = "ready_for_dashboard"
REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY_WITH_WARNINGS = (
    "ready_with_warnings"
)
REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED = "blocked"
REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED = "failed"

REVIEW_TIMELINE_DASHBOARD_ACTION_REVIEW_TIMELINE = "review_timeline"
REVIEW_TIMELINE_DASHBOARD_ACTION_APPROVE_TIMELINE = "approve_timeline"
REVIEW_TIMELINE_DASHBOARD_ACTION_REQUEST_CHANGES = "request_changes"
REVIEW_TIMELINE_DASHBOARD_ACTION_REJECT_TIMELINE = "reject_timeline"

REVIEW_TIMELINE_DASHBOARD_SEVERITY_LOW = "low"
REVIEW_TIMELINE_DASHBOARD_SEVERITY_MEDIUM = "medium"
REVIEW_TIMELINE_DASHBOARD_SEVERITY_HIGH = "high"
REVIEW_TIMELINE_DASHBOARD_SEVERITY_BLOCKING = "blocking"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_review_timeline_dashboard_package_id() -> str:
    return f"review_timeline_dashboard_package_{uuid.uuid4().hex[:12]}"


@dataclass
class ReviewTimelineDashboardItemCard:
    item_id: str
    source_segment_id: str | None = None

    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float | None = None

    source_start_seconds: float | None = None
    source_end_seconds: float | None = None

    action: str = ""
    label: str = ""
    badge: str = ""
    severity: str = REVIEW_TIMELINE_DASHBOARD_SEVERITY_LOW

    final_decision: str = ""
    protection_status: str = ""

    review_required: bool = True
    protected: bool = False
    censor_sfx_required: bool = False
    continuity_blocked: bool = False

    safety_status: str = "unknown"
    warnings: list[str] = field(default_factory=list)
    blocking_errors: list[str] = field(default_factory=list)

    safety_flags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_segment_id": self.source_segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "source_start_seconds": self.source_start_seconds,
            "source_end_seconds": self.source_end_seconds,
            "action": self.action,
            "label": self.label,
            "badge": self.badge,
            "severity": self.severity,
            "final_decision": self.final_decision,
            "protection_status": self.protection_status,
            "review_required": self.review_required,
            "protected": self.protected,
            "censor_sfx_required": self.censor_sfx_required,
            "continuity_blocked": self.continuity_blocked,
            "safety_status": self.safety_status,
            "warnings": list(self.warnings or []),
            "blocking_errors": list(self.blocking_errors or []),
            "safety_flags": list(self.safety_flags or []),
            "notes": list(self.notes or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ReviewTimelineDashboardItemCard":
        data = data or {}

        return cls(
            item_id=str(data.get("item_id") or ""),
            source_segment_id=data.get("source_segment_id"),
            start_seconds=data.get("start_seconds"),
            end_seconds=data.get("end_seconds"),
            duration_seconds=data.get("duration_seconds"),
            source_start_seconds=data.get("source_start_seconds"),
            source_end_seconds=data.get("source_end_seconds"),
            action=str(data.get("action") or ""),
            label=str(data.get("label") or ""),
            badge=str(data.get("badge") or ""),
            severity=str(
                data.get("severity") or REVIEW_TIMELINE_DASHBOARD_SEVERITY_LOW
            ),
            final_decision=str(data.get("final_decision") or ""),
            protection_status=str(data.get("protection_status") or ""),
            review_required=bool(data.get("review_required", True)),
            protected=bool(data.get("protected", False)),
            censor_sfx_required=bool(data.get("censor_sfx_required", False)),
            continuity_blocked=bool(data.get("continuity_blocked", False)),
            safety_status=str(data.get("safety_status") or "unknown"),
            warnings=list(data.get("warnings") or []),
            blocking_errors=list(data.get("blocking_errors") or []),
            safety_flags=list(data.get("safety_flags") or []),
            notes=list(data.get("notes") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class ReviewTimelineDashboardPackage:
    dashboard_package_id: str = field(
        default_factory=new_review_timeline_dashboard_package_id
    )
    job_id: str | None = None

    package_status: str = REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED

    source_review_timeline_plan_id: str | None = None
    source_timeline_approval_gate_id: str | None = None
    source_timeline_safety_validation_id: str | None = None

    review_status: str = "pending_review"
    approval_status: str = "pending_review"
    safety_status: str = "unknown"

    can_proceed_to_execution: bool = False
    can_render: bool = False

    is_safe_for_future_execution: bool = False
    is_safe_for_render: bool = False

    requires_manual_review: bool = True

    summary: dict[str, Any] = field(default_factory=dict)
    counters: dict[str, Any] = field(default_factory=dict)

    timeline_items: list[dict[str, Any]] = field(default_factory=list)
    item_cards: list[ReviewTimelineDashboardItemCard] = field(default_factory=list)

    approval_panel: dict[str, Any] = field(default_factory=dict)
    safety_panel: dict[str, Any] = field(default_factory=dict)

    warnings: list[str] = field(default_factory=list)
    blocking_errors: list[str] = field(default_factory=list)

    dashboard_actions: list[str] = field(default_factory=list)

    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_dashboard_only_safety(self) -> None:
        self.can_render = False
        self.is_safe_for_render = False

        self.metadata.update(
            {
                "dashboard_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_35": True,
                "no_render_in_2b_35": True,
                "can_render_forced_false_by_2b_35": True,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_dashboard_only_safety()

        return {
            "dashboard_package_id": self.dashboard_package_id,
            "job_id": self.job_id,
            "package_status": self.package_status,
            "source_review_timeline_plan_id": self.source_review_timeline_plan_id,
            "source_timeline_approval_gate_id": (
                self.source_timeline_approval_gate_id
            ),
            "source_timeline_safety_validation_id": (
                self.source_timeline_safety_validation_id
            ),
            "review_status": self.review_status,
            "approval_status": self.approval_status,
            "safety_status": self.safety_status,
            "can_proceed_to_execution": self.can_proceed_to_execution,
            "can_render": self.can_render,
            "is_safe_for_future_execution": self.is_safe_for_future_execution,
            "is_safe_for_render": self.is_safe_for_render,
            "requires_manual_review": self.requires_manual_review,
            "summary": dict(self.summary or {}),
            "counters": dict(self.counters or {}),
            "timeline_items": [dict(item or {}) for item in self.timeline_items],
            "item_cards": [
                item_card.to_dict()
                for item_card in list(self.item_cards or [])
            ],
            "approval_panel": dict(self.approval_panel or {}),
            "safety_panel": dict(self.safety_panel or {}),
            "warnings": list(self.warnings or []),
            "blocking_errors": list(self.blocking_errors or []),
            "dashboard_actions": list(self.dashboard_actions or []),
            "created_at": self.created_at,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ReviewTimelineDashboardPackage":
        data = data or {}

        raw_item_cards = data.get("item_cards") or []
        item_cards = [
            ReviewTimelineDashboardItemCard.from_dict(item)
            for item in raw_item_cards
            if isinstance(item, dict)
        ]

        package = cls(
            dashboard_package_id=str(
                data.get("dashboard_package_id")
                or new_review_timeline_dashboard_package_id()
            ),
            job_id=data.get("job_id"),
            package_status=str(
                data.get("package_status")
                or REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED
            ),
            source_review_timeline_plan_id=data.get(
                "source_review_timeline_plan_id"
            ),
            source_timeline_approval_gate_id=data.get(
                "source_timeline_approval_gate_id"
            ),
            source_timeline_safety_validation_id=data.get(
                "source_timeline_safety_validation_id"
            ),
            review_status=str(data.get("review_status") or "pending_review"),
            approval_status=str(
                data.get("approval_status") or "pending_review"
            ),
            safety_status=str(data.get("safety_status") or "unknown"),
            can_proceed_to_execution=bool(
                data.get("can_proceed_to_execution", False)
            ),
            can_render=bool(data.get("can_render", False)),
            is_safe_for_future_execution=bool(
                data.get("is_safe_for_future_execution", False)
            ),
            is_safe_for_render=bool(data.get("is_safe_for_render", False)),
            requires_manual_review=bool(
                data.get("requires_manual_review", True)
            ),
            summary=dict(data.get("summary") or {}),
            counters=dict(data.get("counters") or {}),
            timeline_items=[
                dict(item or {})
                for item in data.get("timeline_items", []) or []
                if isinstance(item, dict)
            ],
            item_cards=item_cards,
            approval_panel=dict(data.get("approval_panel") or {}),
            safety_panel=dict(data.get("safety_panel") or {}),
            warnings=list(data.get("warnings") or []),
            blocking_errors=list(data.get("blocking_errors") or []),
            dashboard_actions=list(data.get("dashboard_actions") or []),
            created_at=str(data.get("created_at") or utc_now_iso()),
            metadata=dict(data.get("metadata") or {}),
        )

        package.enforce_dashboard_only_safety()
        return package


@dataclass
class ReviewTimelineDashboardPackageRunReport:
    status: str = REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED
    source: str = "review_timeline_dashboard_package_builder"

    dashboard_package: ReviewTimelineDashboardPackage | None = None

    review_status: str = "pending_review"
    approval_status: str = "pending_review"
    safety_status: str = "unknown"

    can_proceed_to_execution: bool = False
    can_render: bool = False

    requires_manual_review: bool = True

    warnings: list[str] = field(default_factory=list)
    blocking_errors: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        self.can_render = False

        return {
            "status": self.status,
            "source": self.source,
            "dashboard_package": (
                self.dashboard_package.to_dict()
                if self.dashboard_package is not None
                else None
            ),
            "review_status": self.review_status,
            "approval_status": self.approval_status,
            "safety_status": self.safety_status,
            "can_proceed_to_execution": self.can_proceed_to_execution,
            "can_render": self.can_render,
            "requires_manual_review": self.requires_manual_review,
            "warnings": list(self.warnings or []),
            "blocking_errors": list(self.blocking_errors or []),
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ReviewTimelineDashboardPackageRunReport":
        data = data or {}

        package_data = data.get("dashboard_package")
        dashboard_package = (
            ReviewTimelineDashboardPackage.from_dict(package_data)
            if isinstance(package_data, dict)
            else None
        )

        return cls(
            status=str(
                data.get("status")
                or REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED
            ),
            source=str(
                data.get("source")
                or "review_timeline_dashboard_package_builder"
            ),
            dashboard_package=dashboard_package,
            review_status=str(data.get("review_status") or "pending_review"),
            approval_status=str(
                data.get("approval_status") or "pending_review"
            ),
            safety_status=str(data.get("safety_status") or "unknown"),
            can_proceed_to_execution=bool(
                data.get("can_proceed_to_execution", False)
            ),
            can_render=False,
            requires_manual_review=bool(
                data.get("requires_manual_review", True)
            ),
            warnings=list(data.get("warnings") or []),
            blocking_errors=list(data.get("blocking_errors") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )