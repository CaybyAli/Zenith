from dataclasses import dataclass
from typing import List

from shared.enums import ChannelType, PlatformType, TargetFormat


@dataclass
class PublishPackage:
    job_id: str
    video_path: str
    title: str
    description: str
    hashtags: List[str]
    thumbnail_path: str | None

    platform: PlatformType
    channel_type: ChannelType
    target_format: TargetFormat

    requires_manual_approval: bool
    title_mode: str
    description_mode: str
    hashtags_mode: str
    subtitle_style: str
    packaging_profile: str
    length_profile: str
    preferred_aspect_ratio: str
    thumbnail_required: bool
    uploader_backend: str | None = None

    variant_id: str | None = None
    source_video_path: str | None = None
    short_id: str | None = None