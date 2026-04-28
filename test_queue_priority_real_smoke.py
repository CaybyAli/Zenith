from __future__ import annotations

from core.queue_priority_manager import QueuePriorityManager
from core.queue_store import QueueStore


def main() -> None:
    queue_store = QueueStore("data/queue_entries.json")
    priority_manager = QueuePriorityManager()

    queue_entries = queue_store.list_queue_entries()
    ordered_entries = priority_manager.sort_entries(queue_entries)

    print("QUEUE PRIORITY REAL SMOKE TEST PASSED")
    print(
        {
            "queue_entries_seen": len(queue_entries),
            "queue_entries_sorted": len(ordered_entries),
        }
    )

    for entry in ordered_entries:
        print(
            {
                "queue_entry_id": entry.queue_entry_id,
                "review_view_id": entry.source_review_view_id,
                "channel_type": entry.channel_type,
                "content_kind": entry.content_kind,
                "queue_state": entry.queue_state.value,
                "priority_score": priority_manager.score_entry(entry),
                "opportunity_score": entry.opportunity_score,
                "opportunity_level": entry.opportunity_level.value,
                "lifespan_class": entry.lifespan_class.value,
            }
        )


if __name__ == "__main__":
    main()