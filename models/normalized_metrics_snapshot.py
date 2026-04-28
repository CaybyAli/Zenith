from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from shared.enums import ChannelType, PlatformType


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class NormalizedMetricsSnapshot:
    snapshot_id: str
    job_id: str
    variant_id: str
    target_platform: PlatformType
    channel_type: ChannelType

    platform_video_id: str | None = None
    published_at: str | None = None
    synced_at: str = field(default_factory=utc_now_iso)

    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    saves: int | None = None

    ctr: float | None = None
    average_view_duration_seconds: float | None = None
    completion_rate: float | None = None
    retention_rate: float | None = None

    normalization_version: str = "v1"
    source_snapshot_id: str | None = None
    notes: str | None = None

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
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "saves": self.saves,
            "ctr": self.ctr,
            "average_view_duration_seconds": self.average_view_duration_seconds,
            "completion_rate": self.completion_rate,
            "retention_rate": self.retention_rate,
            "normalization_version": self.normalization_version,
            "source_snapshot_id": self.source_snapshot_id,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NormalizedMetricsSnapshot":
        return cls(
            snapshot_id=str(data.get("snapshot_id")),
            job_id=str(data.get("job_id")),
            variant_id=str(data.get("variant_id")),
            target_platform=PlatformType(data.get("target_platform", "youtube")),
            channel_type=ChannelType(data.get("channel_type", "gaming_main")),
            platform_video_id=data.get("platform_video_id"),
            published_at=data.get("published_at"),
            synced_at=data.get("synced_at", utc_now_iso()),
            views=(
                int(data["views"])
                if data.get("views") is not None
                else None
            ),
            likes=(
                int(data["likes"])
                if data.get("likes") is not None
                else None
            ),
            comments=(
                int(data["comments"])
                if data.get("comments") is not None
                else None
            ),
            shares=(
                int(data["shares"])
                if data.get("shares") is not None
                else None
            ),
            saves=(
                int(data["saves"])
                if data.get("saves") is not None
                else None
            ),
            ctr=(
                float(data["ctr"])
                if data.get("ctr") is not None
                else None
            ),
            average_view_duration_seconds=(
                float(data["average_view_duration_seconds"])
                if data.get("average_view_duration_seconds") is not None
                else None
            ),
            completion_rate=(
                float(data["completion_rate"])
                if data.get("completion_rate") is not None
                else None
            ),
            retention_rate=(
                float(data["retention_rate"])
                if data.get("retention_rate") is not None
                else None
            ),
            normalization_version=str(data.get("normalization_version", "v1")),
            source_snapshot_id=data.get("source_snapshot_id"),
            notes=data.get("notes"),
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
        )