from __future__ import annotations

from core.metrics_sync_manager import MetricsSyncManager
from core.publish_result_repository import PublishResultRepository
from models.normalized_metrics_snapshot import NormalizedMetricsSnapshot
from models.platform_raw_metrics import PlatformRawMetrics
from shared.enums import ChannelType, PlatformType


class PublishResultMetricsBridge:
    def __init__(
        self,
        publish_result_repository: PublishResultRepository | None = None,
        metrics_sync_manager: MetricsSyncManager | None = None,
    ) -> None:
        self.publish_result_repository = (
            publish_result_repository or PublishResultRepository()
        )
        self.metrics_sync_manager = metrics_sync_manager or MetricsSyncManager()

    def sync_platform_metrics(
        self,
        export_path: str,
        channel_type: ChannelType,
        target_platform: PlatformType,
        raw_metrics: dict[str, object],
        raw_source: str = "manual_import",
        publish_results_filename: str = "publish_results.json",
        raw_filename: str = "platform_raw_metrics.json",
        normalized_filename: str = "normalized_metrics_snapshots.json",
    ) -> tuple[PlatformRawMetrics, NormalizedMetricsSnapshot]:
        publish_result = self.publish_result_repository.get_result_by_platform(
            export_path=export_path,
            platform=target_platform.value,
            results_filename=publish_results_filename,
        )

        if publish_result is None:
            raise ValueError(
                f"No publish result found for platform {target_platform.value}"
            )

        return self.metrics_sync_manager.sync_from_publish_result(
            publish_result=publish_result,
            channel_type=channel_type,
            storage_path=export_path,
            raw_metrics=raw_metrics,
            raw_source=raw_source,
            raw_filename=raw_filename,
            normalized_filename=normalized_filename,
        )