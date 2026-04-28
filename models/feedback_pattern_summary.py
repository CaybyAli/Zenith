from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class FeedbackPatternSummary:
    summary_id: str
    category: str
    direction: str
    item_count: int

    channels: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    variant_ids: list[str] = field(default_factory=list)

    summary_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "category": self.category,
            "direction": self.direction,
            "item_count": self.item_count,
            "channels": list(self.channels),
            "platforms": list(self.platforms),
            "variant_ids": list(self.variant_ids),
            "summary_text": self.summary_text,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackPatternSummary":
        return cls(
            summary_id=str(data.get("summary_id")),
            category=str(data.get("category", "")),
            direction=str(data.get("direction", "")),
            item_count=int(data.get("item_count", 0)),
            channels=list(data.get("channels", [])),
            platforms=list(data.get("platforms", [])),
            variant_ids=list(data.get("variant_ids", [])),
            summary_text=str(data.get("summary_text", "")),
            metadata=dict(data.get("metadata", {})),
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
        )