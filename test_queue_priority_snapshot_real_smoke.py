from __future__ import annotations

from core.queue_priority_snapshot_builder import QueuePrioritySnapshotBuilder
from core.queue_store import QueueStore


def main() -> None:
    queue_store = QueueStore("data/queue_entries.json")
    builder = QueuePrioritySnapshotBuilder()

    queue_entries = queue_store.list_queue_entries()
    snapshot = builder.build(queue_entries)

    print("QUEUE PRIORITY SNAPSHOT REAL SMOKE TEST PASSED")
    print(
        {
            "queue_entries_seen": len(queue_entries),
            "snapshot_items": len(snapshot),
        }
    )

    for item in snapshot:
        print(item)


if __name__ == "__main__":
    main()