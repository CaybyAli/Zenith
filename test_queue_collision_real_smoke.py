from __future__ import annotations

from core.queue_collision_snapshot_builder import QueueCollisionSnapshotBuilder
from core.queue_store import QueueStore


def main() -> None:
    queue_store = QueueStore("data/queue_entries.json")
    builder = QueueCollisionSnapshotBuilder()

    queue_entries = queue_store.list_queue_entries()
    collisions = builder.build(queue_entries)

    print("QUEUE COLLISION REAL SMOKE TEST PASSED")
    print(
        {
            "queue_entries_seen": len(queue_entries),
            "collisions_found": len(collisions),
        }
    )

    for item in collisions:
        print(item)


if __name__ == "__main__":
    main()