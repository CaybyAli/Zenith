from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.recovery_planner import RecoveryPlan
from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


@dataclass(slots=True)
class RecoveryExecutionResult:
    applied_action_codes: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    def add_action_code(self, action_code: str) -> None:
        if action_code not in self.applied_action_codes:
            self.applied_action_codes.append(action_code)

    def add_changed_file(self, file_path: str) -> None:
        if file_path not in self.changed_files:
            self.changed_files.append(file_path)

    def bump(self, stat_name: str, amount: int = 1) -> None:
        self.stats[stat_name] = int(self.stats.get(stat_name, 0)) + amount

    def to_dict(self) -> dict[str, Any]:
        return {
            "applied_action_codes": list(self.applied_action_codes),
            "changed_files": list(self.changed_files),
            "stats": dict(self.stats),
        }


class RecoveryExecutor:
    def __init__(self, storage_provider: BaseStorageProvider | None = None) -> None:
        self.storage = storage_provider or LocalStorageProvider()

    def execute_safe_actions(
        self,
        plan: RecoveryPlan,
        *,
        rerender_queue_file: str = r"D:\Zenith\data\rerender_queue.json",
        rerender_jobs_file: str = r"D:\Zenith\data\rerender_jobs.json",
    ) -> RecoveryExecutionResult:
        result = RecoveryExecutionResult()

        safe_action_codes = {
            action.action_code
            for action in plan.actions
            if action.safe_to_apply
        }

        queue_actions = {
            "deduplicate_rerender_queue",
            "remove_invalid_rerender_queue_entry",
        }

        if safe_action_codes & queue_actions:
            self._normalize_rerender_queue(
                rerender_queue_file=rerender_queue_file,
                result=result,
            )

        if "remove_invalid_rerender_job_entry" in safe_action_codes:
            self._normalize_rerender_jobs(
                rerender_jobs_file=rerender_jobs_file,
                result=result,
            )

        return result

    def _normalize_rerender_queue(
        self,
        *,
        rerender_queue_file: str,
        result: RecoveryExecutionResult,
    ) -> None:
        if not self.storage.exists(rerender_queue_file):
            return

        queue_data = self.storage.read_json(rerender_queue_file)

        if not isinstance(queue_data, list):
            return

        normalized_queue: list[dict[str, Any]] = []
        seen_job_ids: set[str] = set()

        removed_invalid_entries = 0
        removed_duplicate_entries = 0

        for item in queue_data:
            if not isinstance(item, dict):
                removed_invalid_entries += 1
                continue

            job_id = str(item.get("job_id") or "").strip()
            if not job_id:
                removed_invalid_entries += 1
                continue

            if job_id in seen_job_ids:
                removed_duplicate_entries += 1
                continue

            seen_job_ids.add(job_id)
            normalized_queue.append(item)

        if removed_invalid_entries == 0 and removed_duplicate_entries == 0:
            return

        self.storage.write_json(rerender_queue_file, normalized_queue, indent=4)
        result.add_changed_file(rerender_queue_file)

        if removed_invalid_entries > 0:
            result.add_action_code("remove_invalid_rerender_queue_entry")
            result.bump("removed_invalid_rerender_queue_entries", removed_invalid_entries)

        if removed_duplicate_entries > 0:
            result.add_action_code("deduplicate_rerender_queue")
            result.bump("removed_duplicate_rerender_queue_entries", removed_duplicate_entries)

    def _normalize_rerender_jobs(
        self,
        *,
        rerender_jobs_file: str,
        result: RecoveryExecutionResult,
    ) -> None:
        if not self.storage.exists(rerender_jobs_file):
            return

        rerender_jobs = self.storage.read_json(rerender_jobs_file)

        if not isinstance(rerender_jobs, list):
            return

        normalized_jobs: list[dict[str, Any]] = []
        removed_invalid_entries = 0

        for item in rerender_jobs:
            if not isinstance(item, dict):
                removed_invalid_entries += 1
                continue

            rerender_job_id = str(item.get("rerender_job_id") or "").strip()
            source_job_id = str(item.get("source_job_id") or "").strip()

            if not rerender_job_id or not source_job_id:
                removed_invalid_entries += 1
                continue

            normalized_jobs.append(item)

        if removed_invalid_entries == 0:
            return

        self.storage.write_json(rerender_jobs_file, normalized_jobs, indent=4)
        result.add_changed_file(rerender_jobs_file)
        result.add_action_code("remove_invalid_rerender_job_entry")
        result.bump("removed_invalid_rerender_job_entries", removed_invalid_entries)