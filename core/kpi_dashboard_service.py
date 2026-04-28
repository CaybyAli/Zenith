from __future__ import annotations

from core.comparison_view_builder import ComparisonViewBuilder
from core.insight_surface_builder import InsightSurfaceBuilder
from core.kpi_view_builder import KpiViewBuilder
from core.normalized_metrics_repository import NormalizedMetricsRepository
from core.performance_attribution_repository import (
    PerformanceAttributionRepository,
)
from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


def _average_score(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


class KpiDashboardService:
    def __init__(
        self,
        storage_provider: BaseStorageProvider | None = None,
        normalized_metrics_repository: NormalizedMetricsRepository | None = None,
        performance_attribution_repository: (
            PerformanceAttributionRepository | None
        ) = None,
        kpi_view_builder: KpiViewBuilder | None = None,
        comparison_view_builder: ComparisonViewBuilder | None = None,
        insight_surface_builder: InsightSurfaceBuilder | None = None,
    ) -> None:
        self.storage = storage_provider or LocalStorageProvider()
        self.normalized_metrics_repository = (
            normalized_metrics_repository or NormalizedMetricsRepository()
        )
        self.performance_attribution_repository = (
            performance_attribution_repository
            or PerformanceAttributionRepository()
        )
        self.kpi_view_builder = kpi_view_builder or KpiViewBuilder()
        self.comparison_view_builder = (
            comparison_view_builder or ComparisonViewBuilder()
        )
        self.insight_surface_builder = (
            insight_surface_builder or InsightSurfaceBuilder()
        )

    def build_surface(
        self,
        base_path: str = "exports",
    ) -> dict[str, object]:
        metrics_snapshots = []
        attribution_snapshots = []

        if not self.storage.exists(base_path):
            return self._build_empty_surface()

        for channel_name in self.storage.list_dir(base_path):
            channel_path = self.storage.join(base_path, channel_name)

            if not self.storage.is_dir(channel_path):
                continue

            for job_id in self.storage.list_dir(channel_path):
                export_path = self.storage.join(channel_path, job_id)

                if not self.storage.is_dir(export_path):
                    continue

                metrics_snapshots.extend(
                    self.normalized_metrics_repository.load_snapshots(export_path)
                )
                attribution_snapshots.extend(
                    self.performance_attribution_repository.load_snapshots(export_path)
                )

        entries = self.kpi_view_builder.build_entries(
            metrics_snapshots=metrics_snapshots,
            attribution_snapshots=attribution_snapshots,
        )
        entries.sort(
            key=lambda item: item.performance_score or 0.0,
            reverse=True,
        )

        comparison_summaries = self.comparison_view_builder.build_all_summaries(
            entries
        )
        insights = self.insight_surface_builder.build_insights(
            entries,
            comparison_summaries,
        )

        top_entries = entries[:5]
        low_entries = sorted(
            entries,
            key=lambda item: item.performance_score or 0.0,
        )[:5]

        return {
            "total_entries": len(entries),
            "winner_count": sum(1 for entry in entries if entry.is_winner),
            "loser_count": sum(1 for entry in entries if entry.is_loser),
            "outlier_count": sum(1 for entry in entries if entry.is_outlier),
            "entries": [entry.to_dict() for entry in entries],
            "top_entries": [entry.to_dict() for entry in top_entries],
            "low_entries": [entry.to_dict() for entry in low_entries],
            "comparison_summaries": [
                summary.to_dict()
                for summary in comparison_summaries[:12]
            ],
            "insights": [
                insight.to_dict()
                for insight in insights[:12]
            ],
            "platform_stats": self._build_platform_stats(entries),
            "channel_stats": self._build_channel_stats(entries),
        }

    def _build_platform_stats(
        self,
        entries,
    ) -> list[dict[str, object]]:
        groups: dict[str, list] = {}

        for entry in entries:
            groups.setdefault(entry.target_platform.value, []).append(entry)

        stats: list[dict[str, object]] = []

        for platform_name, grouped_entries in groups.items():
            grouped_entries = sorted(
                grouped_entries,
                key=lambda item: item.performance_score or 0.0,
                reverse=True,
            )
            scores = [
                float(entry.performance_score or 0.0)
                for entry in grouped_entries
            ]
            top_entry = grouped_entries[0]

            stats.append(
                {
                    "platform": platform_name,
                    "entry_count": len(grouped_entries),
                    "average_score": _average_score(scores),
                    "top_variant_id": top_entry.variant_id,
                    "top_score": top_entry.performance_score,
                }
            )

        stats.sort(
            key=lambda item: item["average_score"] or 0.0,
            reverse=True,
        )
        return stats

    def _build_channel_stats(
        self,
        entries,
    ) -> list[dict[str, object]]:
        groups: dict[str, list] = {}

        for entry in entries:
            groups.setdefault(entry.channel_type.value, []).append(entry)

        stats: list[dict[str, object]] = []

        for channel_name, grouped_entries in groups.items():
            grouped_entries = sorted(
                grouped_entries,
                key=lambda item: item.performance_score or 0.0,
                reverse=True,
            )
            scores = [
                float(entry.performance_score or 0.0)
                for entry in grouped_entries
            ]
            top_entry = grouped_entries[0]

            stats.append(
                {
                    "channel": channel_name,
                    "entry_count": len(grouped_entries),
                    "average_score": _average_score(scores),
                    "top_variant_id": top_entry.variant_id,
                    "top_score": top_entry.performance_score,
                }
            )

        stats.sort(
            key=lambda item: item["average_score"] or 0.0,
            reverse=True,
        )
        return stats

    def _build_empty_surface(self) -> dict[str, object]:
        return {
            "total_entries": 0,
            "winner_count": 0,
            "loser_count": 0,
            "outlier_count": 0,
            "entries": [],
            "top_entries": [],
            "low_entries": [],
            "comparison_summaries": [],
            "insights": [],
            "platform_stats": [],
            "channel_stats": [],
        }