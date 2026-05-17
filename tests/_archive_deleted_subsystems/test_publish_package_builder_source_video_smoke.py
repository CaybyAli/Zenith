from __future__ import annotations

from core.publish_package_builder import PublishPackageBuilder
from models.content_variant import ContentVariant
from shared.enums import ChannelType, PlatformType


def main() -> None:
    variant = ContentVariant(
        variant_id="variant_source_video_smoke_001",
        job_id="job_source_video_smoke_001",
        channel_type=ChannelType.GAMING_MAIN,
        target_platform=PlatformType.YOUTUBE,
        variant_kind="platform_variant",
        video_path="output/job_source_video_smoke_001_final.mp4",
        source_video_path="inbox/gaming_main/real_main_test_001.mp4",
        title="Smoke Title",
        description="Smoke Description",
        hashtags=["#zenith"],
        platform_policy_snapshot={
            "target_format": "short",
            "requires_manual_approval": True,
            "title_mode": "youtube_title",
            "description_mode": "youtube_description",
            "hashtags_mode": "youtube_optional",
            "subtitle_style": "youtube_standard",
            "packaging_profile": "youtube",
            "length_profile": "longform_or_shortform",
            "preferred_aspect_ratio": "16:9_or_9:16",
            "thumbnail_required": True,
            "uploader_backend": "youtube",
        },
    )

    package = PublishPackageBuilder().build_from_variant(variant)

    assert package.video_path == "output/job_source_video_smoke_001_final.mp4"
    assert package.source_video_path == "inbox/gaming_main/real_main_test_001.mp4"

    print("PUBLISH PACKAGE BUILDER SOURCE VIDEO SMOKE TEST PASSED")
    print(
        {
            "video_path": package.video_path,
            "source_video_path": package.source_video_path,
        }
    )


if __name__ == "__main__":
    main()