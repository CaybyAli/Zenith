from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


FINAL_CUT_LIST_STATUS_OK = "ok"
FINAL_CUT_LIST_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
FINAL_CUT_LIST_STATUS_SKIPPED_NO_CUT_LIST_ITEMS = "skipped_no_cut_list_items"
FINAL_CUT_LIST_STATUS_SKIPPED_NO_INPUTS = "skipped_no_inputs"
FINAL_CUT_LIST_STATUS_FAILED = "failed"

FINAL_ACTION_KEEP_REVIEW = "FINAL_KEEP_REVIEW"
FINAL_ACTION_KEEP_HIGH_VALUE = "FINAL_KEEP_HIGH_VALUE"
FINAL_ACTION_TRIM_REVIEW = "FINAL_TRIM_REVIEW"
FINAL_ACTION_REMOVE_REVIEW = "FINAL_REMOVE_REVIEW"
FINAL_ACTION_PROTECT = "FINAL_PROTECT"
FINAL_ACTION_CENSOR_KEEP = "FINAL_CENSOR_KEEP"
FINAL_ACTION_TECHNICAL_REVIEW = "FINAL_TECHNICAL_REVIEW"
FINAL_ACTION_BLOCKED_BY_CONTINUITY = "FINAL_BLOCKED_BY_CONTINUITY"
FINAL_ACTION_UNKNOWN_REVIEW = "FINAL_UNKNOWN_REVIEW"

FINAL_PRIORITY_LOW = "low"
FINAL_PRIORITY_MEDIUM = "medium"
FINAL_PRIORITY_HIGH = "high"


@dataclass
class FinalCutListItem:
    final_item_id: str
    source_item_id: str | None = None
    segment_id: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    duration_seconds: float | None = None
    final_action: str = FINAL_ACTION_UNKNOWN_REVIEW
    final_confidence: float = 0.0
    priority: str = FINAL_PRIORITY_LOW
    segment_type: str | None = None
    cut_list_action: str | None = None
    duration_status: str | None = None
    transition_type: str | None = None
    murch_score: float = 0.0
    continuity_blocked: bool = False
    is_protected: bool = False
    is_censor_keep: bool = False
    is_technical_review: bool = False
    is_review_required: bool = True
    is_keep_candidate: bool = False
    is_trim_candidate: bool = False
    is_remove_candidate: bool = False
    is_invalid_timing: bool = False
    recommended_start_seconds: float | None = None
    recommended_end_seconds: float | None = None
    recommended_duration_seconds: float | None = None
    reason: str = ""
    decision_basis: dict[str, Any] = field(default_factory=dict)
    source_signal_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_item_id": self.final_item_id,
            "source_item_id": self.source_item_id,
            "segment_id": self.segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "duration_seconds": self.duration_seconds,
            "final_action": self.final_action,
            "final_confidence": self.final_confidence,
            "priority": self.priority,
            "segment_type": self.segment_type,
            "cut_list_action": self.cut_list_action,
            "duration_status": self.duration_status,
            "transition_type": self.transition_type,
            "murch_score": self.murch_score,
            "continuity_blocked": self.continuity_blocked,
            "is_protected": self.is_protected,
            "is_censor_keep": self.is_censor_keep,
            "is_technical_review": self.is_technical_review,
            "is_review_required": self.is_review_required,
            "is_keep_candidate": self.is_keep_candidate,
            "is_trim_candidate": self.is_trim_candidate,
            "is_remove_candidate": self.is_remove_candidate,
            "is_invalid_timing": self.is_invalid_timing,
            "recommended_start_seconds": self.recommended_start_seconds,
            "recommended_end_seconds": self.recommended_end_seconds,
            "recommended_duration_seconds": self.recommended_duration_seconds,
            "reason": self.reason,
            "decision_basis": dict(self.decision_basis or {}),
            "source_signal_ids": list(self.source_signal_ids or []),
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "FinalCutListItem":
        data = data or {}

        return cls(
            final_item_id=str(data.get("final_item_id") or ""),
            source_item_id=data.get("source_item_id"),
            segment_id=data.get("segment_id"),
            start_seconds=data.get("start_seconds"),
            end_seconds=data.get("end_seconds"),
            center_seconds=data.get("center_seconds"),
            duration_seconds=data.get("duration_seconds"),
            final_action=str(data.get("final_action") or FINAL_ACTION_UNKNOWN_REVIEW),
            final_confidence=float(data.get("final_confidence") or 0.0),
            priority=str(data.get("priority") or FINAL_PRIORITY_LOW),
            segment_type=data.get("segment_type"),
            cut_list_action=data.get("cut_list_action"),
            duration_status=data.get("duration_status"),
            transition_type=data.get("transition_type"),
            murch_score=float(data.get("murch_score") or 0.0),
            continuity_blocked=bool(data.get("continuity_blocked", False)),
            is_protected=bool(data.get("is_protected", False)),
            is_censor_keep=bool(data.get("is_censor_keep", False)),
            is_technical_review=bool(data.get("is_technical_review", False)),
            is_review_required=bool(data.get("is_review_required", True)),
            is_keep_candidate=bool(data.get("is_keep_candidate", False)),
            is_trim_candidate=bool(data.get("is_trim_candidate", False)),
            is_remove_candidate=bool(data.get("is_remove_candidate", False)),
            is_invalid_timing=bool(data.get("is_invalid_timing", False)),
            recommended_start_seconds=data.get("recommended_start_seconds"),
            recommended_end_seconds=data.get("recommended_end_seconds"),
            recommended_duration_seconds=data.get("recommended_duration_seconds"),
            reason=str(data.get("reason") or ""),
            decision_basis=dict(data.get("decision_basis") or {}),
            source_signal_ids=list(data.get("source_signal_ids") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class FinalCutListPlan:
    status: str = FINAL_CUT_LIST_STATUS_SKIPPED_NO_INPUTS
    final_items: list[FinalCutListItem] = field(default_factory=list)
    final_item_count: int = 0
    final_keep_review_count: int = 0
    final_keep_high_value_count: int = 0
    final_trim_review_count: int = 0
    final_remove_review_count: int = 0
    final_protect_count: int = 0
    final_censor_keep_count: int = 0
    final_technical_review_count: int = 0
    final_blocked_by_continuity_count: int = 0
    final_unknown_review_count: int = 0
    review_required_count: int = 0
    blocking_issue_count: int = 0
    recommendation: str = "final_cut_list_skipped_no_inputs"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.final_item_count = len(self.final_items)
        self.final_keep_review_count = _count_action(
            self.final_items,
            FINAL_ACTION_KEEP_REVIEW,
        )
        self.final_keep_high_value_count = _count_action(
            self.final_items,
            FINAL_ACTION_KEEP_HIGH_VALUE,
        )
        self.final_trim_review_count = _count_action(
            self.final_items,
            FINAL_ACTION_TRIM_REVIEW,
        )
        self.final_remove_review_count = _count_action(
            self.final_items,
            FINAL_ACTION_REMOVE_REVIEW,
        )
        self.final_protect_count = _count_action(
            self.final_items,
            FINAL_ACTION_PROTECT,
        )
        self.final_censor_keep_count = _count_action(
            self.final_items,
            FINAL_ACTION_CENSOR_KEEP,
        )
        self.final_technical_review_count = _count_action(
            self.final_items,
            FINAL_ACTION_TECHNICAL_REVIEW,
        )
        self.final_blocked_by_continuity_count = _count_action(
            self.final_items,
            FINAL_ACTION_BLOCKED_BY_CONTINUITY,
        )
        self.final_unknown_review_count = _count_action(
            self.final_items,
            FINAL_ACTION_UNKNOWN_REVIEW,
        )
        self.review_required_count = sum(
            1 for item in self.final_items if item.is_review_required
        )
        self.blocking_issue_count = sum(
            1 for item in self.final_items if item.continuity_blocked
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()

        return {
            "status": self.status,
            "final_items": [item.to_dict() for item in self.final_items],
            "final_item_count": self.final_item_count,
            "final_keep_review_count": self.final_keep_review_count,
            "final_keep_high_value_count": self.final_keep_high_value_count,
            "final_trim_review_count": self.final_trim_review_count,
            "final_remove_review_count": self.final_remove_review_count,
            "final_protect_count": self.final_protect_count,
            "final_censor_keep_count": self.final_censor_keep_count,
            "final_technical_review_count": self.final_technical_review_count,
            "final_blocked_by_continuity_count": (
                self.final_blocked_by_continuity_count
            ),
            "final_unknown_review_count": self.final_unknown_review_count,
            "review_required_count": self.review_required_count,
            "blocking_issue_count": self.blocking_issue_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "FinalCutListPlan":
        data = data or {}
        final_items = [
            FinalCutListItem.from_dict(item)
            for item in data.get("final_items", []) or []
            if isinstance(item, dict)
        ]

        plan = cls(
            status=str(data.get("status") or FINAL_CUT_LIST_STATUS_SKIPPED_NO_INPUTS),
            final_items=final_items,
            recommendation=str(
                data.get("recommendation") or "final_cut_list_skipped_no_inputs"
            ),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
        plan.refresh_counts()
        return plan


def _count_action(items: list[FinalCutListItem], action: str) -> int:
    return sum(1 for item in items if item.final_action == action)
