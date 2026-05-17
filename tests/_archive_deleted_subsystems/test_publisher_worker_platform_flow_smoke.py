from publisher_worker import (
    build_publish_packages_from_job_data,
    summarize_publish_results,
)
from models.publish_result import PublishResult
from shared.enums import PlatformType


def build_job_dict() -> dict:
    return {
        "job_id": "job_worker_platform_smoke",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube", "tiktok", "instagram_reels"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
        "raw_video_path": "inbox/gaming_main/sample.mp4",
        "title": "Zenith Worker Smoke",
        "description": "Worker platform smoke description",
    }


def main() -> None:
    job = build_job_dict()

    packages = build_publish_packages_from_job_data(
        job=job,
        video_path="exports/tmp/video.mp4",
        title=job["title"],
        description=job["description"],
        hashtags=["zenith", "worker", "smoke"],
        thumbnail_path="exports/tmp/thumb.jpg",
    )

    assert len(packages) == 3

    by_platform = {package.platform.value: package for package in packages}

    assert by_platform["youtube"].uploader_backend == "youtube"
    assert by_platform["youtube"].thumbnail_path == "exports/tmp/thumb.jpg"

    assert by_platform["tiktok"].uploader_backend is None
    assert by_platform["tiktok"].thumbnail_path is None

    assert by_platform["instagram_reels"].uploader_backend is None
    assert by_platform["instagram_reels"].thumbnail_path is None

    published_status, published_video_id = summarize_publish_results(
        [
            PublishResult(
                job_id=job["job_id"],
                platform=PlatformType.YOUTUBE,
                publish_status="published",
                message="youtube published",
                platform_video_id="yt_123",
            ),
            PublishResult(
                job_id=job["job_id"],
                platform=PlatformType.TIKTOK,
                publish_status="unsupported_backend",
                message="tiktok unsupported",
            ),
        ]
    )
    assert published_status == "published"
    assert published_video_id == "yt_123"

    approval_status, approval_video_id = summarize_publish_results(
        [
            PublishResult(
                job_id=job["job_id"],
                platform=PlatformType.TIKTOK,
                publish_status="queued_for_approval",
                message="tiktok queued",
            ),
            PublishResult(
                job_id=job["job_id"],
                platform=PlatformType.INSTAGRAM_REELS,
                publish_status="unsupported_backend",
                message="instagram unsupported",
            ),
        ]
    )
    assert approval_status == "queued_for_approval"
    assert approval_video_id is None

    resolved_status, resolved_video_id = summarize_publish_results(
        [
            PublishResult(
                job_id=job["job_id"],
                platform=PlatformType.TIKTOK,
                publish_status="unsupported_backend",
                message="tiktok unsupported",
            ),
            PublishResult(
                job_id=job["job_id"],
                platform=PlatformType.INSTAGRAM_REELS,
                publish_status="unsupported_backend",
                message="instagram unsupported",
            ),
        ]
    )
    assert resolved_status == "policy_resolved"
    assert resolved_video_id is None

    print("PUBLISHER WORKER PLATFORM FLOW SMOKE TEST PASSED")


if __name__ == "__main__":
    main()