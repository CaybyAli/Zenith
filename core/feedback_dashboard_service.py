from __future__ import annotations

from core.feedback_aggregation_service import FeedbackAggregationService
from core.feedback_repository import FeedbackRepository
from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


class FeedbackDashboardService:
    def __init__(
        self,
        storage_provider: BaseStorageProvider | None = None,
        feedback_repository: FeedbackRepository | None = None,
        feedback_aggregation_service: FeedbackAggregationService | None = None,
    ) -> None:
        self.storage = storage_provider or LocalStorageProvider()
        self.feedback_repository = feedback_repository or FeedbackRepository()
        self.feedback_aggregation_service = (
            feedback_aggregation_service or FeedbackAggregationService()
        )

    def build_surface(
        self,
        base_path: str = "exports",
    ) -> dict[str, object]:
        records = []

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

                records.extend(
                    self.feedback_repository.load_records(export_path)
                )

        records.sort(
            key=lambda item: item.created_at or "",
            reverse=True,
        )

        pattern_summaries = self.feedback_aggregation_service.build_pattern_summaries(
            records
        )

        return {
            "total_records": len(records),
            "recent_feedback": [record.to_dict() for record in records[:10]],
            "pattern_summaries": [
                summary.to_dict() for summary in pattern_summaries[:10]
            ],
            "category_stats": self._build_category_stats(records),
            "direction_stats": self._build_direction_stats(records),
        }

    def _build_category_stats(self, records) -> list[dict[str, object]]:
        counts: dict[str, int] = {}

        for record in records:
            counts[record.feedback_category] = (
                counts.get(record.feedback_category, 0) + 1
            )

        stats = [
            {"category": category, "count": count}
            for category, count in counts.items()
        ]
        stats.sort(key=lambda item: item["count"], reverse=True)
        return stats

    def _build_direction_stats(self, records) -> list[dict[str, object]]:
        counts: dict[str, int] = {}

        for record in records:
            counts[record.feedback_direction] = (
                counts.get(record.feedback_direction, 0) + 1
            )

        stats = [
            {"direction": direction, "count": count}
            for direction, count in counts.items()
        ]
        stats.sort(key=lambda item: item["count"], reverse=True)
        return stats

    def _build_empty_surface(self) -> dict[str, object]:
        return {
            "total_records": 0,
            "recent_feedback": [],
            "pattern_summaries": [],
            "category_stats": [],
            "direction_stats": [],
        }