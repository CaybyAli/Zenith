from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ComparisonViewSummary:
    comparison_id: str
    comparison_type: str
    comparison_key: str

    item_count: int = 0

    winner_variant_id: str | None = None
    loser_variant_id: str | None = None

    winner_label: str | None = None
    loser_label: str | None = None

    winner_score: float | None = None
    loser_score: float | None = None
    average_score: float | None = None

    summary_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "comparison_type": self.comparison_type,
            "comparison_key": self.comparison_key,
            "item_count": self.item_count,
            "winner_variant_id": self.winner_variant_id,
            "loser_variant_id": self.loser_variant_id,
            "winner_label": self.winner_label,
            "loser_label": self.loser_label,
            "winner_score": self.winner_score,
            "loser_score": self.loser_score,
            "average_score": self.average_score,
            "summary_text": self.summary_text,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ComparisonViewSummary":
        return cls(
            comparison_id=str(data.get("comparison_id")),
            comparison_type=str(data.get("comparison_type", "")),
            comparison_key=str(data.get("comparison_key", "")),
            item_count=int(data.get("item_count", 0)),
            winner_variant_id=data.get("winner_variant_id"),
            loser_variant_id=data.get("loser_variant_id"),
            winner_label=data.get("winner_label"),
            loser_label=data.get("loser_label"),
            winner_score=(
                float(data["winner_score"])
                if data.get("winner_score") is not None
                else None
            ),
            loser_score=(
                float(data["loser_score"])
                if data.get("loser_score") is not None
                else None
            ),
            average_score=(
                float(data["average_score"])
                if data.get("average_score") is not None
                else None
            ),
            summary_text=data.get("summary_text"),
            metadata=dict(data.get("metadata", {})),
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
        )