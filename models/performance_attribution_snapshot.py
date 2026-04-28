from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from shared.enums import ChannelType, PlatformType


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class PerformanceAttributionSnapshot:
    attribution_id: str
    metrics_snapshot_id: str
    job_id: str
    variant_id: str
    target_platform: PlatformType
    channel_type: ChannelType

    platform_video_id: str | None = None
    publish_reference: dict[str, Any] = field(default_factory=dict)

    variant_kind: str | None = None
    packaging_profile: str | None = None
    subtitle_style: str | None = None

    metadata_context_snapshot: dict[str, Any] = field(default_factory=dict)
    policy_snapshot: dict[str, Any] = field(default_factory=dict)

    publish_status: str | None = None
    guard_status: str | None = None
    published_at: str | None = None
    synced_at: str | None = None

    attribution_notes: str | None = None

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "attribution_id": self.attribution_id,
            "metrics_snapshot_id": self.metrics_snapshot_id,
            "job_id": self.job_id,
            "variant_id": self.variant_id,
            "target_platform": self.target_platform.value,
            "channel_type": self.channel_type.value,
            "platform_video_id": self.platform_video_id,
            "publish_reference": dict(self.publish_reference),
            "variant_kind": self.variant_kind,
            "packaging_profile": self.packaging_profile,
            "subtitle_style": self.subtitle_style,
            "metadata_context_snapshot": dict(self.metadata_context_snapshot),
            "policy_snapshot": dict(self.policy_snapshot),
            "publish_status": self.publish_status,
            "guard_status": self.guard_status,
            "published_at": self.published_at,
            "synced_at": self.synced_at,
            "attribution_notes": self.attribution_notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PerformanceAttributionSnapshot":
        return cls(
            attribution_id=str(data.get("attribution_id")),
            metrics_snapshot_id=str(data.get("metrics_snapshot_id")),
            job_id=str(data.get("job_id")),
            variant_id=str(data.get("variant_id")),
            target_platform=PlatformType(data.get("target_platform", "youtube")),
            channel_type=ChannelType(data.get("channel_type", "gaming_main")),
            platform_video_id=data.get("platform_video_id"),
            publish_reference=dict(data.get("publish_reference", {})),
            variant_kind=data.get("variant_kind"),
            packaging_profile=data.get("packaging_profile"),
            subtitle_style=data.get("subtitle_style"),
            metadata_context_snapshot=dict(
                data.get("metadata_context_snapshot", {})
            ),
            policy_snapshot=dict(data.get("policy_snapshot", {})),
            publish_status=data.get("publish_status"),
            guard_status=data.get("guard_status"),
            published_at=data.get("published_at"),
            synced_at=data.get("synced_at"),
            attribution_notes=data.get("attribution_notes"),
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
        )