from __future__ import annotations

from core.queue_priority_manager import QueuePriorityManager
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
    manager = QueuePriorityManager()

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
    removed_entry = build_entry(
        queue_entry_id="entry_removed",
        opportunity_score=95.0,
        opportunity_level="very_high",
        lifespan_class="flash",
        queue_state="removed",
        created_at="2026-04-13T07:00:00+00:00",
    )

    flash_high_score = manager.score_entry(flash_high)
    long_very_high_score = manager.score_entry(long_very_high)
    blocked_medium_score = manager.score_entry(blocked_medium)
    removed_entry_score = manager.score_entry(removed_entry)

    assert flash_high_score == 96.0
    assert long_very_high_score == 90.0
    assert blocked_medium_score == 79.0
    assert removed_entry_score == 17.0

    ordered = manager.sort_entries(
        [
            blocked_medium,
            removed_entry,
            long_very_high,
            flash_high,
        ]
    )

    assert ordered[0].queue_entry_id == "entry_flash_high"
    assert ordered[1].queue_entry_id == "entry_long_very_high"
    assert ordered[2].queue_entry_id == "entry_blocked_medium"
    assert ordered[3].queue_entry_id == "entry_removed"

    print("QUEUE PRIORITY SMOKE TEST PASSED")
    for entry in ordered:
        print(
            {
                "queue_entry_id": entry.queue_entry_id,
                "priority_score": manager.score_entry(entry),
                "queue_state": entry.queue_state.value,
                "opportunity_score": entry.opportunity_score,
                "opportunity_level": entry.opportunity_level.value,
                "lifespan_class": entry.lifespan_class.value,
            }
        )


if __name__ == "__main__":
    main()