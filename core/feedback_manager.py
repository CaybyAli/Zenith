from __future__ import annotations

from uuid import uuid4

from core.feedback_repository import FeedbackRepository
from models.feedback_record import FeedbackRecord
from shared.enums import ChannelType, PlatformType


class FeedbackManager:
    def __init__(
        self,
        feedback_repository: FeedbackRepository | None = None,
    ) -> None:
        self.feedback_repository = feedback_repository or FeedbackRepository()

    def create_feedback_record(
        self,
        storage_path: str,
        job_id: str,
        channel_type: ChannelType,
        feedback_category: str,
        feedback_direction: str,
        feedback_text: str,
        variant_id: str | None = None,
        target_platform: PlatformType | None = None,
        author_source: str = "user",
        severity: str = "normal",
        metrics_snapshot_id: str | None = None,
        attribution_id: str | None = None,
        insight_reference: str | None = None,
        context_snapshot: dict[str, object] | None = None,
        learning_tags: list[str] | None = None,
        filename: str = "feedback_records.json",
    ) -> FeedbackRecord:
        record = FeedbackRecord(
            feedback_id=f"fb_{uuid4().hex[:12]}",
            job_id=job_id,
            channel_type=channel_type,
            variant_id=variant_id,
            target_platform=target_platform,
            feedback_category=feedback_category,
            feedback_direction=feedback_direction,
            feedback_text=feedback_text,
            author_source=author_source,
            severity=severity,
            metrics_snapshot_id=metrics_snapshot_id,
            attribution_id=attribution_id,
            insight_reference=insight_reference,
            context_snapshot=dict(context_snapshot or {}),
            learning_tags=list(learning_tags or []),
        )

        self.feedback_repository.append_record(
            storage_path=storage_path,
            record=record,
            filename=filename,
        )
        return record