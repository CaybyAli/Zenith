from __future__ import annotations

from dataclasses import dataclass

from models.job import Job
from shared.channel_policies import get_channel_policy
from shared.platform_policies import get_platform_policy
from shared.enums import PlatformType


@dataclass(frozen=True)
class ResolvedPlatformPolicy:
    platform: PlatformType
    requires_manual_approval: bool
    title_mode: str
    description_mode: str
    hashtags_mode: str
    subtitle_style: str
    packaging_profile: str
    length_profile: str
    preferred_aspect_ratio: str
    thumbnail_required: bool
    uploader_backend: str | None


class PlatformPolicyResolver:
    def resolve_for_job_platform(
        self,
        job: Job,
        platform: str | PlatformType,
    ) -> ResolvedPlatformPolicy:
        channel_policy = get_channel_policy(job.channel_type.value)
        platform_policy = get_platform_policy(platform)

        requires_manual_approval = (
            platform_policy.requires_manual_approval
            if platform_policy.requires_manual_approval is not None
            else channel_policy.requires_manual_approval
        )

        if job.target_format not in platform_policy.allowed_target_formats:
            raise ValueError(
                f"Target format {job.target_format.value} is not allowed for platform "
                f"{platform_policy.platform.value}"
            )

        return ResolvedPlatformPolicy(
            platform=platform_policy.platform,
            requires_manual_approval=requires_manual_approval,
            title_mode=platform_policy.title_mode,
            description_mode=platform_policy.description_mode,
            hashtags_mode=platform_policy.hashtags_mode,
            subtitle_style=platform_policy.subtitle_style,
            packaging_profile=platform_policy.packaging_profile,
            length_profile=platform_policy.length_profile,
            preferred_aspect_ratio=platform_policy.preferred_aspect_ratio,
            thumbnail_required=platform_policy.thumbnail_required,
            uploader_backend=platform_policy.uploader_backend,
        )