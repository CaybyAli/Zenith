from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from shared.enums import ChannelType, PlatformType


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class PlatformRawMetrics:
    snapshot_id: str
    job_id: str
    variant_id: str
    target_platform: PlatformType
    channel_type: ChannelType

    platform_video_id: str | None = None
    published_at: str | None = None
    synced_at: str = field(default_factory=utc_now_iso)

    raw_source: str = "manual_import"
    raw_metrics: dict[str, Any] = field(default_factory=dict)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "job_id": self.job_id,
            "variant_id": self.variant_id,
            "target_platform": self.target_platform.value,
            "channel_type": self.channel_type.value,
            "platform_video_id": self.platform_video_id,
            "published_at": self.published_at,
            "synced_at": self.synced_at,
            "raw_source": self.raw_source,
            "raw_metrics": dict(self.raw_metrics),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlatformRawMetrics":
        return cls(
            snapshot_id=str(data.get("snapshot_id")),
            job_id=str(data.get("job_id")),
            variant_id=str(data.get("variant_id")),
            target_platform=PlatformType(data.get("target_platform", "youtube")),
            channel_type=ChannelType(data.get("channel_type", "gaming_main")),
            platform_video_id=data.get("platform_video_id"),
            published_at=data.get("published_at"),
            synced_at=data.get("synced_at", utc_now_iso()),
            raw_source=str(data.get("raw_source", "manual_import")),
            raw_metrics=dict(data.get("raw_metrics", {})),
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
        )