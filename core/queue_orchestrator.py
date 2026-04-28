from __future__ import annotations

from core.opportunity_review_store import OpportunityReviewStore
from core.queue_store import QueueStore
from models.opportunity_review_view import OpportunityReviewView
from models.queue_entry import QueueEntry
from shared.channel_policies import get_channel_policy
from shared.errors import ValidationError
from shared.opportunity_review_enums import OpportunityReviewStatus
from shared.queue_enums import QueueState


class QueueOrchestrator:
    def __init__(
        self,
        review_store: OpportunityReviewStore,
        queue_store: QueueStore,
    ) -> None:
        self.review_store = review_store
        self.queue_store = queue_store

    def enqueue_review_view(self, review_view_id: str) -> QueueEntry:
        if not review_view_id or not review_view_id.strip():
            raise ValidationError("review_view_id is required")

        review_view = self.review_store.get_review_view(review_view_id)

        if review_view.review_status == OpportunityReviewStatus.REJECTED:
            raise ValidationError("Rejected review views cannot be enqueued")

        channel_type = (review_view.primary_channel or "").strip().lower()
        content_kind = "longform"
        dedupe_key = f"{review_view.review_view_id}:{channel_type or 'missing_channel'}:{content_kind}"

        queue_state, block_reason, channel_group = self._resolve_queue_state(review_view)

        queue_entry = QueueEntry.from_dict(
            {
                "dedupe_key": dedupe_key,
                "source_review_view_id": review_view.review_view_id,
                "source_opportunity_id": review_view.opportunity_id,
                "source_signal_id": review_view.signal_id,
                "topic_label": review_view.topic_label,
                "platform": review_view.platform,
                "channel_type": channel_type or "unknown_channel",
                "channel_group": channel_group,
                "content_kind": content_kind,
                "queue_state": queue_state.value,
                "opportunity_score": review_view.opportunity_score,
                "opportunity_level": review_view.opportunity_level.value,
                "lifespan_class": review_view.lifespan_class.value,
                "review_status": review_view.review_status.value,
                "review_summary": review_view.review_summary,
                "block_reason": block_reason,
            }
        )
        return self.queue_store.create_queue_entry(queue_entry)

    def enqueue_all_review_views(self) -> list[QueueEntry]:
        created_or_existing: list[QueueEntry] = []

        for review_view in self.review_store.list_review_views():
            if review_view.review_status == OpportunityReviewStatus.REJECTED:
                continue

            entry = self.enqueue_review_view(review_view.review_view_id)
            created_or_existing.append(entry)

        return created_or_existing

    def list_queue_entries(self) -> list[QueueEntry]:
        return self.queue_store.list_queue_entries()

    def _resolve_queue_state(
        self,
        review_view: OpportunityReviewView,
    ) -> tuple[QueueState, str | None, str]:
        channel_type = (review_view.primary_channel or "").strip().lower()

        if not channel_type:
            return QueueState.BLOCKED, "missing_primary_channel", "unknown_group"

        try:
            policy = get_channel_policy(channel_type)
        except ValueError:
            return QueueState.BLOCKED, "unknown_channel_policy", "unknown_group"

        if not policy.enabled:
            return QueueState.BLOCKED, "channel_disabled", policy.channel_group

        if review_view.review_status == OpportunityReviewStatus.APPROVED:
            return QueueState.QUEUED, None, policy.channel_group

        if review_view.review_status == OpportunityReviewStatus.PENDING:
            return QueueState.BLOCKED, "review_pending", policy.channel_group

        if review_view.review_status == OpportunityReviewStatus.WATCH:
            return QueueState.BLOCKED, "review_watch", policy.channel_group

        return QueueState.BLOCKED, "review_not_queueable", policy.channel_group