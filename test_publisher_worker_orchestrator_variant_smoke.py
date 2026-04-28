import os
import shutil

import publisher_worker
from core.content_variant_builder import ContentVariantBuilder
from core.cross_platform_publish_orchestrator import CrossPlatformPublishOrchestrator
from core.publish_result_repository import PublishResultRepository
from models.job import Job
from models.metadata_package import MetadataPackage
from models.publish_decision import PublishDecision
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
        if publish_package.platform.value == "youtube":
            return PublishResult(
                job_id=publish_package.job_id,
                platform=publish_package.platform,
                publish_status="published",
                message="youtube published",
                platform_video_id="yt_worker_orchestrator_123",
                variant_id=publish_package.variant_id,
                backend_name="youtube",
                public_url="https://youtube.com/watch?v=yt_worker_orchestrator_123",
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


def build_job() -> Job:
    return Job(
        job_id="job_worker_orchestrator_variant_smoke",
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
    export_path = os.path.join("tmp", "publisher_worker_orchestrator_variant_test")
    if os.path.exists(export_path):
        shutil.rmtree(export_path)
    os.makedirs(export_path, exist_ok=True)

    job = build_job()

    title_package = TitlePackage(
        job_id=job.job_id,
        primary_title="Zenith Worker Orchestrator Variant Smoke",
        backup_titles=["Backup 1", "Backup 2"],
        title_score=8.3,
    )
    metadata = MetadataPackage(
        job_id=job.job_id,
        description="Worker orchestrator variant smoke description",
        hashtags=["#zenith", "#worker", "#orchestrator"],
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

    assert len(packages) == 3
    assert all(package.variant_id is not None for package in packages)

    publisher_worker.cross_platform_publish_orchestrator = CrossPlatformPublishOrchestrator(
        publisher=FakePublisher(),
        publish_result_repository=PublishResultRepository(),
    )

    publish_decision = PublishDecision(
        job_id=job.job_id,
        decision="autopublish_allowed",
        reason="worker orchestrator variant smoke",
    )

    results = publisher_worker.execute_publish_packages(
        publish_packages=packages,
        publish_decision=publish_decision,
        export_path=export_path,
    )

    assert len(results) == 3

    by_platform = {result.platform.value: result for result in results}

    assert by_platform["youtube"].publish_status == "published"
    assert by_platform["youtube"].variant_id == "variant_job_worker_orchestrator_variant_smoke_youtube"

    assert by_platform["tiktok"].publish_status == "unsupported_backend"
    assert by_platform["tiktok"].variant_id == "variant_job_worker_orchestrator_variant_smoke_tiktok"

    assert by_platform["instagram_reels"].publish_status == "unsupported_backend"
    assert (
        by_platform["instagram_reels"].variant_id
        == "variant_job_worker_orchestrator_variant_smoke_instagram_reels"
    )

    loaded_results = PublishResultRepository().load_results(export_path)
    assert len(loaded_results) == 3

    print("PUBLISHER WORKER ORCHESTRATOR VARIANT SMOKE TEST PASSED")


if __name__ == "__main__":
    main()