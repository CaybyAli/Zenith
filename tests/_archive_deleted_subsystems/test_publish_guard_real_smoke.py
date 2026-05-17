import os
import shutil

from core.content_variant_repository import ContentVariantRepository
from core.publish_guard import PublishGuard
from core.publish_result_repository import PublishResultRepository
from models.content_variant import ContentVariant
from models.publish_package import PublishPackage
from models.publish_result import PublishResult
from shared.enums import ChannelType, PlatformType, TargetFormat


TEST_EXPORTS_BASE = os.path.join("tmp", "publish_guard_real_smoke_exports")


def make_export_path(job_id: str) -> str:
    return os.path.join(TEST_EXPORTS_BASE, "gaming_main", job_id)


def build_variant(
    *,
    variant_id: str,
    job_id: str,
    platform: PlatformType,
    video_path: str,
    title: str,
    description: str,
    packaging_profile: str = "standard",
) -> ContentVariant:
    return ContentVariant(
        variant_id=variant_id,
        job_id=job_id,
        channel_type=ChannelType.GAMING_MAIN,
        target_platform=platform,
        variant_kind="platform_variant",
        video_path=video_path,
        thumbnail_or_cover_path="exports/tmp/thumb.jpg",
        subtitle_path=None,
        title=title,
        description=description,
        hashtags=["#zenith", "#guard"],
        variant_status="built",
        source_export_path=None,
        packaging_profile=packaging_profile,
        subtitle_style="standard",
        platform_policy_snapshot={},
        needs_rebuild=False,
        build_notes=None,
    )


def build_result(
    *,
    job_id: str,
    platform: PlatformType,
    variant_id: str,
    platform_video_id: str,
) -> PublishResult:
    return PublishResult(
        job_id=job_id,
        platform=platform,
        publish_status="published",
        message="already published",
        platform_video_id=platform_video_id,
        variant_id=variant_id,
        backend_name="youtube" if platform == PlatformType.YOUTUBE else None,
        public_url=None,
        error_message=None,
        published_at="2026-04-14T12:00:00+00:00",
    )


def build_package(
    *,
    job_id: str,
    variant_id: str,
    platform: PlatformType,
    video_path: str,
    title: str,
    description: str,
    packaging_profile: str = "standard",
) -> PublishPackage:
    return PublishPackage(
        job_id=job_id,
        video_path=video_path,
        title=title,
        description=description,
        hashtags=["#zenith", "#guard"],
        thumbnail_path="exports/tmp/thumb.jpg",
        platform=platform,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        requires_manual_approval=False,
        title_mode="standard",
        description_mode="standard",
        hashtags_mode="standard",
        subtitle_style="standard",
        packaging_profile=packaging_profile,
        length_profile="standard",
        preferred_aspect_ratio="9:16",
        thumbnail_required=True,
        uploader_backend="youtube" if platform == PlatformType.YOUTUBE else None,
        variant_id=variant_id,
    )


def main() -> None:
    if os.path.exists(TEST_EXPORTS_BASE):
        shutil.rmtree(TEST_EXPORTS_BASE)

    variant_repo = ContentVariantRepository()
    result_repo = PublishResultRepository()

    # 1) Exact duplicate on same platform -> block
    export_path_dup = make_export_path("job_dup_ref")
    os.makedirs(export_path_dup, exist_ok=True)

    duplicate_variant = build_variant(
        variant_id="variant_dup_youtube",
        job_id="job_dup_ref",
        platform=PlatformType.YOUTUBE,
        video_path="exports/tmp/video_dup.mp4",
        title="Zenith Duplicate Reference",
        description="duplicate reference description",
    )
    variant_repo.save_variants(export_path_dup, [duplicate_variant])

    duplicate_result = build_result(
        job_id="job_dup_ref",
        platform=PlatformType.YOUTUBE,
        variant_id="variant_dup_youtube",
        platform_video_id="yt_dup_ref_123",
    )
    result_repo.save_results(export_path_dup, [duplicate_result])

    guard = PublishGuard(exports_base_path=TEST_EXPORTS_BASE)

    duplicate_package = build_package(
        job_id="job_dup_candidate",
        variant_id="variant_dup_youtube",
        platform=PlatformType.YOUTUBE,
        video_path="exports/tmp/video_dup.mp4",
        title="Zenith Duplicate Reference",
        description="duplicate reference description",
    )

    duplicate_guard = guard.evaluate_package(duplicate_package)
    assert duplicate_guard.guard_status == "block"
    assert "duplicate_variant" in duplicate_guard.risk_flags

    # 2) Same job, other platform, very similar material -> warn
    export_path_warn = make_export_path("job_cross_ref")
    os.makedirs(export_path_warn, exist_ok=True)

    cross_variant = build_variant(
        variant_id="variant_cross_youtube",
        job_id="job_cross_ref",
        platform=PlatformType.YOUTUBE,
        video_path="exports/tmp/video_cross.mp4",
        title="Zenith Cross Platform Reference",
        description="cross platform description",
        packaging_profile="youtube",
    )
    variant_repo.save_variants(export_path_warn, [cross_variant])

    cross_result = build_result(
        job_id="job_cross_ref",
        platform=PlatformType.YOUTUBE,
        variant_id="variant_cross_youtube",
        platform_video_id="yt_cross_ref_123",
    )
    result_repo.save_results(export_path_warn, [cross_result])

    cross_package = build_package(
        job_id="job_cross_ref",
        variant_id="variant_cross_tiktok",
        platform=PlatformType.TIKTOK,
        video_path="exports/tmp/video_cross.mp4",
        title="Zenith Cross Platform Reference",
        description="cross platform description",
        packaging_profile="youtube",
    )

    cross_guard = guard.evaluate_package(cross_package)
    assert cross_guard.guard_status == "warn"
    assert "cross_platform_too_similar" in cross_guard.risk_flags
    assert cross_guard.requires_manual_review is True

    # 3) New material -> allow
    allow_package = build_package(
        job_id="job_allow_candidate",
        variant_id="variant_allow_youtube",
        platform=PlatformType.YOUTUBE,
        video_path="exports/tmp/video_allow.mp4",
        title="Completely New Material",
        description="brand new description",
        packaging_profile="fresh_profile",
    )

    allow_guard = guard.evaluate_package(allow_package)
    assert allow_guard.guard_status == "allow"
    assert allow_guard.risk_flags == []

    print("PUBLISH GUARD REAL SMOKE TEST PASSED")


if __name__ == "__main__":
    main()