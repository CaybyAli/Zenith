import os
import shutil

from core.cross_platform_publish_orchestrator import CrossPlatformPublishOrchestrator
from core.publish_guard_repository import PublishGuardRepository
from core.publish_result_repository import PublishResultRepository
from models.publish_decision import PublishDecision
from models.publish_guard_result import PublishGuardResult
from models.publish_package import PublishPackage
from models.publish_result import PublishResult
from shared.enums import ChannelType, PlatformType, TargetFormat


class FakePublisher:
    def publish(self, publish_package, publish_decision):
        return PublishResult(
            job_id=publish_package.job_id,
            platform=publish_package.platform,
            publish_status="published",
            message=f"{publish_package.platform.value} published",
            platform_video_id=f"id_{publish_package.platform.value}",
            variant_id=publish_package.variant_id,
            backend_name=publish_package.uploader_backend,
            public_url=f"https://example.com/{publish_package.platform.value}",
            error_message=None,
            published_at="2026-04-14T12:00:00+00:00",
        )


class FakePublishGuard:
    def evaluate_packages(self, publish_packages):
        results = []

        for package in publish_packages:
            if package.platform == PlatformType.YOUTUBE:
                results.append(
                    PublishGuardResult(
                        job_id=package.job_id,
                        variant_id=package.variant_id,
                        target_platform=package.platform,
                        guard_status="allow",
                        risk_flags=[],
                        guard_reason="No material guard risks detected",
                        matched_reference_ids=[],
                        similarity_score=0.0,
                        requires_manual_review=False,
                    )
                )
            elif package.platform == PlatformType.TIKTOK:
                results.append(
                    PublishGuardResult(
                        job_id=package.job_id,
                        variant_id=package.variant_id,
                        target_platform=package.platform,
                        guard_status="warn",
                        risk_flags=["cross_platform_too_similar", "low_originality"],
                        guard_reason="Cross-platform publish is very close to existing material",
                        matched_reference_ids=["variant_ref_tiktok"],
                        similarity_score=0.85,
                        requires_manual_review=True,
                    )
                )
            else:
                results.append(
                    PublishGuardResult(
                        job_id=package.job_id,
                        variant_id=package.variant_id,
                        target_platform=package.platform,
                        guard_status="block",
                        risk_flags=["duplicate_variant"],
                        guard_reason="This exact variant was already published",
                        matched_reference_ids=["variant_ref_instagram"],
                        similarity_score=1.0,
                        requires_manual_review=False,
                    )
                )

        return results


def build_package(platform: PlatformType, variant_id: str) -> PublishPackage:
    return PublishPackage(
        job_id="job_guard_smoke",
        video_path="exports/tmp/video.mp4",
        title="Zenith Guard Smoke",
        description="Guard smoke description",
        hashtags=["#zenith", "#guard", "#smoke"],
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
        uploader_backend="youtube" if platform == PlatformType.YOUTUBE else None,
        variant_id=variant_id,
    )


def main() -> None:
    export_path = os.path.join("tmp", "cross_platform_publish_guard_test")
    if os.path.exists(export_path):
        shutil.rmtree(export_path)

    orchestrator = CrossPlatformPublishOrchestrator(
        publisher=FakePublisher(),
        publish_result_repository=PublishResultRepository(),
        publish_guard=FakePublishGuard(),
        publish_guard_repository=PublishGuardRepository(),
    )

    publish_packages = [
        build_package(PlatformType.YOUTUBE, "variant_guard_youtube"),
        build_package(PlatformType.TIKTOK, "variant_guard_tiktok"),
        build_package(PlatformType.INSTAGRAM_REELS, "variant_guard_instagram"),
    ]

    publish_decision = PublishDecision(
        job_id="job_guard_smoke",
        decision="autopublish_allowed",
        reason="guard smoke",
    )

    results = orchestrator.execute(
        publish_packages=publish_packages,
        publish_decision=publish_decision,
        export_path=export_path,
    )

    assert len(results) == 3

    by_platform = {result.platform.value: result for result in results}

    assert by_platform["youtube"].publish_status == "published"
    assert by_platform["tiktok"].publish_status == "queued_for_approval"
    assert by_platform["instagram_reels"].publish_status == "blocked"

    loaded_guard_results = PublishGuardRepository().load_results(export_path)
    assert len(loaded_guard_results) == 3

    guard_by_platform = {
        result.target_platform.value: result
        for result in loaded_guard_results
    }

    assert guard_by_platform["youtube"].guard_status == "allow"
    assert guard_by_platform["tiktok"].guard_status == "warn"
    assert guard_by_platform["instagram_reels"].guard_status == "block"

    loaded_publish_results = PublishResultRepository().load_results(export_path)
    assert len(loaded_publish_results) == 3

    print("CROSS PLATFORM PUBLISH GUARD SMOKE TEST PASSED")


if __name__ == "__main__":
    main()