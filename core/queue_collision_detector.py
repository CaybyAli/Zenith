from __future__ import annotations

from models.queue_entry import QueueEntry


class QueueCollisionDetector:
    def detect_pair_collision(
        self,
        left: QueueEntry,
        right: QueueEntry,
    ) -> tuple[bool, str | None]:
        if left.queue_entry_id == right.queue_entry_id:
            return False, None

        if left.channel_type != right.channel_type:
            return False, None

        if left.content_kind != right.content_kind:
            return False, None

        left_topic = self._normalize_topic(left.topic_label)
        right_topic = self._normalize_topic(right.topic_label)

        if left_topic and right_topic and left_topic == right_topic:
            return True, "same_topic_same_channel_same_kind"

        if (
            left.source_signal_id
            and right.source_signal_id
            and left.source_signal_id == right.source_signal_id
        ):
            return True, "same_signal_same_channel_same_kind"

        return False, None

    def _normalize_topic(self, value: str | None) -> str:
        return (value or "").strip().lower()