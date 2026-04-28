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
                platform_video_id="yt_variant_binding_123",
                variant_id=publish_package.variant_id,
                backend_name="youtube",
                public_url="https://youtube.com/watch?v=yt_variant_binding_123",
                error_message=None,
                published_at="2026-04-14T12:00:00+00:00",
            )

        return PublishResult(
            job_id=publish_package.job_id,
            platform=publish_package.platform,
            publish_status="unsupported_backend",
            message="backend not implemented",
            variant_id=publish_package.variant_id,
            backend_name=publish_package.uploader_backend,
            error_message="No uploader backend implemented for platform",
        )


def build_package(
    *,
    platform: PlatformType,
    uploader_backend: str | None,
    variant_id: str,
) -> PublishPackage:
    return PublishPackage(
        job_id="job_variant_binding_smoke",
        video_path="exports/tmp/video.mp4",
        title="Zenith Variant Binding Smoke",
        description="Variant binding smoke description",
        hashtags=["#zenith", "#variant", "#binding"],
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
        variant_id=variant_id,
    )


def main() -> None:
    export_path = os.path.join("tmp", "publish_result_variant_binding_test")
    if os.path.exists(export_path):
        shutil.rmtree(export_path)

    orchestrator = CrossPlatformPublishOrchestrator(
        publisher=FakePublisher(),
        publish_result_repository=PublishResultRepository(),
    )

    publish_packages = [
        build_package(
            platform=PlatformType.YOUTUBE,
            uploader_backend="youtube",
            variant_id="variant_job_variant_binding_smoke_youtube",
        ),
        build_package(
            platform=PlatformType.TIKTOK,
            uploader_backend=None,
            variant_id="variant_job_variant_binding_smoke_tiktok",
        ),
    ]

    publish_decision = PublishDecision(
        job_id="job_variant_binding_smoke",
        decision="autopublish_allowed",
        reason="variant binding smoke",
    )

    results = orchestrator.execute(
        publish_packages=publish_packages,
        publish_decision=publish_decision,
        export_path=export_path,
    )

    assert len(results) == 2

    by_platform = {result.platform.value: result for result in results}

    youtube_result = by_platform["youtube"]
    assert youtube_result.variant_id == "variant_job_variant_binding_smoke_youtube"
    assert youtube_result.publish_status == "published"

    tiktok_result = by_platform["tiktok"]
    assert tiktok_result.variant_id == "variant_job_variant_binding_smoke_tiktok"
    assert tiktok_result.publish_status == "unsupported_backend"

    loaded_results = PublishResultRepository().load_results(export_path)
    assert len(loaded_results) == 2

    loaded_by_platform = {result.platform.value: result for result in loaded_results}
    assert (
        loaded_by_platform["youtube"].variant_id
        == "variant_job_variant_binding_smoke_youtube"
    )
    assert (
        loaded_by_platform["tiktok"].variant_id
        == "variant_job_variant_binding_smoke_tiktok"
    )

    print("PUBLISH RESULT VARIANT BINDING SMOKE TEST PASSED")


if __name__ == "__main__":
    main()