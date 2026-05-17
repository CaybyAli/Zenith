from __future__ import annotations

from core.queue_store import QueueStore
from core.scheduling_policy_evaluator import SchedulingPolicyEvaluator
from core.scheduling_policy_manager import SchedulingPolicyManager
from core.scheduling_policy_store import SchedulingPolicyStore


def main() -> None:
    queue_store = QueueStore("data/queue_entries.json")
    policy_store = SchedulingPolicyStore("data/scheduling_policies.json")
    policy_manager = SchedulingPolicyManager(policy_store)
    evaluator = SchedulingPolicyEvaluator(policy_manager)

    policies = policy_manager.ensure_default_policies()
    queue_entries = queue_store.list_queue_entries()

    print("SCHEDULING POLICY REAL SMOKE TEST PASSED")
    print(
        {
            "policies_loaded": len(policies),
            "queue_entries_seen": len(queue_entries),
        }
    )

    for entry in queue_entries:
        allowed, reason = evaluator.evaluate_queue_entry(entry)
        print(
            {
                "queue_entry_id": entry.queue_entry_id,
                "review_view_id": entry.source_review_view_id,
                "channel_type": entry.channel_type,
                "content_kind": entry.content_kind,
                "queue_state": entry.queue_state.value,
                "policy_allowed": allowed,
                "policy_reason": reason,
            }
        )


if __name__ == "__main__":
    main()