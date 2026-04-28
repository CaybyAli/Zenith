from __future__ import annotations

import shutil
from pathlib import Path

from core.metrics_attribution_bridge import MetricsAttributionBridge
from core.normalized_metrics_repository import NormalizedMetricsRepository
from core.performance_attribution_repository import PerformanceAttributionRepository
from core.publish_result_repository import PublishResultRepository
from models.content_variant import ContentVariant
from models.normalized_metrics_snapshot import NormalizedMetricsSnapshot
from models.publish_result import PublishResult
from shared.enums import ChannelType, PlatformType


def run() -> None:
    test_dir = Path("tmp/performance_attribution_test")

    if test_dir.exists():
        shutil.rmtree(test_dir)

    test_dir.mkdir(parents=True, exist_ok=True)

    normalized_metrics_repository = NormalizedMetricsRepository()
    publish_result_repository = PublishResultRepository()
    attribution_repository = PerformanceAttributionRepository()
    bridge = MetricsAttributionBridge()

    content_variant = ContentVariant(
        variant_id="variant_attr_001",
        job_id="job_attr_001",
        channel_type=ChannelType.GAMING_MAIN,
        target_platform=PlatformType.YOUTUBE,
        variant_kind="platform_variant",
        video_path="exports/gaming_main/job_attr_001/video.mp4",
        thumbnail_or_cover_path="exports/gaming_main/job_attr_001/thumbnail.jpg",
        subtitle_path="exports/gaming_main/job_attr_001/subtitles.srt",
        title="Top Hook Title",
        description="High energy gaming clip for YouTube",
        hashtags=["#gaming", "#zenith", "#youtube"],
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

    normalized_metrics_snapshot = NormalizedMetricsSnapshot(
        snapshot_id="metrics_attr_001",
        job_id="job_attr_001",
        variant_id="variant_attr_001",
        target_platform=PlatformType.YOUTUBE,
        channel_type=ChannelType.GAMING_MAIN,
        platform_video_id="yt_attr_001",
        published_at="2026-04-15T12:00:00+00:00",
        synced_at="2026-04-15T13:00:00+00:00",
        views=4200,
        likes=380,
        comments=44,
        shares=17,
        saves=None,
        ctr=5.8,
        average_view_duration_seconds=68.2,
        completion_rate=36.4,
        retention_rate=64.8,
        source_snapshot_id="metrics_attr_001",
    )

    publish_result = PublishResult(
        job_id="job_attr_001",
        platform=PlatformType.YOUTUBE,
        publish_status="published",
        message="YouTube publish success",
        platform_video_id="yt_attr_001",
        variant_id="variant_attr_001",
        backend_name="youtube",
        public_url="https://youtube.com/watch?v=yt_attr_001",
        error_message=None,
        published_at="2026-04-15T12:00:00+00:00",
    )

    normalized_metrics_repository.save_snapshots(
        storage_path=str(test_dir),
        snapshots=[normalized_metrics_snapshot],
    )
    publish_result_repository.save_results(
        export_path=str(test_dir),
        publish_results=[publish_result],
    )

    attribution_snapshot = bridge.build_and_store_attribution(
        export_path=str(test_dir),
        content_variant=content_variant,
        target_platform=PlatformType.YOUTUBE,
        guard_status="allow",
        attribution_notes="Initial attribution smoke test",
    )

    stored_snapshots = attribution_repository.load_snapshots(str(test_dir))
    assert len(stored_snapshots) == 1, "Expected 1 attribution snapshot"

    latest_snapshot = attribution_repository.get_latest_snapshot(
        storage_path=str(test_dir),
        variant_id="variant_attr_001",
        target_platform=PlatformType.YOUTUBE.value,
    )
    assert latest_snapshot is not None
    assert latest_snapshot.attribution_id == attribution_snapshot.attribution_id
    assert latest_snapshot.metrics_snapshot_id == "metrics_attr_001"
    assert latest_snapshot.job_id == "job_attr_001"
    assert latest_snapshot.variant_id == "variant_attr_001"
    assert latest_snapshot.target_platform == PlatformType.YOUTUBE
    assert latest_snapshot.channel_type == ChannelType.GAMING_MAIN
    assert latest_snapshot.platform_video_id == "yt_attr_001"
    assert latest_snapshot.variant_kind == "platform_variant"
    assert latest_snapshot.packaging_profile == "youtube"
    assert latest_snapshot.subtitle_style == "youtube_standard"
    assert latest_snapshot.publish_status == "published"
    assert latest_snapshot.guard_status == "allow"
    assert latest_snapshot.published_at == "2026-04-15T12:00:00+00:00"
    assert latest_snapshot.synced_at == "2026-04-15T13:00:00+00:00"
    assert latest_snapshot.attribution_notes == "Initial attribution smoke test"

    assert latest_snapshot.publish_reference["platform"] == "youtube"
    assert latest_snapshot.publish_reference["publish_status"] == "published"
    assert latest_snapshot.publish_reference["backend_name"] == "youtube"
    assert latest_snapshot.publish_reference["public_url"] == "https://youtube.com/watch?v=yt_attr_001"

    assert latest_snapshot.metadata_context_snapshot["title"] == "Top Hook Title"
    assert latest_snapshot.metadata_context_snapshot["description"] == "High energy gaming clip for YouTube"
    assert latest_snapshot.metadata_context_snapshot["hashtags"] == ["#gaming", "#zenith", "#youtube"]

    assert latest_snapshot.policy_snapshot["title_mode"] == "youtube_title"
    assert latest_snapshot.policy_snapshot["packaging_profile"] == "youtube"

    print("PERFORMANCE ATTRIBUTION SMOKE TEST PASSED")
    print(
        {
            "attribution_id": latest_snapshot.attribution_id,
            "stored_snapshots": len(stored_snapshots),
            "test_dir": str(test_dir),
        }
    )


if __name__ == "__main__":
    run()