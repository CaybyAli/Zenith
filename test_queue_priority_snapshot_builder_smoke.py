from __future__ import annotations

from core.queue_priority_snapshot_builder import QueuePrioritySnapshotBuilder
from models.queue_entry import QueueEntry


def build_entry(
    *,
    queue_entry_id: str,
    opportunity_score: float,
    opportunity_level: str,
    lifespan_class: str,
    queue_state: str,
    created_at: str,
) -> QueueEntry:
    return QueueEntry.from_dict(
        {
            "queue_entry_id": queue_entry_id,
            "dedupe_key": f"{queue_entry_id}:gaming_main:longform",
            "source_review_view_id": f"review_{queue_entry_id}",
            "source_opportunity_id": f"opportunity_{queue_entry_id}",
            "source_signal_id": f"signal_{queue_entry_id}",
            "topic_label": f"topic_{queue_entry_id}",
            "platform": "youtube",
            "channel_type": "gaming_main",
            "channel_group": "main",
            "content_kind": "longform",
            "queue_state": queue_state,
            "opportunity_score": opportunity_score,
            "opportunity_level": opportunity_level,
            "lifespan_class": lifespan_class,
            "review_status": "approved",
            "review_summary": f"summary_{queue_entry_id}",
            "block_reason": None,
            "created_at": created_at,
            "updated_at": created_at,
        }
    )


def main() -> None:
    builder = QueuePrioritySnapshotBuilder()

    flash_high = build_entry(
        queue_entry_id="entry_flash_high",
        opportunity_score=78.0,
        opportunity_level="high",
        lifespan_class="flash",
        queue_state="queued",
        created_at="2026-04-13T10:00:00+00:00",
    )
    long_very_high = build_entry(
        queue_entry_id="entry_long_very_high",
        opportunity_score=80.0,
        opportunity_level="very_high",
        lifespan_class="long",
        queue_state="queued",
        created_at="2026-04-13T09:00:00+00:00",
    )
    blocked_medium = build_entry(
        queue_entry_id="entry_blocked_medium",
        opportunity_score=90.0,
        opportunity_level="high",
        lifespan_class="short",
        queue_state="blocked",
        created_at="2026-04-13T08:00:00+00:00",
    )

    snapshot = builder.build(
        [
            blocked_medium,
            long_very_high,
            flash_high,
        ]
    )

    assert len(snapshot) == 3

    assert snapshot[0]["rank"] == 1
    assert snapshot[0]["queue_entry_id"] == "entry_flash_high"
    assert snapshot[0]["priority_score"] == 96.0

    assert snapshot[1]["rank"] == 2
    assert snapshot[1]["queue_entry_id"] == "entry_long_very_high"
    assert snapshot[1]["priority_score"] == 90.0

    assert snapshot[2]["rank"] == 3
    assert snapshot[2]["queue_entry_id"] == "entry_blocked_medium"
    assert snapshot[2]["priority_score"] == 79.0

    print("QUEUE PRIORITY SNAPSHOT BUILDER SMOKE TEST PASSED")
    for item in snapshot:
        print(item)


if __name__ == "__main__":
    main()