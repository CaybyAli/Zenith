from __future__ import annotations

from core.queue_collision_detector import QueueCollisionDetector
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
    detector = QueueCollisionDetector()

    left = build_entry(
        queue_entry_id="entry_left",
        source_signal_id="signal_same",
        topic_label="GTA 6 Trailer Reactions",
        channel_type="gaming_main",
        content_kind="longform",
    )
    same_topic = build_entry(
        queue_entry_id="entry_same_topic",
        source_signal_id="signal_other",
        topic_label="gta 6 trailer reactions",
        channel_type="gaming_main",
        content_kind="longform",
    )
    same_signal = build_entry(
        queue_entry_id="entry_same_signal",
        source_signal_id="signal_same",
        topic_label="different topic",
        channel_type="gaming_main",
        content_kind="longform",
    )
    other_channel = build_entry(
        queue_entry_id="entry_other_channel",
        source_signal_id="signal_same",
        topic_label="GTA 6 Trailer Reactions",
        channel_type="gaming_uncut",
        content_kind="longform",
    )
    other_kind = build_entry(
        queue_entry_id="entry_other_kind",
        source_signal_id="signal_same",
        topic_label="GTA 6 Trailer Reactions",
        channel_type="gaming_main",
        content_kind="shorts",
    )

    collided, reason = detector.detect_pair_collision(left, same_topic)
    assert collided is True
    assert reason == "same_topic_same_channel_same_kind"

    collided, reason = detector.detect_pair_collision(left, same_signal)
    assert collided is True
    assert reason == "same_signal_same_channel_same_kind"

    collided, reason = detector.detect_pair_collision(left, other_channel)
    assert collided is False
    assert reason is None

    collided, reason = detector.detect_pair_collision(left, other_kind)
    assert collided is False
    assert reason is None

    collided, reason = detector.detect_pair_collision(left, left)
    assert collided is False
    assert reason is None

    print("QUEUE COLLISION DETECTOR SMOKE TEST PASSED")
    print({"same_topic": [True, "same_topic_same_channel_same_kind"]})
    print({"same_signal": [True, "same_signal_same_channel_same_kind"]})
    print({"other_channel": [False, None]})
    print({"other_kind": [False, None]})


if __name__ == "__main__":
    main()