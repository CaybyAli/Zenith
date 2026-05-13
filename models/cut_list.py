from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CUT_LIST_STATUS_OK = "ok"
CUT_LIST_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
CUT_LIST_STATUS_SKIPPED_NO_MURCH_SCORES = "skipped_no_murch_scores"
CUT_LIST_STATUS_SKIPPED_NO_SEGMENTS = "skipped_no_segments"
CUT_LIST_STATUS_FAILED = "failed"

CUT_LIST_ACTION_KEEP = "KEEP"
CUT_LIST_ACTION_REVIEW_KEEP = "REVIEW_KEEP"
CUT_LIST_ACTION_REVIEW_TRIM = "REVIEW_TRIM"
CUT_LIST_ACTION_REVIEW_REMOVE = "REVIEW_REMOVE"
CUT_LIST_ACTION_PROTECT = "PROTECT"
CUT_LIST_ACTION_CENSOR_KEEP = "CENSOR_KEEP"
CUT_LIST_ACTION_TECHNICAL_REVIEW = "TECHNICAL_REVIEW"
CUT_LIST_ACTION_UNKNOWN_REVIEW = "UNKNOWN_REVIEW"

CUT_LIST_PRIORITY_HIGH = "high"
CUT_LIST_PRIORITY_MEDIUM = "medium"
CUT_LIST_PRIORITY_LOW = "low"


@dataclass
class CutListItem:
    item_id: str
    segment_id: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    duration_seconds: float | None = None
    proposed_action: str = CUT_LIST_ACTION_UNKNOWN_REVIEW
    action_confidence: float = 0.0
    priority: str = CUT_LIST_PRIORITY_LOW
    segment_type: str = "unknown"
    murch_score: float = 0.0
    content_value_score: float = 0.0
    risk_score: float = 0.0
    protection_score: float = 0.0
    censor_required: bool = False
    is_protected: bool = False
    is_review_required: bool = True
    is_keep_candidate: bool = False
    is_trim_candidate: bool = False
    is_remove_candidate: bool = False
    is_technical_review: bool = False
    reason: str = ""
    decision_basis: dict[str, Any] = field(default_factory=dict)
    source_segment_id: str | None = None
    source_signal_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "segment_id": self.segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "duration_seconds": self.duration_seconds,
            "proposed_action": self.proposed_action,
            "action_confidence": self.action_confidence,
            "priority": self.priority,
            "segment_type": self.segment_type,
            "murch_score": self.murch_score,
            "content_value_score": self.content_value_score,
            "risk_score": self.risk_score,
            "protection_score": self.protection_score,
            "censor_required": self.censor_required,
            "is_protected": self.is_protected,
            "is_review_required": self.is_review_required,
            "is_keep_candidate": self.is_keep_candidate,
            "is_trim_candidate": self.is_trim_candidate,
            "is_remove_candidate": self.is_remove_candidate,
            "is_technical_review": self.is_technical_review,
            "reason": self.reason,
            "decision_basis": dict(self.decision_basis or {}),
            "source_segment_id": self.source_segment_id,
            "source_signal_ids": list(self.source_signal_ids or []),
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CutListItem":
        data = data or {}
        return cls(
            item_id=str(data.get("item_id") or ""),
            segment_id=data.get("segment_id"),
            start_seconds=data.get("start_seconds"),
            end_seconds=data.get("end_seconds"),
            center_seconds=data.get("center_seconds"),
            duration_seconds=data.get("duration_seconds"),
            proposed_action=str(data.get("proposed_action") or CUT_LIST_ACTION_UNKNOWN_REVIEW),
            action_confidence=float(data.get("action_confidence") or 0.0),
            priority=str(data.get("priority") or CUT_LIST_PRIORITY_LOW),
            segment_type=str(data.get("segment_type") or "unknown"),
            murch_score=float(data.get("murch_score") or 0.0),
            content_value_score=float(data.get("content_value_score") or 0.0),
            risk_score=float(data.get("risk_score") or 0.0),
            protection_score=float(data.get("protection_score") or 0.0),
            censor_required=bool(data.get("censor_required", False)),
            is_protected=bool(data.get("is_protected", False)),
            is_review_required=bool(data.get("is_review_required", True)),
            is_keep_candidate=bool(data.get("is_keep_candidate", False)),
            is_trim_candidate=bool(data.get("is_trim_candidate", False)),
            is_remove_candidate=bool(data.get("is_remove_candidate", False)),
            is_technical_review=bool(data.get("is_technical_review", False)),
            reason=str(data.get("reason") or ""),
            decision_basis=dict(data.get("decision_basis") or {}),
            source_segment_id=data.get("source_segment_id"),
            source_signal_ids=list(data.get("source_signal_ids") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class CutListPlan:
    status: str = CUT_LIST_STATUS_OK
    items: list[CutListItem] = field(default_factory=list)
    item_count: int = 0
    keep_count: int = 0
    review_keep_count: int = 0
    review_trim_count: int = 0
    review_remove_count: int = 0
    protect_count: int = 0
    censor_keep_count: int = 0
    technical_review_count: int = 0
    unknown_review_count: int = 0
    recommendation: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.item_count = len(self.items)
        self.keep_count = sum(1 for item in self.items if item.proposed_action == CUT_LIST_ACTION_KEEP)
        self.review_keep_count = sum(1 for item in self.items if item.proposed_action == CUT_LIST_ACTION_REVIEW_KEEP)
        self.review_trim_count = sum(1 for item in self.items if item.proposed_action == CUT_LIST_ACTION_REVIEW_TRIM)
        self.review_remove_count = sum(1 for item in self.items if item.proposed_action == CUT_LIST_ACTION_REVIEW_REMOVE)
        self.protect_count = sum(1 for item in self.items if item.proposed_action == CUT_LIST_ACTION_PROTECT)
        self.censor_keep_count = sum(1 for item in self.items if item.proposed_action == CUT_LIST_ACTION_CENSOR_KEEP)
        self.technical_review_count = sum(1 for item in self.items if item.proposed_action == CUT_LIST_ACTION_TECHNICAL_REVIEW)
        self.unknown_review_count = sum(1 for item in self.items if item.proposed_action == CUT_LIST_ACTION_UNKNOWN_REVIEW)

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()
        return {
            "status": self.status,
            "items": [item.to_dict() for item in self.items],
            "item_count": self.item_count,
            "keep_count": self.keep_count,
            "review_keep_count": self.review_keep_count,
            "review_trim_count": self.review_trim_count,
            "review_remove_count": self.review_remove_count,
            "protect_count": self.protect_count,
            "censor_keep_count": self.censor_keep_count,
            "technical_review_count": self.technical_review_count,
            "unknown_review_count": self.unknown_review_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CutListPlan":
        data = data or {}
        items = [CutListItem.from_dict(item) for item in data.get("items") or []]
        plan = cls(
            status=str(data.get("status") or CUT_LIST_STATUS_OK),
            items=items,
            recommendation=str(data.get("recommendation") or ""),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
        plan.refresh_counts()
        return plan
