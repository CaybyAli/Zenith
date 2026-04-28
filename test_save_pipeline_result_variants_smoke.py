import json
import os
import shutil

from app import save_pipeline_result
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


def build_job() -> Job:
    return Job(
        job_id="job_save_pipeline_variants_smoke",
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


def ensure_file(path: str, content: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)


def main() -> None:
    job = build_job()

    export_path = os.path.join("exports", job.channel_type.value, job.job_id)
    tmp_video_path = os.path.join("tmp", "save_pipeline_variants_video.mp4")
    tmp_thumbnail_path = os.path.join("tmp", "save_pipeline_variants_thumb.jpg")

    if os.path.exists(export_path):
        shutil.rmtree(export_path)

    ensure_file(tmp_video_path, b"fake video bytes")
    ensure_file(tmp_thumbnail_path, b"fake thumbnail bytes")

    title_package = TitlePackage(
        job_id=job.job_id,
        primary_title="Zenith Save Pipeline Variants Smoke",
        backup_titles=["Backup 1", "Backup 2"],
        title_score=8.2,
    )
    metadata = MetadataPackage(
        job_id=job.job_id,
        description="Save pipeline result with variants smoke description",
        hashtags=["#zenith", "#save", "#variants"],
    )
    thumbnail_package = ThumbnailPackage(
        job_id=job.job_id,
        selected_thumbnail=tmp_thumbnail_path,
        thumbnail_variants=[tmp_thumbnail_path],
        thumbnail_scores=[0.93],
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
    primary_publish_package = publish_packages[0]

    shorts_paths = []

    returned_export_path = save_pipeline_result(
        job=job,
        primary_publish_package=primary_publish_package,
        content_variants=content_variants,
        shorts_paths=shorts_paths,
        export_manager=ExportManager(),
        repo=JobRepository(),
    )

    assert returned_export_path == export_path
    assert os.path.exists(os.path.join(export_path, "job.json"))
    assert os.path.exists(os.path.join(export_path, "variants.json"))
    assert os.path.exists(os.path.join(export_path, "metadata.json"))
    assert os.path.exists(os.path.join(export_path, "video.mp4"))
    assert os.path.exists(os.path.join(export_path, "thumbnail.jpg"))

    with open(os.path.join(export_path, "job.json"), "r", encoding="utf-8") as f:
        job_data = json.load(f)

    assert job_data["job_id"] == job.job_id
    assert job_data["platform_targets"] == ["youtube", "tiktok", "instagram_reels"]

    loaded_variants = ContentVariantRepository().load_variants(export_path)
    assert len(loaded_variants) == 3
    assert all(variant.source_export_path == export_path for variant in loaded_variants)

    print("SAVE PIPELINE RESULT VARIANTS SMOKE TEST PASSED")


if __name__ == "__main__":
    main()