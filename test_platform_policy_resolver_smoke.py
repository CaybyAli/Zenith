from core.platform_policy_resolver import PlatformPolicyResolver
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


def build_job(target_format: TargetFormat, target_platforms: list[str]) -> Job:
    return Job(
        job_id="job_platform_smoke",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=target_format,
        target_platforms=target_platforms,
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/sample.mp4",
    )


def main() -> None:
    resolver = PlatformPolicyResolver()

    short_job = build_job(
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube", "tiktok", "instagram_reels"],
    )

    youtube_policy = resolver.resolve_for_job_platform(short_job, "youtube")
    assert youtube_policy.platform.value == "youtube"
    assert youtube_policy.uploader_backend == "youtube"
    assert youtube_policy.thumbnail_required is True

    tiktok_policy = resolver.resolve_for_job_platform(short_job, "tiktok")
    assert tiktok_policy.platform.value == "tiktok"
    assert tiktok_policy.uploader_backend is None
    assert tiktok_policy.thumbnail_required is False
    assert tiktok_policy.preferred_aspect_ratio == "9:16"

    instagram_policy = resolver.resolve_for_job_platform(short_job, "instagram_reels")
    assert instagram_policy.platform.value == "instagram_reels"
    assert instagram_policy.uploader_backend is None
    assert instagram_policy.thumbnail_required is False
    assert instagram_policy.preferred_aspect_ratio == "9:16"

    longform_job = build_job(
        target_format=TargetFormat.LONGFORM,
        target_platforms=["tiktok"],
    )

    try:
        resolver.resolve_for_job_platform(longform_job, "tiktok")
    except ValueError as exc:
        assert "not allowed for platform" in str(exc)
    else:
        raise AssertionError("Expected ValueError for longform -> tiktok policy")

    print("PLATFORM POLICY RESOLVER SMOKE TEST PASSED")


if __name__ == "__main__":
    main()