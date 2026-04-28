import os
import shutil

from core.cross_platform_publish_orchestrator import CrossPlatformPublishOrchestrator
from core.publish_result_repository import PublishResultRepository
from models.publish_decision import PublishDecision
from models.publish_package import PublishPackage
from models.publish_result import PublishResult
from shared.enums import ChannelType, PlatformType, TargetFormat


class FakePublisher:
    def publish(self, publish_package, publish_decision):
        if publish_package.platform == PlatformType.YOUTUBE:
            return PublishResult(
                job_id=publish_package.job_id,
                platform=publish_package.platform,
                publish_status="published",
                message="youtube published",
                platform_video_id="yt_orchestrator_123",
                backend_name="youtube",
                public_url="https://youtube.com/watch?v=yt_orchestrator_123",
                error_message=None,
                published_at="2026-04-14T12:00:00+00:00",
            )

        return PublishResult(
            job_id=publish_package.job_id,
            platform=publish_package.platform,
            publish_status="unsupported_backend",
            message="backend not implemented",
            backend_name=publish_package.uploader_backend,
            error_message="No uploader backend implemented for platform",
        )


def build_package(
    *,
    platform: PlatformType,
    uploader_backend: str | None,
) -> PublishPackage:
    return PublishPackage(
        job_id="job_orchestrator_smoke",
        video_path="exports/tmp/video.mp4",
        title="Zenith Orchestrator Smoke",
        description="Orchestrator smoke description",
        hashtags=["#zenith", "#orchestrator", "#smoke"],
        thumbnail_path="exports/tmp/thumb.jpg",
        platform=platform,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        requires_manual_approval=False,
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
    export_path = os.path.join("tmp", "cross_platform_publish_orchestrator_test")
    if os.path.exists(export_path):
        shutil.rmtree(export_path)

    orchestrator = CrossPlatformPublishOrchestrator(
        publisher=FakePublisher(),
        publish_result_repository=PublishResultRepository(),
    )

    publish_packages = [
        build_package(platform=PlatformType.YOUTUBE, uploader_backend="youtube"),
        build_package(platform=PlatformType.TIKTOK, uploader_backend=None),
        build_package(platform=PlatformType.INSTAGRAM_REELS, uploader_backend=None),
    ]

    publish_decision = PublishDecision(
        job_id="job_orchestrator_smoke",
        decision="autopublish_allowed",
        reason="orchestrator smoke",
    )

    results = orchestrator.execute(
        publish_packages=publish_packages,
        publish_decision=publish_decision,
        export_path=export_path,
    )

    assert len(results) == 3

    by_platform = {result.platform.value: result for result in results}

    youtube_result = by_platform["youtube"]
    assert youtube_result.publish_status == "published"
    assert youtube_result.backend_name == "youtube"
    assert youtube_result.platform_video_id == "yt_orchestrator_123"
    assert youtube_result.public_url == "https://youtube.com/watch?v=yt_orchestrator_123"

    tiktok_result = by_platform["tiktok"]
    assert tiktok_result.publish_status == "unsupported_backend"
    assert tiktok_result.backend_name is None
    assert tiktok_result.error_message == "No uploader backend implemented for platform"

    instagram_result = by_platform["instagram_reels"]
    assert instagram_result.publish_status == "unsupported_backend"
    assert instagram_result.backend_name is None
    assert instagram_result.error_message == "No uploader backend implemented for platform"

    loaded_results = PublishResultRepository().load_results(export_path)
    assert len(loaded_results) == 3

    loaded_youtube = PublishResultRepository().get_result_by_platform(
        export_path,
        "youtube",
    )
    assert loaded_youtube is not None
    assert loaded_youtube.publish_status == "published"

    print("CROSS PLATFORM PUBLISH ORCHESTRATOR SMOKE TEST PASSED")


if __name__ == "__main__":
    main()