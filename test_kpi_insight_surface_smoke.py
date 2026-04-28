from __future__ import annotations

from core.comparison_view_builder import ComparisonViewBuilder
from core.insight_surface_builder import InsightSurfaceBuilder
from core.kpi_view_builder import KpiViewBuilder
from models.normalized_metrics_snapshot import NormalizedMetricsSnapshot
from models.performance_attribution_snapshot import PerformanceAttributionSnapshot
from shared.enums import ChannelType, PlatformType


def run() -> None:
    metrics_snapshots = [
        NormalizedMetricsSnapshot(
            snapshot_id="metrics_view_001",
            job_id="job_view_001",
            variant_id="variant_view_001",
            target_platform=PlatformType.YOUTUBE,
            channel_type=ChannelType.GAMING_MAIN,
            platform_video_id="yt_view_001",
            published_at="2026-04-15T10:00:00+00:00",
            synced_at="2026-04-15T11:00:00+00:00",
            views=9000,
            likes=850,
            comments=71,
            shares=30,
            ctr=6.3,
            average_view_duration_seconds=74.1,
            completion_rate=40.5,
            retention_rate=69.0,
        ),
        NormalizedMetricsSnapshot(
            snapshot_id="metrics_view_002",
            job_id="job_view_002",
            variant_id="variant_view_002",
            target_platform=PlatformType.TIKTOK,
            channel_type=ChannelType.GAMING_UNCUT,
            platform_video_id="tt_view_002",
            published_at="2026-04-15T10:10:00+00:00",
            synced_at="2026-04-15T11:10:00+00:00",
            views=6200,
            likes=460,
            comments=39,
            shares=64,
            saves=88,
            average_view_duration_seconds=28.3,
            completion_rate=52.4,
            retention_rate=61.8,
        ),
        NormalizedMetricsSnapshot(
            snapshot_id="metrics_view_003",
            job_id="job_view_003",
            variant_id="variant_view_003",
            target_platform=PlatformType.INSTAGRAM_REELS,
            channel_type=ChannelType.FACELESS_TREND,
            platform_video_id="ig_view_003",
            published_at="2026-04-15T10:20:00+00:00",
            synced_at="2026-04-15T11:20:00+00:00",
            views=1800,
            likes=90,
            comments=7,
            shares=4,
            saves=9,
            average_view_duration_seconds=14.2,
            completion_rate=22.0,
            retention_rate=31.5,
        ),
    ]

    attribution_snapshots = [
        PerformanceAttributionSnapshot(
            attribution_id="attrib_view_001",
            metrics_snapshot_id="metrics_view_001",
            job_id="job_view_001",
            variant_id="variant_view_001",
            target_platform=PlatformType.YOUTUBE,
            channel_type=ChannelType.GAMING_MAIN,
            platform_video_id="yt_view_001",
            variant_kind="platform_variant",
            packaging_profile="youtube",
            subtitle_style="youtube_standard",
            publish_status="published",
            published_at="2026-04-15T10:00:00+00:00",
            synced_at="2026-04-15T11:00:00+00:00",
        ),
        PerformanceAttributionSnapshot(
            attribution_id="attrib_view_002",
            metrics_snapshot_id="metrics_view_002",
            job_id="job_view_002",
            variant_id="variant_view_002",
            target_platform=PlatformType.TIKTOK,
            channel_type=ChannelType.GAMING_UNCUT,
            platform_video_id="tt_view_002",
            variant_kind="platform_variant",
            packaging_profile="tiktok",
            subtitle_style="short_burned_in",
            publish_status="published",
            published_at="2026-04-15T10:10:00+00:00",
            synced_at="2026-04-15T11:10:00+00:00",
        ),
        PerformanceAttributionSnapshot(
            attribution_id="attrib_view_003",
            metrics_snapshot_id="metrics_view_003",
            job_id="job_view_003",
            variant_id="variant_view_003",
            target_platform=PlatformType.INSTAGRAM_REELS,
            channel_type=ChannelType.FACELESS_TREND,
            platform_video_id="ig_view_003",
            variant_kind="platform_variant",
            packaging_profile="instagram_reel",
            subtitle_style="short_burned_in",
            publish_status="published",
            published_at="2026-04-15T10:20:00+00:00",
            synced_at="2026-04-15T11:20:00+00:00",
        ),
    ]

    kpi_builder = KpiViewBuilder()
    comparison_builder = ComparisonViewBuilder()
    insight_builder = InsightSurfaceBuilder()

    entries = kpi_builder.build_entries(
        metrics_snapshots=metrics_snapshots,
        attribution_snapshots=attribution_snapshots,
    )
    comparison_summaries = comparison_builder.build_all_summaries(entries)
    insights = insight_builder.build_insights(entries, comparison_summaries)

    assert len(entries) == 3, "Expected 3 KPI view entries"
    assert len(comparison_summaries) >= 3, "Expected grouped comparison summaries"
    assert len(insights) >= 3, "Expected insight summaries"

    overall_sorted = sorted(
        entries,
        key=lambda item: item.performance_score or 0.0,
        reverse=True,
    )

    assert overall_sorted[0].variant_id == "variant_view_001"
    assert overall_sorted[0].is_winner is True
    assert overall_sorted[-1].variant_id == "variant_view_003"
    assert overall_sorted[-1].is_loser is True

    top_entry = next(
        entry for entry in entries if entry.variant_id == "variant_view_001"
    )
    assert top_entry.rank_overall == 1
    assert top_entry.target_platform == PlatformType.YOUTUBE
    assert top_entry.packaging_profile == "youtube"
    assert top_entry.subtitle_style == "youtube_standard"
    assert top_entry.comparison_status in {
        "above_average",
        "near_average",
        "below_average",
    }

    platform_summaries = [
        summary
        for summary in comparison_summaries
        if summary.comparison_type == "platform"
    ]
    assert platform_summaries, "Expected platform comparison summaries"

    insight_titles = [insight.title for insight in insights]
    assert "Top performer detected" in insight_titles
    assert "Low performer detected" in insight_titles

    print("KPI INSIGHT SURFACE SMOKE TEST PASSED")
    print(
        {
            "entries": len(entries),
            "comparison_summaries": len(comparison_summaries),
            "insights": len(insights),
            "top_variant": overall_sorted[0].variant_id,
            "low_variant": overall_sorted[-1].variant_id,
        }
    )


if __name__ == "__main__":
    run()