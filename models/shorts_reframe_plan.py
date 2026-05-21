from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

ShortsLayoutType = Literal["gameplay_centered", "facecam_centered", "hybrid_split"]
ShortsPlatformPreset = Literal["youtube_shorts", "tiktok", "instagram_reels"]


@dataclass(slots=True)
class ShortsReframePlan:
    layout_type: ShortsLayoutType
    ffmpeg_crop_filter: str
    target_aspect_ratio: str = "9:16"
    safe_zone_top_px: int = 120
    safe_zone_bottom_px: int = 120
    face_tracking_enabled: bool = False
    layout_rationale: str = ""
    platform_preset: ShortsPlatformPreset = "youtube_shorts"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ShortsReframePlan":
        raw = dict(data or {})
        return cls(
            layout_type=raw.get("layout_type", "gameplay_centered"),
            ffmpeg_crop_filter=str(raw.get("ffmpeg_crop_filter") or ""),
            target_aspect_ratio=str(raw.get("target_aspect_ratio") or "9:16"),
            safe_zone_top_px=int(raw.get("safe_zone_top_px", 120) or 120),
            safe_zone_bottom_px=int(raw.get("safe_zone_bottom_px", 120) or 120),
            face_tracking_enabled=bool(raw.get("face_tracking_enabled", False)),
            layout_rationale=str(raw.get("layout_rationale") or ""),
            platform_preset=raw.get("platform_preset", "youtube_shorts"),
        )
