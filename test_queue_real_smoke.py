from __future__ import annotations

from core.opportunity_review_store import OpportunityReviewStore
from core.queue_orchestrator import QueueOrchestrator
from core.queue_store import QueueStore


def main() -> None:
    review_store = OpportunityReviewStore("data/opportunity_reviews.json")
    queue_store = QueueStore("data/queue_entries.json")
    orchestrator = QueueOrchestrator(review_store, queue_store)

    before_count = len(queue_store.list_queue_entries())
    entries = orchestrator.enqueue_all_review_views()
    after_count = len(queue_store.list_queue_entries())

    print("QUEUE REAL SMOKE TEST PASSED")
    print(
        {
            "reviews_seen": len(review_store.list_review_views()),
            "queue_entries_returned": len(entries),
            "queue_entries_before": before_count,
            "queue_entries_after": after_count,
        }
    )

    for entry in queue_store.list_queue_entries():
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