from __future__ import annotations

from uuid import uuid4

from core.metrics_normalizer import MetricsNormalizer
from core.normalized_metrics_repository import NormalizedMetricsRepository
from core.platform_raw_metrics_repository import PlatformRawMetricsRepository
from models.normalized_metrics_snapshot import NormalizedMetricsSnapshot
from models.platform_raw_metrics import PlatformRawMetrics
from models.publish_result import PublishResult
from shared.enums import ChannelType


class MetricsSyncManager:
    def __init__(
        self,
        raw_metrics_repository: PlatformRawMetricsRepository | None = None,
        normalized_metrics_repository: NormalizedMetricsRepository | None = None,
        metrics_normalizer: MetricsNormalizer | None = None,
    ) -> None:
        self.raw_metrics_repository = (
            raw_metrics_repository or PlatformRawMetricsRepository()
        )
        self.normalized_metrics_repository = (
            normalized_metrics_repository or NormalizedMetricsRepository()
        )
        self.metrics_normalizer = metrics_normalizer or MetricsNormalizer()

    def sync_from_publish_result(
        self,
        publish_result: PublishResult,
        channel_type: ChannelType,
        storage_path: str,
        raw_metrics: dict[str, object],
        raw_source: str = "manual_import",
        raw_filename: str = "platform_raw_metrics.json",
        normalized_filename: str = "normalized_metrics_snapshots.json",
    ) -> tuple[PlatformRawMetrics, NormalizedMetricsSnapshot]:
        if not publish_result.variant_id:
            raise ValueError(
                "PublishResult.variant_id is required for metrics sync"
            )

        snapshot_id = f"metrics_{uuid4().hex[:12]}"

        raw_snapshot = PlatformRawMetrics(
            snapshot_id=snapshot_id,
            job_id=publish_result.job_id,
            variant_id=publish_result.variant_id,
            target_platform=publish_result.platform,
            channel_type=channel_type,
            platform_video_id=publish_result.platform_video_id,
            published_at=publish_result.published_at,
            raw_source=raw_source,
            raw_metrics=dict(raw_metrics),
        )

        normalized_snapshot = self.metrics_normalizer.normalize(raw_snapshot)

        self.raw_metrics_repository.append_snapshot(
            storage_path=storage_path,
            snapshot=raw_snapshot,
            filename=raw_filename,
        )
        self.normalized_metrics_repository.append_snapshot(
            storage_path=storage_path,
            snapshot=normalized_snapshot,
            filename=normalized_filename,
        )

        return raw_snapshot, normalized_snapshot