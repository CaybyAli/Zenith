from __future__ import annotations

from core.queue_priority_explainer import QueuePriorityExplainer
from core.queue_priority_manager import QueuePriorityManager
from models.queue_entry import QueueEntry


class QueuePrioritySnapshotBuilder:
    def __init__(
        self,
        priority_manager: QueuePriorityManager | None = None,
        explainer: QueuePriorityExplainer | None = None,
    ) -> None:
        self.priority_manager = priority_manager or QueuePriorityManager()
        self.explainer = explainer or QueuePriorityExplainer()

    def build(self, queue_entries: list[QueueEntry]) -> list[dict[str, object]]:
        ordered_entries = self.priority_manager.sort_entries(queue_entries)
        result: list[dict[str, object]] = []

        for index, entry in enumerate(ordered_entries, start=1):
            explanation = self.explainer.explain(entry)
            result.append(
                {
                    "rank": index,
                    "queue_entry_id": entry.queue_entry_id,
                    "review_view_id": entry.source_review_view_id,
                    "channel_type": entry.channel_type,
                    "content_kind": entry.content_kind,
                    "queue_state": entry.queue_state.value,
                    "priority_score": explanation["final_priority_score"],
                    "base_score": explanation["base_score"],
                    "lifespan_bonus": explanation["lifespan_bonus"],
                    "level_bonus": explanation["level_bonus"],
                    "state_adjustment": explanation["state_adjustment"],
                }
            )

        return result