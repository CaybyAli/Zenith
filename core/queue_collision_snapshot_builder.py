from __future__ import annotations

from core.queue_collision_detector import QueueCollisionDetector
from models.queue_entry import QueueEntry


class QueueCollisionSnapshotBuilder:
    def __init__(
        self,
        detector: QueueCollisionDetector | None = None,
    ) -> None:
        self.detector = detector or QueueCollisionDetector()

    def build(self, queue_entries: list[QueueEntry]) -> list[dict[str, str]]:
        collisions: list[dict[str, str]] = []

        for left_index, left in enumerate(queue_entries):
            for right in queue_entries[left_index + 1:]:
                collided, reason = self.detector.detect_pair_collision(left, right)
                if not collided or not reason:
                    continue

                collisions.append(
                    {
                        "left_queue_entry_id": left.queue_entry_id,
                        "right_queue_entry_id": right.queue_entry_id,
                        "left_review_view_id": left.source_review_view_id,
                        "right_review_view_id": right.source_review_view_id,
                        "channel_type": left.channel_type,
                        "content_kind": left.content_kind,
                        "collision_reason": reason,
                    }
                )

        return collisions