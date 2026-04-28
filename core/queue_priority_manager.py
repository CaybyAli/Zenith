from __future__ import annotations

from core.queue_priority_scorer import QueuePriorityScorer
from models.queue_entry import QueueEntry


class QueuePriorityManager:
    def __init__(
        self,
        scorer: QueuePriorityScorer | None = None,
    ) -> None:
        self.scorer = scorer or QueuePriorityScorer()

    def sort_entries(self, queue_entries: list[QueueEntry]) -> list[QueueEntry]:
        return sorted(
            queue_entries,
            key=self._sort_key,
            reverse=True,
        )

    def score_entry(self, queue_entry: QueueEntry) -> float:
        return self.scorer.score(queue_entry)

    def _sort_key(self, queue_entry: QueueEntry) -> tuple[float, float, str]:
        priority_score = self.scorer.score(queue_entry)
        return (
            priority_score,
            queue_entry.opportunity_score,
            queue_entry.created_at,
        )