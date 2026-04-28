from __future__ import annotations

from uuid import uuid4

from models.content_variant import ContentVariant
from models.normalized_metrics_snapshot import NormalizedMetricsSnapshot
from models.performance_attribution_snapshot import PerformanceAttributionSnapshot
from models.publish_result import PublishResult


class PerformanceAttributionBuilder:
    def build_snapshot(
        self,
        metrics_snapshot: NormalizedMetricsSnapshot,
        content_variant: ContentVariant,
        publish_result: PublishResult,
        guard_status: str | None = None,
        policy_snapshot: dict[str, object] | None = None,
        attribution_notes: str | None = None,
    ) -> PerformanceAttributionSnapshot:
        if metrics_snapshot.variant_id != content_variant.variant_id:
            raise ValueError(
                "Metrics snapshot and content variant variant_id do not match"
            )

        if metrics_snapshot.variant_id != (publish_result.variant_id or ""):
            raise ValueError(
                "Metrics snapshot and publish result variant_id do not match"
            )

        if metrics_snapshot.job_id != content_variant.job_id:
            raise ValueError(
                "Metrics snapshot and content variant job_id do not match"
            )

        if metrics_snapshot.job_id != publish_result.job_id:
            raise ValueError(
                "Metrics snapshot and publish result job_id do not match"
            )

        return PerformanceAttributionSnapshot(
            attribution_id=f"attrib_{uuid4().hex[:12]}",
            metrics_snapshot_id=metrics_snapshot.snapshot_id,
            job_id=metrics_snapshot.job_id,
            variant_id=metrics_snapshot.variant_id,
            target_platform=metrics_snapshot.target_platform,
            channel_type=metrics_snapshot.channel_type,
            platform_video_id=metrics_snapshot.platform_video_id,
            publish_reference={
                "platform": publish_result.platform.value,
                "publish_status": publish_result.publish_status,
                "backend_name": publish_result.backend_name,
                "public_url": publish_result.public_url,
                "message": publish_result.message,
                "error_message": publish_result.error_message,
                "published_at": publish_result.published_at,
                "last_updated_at": publish_result.last_updated_at,
            },
            variant_kind=content_variant.variant_kind,
            packaging_profile=content_variant.packaging_profile,
            subtitle_style=content_variant.subtitle_style,
            metadata_context_snapshot={
                "title": content_variant.title,
                "description": content_variant.description,
                "hashtags": list(content_variant.hashtags),
                "thumbnail_or_cover_path": content_variant.thumbnail_or_cover_path,
                "subtitle_path": content_variant.subtitle_path,
            },
            policy_snapshot=dict(
                policy_snapshot
                if policy_snapshot is not None
                else content_variant.platform_policy_snapshot
            ),
            publish_status=publish_result.publish_status,
            guard_status=guard_status,
            published_at=publish_result.published_at,
            synced_at=metrics_snapshot.synced_at,
            attribution_notes=attribution_notes,
        )