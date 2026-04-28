from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from shared.enums import ChannelType, PlatformType


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ContentVariant:
    variant_id: str
    job_id: str
    channel_type: ChannelType
    target_platform: PlatformType
    variant_kind: str

    video_path: str
    source_video_path: str | None = None
    thumbnail_or_cover_path: str | None = None
    subtitle_path: str | None = None

    title: str = ""
    description: str = ""
    hashtags: list[str] = field(default_factory=list)

    variant_status: str = "built"
    source_export_path: str | None = None

    packaging_profile: str | None = None
    subtitle_style: str | None = None
    platform_policy_snapshot: dict[str, Any] = field(default_factory=dict)

    needs_rebuild: bool = False
    build_notes: str | None = None

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "job_id": self.job_id,
            "channel_type": self.channel_type.value,
            "target_platform": self.target_platform.value,
            "variant_kind": self.variant_kind,
            "video_path": self.video_path,
            "source_video_path": self.source_video_path,
            "thumbnail_or_cover_path": self.thumbnail_or_cover_path,
            "subtitle_path": self.subtitle_path,
            "title": self.title,
            "description": self.description,
            "hashtags": list(self.hashtags),
            "variant_status": self.variant_status,
            "source_export_path": self.source_export_path,
            "packaging_profile": self.packaging_profile,
            "subtitle_style": self.subtitle_style,
            "platform_policy_snapshot": dict(self.platform_policy_snapshot),
            "needs_rebuild": self.needs_rebuild,
            "build_notes": self.build_notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContentVariant":
        return cls(
            variant_id=str(data.get("variant_id")),
            job_id=str(data.get("job_id")),
            channel_type=ChannelType(data.get("channel_type", "gaming_main")),
            target_platform=PlatformType(data.get("target_platform", "youtube")),
            variant_kind=str(data.get("variant_kind", "platform_variant")),
            video_path=str(data.get("video_path")),
            source_video_path=data.get("source_video_path"),
            thumbnail_or_cover_path=data.get("thumbnail_or_cover_path"),
            subtitle_path=data.get("subtitle_path"),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            hashtags=list(data.get("hashtags", [])),
            variant_status=str(data.get("variant_status", "built")),
            source_export_path=data.get("source_export_path"),
            packaging_profile=data.get("packaging_profile"),
            subtitle_style=data.get("subtitle_style"),
            platform_policy_snapshot=dict(data.get("platform_policy_snapshot", {})),
            needs_rebuild=bool(data.get("needs_rebuild", False)),
            build_notes=data.get("build_notes"),
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
        )