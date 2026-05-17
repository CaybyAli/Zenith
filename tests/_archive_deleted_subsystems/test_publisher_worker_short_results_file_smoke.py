import os
import shutil

import publisher_worker
from core.cross_platform_publish_orchestrator import CrossPlatformPublishOrchestrator
from core.publish_result_repository import PublishResultRepository
from models.publish_decision import PublishDecision
from models.publish_result import PublishResult
from shared.enums import PlatformType, TargetFormat


class FakePublisher:
    def publish(self, publish_package, publish_decision):
        if publish_package.platform == PlatformType.YOUTUBE:
            return PublishResult(
                job_id=publish_package.job_id,
                platform=publish_package.platform,
                publish_status="published",
                message="youtube short published",
                platform_video_id="yt_short_results_123",
                variant_id=publish_package.variant_id,
                backend_name="youtube",
                public_url="https://youtube.com/watch?v=yt_short_results_123",
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


def build_job_dict() -> dict:
    return {
        "job_id": "job_short_results_file_smoke",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube", "tiktok", "instagram_reels"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "safe_auto",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
        "raw_video_path": "inbox/gaming_main/sample.mp4",
        "title": "Zenith Short Results File Smoke",
        "description": "Short results file smoke description",
        "video_path": "exports/tmp/video.mp4",
        "thumbnail_path": "exports/tmp/thumb.jpg",
    }


def main() -> None:
    export_path = os.path.join("tmp", "publisher_worker_short_results_file_test")
    if os.path.exists(export_path):
        shutil.rmtree(export_path)
    os.makedirs(export_path, exist_ok=True)

    publisher_worker.cross_platform_publish_orchestrator = CrossPlatformPublishOrchestrator(
        publisher=FakePublisher(),
        publish_result_repository=PublishResultRepository(),
    )

    job = build_job_dict()
    short_id = "short_1"

    publish_packages = publisher_worker.build_publish_packages_from_job_data(
        job=job,
        video_path="exports/tmp/short_1.mp4",
        title=f'{job["title"]} [{short_id}]',
        description=job["description"],
        hashtags=[],
        thumbnail_path=job["thumbnail_path"],
        short_id=short_id,
        target_format_override=TargetFormat.SHORT,
        platform_targets_override=["youtube", "tiktok", "instagram_reels"],
    )

    publish_decision = PublishDecision(
        job_id=job["job_id"],
        decision="autopublish_allowed",
        reason="short results file smoke",
    )

    results_filename = publisher_worker.get_short_results_filename(short_id)

    results = publisher_worker.execute_publish_packages(
        publish_packages=publish_packages,
        publish_decision=publish_decision,
        export_path=export_path,
        results_filename=results_filename,
    )

    assert len(results) == 3

    by_platform = {result.platform.value: result for result in results}
    assert by_platform["youtube"].publish_status == "published"
    assert by_platform["tiktok"].publish_status == "unsupported_backend"
    assert by_platform["instagram_reels"].publish_status == "unsupported_backend"

    short_results_path = os.path.join(export_path, results_filename)
    assert os.path.exists(short_results_path)

    loaded_short_results = PublishResultRepository().load_results(
        export_path,
        results_filename=results_filename,
    )
    assert len(loaded_short_results) == 3

    default_results = PublishResultRepository().load_results(export_path)
    assert default_results == []

    print("PUBLISHER WORKER SHORT RESULTS FILE SMOKE TEST PASSED")


if __name__ == "__main__":
    main()