from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import os

from core.integrity_scanner import IntegrityScanner
from core.recovery_executor import RecoveryExecutor
from core.recovery_planner import RecoveryPlanner
from core.retention_planner import RetentionPlanner
from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class MaintenanceRunResult:
    report_path: str
    report: dict[str, Any]
    execution_result: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_path": self.report_path,
            "report": self.report,
            "execution_result": self.execution_result,
        }


class MaintenanceRunner:
    def __init__(
        self,
        storage_provider: BaseStorageProvider | None = None,
    ) -> None:
        self.storage = storage_provider or LocalStorageProvider()
        self.integrity_scanner = IntegrityScanner(storage_provider=self.storage)
        self.recovery_planner = RecoveryPlanner()
        self.recovery_executor = RecoveryExecutor(storage_provider=self.storage)
        self.retention_planner = RetentionPlanner()

    def run(
        self,
        *,
        exports_base_path: str = "exports",
        rerender_queue_file: str = r"D:\Zenith\data\rerender_queue.json",
        rerender_jobs_file: str = r"D:\Zenith\data\rerender_jobs.json",
        report_output_path: str = r"D:\Zenith\data\maintenance\latest_maintenance_report.json",
    ) -> MaintenanceRunResult:
        pre_scan = self.integrity_scanner.scan(
            exports_base_path=exports_base_path,
            rerender_queue_file=rerender_queue_file,
            rerender_jobs_file=rerender_jobs_file,
        )

        recovery_plan = self.recovery_planner.plan(pre_scan)

        execution_result = self.recovery_executor.execute_safe_actions(
            recovery_plan,
            rerender_queue_file=rerender_queue_file,
            rerender_jobs_file=rerender_jobs_file,
        )

        post_scan = self.integrity_scanner.scan(
            exports_base_path=exports_base_path,
            rerender_queue_file=rerender_queue_file,
            rerender_jobs_file=rerender_jobs_file,
        )

        export_jobs = self._load_export_jobs(exports_base_path)
        rerender_jobs = self._load_json_list(rerender_jobs_file)

        retention_plan = self.retention_planner.build_plan(
            export_jobs=export_jobs,
            rerender_jobs=rerender_jobs,
        )

        report = {
            "generated_at": utc_now_iso(),
            "pre_recovery_integrity": pre_scan.to_dict(),
            "recovery_plan": recovery_plan.to_dict(),
            "safe_recovery_execution": execution_result.to_dict(),
            "post_recovery_integrity": post_scan.to_dict(),
            "retention_plan": retention_plan.to_dict(),
        }

        self._write_report(report_output_path, report)

        return MaintenanceRunResult(
            report_path=report_output_path,
            report=report,
            execution_result=execution_result.to_dict(),
        )

    def _write_report(self, report_output_path: str, report: dict[str, Any]) -> None:
        parent_dir = os.path.dirname(report_output_path)
        if parent_dir:
            self.storage.ensure_dir(parent_dir)

        self.storage.write_json(report_output_path, report, indent=4)

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
                except Exception:
                    continue

                if isinstance(job_data, dict):
                    jobs.append(job_data)

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