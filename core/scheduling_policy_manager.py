from __future__ import annotations

from core.scheduling_policy_store import SchedulingPolicyStore
from models.scheduling_policy import SchedulingPolicy
from shared.channel_policies import get_all_channel_policies, get_channel_policy
from shared.errors import NotFoundError, ValidationError


class SchedulingPolicyManager:
    def __init__(
        self,
        policy_store: SchedulingPolicyStore,
    ) -> None:
        self.policy_store = policy_store

    def ensure_default_policies(self) -> list[SchedulingPolicy]:
        created_or_existing: list[SchedulingPolicy] = []

        for channel_policy in get_all_channel_policies():
            policy = self.get_policy(channel_policy.channel_type)
            created_or_existing.append(policy)

        return created_or_existing

    def get_policy(self, channel_type: str) -> SchedulingPolicy:
        normalized_channel_type = self._normalize_channel_type(channel_type)

        try:
            return self.policy_store.get_policy(normalized_channel_type)
        except NotFoundError:
            default_policy = self._build_default_policy(normalized_channel_type)
            return self.policy_store.create_policy(default_policy)

    def list_policies(self) -> list[SchedulingPolicy]:
        self.ensure_default_policies()
        return self.policy_store.list_policies()

    def update_policy(
        self,
        channel_type: str,
        *,
        is_enabled: bool | None = None,
        allows_longform: bool | None = None,
        allows_shorts: bool | None = None,
        publish_days: list[int] | None = None,
        publish_hour: int | None = None,
        publish_minute: int | None = None,
        min_gap_hours: int | None = None,
    ) -> SchedulingPolicy:
        existing = self.get_policy(channel_type)
        payload = existing.to_dict()

        if is_enabled is not None:
            payload["is_enabled"] = is_enabled
        if allows_longform is not None:
            payload["allows_longform"] = allows_longform
        if allows_shorts is not None:
            payload["allows_shorts"] = allows_shorts
        if publish_days is not None:
            payload["publish_days"] = publish_days
        if publish_hour is not None:
            payload["publish_hour"] = publish_hour
        if publish_minute is not None:
            payload["publish_minute"] = publish_minute
        if min_gap_hours is not None:
            payload["min_gap_hours"] = min_gap_hours

        updated = SchedulingPolicy.from_dict(payload)
        return self.policy_store.update_policy(updated)

    def _build_default_policy(self, channel_type: str) -> SchedulingPolicy:
        channel_policy = get_channel_policy(channel_type)

        return SchedulingPolicy.from_dict(
            {
                "channel_type": channel_policy.channel_type,
                "is_enabled": channel_policy.enabled,
                "allows_longform": True,
                "allows_shorts": channel_policy.shorts_enabled,
                "publish_days": channel_policy.publish_days,
                "publish_hour": channel_policy.publish_hour,
                "publish_minute": channel_policy.publish_minute,
                "min_gap_hours": channel_policy.upload_every_hours,
            }
        )

    def _normalize_channel_type(self, channel_type: str) -> str:
        cleaned = (channel_type or "").strip().lower()
        if not cleaned:
            raise ValidationError("channel_type is required")
        return cleaned