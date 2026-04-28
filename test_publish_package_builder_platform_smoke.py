from types import SimpleNamespace

from core.publish_package_builder import PublishPackageBuilder
from models.job import Job
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
        job_id="job_builder_smoke",
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
    builder = PublishPackageBuilder()
    job = build_job()

    title_package = SimpleNamespace(primary_title="Zenith Builder Smoke Title")
    metadata = SimpleNamespace(
        description="Zenith builder smoke description",
        hashtags=["zenith", "smoke", "test"],
    )
    thumbnail_package = SimpleNamespace(selected_thumbnail="exports/tmp/thumb.jpg")

    packages = builder.build(
        job=job,
        final_video_path="exports/tmp/video.mp4",
        title_package=title_package,
        metadata=metadata,
        thumbnail_package=thumbnail_package,
    )

    assert len(packages) == 3

    by_platform = {package.platform.value: package for package in packages}

    youtube_package = by_platform["youtube"]
    assert youtube_package.thumbnail_required is True
    assert youtube_package.thumbnail_path == "exports/tmp/thumb.jpg"
    assert youtube_package.uploader_backend == "youtube"
    assert youtube_package.packaging_profile == "youtube"

    tiktok_package = by_platform["tiktok"]
    assert tiktok_package.thumbnail_required is False
    assert tiktok_package.thumbnail_path is None
    assert tiktok_package.uploader_backend is None
    assert tiktok_package.packaging_profile == "tiktok"

    instagram_package = by_platform["instagram_reels"]
    assert instagram_package.thumbnail_required is False
    assert instagram_package.thumbnail_path is None
    assert instagram_package.uploader_backend is None
    assert instagram_package.packaging_profile == "instagram_reel"

    print("PUBLISH PACKAGE BUILDER PLATFORM SMOKE TEST PASSED")


if __name__ == "__main__":
    main()