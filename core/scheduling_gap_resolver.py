from __future__ import annotations

from datetime import datetime, timedelta


class SchedulingGapResolver:
    def resolve_not_before(
        self,
        *,
        min_gap_hours: int,
        last_scheduled_at: str | None = None,
        now: datetime | None = None,
    ) -> datetime:
        current = now or datetime.now()

        try:
            gap_hours = max(1, int(min_gap_hours))
        except (TypeError, ValueError):
            gap_hours = 24

        if not last_scheduled_at:
            return current

        try:
            last_scheduled_dt = datetime.strptime(last_scheduled_at, "%Y-%m-%d %H:%M")
        except ValueError:
            return current

        gap_ready_at = last_scheduled_dt + timedelta(hours=gap_hours)
        return max(current, gap_ready_at)