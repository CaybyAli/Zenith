from __future__ import annotations

from core.platform_policy_resolver import PlatformPolicyResolver
from models.content_variant import ContentVariant
from models.job import Job
from models.metadata_package import MetadataPackage
from models.thumbnail_package import ThumbnailPackage
from models.title_package import TitlePackage
from shared.enums import PlatformType


class ContentVariantBuilder:
    def __init__(self) -> None:
        self._platform_policy_resolver = PlatformPolicyResolver()

    def build_for_platform(
        self,
        job: Job,
        video_path: str,
        title_package: TitlePackage,
        metadata: MetadataPackage,
        thumbnail_package: ThumbnailPackage,
        platform: str | PlatformType,
        subtitle_path: str | None = None,
        source_export_path: str | None = None,
    ) -> ContentVariant:
        resolved_policy = self._platform_policy_resolver.resolve_for_job_platform(
            job=job,
            platform=platform,
        )

        thumbnail_or_cover_path = (
            thumbnail_package.selected_thumbnail
            if resolved_policy.thumbnail_required
            else None
        )

        return ContentVariant(
            variant_id=(
                f"variant_{job.job_id}_{resolved_policy.platform.value}"
            ),
            job_id=job.job_id,
            channel_type=job.channel_type,
            target_platform=resolved_policy.platform,
            variant_kind="platform_variant",
            video_path=video_path,
            source_video_path=job.raw_video_path,
            thumbnail_or_cover_path=thumbnail_or_cover_path,
            subtitle_path=subtitle_path,
            title=title_package.primary_title,
            description=metadata.description,
            hashtags=list(metadata.hashtags),
            variant_status="built",
            source_export_path=source_export_path,
            packaging_profile=resolved_policy.packaging_profile,
            subtitle_style=resolved_policy.subtitle_style,
            platform_policy_snapshot={
                "platform": resolved_policy.platform.value,
                "target_format": job.target_format.value,
                "requires_manual_approval": resolved_policy.requires_manual_approval,
                "title_mode": resolved_policy.title_mode,
                "description_mode": resolved_policy.description_mode,
                "hashtags_mode": resolved_policy.hashtags_mode,
                "subtitle_style": resolved_policy.subtitle_style,
                "packaging_profile": resolved_policy.packaging_profile,
                "length_profile": resolved_policy.length_profile,
                "preferred_aspect_ratio": resolved_policy.preferred_aspect_ratio,
                "thumbnail_required": resolved_policy.thumbnail_required,
                "uploader_backend": resolved_policy.uploader_backend,
            },
            needs_rebuild=False,
            build_notes=None,
        )

    def build(
        self,
        job: Job,
        video_path: str,
        title_package: TitlePackage,
        metadata: MetadataPackage,
        thumbnail_package: ThumbnailPackage,
        subtitle_path: str | None = None,
        source_export_path: str | None = None,
    ) -> list[ContentVariant]:
        if not job.target_platforms:
            raise ValueError(f"Job {job.job_id} has no target_platforms")

        return [
            self.build_for_platform(
                job=job,
                video_path=video_path,
                title_package=title_package,
                metadata=metadata,
                thumbnail_package=thumbnail_package,
                platform=platform,
                subtitle_path=subtitle_path,
                source_export_path=source_export_path,
            )
            for platform in job.target_platforms
        ]