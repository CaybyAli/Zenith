from __future__ import annotations

import shutil
from pathlib import Path

from core.metrics_sync_manager import MetricsSyncManager
from core.normalized_metrics_repository import NormalizedMetricsRepository
from core.platform_raw_metrics_repository import PlatformRawMetricsRepository
from models.publish_result import PublishResult
from shared.enums import ChannelType, PlatformType


def run() -> None:
    test_dir = Path("tmp/unified_metrics_layer_test")

    if test_dir.exists():
        shutil.rmtree(test_dir)

    test_dir.mkdir(parents=True, exist_ok=True)

    manager = MetricsSyncManager()
    raw_repository = PlatformRawMetricsRepository()
    normalized_repository = NormalizedMetricsRepository()

    youtube_result = PublishResult(
        job_id="job_metrics_youtube",
        platform=PlatformType.YOUTUBE,
        publish_status="published",
        message="YouTube publish success",
        platform_video_id="yt_video_001",
        variant_id="variant_youtube_001",
        backend_name="youtube",
        public_url="https://youtube.com/watch?v=yt_video_001",
        error_message=None,
        published_at="2026-04-15T10:00:00+00:00",
    )

    tiktok_result = PublishResult(
        job_id="job_metrics_tiktok",
        platform=PlatformType.TIKTOK,
        publish_status="published",
        message="TikTok publish success",
        platform_video_id="tt_video_001",
        variant_id="variant_tiktok_001",
        backend_name="tiktok",
        public_url=None,
        error_message=None,
        published_at="2026-04-15T10:05:00+00:00",
    )

    instagram_result = PublishResult(
        job_id="job_metrics_instagram",
        platform=PlatformType.INSTAGRAM_REELS,
        publish_status="published",
        message="Instagram publish success",
        platform_video_id="ig_video_001",
        variant_id="variant_instagram_001",
        backend_name="instagram_reels",
        public_url=None,
        error_message=None,
        published_at="2026-04-15T10:10:00+00:00",
    )

    manager.sync_from_publish_result(
        publish_result=youtube_result,
        channel_type=ChannelType.GAMING_MAIN,
        storage_path=str(test_dir),
        raw_metrics={
            "views": 1200,
            "likes": 140,
            "comments": 18,
            "shares": 6,
            "ctr": 4.2,
            "average_view_duration_seconds": 52.5,
            "completion_rate": 31.0,
            "average_percentage_viewed": 63.4,
        },
        raw_source="youtube_manual_test",
    )

    manager.sync_from_publish_result(
        publish_result=tiktok_result,
        channel_type=ChannelType.GAMING_UNCUT,
        storage_path=str(test_dir),
        raw_metrics={
            "views": 5400,
            "likes": 420,
            "comments": 36,
            "shares": 55,
            "saves": 61,
            "ctr": None,
            "average_view_duration_seconds": 21.8,
            "completion_rate": 47.5,
            "retention_rate": 58.2,
        },
        raw_source="tiktok_manual_test",
    )

    manager.sync_from_publish_result(
        publish_result=instagram_result,
        channel_type=ChannelType.FACELESS_TREND,
        storage_path=str(test_dir),
        raw_metrics={
            "views": 3100,
            "likes": 280,
            "comments": 22,
            "shares": 19,
            "saves": 34,
            "ctr": None,
            "average_view_duration_seconds": 18.6,
            "completion_rate": 41.3,
            "retention_rate": 49.7,
        },
        raw_source="instagram_manual_test",
    )

    raw_snapshots = raw_repository.load_snapshots(str(test_dir))
    normalized_snapshots = normalized_repository.load_snapshots(str(test_dir))

    assert len(raw_snapshots) == 3, "Expected 3 raw metric snapshots"
    assert len(normalized_snapshots) == 3, "Expected 3 normalized metric snapshots"

    youtube_snapshot = normalized_repository.get_latest_snapshot(
        storage_path=str(test_dir),
        variant_id="variant_youtube_001",
        target_platform=PlatformType.YOUTUBE.value,
    )
    assert youtube_snapshot is not None
    assert youtube_snapshot.job_id == "job_metrics_youtube"
    assert youtube_snapshot.channel_type == ChannelType.GAMING_MAIN
    assert youtube_snapshot.views == 1200
    assert youtube_snapshot.likes == 140
    assert youtube_snapshot.comments == 18
    assert youtube_snapshot.shares == 6
    assert youtube_snapshot.saves is None
    assert youtube_snapshot.ctr == 4.2
    assert youtube_snapshot.average_view_duration_seconds == 52.5
    assert youtube_snapshot.completion_rate == 31.0
    assert youtube_snapshot.retention_rate == 63.4

    tiktok_snapshot = normalized_repository.get_latest_snapshot(
        storage_path=str(test_dir),
        variant_id="variant_tiktok_001",
        target_platform=PlatformType.TIKTOK.value,
    )
    assert tiktok_snapshot is not None
    assert tiktok_snapshot.job_id == "job_metrics_tiktok"
    assert tiktok_snapshot.channel_type == ChannelType.GAMING_UNCUT
    assert tiktok_snapshot.views == 5400
    assert tiktok_snapshot.likes == 420
    assert tiktok_snapshot.comments == 36
    assert tiktok_snapshot.shares == 55
    assert tiktok_snapshot.saves == 61
    assert tiktok_snapshot.ctr is None
    assert tiktok_snapshot.average_view_duration_seconds == 21.8
    assert tiktok_snapshot.completion_rate == 47.5
    assert tiktok_snapshot.retention_rate == 58.2

    instagram_snapshot = normalized_repository.get_latest_snapshot(
        storage_path=str(test_dir),
        variant_id="variant_instagram_001",
        target_platform=PlatformType.INSTAGRAM_REELS.value,
    )
    assert instagram_snapshot is not None
    assert instagram_snapshot.job_id == "job_metrics_instagram"
    assert instagram_snapshot.channel_type == ChannelType.FACELESS_TREND
    assert instagram_snapshot.views == 3100
    assert instagram_snapshot.likes == 280
    assert instagram_snapshot.comments == 22
    assert instagram_snapshot.shares == 19
    assert instagram_snapshot.saves == 34
    assert instagram_snapshot.ctr is None
    assert instagram_snapshot.average_view_duration_seconds == 18.6
    assert instagram_snapshot.completion_rate == 41.3
    assert instagram_snapshot.retention_rate == 49.7

    print("UNIFIED METRICS LAYER SMOKE TEST PASSED")
    print(
        {
            "raw_snapshots": len(raw_snapshots),
            "normalized_snapshots": len(normalized_snapshots),
            "test_dir": str(test_dir),
        }
    )


if __name__ == "__main__":
    run()