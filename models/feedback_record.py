from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from shared.enums import ChannelType, PlatformType


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class FeedbackRecord:
    feedback_id: str
    job_id: str
    channel_type: ChannelType

    variant_id: str | None = None
    target_platform: PlatformType | None = None

    feedback_category: str = "overall_quality"
    feedback_direction: str = "improvement_request"
    feedback_text: str = ""

    author_source: str = "user"
    severity: str = "normal"

    metrics_snapshot_id: str | None = None
    attribution_id: str | None = None
    insight_reference: str | None = None

    context_snapshot: dict[str, Any] = field(default_factory=dict)
    learning_tags: list[str] = field(default_factory=list)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "job_id": self.job_id,
            "channel_type": self.channel_type.value,
            "variant_id": self.variant_id,
            "target_platform": (
                self.target_platform.value
                if self.target_platform is not None
                else None
            ),
            "feedback_category": self.feedback_category,
            "feedback_direction": self.feedback_direction,
            "feedback_text": self.feedback_text,
            "author_source": self.author_source,
            "severity": self.severity,
            "metrics_snapshot_id": self.metrics_snapshot_id,
            "attribution_id": self.attribution_id,
            "insight_reference": self.insight_reference,
            "context_snapshot": dict(self.context_snapshot),
            "learning_tags": list(self.learning_tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackRecord":
        return cls(
            feedback_id=str(data.get("feedback_id")),
            job_id=str(data.get("job_id")),
            channel_type=ChannelType(data.get("channel_type", "gaming_main")),
            variant_id=data.get("variant_id"),
            target_platform=(
                PlatformType(data["target_platform"])
                if data.get("target_platform") is not None
                else None
            ),
            feedback_category=str(data.get("feedback_category", "overall_quality")),
            feedback_direction=str(
                data.get("feedback_direction", "improvement_request")
            ),
            feedback_text=str(data.get("feedback_text", "")),
            author_source=str(data.get("author_source", "user")),
            severity=str(data.get("severity", "normal")),
            metrics_snapshot_id=data.get("metrics_snapshot_id"),
            attribution_id=data.get("attribution_id"),
            insight_reference=data.get("insight_reference"),
            context_snapshot=dict(data.get("context_snapshot", {})),
            learning_tags=list(data.get("learning_tags", [])),
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
        )