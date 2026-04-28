from __future__ import annotations

import shutil
from pathlib import Path

from core.normalized_metrics_repository import NormalizedMetricsRepository
from core.platform_raw_metrics_repository import PlatformRawMetricsRepository
from core.publish_result_metrics_bridge import PublishResultMetricsBridge
from core.publish_result_repository import PublishResultRepository
from models.publish_result import PublishResult
from shared.enums import ChannelType, PlatformType


def run() -> None:
    test_dir = Path("tmp/publish_result_metrics_bridge_test")

    if test_dir.exists():
        shutil.rmtree(test_dir)

    test_dir.mkdir(parents=True, exist_ok=True)

    publish_result_repository = PublishResultRepository()
    bridge = PublishResultMetricsBridge()
    raw_repository = PlatformRawMetricsRepository()
    normalized_repository = NormalizedMetricsRepository()

    publish_results = [
        PublishResult(
            job_id="job_bridge_youtube",
            platform=PlatformType.YOUTUBE,
            publish_status="published",
            message="YouTube publish success",
            platform_video_id="yt_bridge_001",
            variant_id="variant_bridge_youtube_001",
            backend_name="youtube",
            public_url="https://youtube.com/watch?v=yt_bridge_001",
            error_message=None,
            published_at="2026-04-15T11:00:00+00:00",
        ),
        PublishResult(
            job_id="job_bridge_tiktok",
            platform=PlatformType.TIKTOK,
            publish_status="published",
            message="TikTok publish success",
            platform_video_id="tt_bridge_001",
            variant_id="variant_bridge_tiktok_001",
            backend_name="tiktok",
            public_url=None,
            error_message=None,
            published_at="2026-04-15T11:05:00+00:00",
        ),
    ]

    publish_result_repository.save_results(
        export_path=str(test_dir),
        publish_results=publish_results,
    )

    bridge.sync_platform_metrics(
        export_path=str(test_dir),
        channel_type=ChannelType.GAMING_MAIN,
        target_platform=PlatformType.YOUTUBE,
        raw_metrics={
            "views": 2100,
            "likes": 240,
            "comments": 21,
            "shares": 12,
            "ctr": 5.1,
            "average_view_duration_seconds": 61.4,
            "completion_rate": 33.8,
            "average_percentage_viewed": 66.2,
        },
        raw_source="bridge_youtube_test",
    )

    bridge.sync_platform_metrics(
        export_path=str(test_dir),
        channel_type=ChannelType.GAMING_UNCUT,
        target_platform=PlatformType.TIKTOK,
        raw_metrics={
            "views": 8700,
            "likes": 690,
            "comments": 48,
            "shares": 91,
            "saves": 77,
            "ctr": None,
            "average_view_duration_seconds": 24.9,
            "completion_rate": 51.6,
            "retention_rate": 60.3,
        },
        raw_source="bridge_tiktok_test",
    )

    raw_snapshots = raw_repository.load_snapshots(str(test_dir))
    normalized_snapshots = normalized_repository.load_snapshots(str(test_dir))

    assert len(raw_snapshots) == 2, "Expected 2 raw metric snapshots"
    assert len(normalized_snapshots) == 2, "Expected 2 normalized metric snapshots"

    youtube_snapshot = normalized_repository.get_latest_snapshot(
        storage_path=str(test_dir),
        variant_id="variant_bridge_youtube_001",
        target_platform=PlatformType.YOUTUBE.value,
    )
    assert youtube_snapshot is not None
    assert youtube_snapshot.job_id == "job_bridge_youtube"
    assert youtube_snapshot.platform_video_id == "yt_bridge_001"
    assert youtube_snapshot.channel_type == ChannelType.GAMING_MAIN
    assert youtube_snapshot.views == 2100
    assert youtube_snapshot.retention_rate == 66.2

    tiktok_snapshot = normalized_repository.get_latest_snapshot(
        storage_path=str(test_dir),
        variant_id="variant_bridge_tiktok_001",
        target_platform=PlatformType.TIKTOK.value,
    )
    assert tiktok_snapshot is not None
    assert tiktok_snapshot.job_id == "job_bridge_tiktok"
    assert tiktok_snapshot.platform_video_id == "tt_bridge_001"
    assert tiktok_snapshot.channel_type == ChannelType.GAMING_UNCUT
    assert tiktok_snapshot.views == 8700
    assert tiktok_snapshot.saves == 77
    assert tiktok_snapshot.retention_rate == 60.3

    print("PUBLISH RESULT METRICS BRIDGE SMOKE TEST PASSED")
    print(
        {
            "publish_results": len(publish_results),
            "raw_snapshots": len(raw_snapshots),
            "normalized_snapshots": len(normalized_snapshots),
            "test_dir": str(test_dir),
        }
    )


if __name__ == "__main__":
    run()