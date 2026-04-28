from __future__ import annotations

from core.normalized_metrics_repository import NormalizedMetricsRepository
from core.performance_attribution_builder import PerformanceAttributionBuilder
from core.performance_attribution_repository import (
    PerformanceAttributionRepository,
)
from core.publish_result_repository import PublishResultRepository
from models.content_variant import ContentVariant
from models.performance_attribution_snapshot import PerformanceAttributionSnapshot
from shared.enums import PlatformType


class MetricsAttributionBridge:
    def __init__(
        self,
        normalized_metrics_repository: NormalizedMetricsRepository | None = None,
        publish_result_repository: PublishResultRepository | None = None,
        performance_attribution_builder: PerformanceAttributionBuilder | None = None,
        performance_attribution_repository: (
            PerformanceAttributionRepository | None
        ) = None,
    ) -> None:
        self.normalized_metrics_repository = (
            normalized_metrics_repository or NormalizedMetricsRepository()
        )
        self.publish_result_repository = (
            publish_result_repository or PublishResultRepository()
        )
        self.performance_attribution_builder = (
            performance_attribution_builder or PerformanceAttributionBuilder()
        )
        self.performance_attribution_repository = (
            performance_attribution_repository
            or PerformanceAttributionRepository()
        )

    def build_and_store_attribution(
        self,
        export_path: str,
        content_variant: ContentVariant,
        target_platform: PlatformType,
        guard_status: str | None = None,
        policy_snapshot: dict[str, object] | None = None,
        attribution_notes: str | None = None,
        normalized_metrics_filename: str = "normalized_metrics_snapshots.json",
        publish_results_filename: str = "publish_results.json",
        attribution_filename: str = "performance_attribution_snapshots.json",
    ) -> PerformanceAttributionSnapshot:
        metrics_snapshot = self.normalized_metrics_repository.get_latest_snapshot(
            storage_path=export_path,
            variant_id=content_variant.variant_id,
            target_platform=target_platform.value,
            filename=normalized_metrics_filename,
        )
        if metrics_snapshot is None:
            raise ValueError(
                "No normalized metrics snapshot found for "
                f"variant {content_variant.variant_id} on "
                f"{target_platform.value}"
            )

        publish_result = self.publish_result_repository.get_result_by_platform(
            export_path=export_path,
            platform=target_platform.value,
            results_filename=publish_results_filename,
        )
        if publish_result is None:
            raise ValueError(
                f"No publish result found for platform {target_platform.value}"
            )

        attribution_snapshot = self.performance_attribution_builder.build_snapshot(
            metrics_snapshot=metrics_snapshot,
            content_variant=content_variant,
            publish_result=publish_result,
            guard_status=guard_status,
            policy_snapshot=policy_snapshot,
            attribution_notes=attribution_notes,
        )

        self.performance_attribution_repository.append_snapshot(
            storage_path=export_path,
            snapshot=attribution_snapshot,
            filename=attribution_filename,
        )

        return attribution_snapshot