from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from shared.trend_enums import TrendPlatform, TrendSourceType


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp_float(value: float | int | str | None, *, minimum: float, maximum: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = minimum

    return max(minimum, min(maximum, numeric))


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _normalize_platform(value: Any) -> TrendPlatform:
    cleaned = _clean_text(value, "unknown").lower()

    alias_map = {
        "youtube": TrendPlatform.YOUTUBE,
        "yt": TrendPlatform.YOUTUBE,
        "youtube_shorts": TrendPlatform.YOUTUBE,
        "tiktok": TrendPlatform.TIKTOK,
        "tik tok": TrendPlatform.TIKTOK,
        "tik_tok": TrendPlatform.TIKTOK,
        "instagram": TrendPlatform.INSTAGRAM,
        "insta": TrendPlatform.INSTAGRAM,
        "reels": TrendPlatform.INSTAGRAM,
        "x": TrendPlatform.X,
        "twitter": TrendPlatform.X,
        "reddit": TrendPlatform.REDDIT,
        "web": TrendPlatform.WEB,
        "website": TrendPlatform.WEB,
        "blog": TrendPlatform.WEB,
        "news": TrendPlatform.WEB,
        "unknown": TrendPlatform.UNKNOWN,
    }

    return alias_map.get(cleaned, TrendPlatform.UNKNOWN)


def _normalize_source_type(value: Any) -> TrendSourceType:
    cleaned = _clean_text(value, "manual").lower()

    for source_type in TrendSourceType:
        if source_type.value == cleaned:
            return source_type

    return TrendSourceType.MANUAL


@dataclass(slots=True)
class TrendSource:
    source_id: str
    source_type: TrendSourceType
    source_name: str
    platform: TrendPlatform
    reliability_weight: float = 0.5
    default_half_life_hours: float = 24.0
    enabled: bool = True
    workspace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_type"] = self.source_type.value
        data["platform"] = self.platform.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrendSource":
        return cls(
            source_id=_clean_text(data.get("source_id")) or f"source_{uuid4().hex[:12]}",
            source_type=_normalize_source_type(data.get("source_type")),
            source_name=_clean_text(data.get("source_name"), "Unnamed Source"),
            platform=_normalize_platform(data.get("platform")),
            reliability_weight=_clamp_float(
                data.get("reliability_weight", 0.5),
                minimum=0.0,
                maximum=1.0,
            ),
            default_half_life_hours=_clamp_float(
                data.get("default_half_life_hours", 24.0),
                minimum=1.0,
                maximum=720.0,
            ),
            enabled=bool(data.get("enabled", True)),
            workspace_id=_clean_text(data.get("workspace_id")) or None,
            metadata=dict(data.get("metadata", {})),
            created_at=_clean_text(data.get("created_at")) or utc_now_iso(),
            updated_at=_clean_text(data.get("updated_at")) or utc_now_iso(),
        )