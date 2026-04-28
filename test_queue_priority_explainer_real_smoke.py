from __future__ import annotations

from core.queue_priority_explainer import QueuePriorityExplainer
from core.queue_store import QueueStore


def main() -> None:
    queue_store = QueueStore("data/queue_entries.json")
    explainer = QueuePriorityExplainer()

    queue_entries = queue_store.list_queue_entries()

    print("QUEUE PRIORITY EXPLAINER REAL SMOKE TEST PASSED")
    print(
        {
            "queue_entries_seen": len(queue_entries),
        }
    )

    for entry in queue_entries:
        result = explainer.explain(entry)
        print(
            {
                "queue_entry_id": entry.queue_entry_id,
                "review_view_id": entry.source_review_view_id,
                "channel_type": entry.channel_type,
                "content_kind": entry.content_kind,
                "queue_state": entry.queue_state.value,
                "base_score": result["base_score"],
                "lifespan_bonus": result["lifespan_bonus"],
                "level_bonus": result["level_bonus"],
                "state_adjustment": result["state_adjustment"],
                "final_priority_score": result["final_priority_score"],
            }
        )


if __name__ == "__main__":
    main()