from core.publisher import Publisher
from models.publish_decision import PublishDecision
from models.publish_package import PublishPackage
from shared.enums import ChannelType, PlatformType, TargetFormat


def build_package(
    *,
    platform: PlatformType,
    uploader_backend: str | None,
    requires_manual_approval: bool,
) -> PublishPackage:
    return PublishPackage(
        job_id="job_publisher_smoke",
        video_path="exports/tmp/video.mp4",
        title="Zenith Publisher Smoke",
        description="Publisher platform smoke test",
        hashtags=["zenith", "publisher", "smoke"],
        thumbnail_path="exports/tmp/thumb.jpg",
        platform=platform,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        requires_manual_approval=requires_manual_approval,
        title_mode="standard",
        description_mode="standard",
        hashtags_mode="standard",
        subtitle_style="standard",
        packaging_profile="standard",
        length_profile="standard",
        preferred_aspect_ratio="9:16",
        thumbnail_required=True,
        uploader_backend=uploader_backend,
    )


def main() -> None:
    publisher = Publisher()

    approval_required_decision = PublishDecision(
        job_id="job_publisher_smoke",
        decision="approval_required",
        reason="manual gate",
    )

    youtube_package = build_package(
        platform=PlatformType.YOUTUBE,
        uploader_backend="youtube",
        requires_manual_approval=False,
    )

    approval_result = publisher.publish(
        youtube_package,
        approval_required_decision,
    )
    assert approval_result.platform == PlatformType.YOUTUBE
    assert approval_result.publish_status == "queued_for_approval"

    autopublish_decision = PublishDecision(
        job_id="job_publisher_smoke",
        decision="autopublish_allowed",
        reason="validator passed",
    )

    tiktok_package = build_package(
        platform=PlatformType.TIKTOK,
        uploader_backend=None,
        requires_manual_approval=False,
    )

    tiktok_result = publisher.publish(
        tiktok_package,
        autopublish_decision,
    )
    assert tiktok_result.platform == PlatformType.TIKTOK
    assert tiktok_result.publish_status == "unsupported_backend"

    instagram_package = build_package(
        platform=PlatformType.INSTAGRAM_REELS,
        uploader_backend=None,
        requires_manual_approval=True,
    )

    instagram_result = publisher.publish(
        instagram_package,
        autopublish_decision,
    )
    assert instagram_result.platform == PlatformType.INSTAGRAM_REELS
    assert instagram_result.publish_status == "queued_for_approval"

    print("PUBLISHER PLATFORM POLICY SMOKE TEST PASSED")


if __name__ == "__main__":
    main()