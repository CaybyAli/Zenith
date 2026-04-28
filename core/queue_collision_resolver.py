from __future__ import annotations

from core.queue_collision_detector import QueueCollisionDetector
from core.queue_priority_manager import QueuePriorityManager
from models.queue_entry import QueueEntry


class QueueCollisionResolver:
    def __init__(
        self,
        detector: QueueCollisionDetector | None = None,
        priority_manager: QueuePriorityManager | None = None,
    ) -> None:
        self.detector = detector or QueueCollisionDetector()
        self.priority_manager = priority_manager or QueuePriorityManager()

    def resolve(self, queue_entries: list[QueueEntry]) -> list[dict[str, object]]:
        ordered_entries = self.priority_manager.sort_entries(queue_entries)

        decisions: dict[str, dict[str, object]] = {}
        for entry in ordered_entries:
            decisions[entry.queue_entry_id] = {
                "decision": "keep",
                "collision_reason": None,
                "shadowed_by_queue_entry_id": None,
            }

        for left_index, left in enumerate(ordered_entries):
            left_decision = decisions[left.queue_entry_id]["decision"]
            if left_decision != "keep":
                continue

            for right in ordered_entries[left_index + 1:]:
                right_decision = decisions[right.queue_entry_id]["decision"]
                if right_decision != "keep":
                    continue

                collided, reason = self.detector.detect_pair_collision(left, right)
                if not collided or not reason:
                    continue

                decisions[right.queue_entry_id] = {
                    "decision": "suppress",
                    "collision_reason": reason,
                    "shadowed_by_queue_entry_id": left.queue_entry_id,
                }

        result: list[dict[str, object]] = []
        for rank, entry in enumerate(ordered_entries, start=1):
            decision = decisions[entry.queue_entry_id]
            result.append(
                {
                    "rank": rank,
                    "queue_entry_id": entry.queue_entry_id,
                    "review_view_id": entry.source_review_view_id,
                    "channel_type": entry.channel_type,
                    "content_kind": entry.content_kind,
                    "queue_state": entry.queue_state.value,
                    "priority_score": self.priority_manager.score_entry(entry),
                    "decision": decision["decision"],
                    "collision_reason": decision["collision_reason"],
                    "shadowed_by_queue_entry_id": decision["shadowed_by_queue_entry_id"],
                }
            )

        return result