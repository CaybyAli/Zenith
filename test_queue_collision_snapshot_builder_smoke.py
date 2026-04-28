from __future__ import annotations

from core.queue_collision_snapshot_builder import QueueCollisionSnapshotBuilder
from models.queue_entry import QueueEntry


def build_entry(
    *,
    queue_entry_id: str,
    source_signal_id: str,
    topic_label: str,
    channel_type: str,
    content_kind: str,
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
            "queue_state": "queued",
            "opportunity_score": 70.0,
            "opportunity_level": "high",
            "lifespan_class": "short",
            "review_status": "approved",
            "review_summary": f"summary_{queue_entry_id}",
            "block_reason": None,
        }
    )


def main() -> None:
    builder = QueueCollisionSnapshotBuilder()

    entry_a = build_entry(
        queue_entry_id="entry_a",
        source_signal_id="signal_1",
        topic_label="GTA 6 Trailer Reactions",
        channel_type="gaming_main",
        content_kind="longform",
    )
    entry_b = build_entry(
        queue_entry_id="entry_b",
        source_signal_id="signal_2",
        topic_label="gta 6 trailer reactions",
        channel_type="gaming_main",
        content_kind="longform",
    )
    entry_c = build_entry(
        queue_entry_id="entry_c",
        source_signal_id="signal_1",
        topic_label="different topic",
        channel_type="gaming_main",
        content_kind="longform",
    )
    entry_d = build_entry(
        queue_entry_id="entry_d",
        source_signal_id="signal_1",
        topic_label="GTA 6 Trailer Reactions",
        channel_type="gaming_uncut",
        content_kind="longform",
    )

    collisions = builder.build(
        [
            entry_a,
            entry_b,
            entry_c,
            entry_d,
        ]
    )

    assert len(collisions) == 2

    assert collisions[0]["left_queue_entry_id"] == "entry_a"
    assert collisions[0]["right_queue_entry_id"] == "entry_b"
    assert collisions[0]["collision_reason"] == "same_topic_same_channel_same_kind"

    assert collisions[1]["left_queue_entry_id"] == "entry_a"
    assert collisions[1]["right_queue_entry_id"] == "entry_c"
    assert collisions[1]["collision_reason"] == "same_signal_same_channel_same_kind"

    print("QUEUE COLLISION SNAPSHOT BUILDER SMOKE TEST PASSED")
    for item in collisions:
        print(item)


if __name__ == "__main__":
    main()