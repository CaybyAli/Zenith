from core.content_variant_builder import ContentVariantBuilder
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


def build_job() -> Job:
    return Job(
        job_id="job_variant_publish_smoke",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube", "tiktok", "instagram_reels"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/sample.mp4",
    )


def main() -> None:
    job = build_job()

    title_package = TitlePackage(
        job_id=job.job_id,
        primary_title="Zenith Variant Publish Smoke",
        backup_titles=["Backup 1", "Backup 2"],
        title_score=8.0,
    )
    metadata = MetadataPackage(
        job_id=job.job_id,
        description="Zenith variant to publish package smoke description",
        hashtags=["#zenith", "#variant", "#publish"],
    )
    thumbnail_package = ThumbnailPackage(
        job_id=job.job_id,
        selected_thumbnail="exports/tmp/thumb.jpg",
        thumbnail_variants=["exports/tmp/thumb.jpg"],
        thumbnail_scores=[0.9],
        selected_index=0,
    )

    variant_builder = ContentVariantBuilder()
    publish_package_builder = PublishPackageBuilder()

    variants = variant_builder.build(
        job=job,
        video_path="exports/tmp/video.mp4",
        title_package=title_package,
        metadata=metadata,
        thumbnail_package=thumbnail_package,
        subtitle_path=None,
        source_export_path=None,
    )

    packages = publish_package_builder.build(variants)

    assert len(variants) == 3
    assert len(packages) == 3

    by_platform = {package.platform.value: package for package in packages}

    youtube_package = by_platform["youtube"]
    assert youtube_package.target_format == TargetFormat.SHORT
    assert youtube_package.thumbnail_path == "exports/tmp/thumb.jpg"
    assert youtube_package.uploader_backend == "youtube"
    assert youtube_package.packaging_profile == "youtube"

    tiktok_package = by_platform["tiktok"]
    assert tiktok_package.target_format == TargetFormat.SHORT
    assert tiktok_package.thumbnail_path is None
    assert tiktok_package.uploader_backend is None
    assert tiktok_package.packaging_profile == "tiktok"

    instagram_package = by_platform["instagram_reels"]
    assert instagram_package.target_format == TargetFormat.SHORT
    assert instagram_package.thumbnail_path is None
    assert instagram_package.uploader_backend is None
    assert instagram_package.packaging_profile == "instagram_reel"

    print("VARIANT TO PUBLISH PACKAGE SMOKE TEST PASSED")


if __name__ == "__main__":
    main()