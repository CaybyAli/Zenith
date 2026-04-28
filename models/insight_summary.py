from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class InsightSummary:
    insight_id: str
    insight_type: str
    title: str
    summary_text: str

    severity: str = "info"
    related_variant_ids: list[str] = field(default_factory=list)
    related_platforms: list[str] = field(default_factory=list)
    related_channels: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "insight_type": self.insight_type,
            "title": self.title,
            "summary_text": self.summary_text,
            "severity": self.severity,
            "related_variant_ids": list(self.related_variant_ids),
            "related_platforms": list(self.related_platforms),
            "related_channels": list(self.related_channels),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InsightSummary":
        return cls(
            insight_id=str(data.get("insight_id")),
            insight_type=str(data.get("insight_type", "")),
            title=str(data.get("title", "")),
            summary_text=str(data.get("summary_text", "")),
            severity=str(data.get("severity", "info")),
            related_variant_ids=list(data.get("related_variant_ids", [])),
            related_platforms=list(data.get("related_platforms", [])),
            related_channels=list(data.get("related_channels", [])),
            metadata=dict(data.get("metadata", {})),
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
        )