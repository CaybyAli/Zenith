from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from core.scheduling_policy_evaluator import SchedulingPolicyEvaluator
from core.scheduling_policy_manager import SchedulingPolicyManager
from core.scheduling_policy_store import SchedulingPolicyStore
from models.queue_entry import QueueEntry


def build_queue_entry(
    *,
    queue_entry_id: str,
    channel_type: str,
    channel_group: str,
    content_kind: str,
) -> QueueEntry:
    return QueueEntry.from_dict(
        {
            "queue_entry_id": queue_entry_id,
            "dedupe_key": f"{queue_entry_id}:{channel_type}:{content_kind}",
            "source_review_view_id": f"review_{queue_entry_id}",
            "source_opportunity_id": f"opportunity_{queue_entry_id}",
            "source_signal_id": f"signal_{queue_entry_id}",
            "topic_label": f"topic_{queue_entry_id}",
            "platform": "youtube",
            "channel_type": channel_type,
            "channel_group": channel_group,
            "content_kind": content_kind,
            "queue_state": "queued",
            "opportunity_score": 80.0,
            "opportunity_level": "high",
            "lifespan_class": "short",
            "review_status": "approved",
            "review_summary": f"summary_{queue_entry_id}",
            "block_reason": None,
        }
    )


def main() -> None:
    with TemporaryDirectory() as tmp_dir:
        base_path = Path(tmp_dir)
        policies_path = base_path / "scheduling_policies.json"

        policy_store = SchedulingPolicyStore(str(policies_path))
        policy_manager = SchedulingPolicyManager(policy_store)
        evaluator = SchedulingPolicyEvaluator(policy_manager)

        policy_manager.ensure_default_policies()

        main_longform = build_queue_entry(
            queue_entry_id="entry_main_longform",
            channel_type="gaming_main",
            channel_group="main",
            content_kind="longform",
        )
        allowed, reason = evaluator.evaluate_queue_entry(main_longform)
        assert allowed is True
        assert reason is None

        main_shorts = build_queue_entry(
            queue_entry_id="entry_main_shorts",
            channel_type="gaming_main",
            channel_group="main",
            content_kind="shorts",
        )
        allowed, reason = evaluator.evaluate_queue_entry(main_shorts)
        assert allowed is True
        assert reason is None

        policy_manager.update_policy(
            "gaming_main",
            allows_shorts=False,
        )
        allowed, reason = evaluator.evaluate_queue_entry(main_shorts)
        assert allowed is False
        assert reason == "shorts_not_allowed"

        faceless_longform = build_queue_entry(
            queue_entry_id="entry_faceless_longform",
            channel_type="faceless_trend",
            channel_group="faceless",
            content_kind="longform",
        )
        allowed, reason = evaluator.evaluate_queue_entry(faceless_longform)
        assert allowed is False
        assert reason == "policy_disabled"

        policy_manager.update_policy(
            "gaming_uncut",
            publish_days=[],
        )
        uncut_longform = build_queue_entry(
            queue_entry_id="entry_uncut_longform",
            channel_type="gaming_uncut",
            channel_group="uncut",
            content_kind="longform",
        )
        allowed, reason = evaluator.evaluate_queue_entry(uncut_longform)
        assert allowed is False
        assert reason == "no_publish_days"

        policy_manager.update_policy(
            "gaming_uncut",
            publish_days=[1, 3, 5],
            allows_longform=False,
        )
        allowed, reason = evaluator.evaluate_queue_entry(uncut_longform)
        assert allowed is False
        assert reason == "longform_not_allowed"

        print("SCHEDULING POLICY EVALUATOR SMOKE TEST PASSED")
        print({"main_longform": [True, None]})
        print({"main_shorts_after_disable": [False, "shorts_not_allowed"]})
        print({"faceless_longform": [False, "policy_disabled"]})
        print({"uncut_no_days": [False, "no_publish_days"]})
        print({"uncut_longform_blocked": [False, "longform_not_allowed"]})


if __name__ == "__main__":
    main()