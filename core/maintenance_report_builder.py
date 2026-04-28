from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.integrity_scanner import IntegrityScanner
from core.recovery_planner import RecoveryPlanner
from core.retention_planner import RetentionPlanner
from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


@dataclass(slots=True)
class MaintenanceReport:
    integrity: dict[str, Any]
    recovery_plan: dict[str, Any]
    retention_plan: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "integrity": self.integrity,
            "recovery_plan": self.recovery_plan,
            "retention_plan": self.retention_plan,
        }


class MaintenanceReportBuilder:
    def __init__(
        self,
        storage_provider: BaseStorageProvider | None = None,
    ) -> None:
        self.storage = storage_provider or LocalStorageProvider()
        self.integrity_scanner = IntegrityScanner(storage_provider=self.storage)
        self.recovery_planner = RecoveryPlanner()
        self.retention_planner = RetentionPlanner()

    def build(
        self,
        *,
        exports_base_path: str = "exports",
        rerender_queue_file: str = r"D:\Zenith\data\rerender_queue.json",
        rerender_jobs_file: str = r"D:\Zenith\data\rerender_jobs.json",
        export_jobs: list[dict[str, Any]] | None = None,
        rerender_jobs: list[dict[str, Any]] | None = None,
    ) -> MaintenanceReport:
        integrity_result = self.integrity_scanner.scan(
            exports_base_path=exports_base_path,
            rerender_queue_file=rerender_queue_file,
            rerender_jobs_file=rerender_jobs_file,
        )

        recovery_plan = self.recovery_planner.plan(integrity_result)

        export_job_items = export_jobs
        if export_job_items is None:
            export_job_items = self._load_export_jobs(exports_base_path)

        rerender_job_items = rerender_jobs
        if rerender_job_items is None:
            rerender_job_items = self._load_json_list(rerender_jobs_file)

        retention_plan = self.retention_planner.build_plan(
            export_jobs=export_job_items,
            rerender_jobs=rerender_job_items,
        )

        return MaintenanceReport(
            integrity=integrity_result.to_dict(),
            recovery_plan=recovery_plan.to_dict(),
            retention_plan=retention_plan.to_dict(),
        )

    def _load_export_jobs(self, exports_base_path: str) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []

        if not self.storage.exists(exports_base_path):
            return jobs

        for channel_name in self.storage.list_dir(exports_base_path):
            channel_path = self.storage.join(exports_base_path, channel_name)

            if not self.storage.is_dir(channel_path):
                continue

            for job_id in self.storage.list_dir(channel_path):
                job_path = self.storage.join(channel_path, job_id)

                if not self.storage.is_dir(job_path):
                    continue

                job_file = self.storage.join(job_path, "job.json")

                if not self.storage.exists(job_file):
                    continue

                try:
                    job_data = self.storage.read_json(job_file)
                    if isinstance(job_data, dict):
                        jobs.append(job_data)
                except Exception:
                    continue

        return jobs

    def _load_json_list(self, file_path: str) -> list[dict[str, Any]]:
        if not self.storage.exists(file_path):
            return []

        try:
            data = self.storage.read_json(file_path)
        except Exception:
            return []

        if not isinstance(data, list):
            return []

        return [item for item in data if isinstance(item, dict)]