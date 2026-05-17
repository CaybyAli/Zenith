import os
import shutil
from types import SimpleNamespace

from app import finalize_pipeline_result
from core.content_variant_builder import ContentVariantBuilder
from core.content_variant_repository import ContentVariantRepository
from core.export_manager import ExportManager
from core.job_repository import JobRepository
from core.publish_package_builder import PublishPackageBuilder
from models.job import Job
from models.metadata_package import MetadataPackage
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

class FakeScheduler:
    def is_due(self, scheduled_at):
        return True

class FakePublisher:
    def publish(self, publish_package, publish_decision):
        from models.publish_result import PublishResult

        if publish_package.uploader_backend == "youtube":
            return PublishResult(
                job_id=publish_package.job_id,
                platform=publish_package.platform,
                publish_status="published",
                message="youtube published",
                platform_video_id="yt_finalize_123",
            )

        return PublishResult(
            job_id=publish_package.job_id,
            platform=publish_package.platform,
            publish_status="unsupported_backend",
            message="backend not implemented",
        )


class FakeShortsGenerator:
    def generate(self, package, shorts_decision, platform_targets=None):
        return []


def build_job() -> Job:
    return Job(
        job_id="job_finalize_variants_smoke",
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


def ensure_file(path: str, content: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)


def main() -> None:
    job = build_job()
    job.review_status = "approved"
    job.is_scheduled = True
    job.scheduled_at = "2026-04-14 12:00"
    export_path = os.path.join("exports", job.channel_type.value, job.job_id)
    tmp_video_path = os.path.join("tmp", "finalize_variants_video.mp4")
    tmp_thumbnail_path = os.path.join("tmp", "finalize_variants_thumb.jpg")

    if os.path.exists(export_path):
        shutil.rmtree(export_path)

    ensure_file(tmp_video_path, b"fake video bytes")
    ensure_file(tmp_thumbnail_path, b"fake thumbnail bytes")

    title_package = TitlePackage(
        job_id=job.job_id,
        primary_title="Zenith Finalize Variants Smoke",
        backup_titles=["Backup 1", "Backup 2"],
        title_score=8.4,
    )
    metadata = MetadataPackage(
        job_id=job.job_id,
        description="Finalize pipeline result with variants smoke description",
        hashtags=["#zenith", "#finalize", "#variants"],
    )
    thumbnail_package = ThumbnailPackage(
        job_id=job.job_id,
        selected_thumbnail=tmp_thumbnail_path,
        thumbnail_variants=[tmp_thumbnail_path],
        thumbnail_scores=[0.91],
        selected_index=0,
    )

    content_variants = ContentVariantBuilder().build(
        job=job,
        video_path=tmp_video_path,
        title_package=title_package,
        metadata=metadata,
        thumbnail_package=thumbnail_package,
        subtitle_path=None,
        source_export_path=None,
    )

    publish_packages = PublishPackageBuilder().build(content_variants)

    validator_result = SimpleNamespace(ready_for_publish=True)
    shorts_decision = SimpleNamespace(selected_segments=[], shorts_count=0)

    result = finalize_pipeline_result(
        job=job,
        content_variants=content_variants,
        publish_packages=publish_packages,
        validator_result=validator_result,
        shorts_decision=shorts_decision,
        autopublish_gate=__import__("core.autopublish_gate", fromlist=["AutopublishGate"]).AutopublishGate(),
        shorts_generator=FakeShortsGenerator(),
        publisher=FakePublisher(),
        export_manager=ExportManager(),
        repo=JobRepository(),
        scheduler=FakeScheduler(),
    )

    print("FINALIZE publish_status:", result["publish_result"].publish_status)
    print("FINALIZE platform:", result["publish_result"].platform.value)
    print("ALL publish_statuses:", [r.publish_status for r in result["publish_results"]])
    print("ALL platforms:", [r.platform.value for r in result["publish_results"]])

    assert result["publish_decision"].decision == "autopublish_allowed"

    assert os.path.exists(os.path.join(result["export_path"], "variants.json"))

    loaded_variants = ContentVariantRepository().load_variants(result["export_path"])
    assert len(loaded_variants) == 3

    print("FINALIZE PIPELINE RESULT VARIANTS SMOKE TEST PASSED")


if __name__ == "__main__":
    main()