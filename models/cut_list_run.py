from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.cut_list import CutListItem, CutListPlan


@dataclass
class CutListRunReport:
    status: str = "ok"
    source: str = "cut_list_generator"
    cut_list_plan: CutListPlan | None = None
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
    recommendation: str = "review_cut_list_candidates"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "cut_list_plan": (
                self.cut_list_plan.to_dict()
                if self.cut_list_plan is not None
                else None
            ),
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
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CutListRunReport":
        if not isinstance(data, dict):
            data = {}

        plan_data = data.get("cut_list_plan")
        plan = CutListPlan.from_dict(plan_data) if isinstance(plan_data, dict) else None

        items = [
            CutListItem.from_dict(item_data)
            for item_data in data.get("items") or []
            if isinstance(item_data, dict)
        ]

        if not items and plan is not None:
            items = list(plan.items)

        return cls(
            status=str(data.get("status") or "ok"),
            source=str(data.get("source") or "cut_list_generator"),
            cut_list_plan=plan,
            items=items,
            item_count=int(data.get("item_count", len(items)) or 0),
            keep_count=int(data.get("keep_count") or 0),
            review_keep_count=int(data.get("review_keep_count") or 0),
            review_trim_count=int(data.get("review_trim_count") or 0),
            review_remove_count=int(data.get("review_remove_count") or 0),
            protect_count=int(data.get("protect_count") or 0),
            censor_keep_count=int(data.get("censor_keep_count") or 0),
            technical_review_count=int(data.get("technical_review_count") or 0),
            unknown_review_count=int(data.get("unknown_review_count") or 0),
            recommendation=str(data.get("recommendation") or "review_cut_list_candidates"),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
