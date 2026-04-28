from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from shared.enums import PlatformType


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class PublishResult:
    job_id: str
    platform: PlatformType
    publish_status: str
    message: str

    platform_video_id: str | None = None
    variant_id: str | None = None
    backend_name: str | None = None
    public_url: str | None = None
    error_message: str | None = None
    published_at: str | None = None
    last_updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.last_updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "platform": self.platform.value,
            "publish_status": self.publish_status,
            "message": self.message,
            "platform_video_id": self.platform_video_id,
            "variant_id": self.variant_id,
            "backend_name": self.backend_name,
            "public_url": self.public_url,
            "error_message": self.error_message,
            "published_at": self.published_at,
            "last_updated_at": self.last_updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PublishResult":
        return cls(
            job_id=str(data.get("job_id")),
            platform=PlatformType(data.get("platform", "youtube")),
            publish_status=str(data.get("publish_status", "pending")),
            message=str(data.get("message", "")),
            platform_video_id=data.get("platform_video_id"),
            variant_id=data.get("variant_id"),
            backend_name=data.get("backend_name"),
            public_url=data.get("public_url"),
            error_message=data.get("error_message"),
            published_at=data.get("published_at"),
            last_updated_at=data.get("last_updated_at", utc_now_iso()),
        )