from __future__ import annotations

import shutil
from pathlib import Path

from core.metrics_attribution_bridge import MetricsAttributionBridge
from core.normalized_metrics_repository import NormalizedMetricsRepository
from core.performance_attribution_repository import PerformanceAttributionRepository
from core.platform_raw_metrics_repository import PlatformRawMetricsRepository
from core.publish_result_metrics_bridge import PublishResultMetricsBridge
from core.publish_result_repository import PublishResultRepository
from models.content_variant import ContentVariant
from models.publish_result import PublishResult
from shared.enums import ChannelType, PlatformType


def run() -> None:
    test_dir = Path("tmp/metrics_to_attribution_chain_test")

    if test_dir.exists():
        shutil.rmtree(test_dir)

    test_dir.mkdir(parents=True, exist_ok=True)

    publish_result_repository = PublishResultRepository()
    raw_repository = PlatformRawMetricsRepository()
    normalized_repository = NormalizedMetricsRepository()
    attribution_repository = PerformanceAttributionRepository()

    metrics_bridge = PublishResultMetricsBridge()
    attribution_bridge = MetricsAttributionBridge()

    publish_result = PublishResult(
        job_id="job_chain_001",
        platform=PlatformType.YOUTUBE,
        publish_status="published",
        message="YouTube publish success",
        platform_video_id="yt_chain_001",
        variant_id="variant_chain_001",
        backend_name="youtube",
        public_url="https://youtube.com/watch?v=yt_chain_001",
        error_message=None,
        published_at="2026-04-15T14:00:00+00:00",
    )

    publish_result_repository.save_results(
        export_path=str(test_dir),
        publish_results=[publish_result],
    )

    metrics_bridge.sync_platform_metrics(
        export_path=str(test_dir),
        channel_type=ChannelType.GAMING_MAIN,
        target_platform=PlatformType.YOUTUBE,
        raw_metrics={
            "views": 7300,
            "likes": 640,
            "comments": 58,
            "shares": 23,
            "ctr": 6.4,
            "average_view_duration_seconds": 72.3,
            "completion_rate": 39.1,
            "average_percentage_viewed": 67.5,
        },
        raw_source="chain_youtube_test",
    )

    content_variant = ContentVariant(
        variant_id="variant_chain_001",
        job_id="job_chain_001",
        channel_type=ChannelType.GAMING_MAIN,
        target_platform=PlatformType.YOUTUBE,
        variant_kind="platform_variant",
        video_path="exports/gaming_main/job_chain_001/video.mp4",
        thumbnail_or_cover_path="exports/gaming_main/job_chain_001/thumbnail.jpg",
        subtitle_path="exports/gaming_main/job_chain_001/subtitles.srt",
        title="Chain Test Title",
        description="Unified metrics to attribution chain test",
        hashtags=["#gaming", "#chain", "#zenith"],
        packaging_profile="youtube",
        subtitle_style="youtube_standard",
        platform_policy_snapshot={
            "title_mode": "youtube_title",
            "description_mode": "youtube_description",
            "hashtags_mode": "youtube_optional",
            "subtitle_style": "youtube_standard",
            "packaging_profile": "youtube",
        },
    )

    attribution_snapshot = attribution_bridge.build_and_store_attribution(
        export_path=str(test_dir),
        content_variant=content_variant,
        target_platform=PlatformType.YOUTUBE,
        guard_status="allow",
        attribution_notes="End to end metrics to attribution chain",
    )

    raw_snapshots = raw_repository.load_snapshots(str(test_dir))
    normalized_snapshots = normalized_repository.load_snapshots(str(test_dir))
    attribution_snapshots = attribution_repository.load_snapshots(str(test_dir))

    assert len(raw_snapshots) == 1, "Expected 1 raw metrics snapshot"
    assert len(normalized_snapshots) == 1, "Expected 1 normalized metrics snapshot"
    assert len(attribution_snapshots) == 1, "Expected 1 attribution snapshot"

    latest_normalized = normalized_repository.get_latest_snapshot(
        storage_path=str(test_dir),
        variant_id="variant_chain_001",
        target_platform=PlatformType.YOUTUBE.value,
    )
    assert latest_normalized is not None
    assert latest_normalized.views == 7300
    assert latest_normalized.retention_rate == 67.5

    latest_attribution = attribution_repository.get_latest_snapshot(
        storage_path=str(test_dir),
        variant_id="variant_chain_001",
        target_platform=PlatformType.YOUTUBE.value,
    )
    assert latest_attribution is not None
    assert latest_attribution.attribution_id == attribution_snapshot.attribution_id
    assert latest_attribution.metrics_snapshot_id == latest_normalized.snapshot_id
    assert latest_attribution.job_id == "job_chain_001"
    assert latest_attribution.variant_id == "variant_chain_001"
    assert latest_attribution.platform_video_id == "yt_chain_001"
    assert latest_attribution.packaging_profile == "youtube"
    assert latest_attribution.subtitle_style == "youtube_standard"
    assert latest_attribution.publish_status == "published"
    assert latest_attribution.guard_status == "allow"
    assert latest_attribution.publish_reference["platform"] == "youtube"
    assert latest_attribution.publish_reference["backend_name"] == "youtube"
    assert latest_attribution.metadata_context_snapshot["title"] == "Chain Test Title"
    assert latest_attribution.policy_snapshot["title_mode"] == "youtube_title"

    print("METRICS TO ATTRIBUTION CHAIN SMOKE TEST PASSED")
    print(
        {
            "raw_snapshots": len(raw_snapshots),
            "normalized_snapshots": len(normalized_snapshots),
            "attribution_snapshots": len(attribution_snapshots),
            "attribution_id": latest_attribution.attribution_id,
            "test_dir": str(test_dir),
        }
    )


if __name__ == "__main__":
    run()