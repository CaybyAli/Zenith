from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from shared.enums import ChannelType, PlatformType


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class KpiViewEntry:
    view_id: str
    job_id: str
    variant_id: str
    target_platform: PlatformType
    channel_type: ChannelType

    metrics_snapshot_id: str
    attribution_id: str | None = None
    platform_video_id: str | None = None

    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    saves: int | None = None

    ctr: float | None = None
    average_view_duration_seconds: float | None = None
    completion_rate: float | None = None
    retention_rate: float | None = None

    variant_kind: str | None = None
    packaging_profile: str | None = None
    subtitle_style: str | None = None

    performance_score: float | None = None
    rank_overall: int | None = None
    rank_within_platform: int | None = None
    rank_within_channel: int | None = None

    comparison_status: str | None = None
    is_winner: bool = False
    is_loser: bool = False
    is_outlier: bool = False

    published_at: str | None = None
    synced_at: str | None = None

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, object]:
        return {
            "view_id": self.view_id,
            "job_id": self.job_id,
            "variant_id": self.variant_id,
            "target_platform": self.target_platform.value,
            "channel_type": self.channel_type.value,
            "metrics_snapshot_id": self.metrics_snapshot_id,
            "attribution_id": self.attribution_id,
            "platform_video_id": self.platform_video_id,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "saves": self.saves,
            "ctr": self.ctr,
            "average_view_duration_seconds": self.average_view_duration_seconds,
            "completion_rate": self.completion_rate,
            "retention_rate": self.retention_rate,
            "variant_kind": self.variant_kind,
            "packaging_profile": self.packaging_profile,
            "subtitle_style": self.subtitle_style,
            "performance_score": self.performance_score,
            "rank_overall": self.rank_overall,
            "rank_within_platform": self.rank_within_platform,
            "rank_within_channel": self.rank_within_channel,
            "comparison_status": self.comparison_status,
            "is_winner": self.is_winner,
            "is_loser": self.is_loser,
            "is_outlier": self.is_outlier,
            "published_at": self.published_at,
            "synced_at": self.synced_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "KpiViewEntry":
        return cls(
            view_id=str(data.get("view_id")),
            job_id=str(data.get("job_id")),
            variant_id=str(data.get("variant_id")),
            target_platform=PlatformType(data.get("target_platform", "youtube")),
            channel_type=ChannelType(data.get("channel_type", "gaming_main")),
            metrics_snapshot_id=str(data.get("metrics_snapshot_id")),
            attribution_id=(
                str(data["attribution_id"])
                if data.get("attribution_id") is not None
                else None
            ),
            platform_video_id=(
                str(data["platform_video_id"])
                if data.get("platform_video_id") is not None
                else None
            ),
            views=int(data["views"]) if data.get("views") is not None else None,
            likes=int(data["likes"]) if data.get("likes") is not None else None,
            comments=int(data["comments"]) if data.get("comments") is not None else None,
            shares=int(data["shares"]) if data.get("shares") is not None else None,
            saves=int(data["saves"]) if data.get("saves") is not None else None,
            ctr=float(data["ctr"]) if data.get("ctr") is not None else None,
            average_view_duration_seconds=(
                float(data["average_view_duration_seconds"])
                if data.get("average_view_duration_seconds") is not None
                else None
            ),
            completion_rate=(
                float(data["completion_rate"])
                if data.get("completion_rate") is not None
                else None
            ),
            retention_rate=(
                float(data["retention_rate"])
                if data.get("retention_rate") is not None
                else None
            ),
            variant_kind=(
                str(data["variant_kind"])
                if data.get("variant_kind") is not None
                else None
            ),
            packaging_profile=(
                str(data["packaging_profile"])
                if data.get("packaging_profile") is not None
                else None
            ),
            subtitle_style=(
                str(data["subtitle_style"])
                if data.get("subtitle_style") is not None
                else None
            ),
            performance_score=(
                float(data["performance_score"])
                if data.get("performance_score") is not None
                else None
            ),
            rank_overall=(
                int(data["rank_overall"])
                if data.get("rank_overall") is not None
                else None
            ),
            rank_within_platform=(
                int(data["rank_within_platform"])
                if data.get("rank_within_platform") is not None
                else None
            ),
            rank_within_channel=(
                int(data["rank_within_channel"])
                if data.get("rank_within_channel") is not None
                else None
            ),
            comparison_status=(
                str(data["comparison_status"])
                if data.get("comparison_status") is not None
                else None
            ),
            is_winner=bool(data.get("is_winner", False)),
            is_loser=bool(data.get("is_loser", False)),
            is_outlier=bool(data.get("is_outlier", False)),
            published_at=(
                str(data["published_at"])
                if data.get("published_at") is not None
                else None
            ),
            synced_at=(
                str(data["synced_at"])
                if data.get("synced_at") is not None
                else None
            ),
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
        )