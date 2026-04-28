from __future__ import annotations

from models.queue_entry import QueueEntry


class QueuePriorityExplainer:
    def explain(self, queue_entry: QueueEntry) -> dict[str, float | str]:
        base_score = float(queue_entry.opportunity_score)
        lifespan_bonus = self._lifespan_bonus(queue_entry.lifespan_class.value)
        level_bonus = self._level_bonus(queue_entry.opportunity_level.value)
        state_adjustment = self._state_adjustment(queue_entry.queue_state.value)

        final_score = round(
            max(0.0, min(100.0, base_score + lifespan_bonus + level_bonus + state_adjustment)),
            2,
        )

        return {
            "queue_entry_id": queue_entry.queue_entry_id,
            "base_score": round(base_score, 2),
            "lifespan_bonus": lifespan_bonus,
            "level_bonus": level_bonus,
            "state_adjustment": state_adjustment,
            "final_priority_score": final_score,
        }

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