from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


TIMELINE_SAFETY_STATUS_PASSED = "passed"
TIMELINE_SAFETY_STATUS_PASSED_WITH_WARNINGS = "passed_with_warnings"
TIMELINE_SAFETY_STATUS_BLOCKED = "blocked"
TIMELINE_SAFETY_STATUS_FAILED = "failed"

TIMELINE_SAFETY_REASON_MISSING_REVIEW_TIMELINE_PLAN = (
    "missing_review_timeline_plan"
)
TIMELINE_SAFETY_REASON_MISSING_REVIEW_TIMELINE_ITEMS = (
    "missing_review_timeline_items"
)
TIMELINE_SAFETY_REASON_NEGATIVE_START_TIME = "negative_start_time"
TIMELINE_SAFETY_REASON_NEGATIVE_END_TIME = "negative_end_time"
TIMELINE_SAFETY_REASON_END_BEFORE_START = "end_before_start"
TIMELINE_SAFETY_REASON_ZERO_OR_NEGATIVE_DURATION = (
    "zero_or_negative_duration"
)
TIMELINE_SAFETY_REASON_TIMELINE_OVERLAP = "timeline_overlap"
TIMELINE_SAFETY_REASON_TIMELINE_GAP = "timeline_gap"
TIMELINE_SAFETY_REASON_INVALID_SOURCE_TIMING = "invalid_source_timing"
TIMELINE_SAFETY_REASON_PROTECTED_ITEM_HAS_UNSAFE_ACTION = (
    "protected_item_has_unsafe_action"
)
TIMELINE_SAFETY_REASON_CENSOR_ITEM_NOT_PROTECTED = (
    "censor_item_not_protected"
)
TIMELINE_SAFETY_REASON_CONTINUITY_BLOCK_NOT_PRESERVED = (
    "continuity_block_not_preserved"
)
TIMELINE_SAFETY_REASON_REMOVE_REVIEW_WITHOUT_HUMAN_REVIEW_SAFETY = (
    "remove_review_without_human_review_safety"
)
TIMELINE_SAFETY_REASON_TRIM_REVIEW_WITHOUT_HUMAN_REVIEW_SAFETY = (
    "trim_review_without_human_review_safety"
)
TIMELINE_SAFETY_REASON_APPROVAL_OVERRIDDEN_BY_SAFETY_VALIDATOR = (
    "approval_overridden_by_safety_validator"
)
TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34 = (
    "render_not_allowed_in_2b_34"
)
TIMELINE_SAFETY_REASON_EXECUTION_NOT_SAFE = "execution_not_safe"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_timeline_safety_validation_id() -> str:
    return f"timeline_safety_validation_{uuid.uuid4().hex[:12]}"


@dataclass
class TimelineSafetyItemResult:
    item_index: int = 0
    item_id: str | None = None

    action: str | None = None
    protection_status: str | None = None

    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float | None = None

    source_start_seconds: float | None = None
    source_end_seconds: float | None = None

    is_valid: bool = True
    blocking_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_index": self.item_index,
            "item_id": self.item_id,
            "action": self.action,
            "protection_status": self.protection_status,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "source_start_seconds": self.source_start_seconds,
            "source_end_seconds": self.source_end_seconds,
            "is_valid": self.is_valid,
            "blocking_errors": list(self.blocking_errors or []),
            "warnings": list(self.warnings or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "TimelineSafetyItemResult":
        data = data or {}

        return cls(
            item_index=int(data.get("item_index", 0) or 0),
            item_id=data.get("item_id"),
            action=data.get("action"),
            protection_status=data.get("protection_status"),
            start_seconds=data.get("start_seconds"),
            end_seconds=data.get("end_seconds"),
            duration_seconds=data.get("duration_seconds"),
            source_start_seconds=data.get("source_start_seconds"),
            source_end_seconds=data.get("source_end_seconds"),
            is_valid=bool(data.get("is_valid", True)),
            blocking_errors=list(data.get("blocking_errors") or []),
            warnings=list(data.get("warnings") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class TimelineSafetyValidation:
    safety_validation_id: str = field(
        default_factory=new_timeline_safety_validation_id
    )
    job_id: str | None = None

    source_review_timeline_plan_id: str | None = None
    source_timeline_approval_gate_id: str | None = None

    validation_status: str = TIMELINE_SAFETY_STATUS_BLOCKED

    is_safe_for_future_execution: bool = False
    is_safe_for_render: bool = False
    requires_manual_review: bool = True

    blocking_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    item_results: list[TimelineSafetyItemResult] = field(default_factory=list)

    total_items_checked: int = 0

    invalid_timing_count: int = 0
    overlap_count: int = 0
    gap_count: int = 0
    negative_time_count: int = 0
    zero_or_negative_duration_count: int = 0

    protected_violation_count: int = 0
    censor_violation_count: int = 0
    continuity_violation_count: int = 0
    approval_violation_count: int = 0

    future_execution_safety_status: str = "blocked"

    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "safety_validation_id": self.safety_validation_id,
            "job_id": self.job_id,
            "source_review_timeline_plan_id": self.source_review_timeline_plan_id,
            "source_timeline_approval_gate_id": (
                self.source_timeline_approval_gate_id
            ),
            "validation_status": self.validation_status,
            "is_safe_for_future_execution": self.is_safe_for_future_execution,
            "is_safe_for_render": self.is_safe_for_render,
            "requires_manual_review": self.requires_manual_review,
            "blocking_errors": list(self.blocking_errors or []),
            "warnings": list(self.warnings or []),
            "item_results": [
                item.to_dict()
                for item in list(self.item_results or [])
            ],
            "total_items_checked": self.total_items_checked,
            "invalid_timing_count": self.invalid_timing_count,
            "overlap_count": self.overlap_count,
            "gap_count": self.gap_count,
            "negative_time_count": self.negative_time_count,
            "zero_or_negative_duration_count": (
                self.zero_or_negative_duration_count
            ),
            "protected_violation_count": self.protected_violation_count,
            "censor_violation_count": self.censor_violation_count,
            "continuity_violation_count": self.continuity_violation_count,
            "approval_violation_count": self.approval_violation_count,
            "future_execution_safety_status": (
                self.future_execution_safety_status
            ),
            "created_at": self.created_at,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "TimelineSafetyValidation":
        data = data or {}

        raw_item_results = data.get("item_results") or []
        item_results = [
            TimelineSafetyItemResult.from_dict(item)
            for item in raw_item_results
            if isinstance(item, dict)
        ]

        return cls(
            safety_validation_id=str(
                data.get("safety_validation_id")
                or new_timeline_safety_validation_id()
            ),
            job_id=data.get("job_id"),
            source_review_timeline_plan_id=data.get(
                "source_review_timeline_plan_id"
            ),
            source_timeline_approval_gate_id=data.get(
                "source_timeline_approval_gate_id"
            ),
            validation_status=str(
                data.get("validation_status")
                or TIMELINE_SAFETY_STATUS_BLOCKED
            ),
            is_safe_for_future_execution=bool(
                data.get("is_safe_for_future_execution", False)
            ),
            is_safe_for_render=bool(data.get("is_safe_for_render", False)),
            requires_manual_review=bool(
                data.get("requires_manual_review", True)
            ),
            blocking_errors=list(data.get("blocking_errors") or []),
            warnings=list(data.get("warnings") or []),
            item_results=item_results,
            total_items_checked=int(data.get("total_items_checked", 0) or 0),
            invalid_timing_count=int(
                data.get("invalid_timing_count", 0) or 0
            ),
            overlap_count=int(data.get("overlap_count", 0) or 0),
            gap_count=int(data.get("gap_count", 0) or 0),
            negative_time_count=int(
                data.get("negative_time_count", 0) or 0
            ),
            zero_or_negative_duration_count=int(
                data.get("zero_or_negative_duration_count", 0) or 0
            ),
            protected_violation_count=int(
                data.get("protected_violation_count", 0) or 0
            ),
            censor_violation_count=int(
                data.get("censor_violation_count", 0) or 0
            ),
            continuity_violation_count=int(
                data.get("continuity_violation_count", 0) or 0
            ),
            approval_violation_count=int(
                data.get("approval_violation_count", 0) or 0
            ),
            future_execution_safety_status=str(
                data.get("future_execution_safety_status") or "blocked"
            ),
            created_at=str(data.get("created_at") or utc_now_iso()),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class TimelineSafetyValidatorRunReport:
    status: str = TIMELINE_SAFETY_STATUS_BLOCKED
    source: str = "timeline_safety_validator"

    timeline_safety_validation: TimelineSafetyValidation | None = None

    validation_status: str = TIMELINE_SAFETY_STATUS_BLOCKED
    is_safe_for_future_execution: bool = False
    is_safe_for_render: bool = False
    requires_manual_review: bool = True

    blocking_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "timeline_safety_validation": (
                self.timeline_safety_validation.to_dict()
                if self.timeline_safety_validation is not None
                else None
            ),
            "validation_status": self.validation_status,
            "is_safe_for_future_execution": self.is_safe_for_future_execution,
            "is_safe_for_render": self.is_safe_for_render,
            "requires_manual_review": self.requires_manual_review,
            "blocking_errors": list(self.blocking_errors or []),
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "TimelineSafetyValidatorRunReport":
        data = data or {}

        validation_data = data.get("timeline_safety_validation")
        validation = (
            TimelineSafetyValidation.from_dict(validation_data)
            if isinstance(validation_data, dict)
            else None
        )

        return cls(
            status=str(data.get("status") or TIMELINE_SAFETY_STATUS_BLOCKED),
            source=str(data.get("source") or "timeline_safety_validator"),
            timeline_safety_validation=validation,
            validation_status=str(
                data.get("validation_status")
                or TIMELINE_SAFETY_STATUS_BLOCKED
            ),
            is_safe_for_future_execution=bool(
                data.get("is_safe_for_future_execution", False)
            ),
            is_safe_for_render=bool(data.get("is_safe_for_render", False)),
            requires_manual_review=bool(
                data.get("requires_manual_review", True)
            ),
            blocking_errors=list(data.get("blocking_errors") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
