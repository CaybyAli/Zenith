from __future__ import annotations

from datetime import datetime

from core.scheduling_time_resolver import SchedulingTimeResolver
from models.scheduling_policy import SchedulingPolicy


def main() -> None:
    resolver = SchedulingTimeResolver()

    monday_morning = datetime(2026, 4, 13, 10, 0)

    main_policy = SchedulingPolicy.from_dict(
        {
            "channel_type": "gaming_main",
            "is_enabled": True,
            "allows_longform": True,
            "allows_shorts": True,
            "publish_days": [0, 2, 4],
            "publish_hour": 17,
            "publish_minute": 0,
            "min_gap_hours": 24,
        }
    )
    slot = resolver.resolve_next_slot(main_policy, now=monday_morning)
    assert slot == "2026-04-13 17:00"

    monday_evening = datetime(2026, 4, 13, 18, 0)
    slot = resolver.resolve_next_slot(main_policy, now=monday_evening)
    assert slot == "2026-04-15 17:00"

    slot = resolver.resolve_next_slot(
        main_policy,
        now=monday_morning,
        last_scheduled_at="2026-04-13 09:00",
    )
    assert slot == "2026-04-15 17:00"

    disabled_policy = SchedulingPolicy.from_dict(
        {
            "channel_type": "faceless_trend",
            "is_enabled": False,
            "allows_longform": True,
            "allows_shorts": False,
            "publish_days": [0, 1, 2, 3, 4, 5, 6],
            "publish_hour": 17,
            "publish_minute": 0,
            "min_gap_hours": 24,
        }
    )
    slot = resolver.resolve_next_slot(disabled_policy, now=monday_morning)
    assert slot is None

    no_days_policy = SchedulingPolicy.from_dict(
        {
            "channel_type": "gaming_uncut",
            "is_enabled": True,
            "allows_longform": True,
            "allows_shorts": False,
            "publish_days": [],
            "publish_hour": 17,
            "publish_minute": 0,
            "min_gap_hours": 24,
        }
    )
    slot = resolver.resolve_next_slot(no_days_policy, now=monday_morning)
    assert slot is None

    print("SCHEDULING TIME RESOLVER SMOKE TEST PASSED")
    print({"same_day_slot": "2026-04-13 17:00"})
    print({"next_valid_day_slot": "2026-04-15 17:00"})
    print({"gap_shifted_slot": "2026-04-15 17:00"})
    print({"disabled_policy_slot": None})
    print({"no_days_policy_slot": None})


if __name__ == "__main__":
    main()