from __future__ import annotations

from core.queue_collision_resolver import QueueCollisionResolver
from models.queue_entry import QueueEntry


def build_entry(
    *,
    queue_entry_id: str,
    source_signal_id: str,
    topic_label: str,
    channel_type: str,
    content_kind: str,
    opportunity_score: float,
    opportunity_level: str,
    lifespan_class: str,
    queue_state: str,
    created_at: str,
) -> QueueEntry:
    return QueueEntry.from_dict(
        {
            "queue_entry_id": queue_entry_id,
            "dedupe_key": f"{queue_entry_id}:{channel_type}:{content_kind}",
            "source_review_view_id": f"review_{queue_entry_id}",
            "source_opportunity_id": f"opportunity_{queue_entry_id}",
            "source_signal_id": source_signal_id,
            "topic_label": topic_label,
            "platform": "youtube",
            "channel_type": channel_type,
            "channel_group": "main",
            "content_kind": content_kind,
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
    resolver = QueueCollisionResolver()

    winner = build_entry(
        queue_entry_id="entry_winner",
        source_signal_id="signal_1",
        topic_label="GTA 6 Trailer Reactions",
        channel_type="gaming_main",
        content_kind="longform",
        opportunity_score=82.0,
        opportunity_level="high",
        lifespan_class="flash",
        queue_state="queued",
        created_at="2026-04-13T10:00:00+00:00",
    )
    loser_same_topic = build_entry(
        queue_entry_id="entry_loser_same_topic",
        source_signal_id="signal_2",
        topic_label="gta 6 trailer reactions",
        channel_type="gaming_main",
        content_kind="longform",
        opportunity_score=70.0,
        opportunity_level="medium",
        lifespan_class="short",
        queue_state="queued",
        created_at="2026-04-13T09:00:00+00:00",
    )
    loser_same_signal = build_entry(
        queue_entry_id="entry_loser_same_signal",
        source_signal_id="signal_1",
        topic_label="different topic",
        channel_type="gaming_main",
        content_kind="longform",
        opportunity_score=68.0,
        opportunity_level="medium",
        lifespan_class="short",
        queue_state="queued",
        created_at="2026-04-13T08:00:00+00:00",
    )
    safe_other_channel = build_entry(
        queue_entry_id="entry_safe_other_channel",
        source_signal_id="signal_1",
        topic_label="GTA 6 Trailer Reactions",
        channel_type="gaming_uncut",
        content_kind="longform",
        opportunity_score=75.0,
        opportunity_level="high",
        lifespan_class="short",
        queue_state="queued",
        created_at="2026-04-13T07:00:00+00:00",
    )

    result = resolver.resolve(
        [
            loser_same_topic,
            safe_other_channel,
            winner,
            loser_same_signal,
        ]
    )

    assert len(result) == 4

    assert result[0]["queue_entry_id"] == "entry_winner"
    assert result[0]["decision"] == "keep"
    assert result[0]["collision_reason"] is None

    assert result[1]["queue_entry_id"] == "entry_safe_other_channel"
    assert result[1]["decision"] == "keep"

    assert result[2]["queue_entry_id"] == "entry_loser_same_topic"
    assert result[2]["decision"] == "suppress"
    assert result[2]["collision_reason"] == "same_topic_same_channel_same_kind"
    assert result[2]["shadowed_by_queue_entry_id"] == "entry_winner"

    assert result[3]["queue_entry_id"] == "entry_loser_same_signal"
    assert result[3]["decision"] == "suppress"
    assert result[3]["collision_reason"] == "same_signal_same_channel_same_kind"
    assert result[3]["shadowed_by_queue_entry_id"] == "entry_winner"

    print("QUEUE COLLISION RESOLVER SMOKE TEST PASSED")
    for item in result:
        print(item)


if __name__ == "__main__":
    main()