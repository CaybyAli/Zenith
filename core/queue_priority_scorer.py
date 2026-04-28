from __future__ import annotations

from models.queue_entry import QueueEntry


class QueuePriorityScorer:
    def score(self, queue_entry: QueueEntry) -> float:
        score = float(queue_entry.opportunity_score)

        score += self._lifespan_bonus(queue_entry.lifespan_class.value)
        score += self._level_bonus(queue_entry.opportunity_level.value)
        score += self._state_adjustment(queue_entry.queue_state.value)

        return round(max(0.0, min(100.0, score)), 2)

    def _lifespan_bonus(self, lifespan_class: str) -> float:
        mapping = {
            "flash": 12.0,
            "short": 8.0,
            "medium": 4.0,
            "long": 0.0,
        }
        return mapping.get(lifespan_class, 0.0)

    def _level_bonus(self, opportunity_level: str) -> float:
        mapping = {
            "very_high": 10.0,
            "high": 6.0,
            "medium": 2.0,
            "low": 0.0,
        }
        return mapping.get(opportunity_level, 0.0)

    def _state_adjustment(self, queue_state: str) -> float:
        if queue_state == "queued":
            return 0.0
        if queue_state == "blocked":
            return -25.0
        if queue_state == "removed":
            return -100.0
        return -10.0