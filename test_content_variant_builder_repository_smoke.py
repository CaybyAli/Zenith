import os
import shutil

from core.content_variant_builder import ContentVariantBuilder
from core.content_variant_repository import ContentVariantRepository
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
        job_id="job_variant_smoke",
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
    export_path = os.path.join("tmp", "content_variant_repo_test")
    if os.path.exists(export_path):
        shutil.rmtree(export_path)

    builder = ContentVariantBuilder()
    repository = ContentVariantRepository()

    job = build_job()
    title_package = TitlePackage(
        job_id=job.job_id,
        primary_title="Zenith Variant Smoke",
        backup_titles=["Zenith Backup 1", "Zenith Backup 2"],
        title_score=8.5,
    )
    metadata = MetadataPackage(
        job_id=job.job_id,
        description="Zenith variant smoke description",
        hashtags=["#zenith", "#variant", "#smoke"],
    )
    thumbnail_package = ThumbnailPackage(
        job_id=job.job_id,
        selected_thumbnail="exports/tmp/thumb.jpg",
        thumbnail_variants=["exports/tmp/thumb.jpg"],
        thumbnail_scores=[0.95],
        selected_index=0,
    )

    variants = builder.build(
        job=job,
        video_path="exports/tmp/video.mp4",
        title_package=title_package,
        metadata=metadata,
        thumbnail_package=thumbnail_package,
        subtitle_path="exports/tmp/subtitles.srt",
        source_export_path="exports/gaming_main/job_variant_smoke",
    )

    assert len(variants) == 3

    by_platform = {variant.target_platform.value: variant for variant in variants}

    youtube_variant = by_platform["youtube"]
    assert youtube_variant.thumbnail_or_cover_path == "exports/tmp/thumb.jpg"
    assert youtube_variant.packaging_profile == "youtube"
    assert youtube_variant.subtitle_style == "youtube_standard"
    assert youtube_variant.platform_policy_snapshot["target_format"] == "short"

    tiktok_variant = by_platform["tiktok"]
    assert tiktok_variant.thumbnail_or_cover_path is None
    assert tiktok_variant.packaging_profile == "tiktok"
    assert tiktok_variant.subtitle_style == "short_burned_in"

    instagram_variant = by_platform["instagram_reels"]
    assert instagram_variant.thumbnail_or_cover_path is None
    assert instagram_variant.packaging_profile == "instagram_reel"
    assert instagram_variant.subtitle_style == "short_burned_in"

    variants_file = repository.save_variants(export_path, variants)
    assert os.path.exists(variants_file)

    loaded_variants = repository.load_variants(export_path)
    assert len(loaded_variants) == 3

    loaded_youtube = repository.get_variant_by_platform(export_path, "youtube")
    assert loaded_youtube is not None
    assert loaded_youtube.target_platform.value == "youtube"
    assert loaded_youtube.variant_kind == "platform_variant"

    print("CONTENT VARIANT BUILDER/REPOSITORY SMOKE TEST PASSED")


if __name__ == "__main__":
    main()