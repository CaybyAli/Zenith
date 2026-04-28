from __future__ import annotations

from core.queue_priority_explainer import QueuePriorityExplainer
from models.queue_entry import QueueEntry


def build_entry(
    *,
    queue_entry_id: str,
    opportunity_score: float,
    opportunity_level: str,
    lifespan_class: str,
    queue_state: str,
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
        }
    )


def main() -> None:
    explainer = QueuePriorityExplainer()

    queued_flash = build_entry(
        queue_entry_id="entry_queued_flash",
        opportunity_score=78.0,
        opportunity_level="high",
        lifespan_class="flash",
        queue_state="queued",
    )
    blocked_short = build_entry(
        queue_entry_id="entry_blocked_short",
        opportunity_score=80.0,
        opportunity_level="medium",
        lifespan_class="short",
        queue_state="blocked",
    )

    queued_result = explainer.explain(queued_flash)
    blocked_result = explainer.explain(blocked_short)

    assert queued_result["base_score"] == 78.0
    assert queued_result["lifespan_bonus"] == 12.0
    assert queued_result["level_bonus"] == 6.0
    assert queued_result["state_adjustment"] == 0.0
    assert queued_result["final_priority_score"] == 96.0

    assert blocked_result["base_score"] == 80.0
    assert blocked_result["lifespan_bonus"] == 8.0
    assert blocked_result["level_bonus"] == 2.0
    assert blocked_result["state_adjustment"] == -25.0
    assert blocked_result["final_priority_score"] == 65.0

    print("QUEUE PRIORITY EXPLAINER SMOKE TEST PASSED")
    print(queued_result)
    print(blocked_result)


if __name__ == "__main__":
    main()