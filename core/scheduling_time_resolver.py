from __future__ import annotations

from datetime import datetime, timedelta

from core.scheduling_gap_resolver import SchedulingGapResolver
from models.scheduling_policy import SchedulingPolicy


class SchedulingTimeResolver:
    def __init__(
        self,
        gap_resolver: SchedulingGapResolver | None = None,
    ) -> None:
        self.gap_resolver = gap_resolver or SchedulingGapResolver()

    def resolve_next_slot(
        self,
        policy: SchedulingPolicy,
        *,
        now: datetime | None = None,
        last_scheduled_at: str | None = None,
    ) -> str | None:
        if not policy.is_enabled:
            return None

        if not policy.publish_days:
            return None

        not_before = self.gap_resolver.resolve_not_before(
            min_gap_hours=policy.min_gap_hours,
            last_scheduled_at=last_scheduled_at,
            now=now,
        )

        for day_offset in range(0, 14):
            candidate_day = not_before + timedelta(days=day_offset)

            if candidate_day.weekday() not in policy.publish_days:
                continue

            candidate = candidate_day.replace(
                hour=policy.publish_hour,
                minute=policy.publish_minute,
                second=0,
                microsecond=0,
            )

            if candidate >= not_before:
                return candidate.strftime("%Y-%m-%d %H:%M")

        return None