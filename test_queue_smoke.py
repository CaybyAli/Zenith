from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from core.opportunity_review_store import OpportunityReviewStore
from core.queue_orchestrator import QueueOrchestrator
from core.queue_store import QueueStore
from models.opportunity_review_view import OpportunityReviewView
from shared.errors import ValidationError
from shared.opportunity_review_enums import OpportunityReviewStatus
from shared.queue_enums import QueueState


def build_review(
    *,
    review_view_id: str,
    opportunity_id: str,
    signal_id: str,
    primary_channel: str | None,
    review_status: OpportunityReviewStatus,
) -> OpportunityReviewView:
    return OpportunityReviewView.from_dict(
        {
            "review_view_id": review_view_id,
            "signal_id": signal_id,
            "qualification_id": f"qualification_{review_view_id}",
            "opportunity_id": opportunity_id,
            "topic_label": f"topic_{review_view_id}",
            "platform": "youtube",
            "primary_channel": primary_channel,
            "opportunity_score": 82.5,
            "opportunity_level": "high",
            "upside_preview": ["fast trend"],
            "downside_preview": ["competition"],
            "risk_flags": [],
            "lifespan_class": "short",
            "review_status": review_status.value,
            "review_summary": f"summary_{review_view_id}",
        }
    )


def main() -> None:
    with TemporaryDirectory() as tmp_dir:
        base_path = Path(tmp_dir)
        reviews_path = base_path / "opportunity_reviews.json"
        queue_path = base_path / "queue_entries.json"

        review_store = OpportunityReviewStore(str(reviews_path))
        queue_store = QueueStore(str(queue_path))
        orchestrator = QueueOrchestrator(review_store, queue_store)

        approved_main = build_review(
            review_view_id="review_main_approved",
            opportunity_id="opportunity_main_approved",
            signal_id="signal_main_approved",
            primary_channel="gaming_main",
            review_status=OpportunityReviewStatus.APPROVED,
        )
        pending_main = build_review(
            review_view_id="review_main_pending",
            opportunity_id="opportunity_main_pending",
            signal_id="signal_main_pending",
            primary_channel="gaming_main",
            review_status=OpportunityReviewStatus.PENDING,
        )
        watch_uncut = build_review(
            review_view_id="review_uncut_watch",
            opportunity_id="opportunity_uncut_watch",
            signal_id="signal_uncut_watch",
            primary_channel="gaming_uncut",
            review_status=OpportunityReviewStatus.WATCH,
        )
        approved_faceless = build_review(
            review_view_id="review_faceless_approved",
            opportunity_id="opportunity_faceless_approved",
            signal_id="signal_faceless_approved",
            primary_channel="faceless_trend",
            review_status=OpportunityReviewStatus.APPROVED,
        )
        missing_channel = build_review(
            review_view_id="review_missing_channel",
            opportunity_id="opportunity_missing_channel",
            signal_id="signal_missing_channel",
            primary_channel=None,
            review_status=OpportunityReviewStatus.APPROVED,
        )
        rejected_main = build_review(
            review_view_id="review_main_rejected",
            opportunity_id="opportunity_main_rejected",
            signal_id="signal_main_rejected",
            primary_channel="gaming_main",
            review_status=OpportunityReviewStatus.REJECTED,
        )

        review_store.create_review_view(approved_main)
        review_store.create_review_view(pending_main)
        review_store.create_review_view(watch_uncut)
        review_store.create_review_view(approved_faceless)
        review_store.create_review_view(missing_channel)
        review_store.create_review_view(rejected_main)

        queued_entry = orchestrator.enqueue_review_view("review_main_approved")
        assert queued_entry.queue_state == QueueState.QUEUED
        assert queued_entry.channel_type == "gaming_main"
        assert queued_entry.channel_group == "main"
        assert queued_entry.block_reason is None

        deduped_entry = orchestrator.enqueue_review_view("review_main_approved")
        assert deduped_entry.queue_entry_id == queued_entry.queue_entry_id
        assert deduped_entry.dedupe_key == queued_entry.dedupe_key

        pending_entry = orchestrator.enqueue_review_view("review_main_pending")
        assert pending_entry.queue_state == QueueState.BLOCKED
        assert pending_entry.block_reason == "review_pending"

        watch_entry = orchestrator.enqueue_review_view("review_uncut_watch")
        assert watch_entry.queue_state == QueueState.BLOCKED
        assert watch_entry.block_reason == "review_watch"
        assert watch_entry.channel_group == "uncut"

        faceless_entry = orchestrator.enqueue_review_view("review_faceless_approved")
        assert faceless_entry.queue_state == QueueState.BLOCKED
        assert faceless_entry.block_reason == "channel_disabled"
        assert faceless_entry.channel_group == "faceless"

        missing_channel_entry = orchestrator.enqueue_review_view("review_missing_channel")
        assert missing_channel_entry.queue_state == QueueState.BLOCKED
        assert missing_channel_entry.block_reason == "missing_primary_channel"
        assert missing_channel_entry.channel_group == "unknown_group"

        try:
            orchestrator.enqueue_review_view("review_main_rejected")
            raise AssertionError("Rejected review should not be enqueued")
        except ValidationError:
            pass

        all_entries = orchestrator.list_queue_entries()
        assert len(all_entries) == 5

        bulk_entries = orchestrator.enqueue_all_review_views()
        assert len(bulk_entries) == 5

        all_entries_after_bulk = orchestrator.list_queue_entries()
        assert len(all_entries_after_bulk) == 5

        print("QUEUE SMOKE TEST PASSED")
        for entry in all_entries_after_bulk:
            print(
                {
                    "queue_entry_id": entry.queue_entry_id,
                    "review_view_id": entry.source_review_view_id,
                    "channel_type": entry.channel_type,
                    "queue_state": entry.queue_state.value,
                    "block_reason": entry.block_reason,
                }
            )


if __name__ == "__main__":
    main()