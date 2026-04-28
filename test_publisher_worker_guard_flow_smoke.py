import os
import shutil

import publisher_worker
from core.content_variant_builder import ContentVariantBuilder
from core.cross_platform_publish_orchestrator import CrossPlatformPublishOrchestrator
from core.publish_guard_repository import PublishGuardRepository
from core.publish_result_repository import PublishResultRepository
from models.job import Job
from models.metadata_package import MetadataPackage
from models.publish_decision import PublishDecision
from models.publish_guard_result import PublishGuardResult
from models.publish_result import PublishResult
from models.thumbnail_package import ThumbnailPackage
from models.title_package import TitlePackage
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


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
            if package.platform.value == "youtube":
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
            elif package.platform.value == "tiktok":
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


def build_job() -> Job:
    return Job(
        job_id="job_worker_guard_flow_smoke",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube", "tiktok", "instagram_reels"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.SAFE_AUTO,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/sample.mp4",
    )


def main() -> None:
    export_path = os.path.join("tmp", "publisher_worker_guard_flow_test")
    if os.path.exists(export_path):
        shutil.rmtree(export_path)
    os.makedirs(export_path, exist_ok=True)

    job = build_job()

    title_package = TitlePackage(
        job_id=job.job_id,
        primary_title="Zenith Worker Guard Flow Smoke",
        backup_titles=["Backup 1", "Backup 2"],
        title_score=8.3,
    )
    metadata = MetadataPackage(
        job_id=job.job_id,
        description="Worker guard flow smoke description",
        hashtags=["#zenith", "#worker", "#guard"],
    )
    thumbnail_package = ThumbnailPackage(
        job_id=job.job_id,
        selected_thumbnail="exports/tmp/thumb.jpg",
        thumbnail_variants=["exports/tmp/thumb.jpg"],
        thumbnail_scores=[0.92],
        selected_index=0,
    )

    variants = ContentVariantBuilder().build(
        job=job,
        video_path="exports/tmp/video.mp4",
        title_package=title_package,
        metadata=metadata,
        thumbnail_package=thumbnail_package,
        subtitle_path=None,
        source_export_path=export_path,
    )

    publisher_worker.content_variant_repository.save_variants(export_path, variants)

    job_dict = job.to_dict()
    job_dict["title"] = title_package.primary_title
    job_dict["description"] = metadata.description
    job_dict["video_path"] = "exports/tmp/video.mp4"
    job_dict["thumbnail_path"] = "exports/tmp/thumb.jpg"

    packages = publisher_worker.build_publish_packages_for_export(
        job=job_dict,
        export_path=export_path,
    )

    publisher_worker.cross_platform_publish_orchestrator = CrossPlatformPublishOrchestrator(
        publisher=FakePublisher(),
        publish_result_repository=PublishResultRepository(),
        publish_guard=FakePublishGuard(),
        publish_guard_repository=PublishGuardRepository(),
    )

    publish_decision = PublishDecision(
        job_id=job.job_id,
        decision="autopublish_allowed",
        reason="worker guard flow smoke",
    )

    results = publisher_worker.execute_publish_packages(
        publish_packages=packages,
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

    print("PUBLISHER WORKER GUARD FLOW SMOKE TEST PASSED")


if __name__ == "__main__":
    main()