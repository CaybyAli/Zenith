from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.scheduling_policy import SchedulingPolicy
from shared.errors import NotFoundError, StorageError


class SchedulingPolicyStore:
    def __init__(
        self,
        policies_path: str = "data/scheduling_policies.json",
    ) -> None:
        self.policies_path = Path(policies_path)
        self.policies_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.policies_path.exists():
            self._write_raw({"policies": {}})

    def create_policy(self, policy: SchedulingPolicy) -> SchedulingPolicy:
        data = self._read_raw()
        policies = data["policies"]

        if policy.channel_type in policies:
            existing = SchedulingPolicy.from_dict(policies[policy.channel_type])
            return existing

        policies[policy.channel_type] = policy.to_dict()
        self._write_raw(data)
        return policy

    def update_policy(self, policy: SchedulingPolicy) -> SchedulingPolicy:
        data = self._read_raw()
        policies = data["policies"]

        if policy.channel_type not in policies:
            raise NotFoundError(f"Scheduling policy not found: {policy.channel_type}")

        policy.touch()
        policies[policy.channel_type] = policy.to_dict()
        self._write_raw(data)
        return policy

    def get_policy(self, channel_type: str) -> SchedulingPolicy:
        data = self._read_raw()
        policies = data["policies"]

        if channel_type not in policies:
            raise NotFoundError(f"Scheduling policy not found: {channel_type}")

        return SchedulingPolicy.from_dict(policies[channel_type])

    def list_policies(self) -> list[SchedulingPolicy]:
        data = self._read_raw()
        return [SchedulingPolicy.from_dict(item) for item in data["policies"].values()]

    def _read_raw(self) -> dict[str, Any]:
        try:
            with self.policies_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            raise StorageError(f"Could not read scheduling policy store: {exc}") from exc

    def _write_raw(self, data: dict[str, Any]) -> None:
        try:
            with self.policies_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            raise StorageError(f"Could not write scheduling policy store: {exc}") from exc