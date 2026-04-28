from __future__ import annotations

import shutil
from pathlib import Path

from core.kpi_dashboard_service import KpiDashboardService
from core.normalized_metrics_repository import NormalizedMetricsRepository
from core.performance_attribution_repository import PerformanceAttributionRepository
from models.normalized_metrics_snapshot import NormalizedMetricsSnapshot
from models.performance_attribution_snapshot import PerformanceAttributionSnapshot
from shared.enums import ChannelType, PlatformType


def run() -> None:
    test_dir = Path("tmp/kpi_dashboard_service_test")

    if test_dir.exists():
        shutil.rmtree(test_dir)

    (test_dir / "gaming_main" / "job_dash_001").mkdir(parents=True, exist_ok=True)
    (test_dir / "gaming_uncut" / "job_dash_002").mkdir(parents=True, exist_ok=True)

    normalized_repository = NormalizedMetricsRepository()
    attribution_repository = PerformanceAttributionRepository()
    service = KpiDashboardService()

    export_path_1 = str(test_dir / "gaming_main" / "job_dash_001")
    export_path_2 = str(test_dir / "gaming_uncut" / "job_dash_002")

    normalized_repository.save_snapshots(
        storage_path=export_path_1,
        snapshots=[
            NormalizedMetricsSnapshot(
                snapshot_id="metrics_dash_001",
                job_id="job_dash_001",
                variant_id="variant_dash_001",
                target_platform=PlatformType.YOUTUBE,
                channel_type=ChannelType.GAMING_MAIN,
                platform_video_id="yt_dash_001",
                published_at="2026-04-15T15:00:00+00:00",
                synced_at="2026-04-15T16:00:00+00:00",
                views=8400,
                likes=730,
                comments=60,
                shares=28,
                ctr=6.0,
                average_view_duration_seconds=70.0,
                completion_rate=38.0,
                retention_rate=66.0,
            )
        ],
    )

    normalized_repository.save_snapshots(
        storage_path=export_path_2,
        snapshots=[
            NormalizedMetricsSnapshot(
                snapshot_id="metrics_dash_002",
                job_id="job_dash_002",
                variant_id="variant_dash_002",
                target_platform=PlatformType.TIKTOK,
                channel_type=ChannelType.GAMING_UNCUT,
                platform_video_id="tt_dash_002",
                published_at="2026-04-15T15:10:00+00:00",
                synced_at="2026-04-15T16:10:00+00:00",
                views=2600,
                likes=140,
                comments=11,
                shares=15,
                saves=19,
                average_view_duration_seconds=19.0,
                completion_rate=27.0,
                retention_rate=36.0,
            )
        ],
    )

    attribution_repository.save_snapshots(
        storage_path=export_path_1,
        snapshots=[
            PerformanceAttributionSnapshot(
                attribution_id="attrib_dash_001",
                metrics_snapshot_id="metrics_dash_001",
                job_id="job_dash_001",
                variant_id="variant_dash_001",
                target_platform=PlatformType.YOUTUBE,
                channel_type=ChannelType.GAMING_MAIN,
                platform_video_id="yt_dash_001",
                variant_kind="platform_variant",
                packaging_profile="youtube",
                subtitle_style="youtube_standard",
                publish_status="published",
                guard_status="allow",
                published_at="2026-04-15T15:00:00+00:00",
                synced_at="2026-04-15T16:00:00+00:00",
            )
        ],
    )

    attribution_repository.save_snapshots(
        storage_path=export_path_2,
        snapshots=[
            PerformanceAttributionSnapshot(
                attribution_id="attrib_dash_002",
                metrics_snapshot_id="metrics_dash_002",
                job_id="job_dash_002",
                variant_id="variant_dash_002",
                target_platform=PlatformType.TIKTOK,
                channel_type=ChannelType.GAMING_UNCUT,
                platform_video_id="tt_dash_002",
                variant_kind="platform_variant",
                packaging_profile="tiktok",
                subtitle_style="short_burned_in",
                publish_status="published",
                guard_status="allow",
                published_at="2026-04-15T15:10:00+00:00",
                synced_at="2026-04-15T16:10:00+00:00",
            )
        ],
    )

    surface = service.build_surface(base_path=str(test_dir))

    assert surface["total_entries"] == 2, "Expected 2 KPI entries"
    assert len(surface["top_entries"]) == 2, "Expected 2 top entries"
    assert len(surface["low_entries"]) == 2, "Expected 2 low entries"
    assert len(surface["platform_stats"]) == 2, "Expected 2 platform stats"
    assert len(surface["channel_stats"]) == 2, "Expected 2 channel stats"
    assert len(surface["comparison_summaries"]) >= 2, "Expected comparison summaries"
    assert len(surface["insights"]) >= 2, "Expected insight summaries"

    assert surface["top_entries"][0]["variant_id"] == "variant_dash_001"
    assert surface["top_entries"][0]["target_platform"] == "youtube"
    assert surface["top_entries"][0]["is_winner"] is True

    assert surface["low_entries"][0]["variant_id"] == "variant_dash_002"

    platform_names = [item["platform"] for item in surface["platform_stats"]]
    assert "youtube" in platform_names
    assert "tiktok" in platform_names

    channel_names = [item["channel"] for item in surface["channel_stats"]]
    assert "gaming_main" in channel_names
    assert "gaming_uncut" in channel_names

    print("KPI DASHBOARD SERVICE SMOKE TEST PASSED")
    print(
        {
            "total_entries": surface["total_entries"],
            "platform_stats": len(surface["platform_stats"]),
            "channel_stats": len(surface["channel_stats"]),
            "insights": len(surface["insights"]),
            "top_variant": surface["top_entries"][0]["variant_id"],
        }
    )


if __name__ == "__main__":
    run()