from __future__ import annotations

from core.queue_collision_resolver import QueueCollisionResolver
from core.queue_store import QueueStore


def main() -> None:
    queue_store = QueueStore("data/queue_entries.json")
    resolver = QueueCollisionResolver()

    queue_entries = queue_store.list_queue_entries()
    result = resolver.resolve(queue_entries)

    print("QUEUE COLLISION RESOLVER REAL SMOKE TEST PASSED")
    print(
        {
            "queue_entries_seen": len(queue_entries),
            "resolver_items": len(result),
        }
    )

    for item in result:
        print(item)


if __name__ == "__main__":
    main()