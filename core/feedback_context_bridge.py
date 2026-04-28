from __future__ import annotations

from core.feedback_manager import FeedbackManager
from models.feedback_record import FeedbackRecord
from models.insight_summary import InsightSummary
from models.performance_attribution_snapshot import (
    PerformanceAttributionSnapshot,
)


class FeedbackContextBridge:
    def __init__(
        self,
        feedback_manager: FeedbackManager | None = None,
    ) -> None:
        self.feedback_manager = feedback_manager or FeedbackManager()

    def create_feedback_from_attribution(
        self,
        storage_path: str,
        attribution_snapshot: PerformanceAttributionSnapshot,
        feedback_category: str,
        feedback_direction: str,
        feedback_text: str,
        insight_summary: InsightSummary | None = None,
        author_source: str = "user",
        severity: str = "normal",
        learning_tags: list[str] | None = None,
        extra_context: dict[str, object] | None = None,
        filename: str = "feedback_records.json",
    ) -> FeedbackRecord:
        context_snapshot = {
            "variant_kind": attribution_snapshot.variant_kind,
            "packaging_profile": attribution_snapshot.packaging_profile,
            "subtitle_style": attribution_snapshot.subtitle_style,
            "publish_status": attribution_snapshot.publish_status,
            "guard_status": attribution_snapshot.guard_status,
            "published_at": attribution_snapshot.published_at,
            "synced_at": attribution_snapshot.synced_at,
            "publish_reference": dict(attribution_snapshot.publish_reference),
            "metadata_context_snapshot": dict(
                attribution_snapshot.metadata_context_snapshot
            ),
            "policy_snapshot": dict(attribution_snapshot.policy_snapshot),
        }

        if insight_summary is not None:
            context_snapshot["insight_summary"] = {
                "insight_id": insight_summary.insight_id,
                "insight_type": insight_summary.insight_type,
                "title": insight_summary.title,
                "summary_text": insight_summary.summary_text,
                "severity": insight_summary.severity,
            }

        if extra_context:
            context_snapshot.update(dict(extra_context))

        return self.feedback_manager.create_feedback_record(
            storage_path=storage_path,
            job_id=attribution_snapshot.job_id,
            channel_type=attribution_snapshot.channel_type,
            variant_id=attribution_snapshot.variant_id,
            target_platform=attribution_snapshot.target_platform,
            feedback_category=feedback_category,
            feedback_direction=feedback_direction,
            feedback_text=feedback_text,
            author_source=author_source,
            severity=severity,
            metrics_snapshot_id=attribution_snapshot.metrics_snapshot_id,
            attribution_id=attribution_snapshot.attribution_id,
            insight_reference=(
                insight_summary.insight_id
                if insight_summary is not None
                else None
            ),
            context_snapshot=context_snapshot,
            learning_tags=list(learning_tags or []),
            filename=filename,
        )