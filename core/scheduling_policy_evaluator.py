from __future__ import annotations

from core.scheduling_policy_manager import SchedulingPolicyManager
from models.queue_entry import QueueEntry


class SchedulingPolicyEvaluator:
    def __init__(
        self,
        policy_manager: SchedulingPolicyManager,
    ) -> None:
        self.policy_manager = policy_manager

    def evaluate_queue_entry(self, queue_entry: QueueEntry) -> tuple[bool, str | None]:
        policy = self.policy_manager.get_policy(queue_entry.channel_type)

        if not policy.is_enabled:
            return False, "policy_disabled"

        if not policy.publish_days:
            return False, "no_publish_days"

        if queue_entry.content_kind == "longform" and not policy.allows_longform:
            return False, "longform_not_allowed"

        if queue_entry.content_kind == "shorts" and not policy.allows_shorts:
            return False, "shorts_not_allowed"

        return True, None