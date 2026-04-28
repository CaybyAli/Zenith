from __future__ import annotations

from uuid import uuid4

from models.kpi_view_entry import KpiViewEntry
from models.normalized_metrics_snapshot import NormalizedMetricsSnapshot
from models.performance_attribution_snapshot import PerformanceAttributionSnapshot


def _safe_number(value: int | float | None) -> float:
    if value is None:
        return 0.0
    return float(value)


class KpiViewBuilder:
    def build_entries(
        self,
        metrics_snapshots: list[NormalizedMetricsSnapshot],
        attribution_snapshots: list[PerformanceAttributionSnapshot],
    ) -> list[KpiViewEntry]:
        attribution_by_metrics_id = {
            snapshot.metrics_snapshot_id: snapshot
            for snapshot in attribution_snapshots
        }

        entries: list[KpiViewEntry] = []

        for metrics_snapshot in metrics_snapshots:
            attribution_snapshot = attribution_by_metrics_id.get(
                metrics_snapshot.snapshot_id
            )

            entry = KpiViewEntry(
                view_id=f"kpi_{uuid4().hex[:12]}",
                job_id=metrics_snapshot.job_id,
                variant_id=metrics_snapshot.variant_id,
                target_platform=metrics_snapshot.target_platform,
                channel_type=metrics_snapshot.channel_type,
                metrics_snapshot_id=metrics_snapshot.snapshot_id,
                attribution_id=(
                    attribution_snapshot.attribution_id
                    if attribution_snapshot is not None
                    else None
                ),
                platform_video_id=metrics_snapshot.platform_video_id,
                views=metrics_snapshot.views,
                likes=metrics_snapshot.likes,
                comments=metrics_snapshot.comments,
                shares=metrics_snapshot.shares,
                saves=metrics_snapshot.saves,
                ctr=metrics_snapshot.ctr,
                average_view_duration_seconds=(
                    metrics_snapshot.average_view_duration_seconds
                ),
                completion_rate=metrics_snapshot.completion_rate,
                retention_rate=metrics_snapshot.retention_rate,
                variant_kind=(
                    attribution_snapshot.variant_kind
                    if attribution_snapshot is not None
                    else None
                ),
                packaging_profile=(
                    attribution_snapshot.packaging_profile
                    if attribution_snapshot is not None
                    else None
                ),
                subtitle_style=(
                    attribution_snapshot.subtitle_style
                    if attribution_snapshot is not None
                    else None
                ),
                performance_score=self._calculate_performance_score(
                    metrics_snapshot
                ),
                published_at=metrics_snapshot.published_at,
                synced_at=metrics_snapshot.synced_at,
            )
            entries.append(entry)

        self._apply_rankings(entries)
        self._apply_status_flags(entries)

        return entries

    def _calculate_performance_score(
        self,
        metrics_snapshot: NormalizedMetricsSnapshot,
    ) -> float:
        score = 0.0

        score += min(30.0, _safe_number(metrics_snapshot.views) / 500.0)
        score += min(15.0, _safe_number(metrics_snapshot.likes) / 50.0)
        score += min(10.0, _safe_number(metrics_snapshot.comments) / 10.0)
        score += min(10.0, _safe_number(metrics_snapshot.shares) / 10.0)
        score += min(10.0, _safe_number(metrics_snapshot.saves) / 10.0)
        score += min(8.0, _safe_number(metrics_snapshot.ctr) * 2.0)
        score += min(8.0, _safe_number(metrics_snapshot.completion_rate) / 10.0)
        score += min(9.0, _safe_number(metrics_snapshot.retention_rate) / 10.0)

        return round(score, 2)

    def _apply_rankings(self, entries: list[KpiViewEntry]) -> None:
        overall_sorted = sorted(
            entries,
            key=lambda item: item.performance_score or 0.0,
            reverse=True,
        )
        for index, entry in enumerate(overall_sorted, start=1):
            entry.rank_overall = index

        platform_groups: dict[str, list[KpiViewEntry]] = {}
        for entry in entries:
            platform_groups.setdefault(entry.target_platform.value, []).append(entry)

        for grouped_entries in platform_groups.values():
            grouped_entries.sort(
                key=lambda item: item.performance_score or 0.0,
                reverse=True,
            )
            for index, entry in enumerate(grouped_entries, start=1):
                entry.rank_within_platform = index

        channel_groups: dict[str, list[KpiViewEntry]] = {}
        for entry in entries:
            channel_groups.setdefault(entry.channel_type.value, []).append(entry)

        for grouped_entries in channel_groups.values():
            grouped_entries.sort(
                key=lambda item: item.performance_score or 0.0,
                reverse=True,
            )
            for index, entry in enumerate(grouped_entries, start=1):
                entry.rank_within_channel = index

    def _apply_status_flags(self, entries: list[KpiViewEntry]) -> None:
        if not entries:
            return

        scores = [entry.performance_score or 0.0 for entry in entries]
        average_score = sum(scores) / len(scores)

        sorted_entries = sorted(
            entries,
            key=lambda item: item.performance_score or 0.0,
            reverse=True,
        )

        top_entry = sorted_entries[0]
        low_entry = sorted_entries[-1]

        if len(sorted_entries) >= 1:
            top_entry.is_winner = True

        if len(sorted_entries) > 1:
            low_entry.is_loser = True

        for entry in entries:
            score = entry.performance_score or 0.0

            if score >= average_score * 1.15:
                entry.comparison_status = "above_average"
            elif score <= average_score * 0.85:
                entry.comparison_status = "below_average"
            else:
                entry.comparison_status = "near_average"

            if score >= average_score * 1.50 or score <= average_score * 0.50:
                entry.is_outlier = True