from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from core.scheduling_policy_manager import SchedulingPolicyManager
from core.scheduling_policy_store import SchedulingPolicyStore


def main() -> None:
    with TemporaryDirectory() as tmp_dir:
        base_path = Path(tmp_dir)
        policies_path = base_path / "scheduling_policies.json"

        policy_store = SchedulingPolicyStore(str(policies_path))
        policy_manager = SchedulingPolicyManager(policy_store)

        defaults = policy_manager.ensure_default_policies()
        assert len(defaults) == 3

        all_policies = policy_manager.list_policies()
        assert len(all_policies) == 3

        gaming_main = policy_manager.get_policy("gaming_main")
        assert gaming_main.channel_type == "gaming_main"
        assert gaming_main.is_enabled is True
        assert gaming_main.allows_longform is True
        assert gaming_main.allows_shorts is True
        assert gaming_main.publish_days == [0, 1, 2, 3, 4, 5, 6]
        assert gaming_main.publish_hour == 17
        assert gaming_main.publish_minute == 0
        assert gaming_main.min_gap_hours == 24

        gaming_uncut = policy_manager.get_policy("gaming_uncut")
        assert gaming_uncut.channel_type == "gaming_uncut"
        assert gaming_uncut.is_enabled is True
        assert gaming_uncut.allows_longform is True
        assert gaming_uncut.allows_shorts is False

        faceless = policy_manager.get_policy("faceless_trend")
        assert faceless.channel_type == "faceless_trend"
        assert faceless.is_enabled is False
        assert faceless.allows_longform is True
        assert faceless.allows_shorts is False

        updated_main = policy_manager.update_policy(
            "gaming_main",
            publish_hour=19,
            publish_minute=30,
            min_gap_hours=36,
            allows_shorts=False,
        )
        assert updated_main.publish_hour == 19
        assert updated_main.publish_minute == 30
        assert updated_main.min_gap_hours == 36
        assert updated_main.allows_shorts is False

        reloaded_main = policy_manager.get_policy("gaming_main")
        assert reloaded_main.publish_hour == 19
        assert reloaded_main.publish_minute == 30
        assert reloaded_main.min_gap_hours == 36
        assert reloaded_main.allows_shorts is False

        print("SCHEDULING POLICY SMOKE TEST PASSED")
        for policy in policy_manager.list_policies():
            print(
                {
                    "channel_type": policy.channel_type,
                    "is_enabled": policy.is_enabled,
                    "allows_longform": policy.allows_longform,
                    "allows_shorts": policy.allows_shorts,
                    "publish_days": policy.publish_days,
                    "publish_hour": policy.publish_hour,
                    "publish_minute": policy.publish_minute,
                    "min_gap_hours": policy.min_gap_hours,
                }
            )


if __name__ == "__main__":
    main()