from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.final_cut_list import FinalCutListItem, FinalCutListPlan


@dataclass
class FinalCutListRunReport:
    status: str = "skipped_no_inputs"
    source: str = "cut_list_finalizer"
    final_cut_list_plan: FinalCutListPlan | None = None
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "final_cut_list_plan": (
                self.final_cut_list_plan.to_dict()
                if self.final_cut_list_plan is not None
                else None
            ),
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
    def from_dict(cls, data: dict[str, Any] | None) -> "FinalCutListRunReport":
        data = data or {}

        plan_data = data.get("final_cut_list_plan")
        final_cut_list_plan = (
            FinalCutListPlan.from_dict(plan_data)
            if isinstance(plan_data, dict)
            else None
        )
        final_items = [
            FinalCutListItem.from_dict(item)
            for item in data.get("final_items", []) or []
            if isinstance(item, dict)
        ]
        if not final_items and final_cut_list_plan is not None:
            final_items = list(final_cut_list_plan.final_items)

        return cls(
            status=str(data.get("status") or "skipped_no_inputs"),
            source=str(data.get("source") or "cut_list_finalizer"),
            final_cut_list_plan=final_cut_list_plan,
            final_items=final_items,
            final_item_count=int(data.get("final_item_count", len(final_items)) or 0),
            final_keep_review_count=int(
                data.get("final_keep_review_count", 0) or 0
            ),
            final_keep_high_value_count=int(
                data.get("final_keep_high_value_count", 0) or 0
            ),
            final_trim_review_count=int(
                data.get("final_trim_review_count", 0) or 0
            ),
            final_remove_review_count=int(
                data.get("final_remove_review_count", 0) or 0
            ),
            final_protect_count=int(data.get("final_protect_count", 0) or 0),
            final_censor_keep_count=int(
                data.get("final_censor_keep_count", 0) or 0
            ),
            final_technical_review_count=int(
                data.get("final_technical_review_count", 0) or 0
            ),
            final_blocked_by_continuity_count=int(
                data.get("final_blocked_by_continuity_count", 0) or 0
            ),
            final_unknown_review_count=int(
                data.get("final_unknown_review_count", 0) or 0
            ),
            review_required_count=int(data.get("review_required_count", 0) or 0),
            blocking_issue_count=int(data.get("blocking_issue_count", 0) or 0),
            recommendation=str(
                data.get("recommendation") or "final_cut_list_skipped_no_inputs"
            ),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
