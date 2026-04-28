from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from shared.enums import PlatformType, TargetFormat


@dataclass(frozen=True)
class PlatformPolicy:
    platform: PlatformType
    enabled: bool = True
    requires_manual_approval: bool | None = None

    title_mode: str = "standard"
    description_mode: str = "standard"
    hashtags_mode: str = "standard"
    subtitle_style: str = "standard"
    packaging_profile: str = "standard"

    length_profile: str = "standard"
    preferred_aspect_ratio: str = "16:9"
    allowed_target_formats: List[TargetFormat] = field(default_factory=list)

    thumbnail_required: bool = True
    uploader_backend: str | None = None


PLATFORM_POLICIES: Dict[str, PlatformPolicy] = {
    PlatformType.YOUTUBE.value: PlatformPolicy(
        platform=PlatformType.YOUTUBE,
        enabled=True,
        requires_manual_approval=None,
        title_mode="youtube_title",
        description_mode="youtube_description",
        hashtags_mode="youtube_optional",
        subtitle_style="youtube_standard",
        packaging_profile="youtube",
        length_profile="longform_or_shortform",
        preferred_aspect_ratio="16:9_or_9:16",
        allowed_target_formats=[
            TargetFormat.LONGFORM,
            TargetFormat.SHORT,
            TargetFormat.BOTH,
        ],
        thumbnail_required=True,
        uploader_backend="youtube",
    ),
    PlatformType.TIKTOK.value: PlatformPolicy(
        platform=PlatformType.TIKTOK,
        enabled=True,
        requires_manual_approval=None,
        title_mode="short_hook_title",
        description_mode="tiktok_caption",
        hashtags_mode="tiktok_native",
        subtitle_style="short_burned_in",
        packaging_profile="tiktok",
        length_profile="shortform_focused",
        preferred_aspect_ratio="9:16",
        allowed_target_formats=[
            TargetFormat.SHORT,
            TargetFormat.BOTH,
        ],
        thumbnail_required=False,
        uploader_backend=None,
    ),
    PlatformType.INSTAGRAM_REELS.value: PlatformPolicy(
        platform=PlatformType.INSTAGRAM_REELS,
        enabled=True,
        requires_manual_approval=None,
        title_mode="short_hook_title",
        description_mode="instagram_reel_caption",
        hashtags_mode="instagram_native",
        subtitle_style="short_burned_in",
        packaging_profile="instagram_reel",
        length_profile="shortform_focused",
        preferred_aspect_ratio="9:16",
        allowed_target_formats=[
            TargetFormat.SHORT,
            TargetFormat.BOTH,
        ],
        thumbnail_required=False,
        uploader_backend=None,
    ),
}


def normalize_platform(platform: str | PlatformType) -> PlatformType:
    if isinstance(platform, PlatformType):
        return platform

    try:
        return PlatformType(platform)
    except ValueError as exc:
        raise ValueError(f"Unknown platform: {platform}") from exc


def get_platform_policy(platform: str | PlatformType) -> PlatformPolicy:
    normalized_platform = normalize_platform(platform)
    policy = PLATFORM_POLICIES.get(normalized_platform.value)

    if policy is None:
        raise ValueError(f"Unknown platform: {normalized_platform.value}")

    return policy


def get_all_platform_policies() -> List[PlatformPolicy]:
    return list(PLATFORM_POLICIES.values())


def get_enabled_platform_policies() -> List[PlatformPolicy]:
    return [
        policy
        for policy in PLATFORM_POLICIES.values()
        if policy.enabled
    ]


def is_platform_enabled(platform: str | PlatformType) -> bool:
    return get_platform_policy(platform).enabled