from __future__ import annotations

from models.normalized_metrics_snapshot import NormalizedMetricsSnapshot
from models.platform_raw_metrics import PlatformRawMetrics
from shared.enums import PlatformType


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class MetricsNormalizer:
    def normalize(
        self,
        raw_snapshot: PlatformRawMetrics,
    ) -> NormalizedMetricsSnapshot:
        if raw_snapshot.target_platform == PlatformType.YOUTUBE:
            return self._normalize_youtube(raw_snapshot)

        if raw_snapshot.target_platform == PlatformType.TIKTOK:
            return self._normalize_tiktok(raw_snapshot)

        if raw_snapshot.target_platform == PlatformType.INSTAGRAM_REELS:
            return self._normalize_instagram_reels(raw_snapshot)

        raise ValueError(
            f"Unsupported platform for normalization: "
            f"{raw_snapshot.target_platform.value}"
        )

    def _build_base_snapshot(
        self,
        raw_snapshot: PlatformRawMetrics,
    ) -> NormalizedMetricsSnapshot:
        return NormalizedMetricsSnapshot(
            snapshot_id=raw_snapshot.snapshot_id,
            job_id=raw_snapshot.job_id,
            variant_id=raw_snapshot.variant_id,
            target_platform=raw_snapshot.target_platform,
            channel_type=raw_snapshot.channel_type,
            platform_video_id=raw_snapshot.platform_video_id,
            published_at=raw_snapshot.published_at,
            synced_at=raw_snapshot.synced_at,
            source_snapshot_id=raw_snapshot.snapshot_id,
        )

    def _normalize_youtube(
        self,
        raw_snapshot: PlatformRawMetrics,
    ) -> NormalizedMetricsSnapshot:
        raw = raw_snapshot.raw_metrics
        normalized = self._build_base_snapshot(raw_snapshot)

        normalized.views = _safe_int(raw.get("views"))
        normalized.likes = _safe_int(raw.get("likes"))
        normalized.comments = _safe_int(raw.get("comments"))
        normalized.shares = _safe_int(raw.get("shares"))
        normalized.saves = None
        normalized.ctr = _safe_float(raw.get("ctr"))
        normalized.average_view_duration_seconds = _safe_float(
            raw.get("average_view_duration_seconds")
        )
        normalized.completion_rate = _safe_float(raw.get("completion_rate"))
        normalized.retention_rate = _safe_float(
            raw.get("average_percentage_viewed")
        )

        return normalized

    def _normalize_tiktok(
        self,
        raw_snapshot: PlatformRawMetrics,
    ) -> NormalizedMetricsSnapshot:
        raw = raw_snapshot.raw_metrics
        normalized = self._build_base_snapshot(raw_snapshot)

        normalized.views = _safe_int(raw.get("views"))
        normalized.likes = _safe_int(raw.get("likes"))
        normalized.comments = _safe_int(raw.get("comments"))
        normalized.shares = _safe_int(raw.get("shares"))
        normalized.saves = _safe_int(raw.get("saves"))
        normalized.ctr = _safe_float(raw.get("ctr"))
        normalized.average_view_duration_seconds = _safe_float(
            raw.get("average_view_duration_seconds")
        )
        normalized.completion_rate = _safe_float(raw.get("completion_rate"))
        normalized.retention_rate = _safe_float(raw.get("retention_rate"))

        return normalized

    def _normalize_instagram_reels(
        self,
        raw_snapshot: PlatformRawMetrics,
    ) -> NormalizedMetricsSnapshot:
        raw = raw_snapshot.raw_metrics
        normalized = self._build_base_snapshot(raw_snapshot)

        normalized.views = _safe_int(raw.get("views"))
        normalized.likes = _safe_int(raw.get("likes"))
        normalized.comments = _safe_int(raw.get("comments"))
        normalized.shares = _safe_int(raw.get("shares"))
        normalized.saves = _safe_int(raw.get("saves"))
        normalized.ctr = _safe_float(raw.get("ctr"))
        normalized.average_view_duration_seconds = _safe_float(
            raw.get("average_view_duration_seconds")
        )
        normalized.completion_rate = _safe_float(raw.get("completion_rate"))
        normalized.retention_rate = _safe_float(raw.get("retention_rate"))

        return normalized