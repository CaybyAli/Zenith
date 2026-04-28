from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


@dataclass(slots=True)
class IntegrityIssue:
    issue_code: str
    severity: str
    scope: str
    reference_id: str
    message: str


@dataclass(slots=True)
class IntegrityScanResult:
    export_jobs_seen: int = 0
    rerender_jobs_seen: int = 0
    rerender_queue_items_seen: int = 0
    issues: list[IntegrityIssue] = field(default_factory=list)

    def add_issue(
        self,
        *,
        issue_code: str,
        severity: str,
        scope: str,
        reference_id: str,
        message: str,
    ) -> None:
        self.issues.append(
            IntegrityIssue(
                issue_code=issue_code,
                severity=severity,
                scope=scope,
                reference_id=reference_id,
                message=message,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "export_jobs_seen": self.export_jobs_seen,
            "rerender_jobs_seen": self.rerender_jobs_seen,
            "rerender_queue_items_seen": self.rerender_queue_items_seen,
            "issues": [
                {
                    "issue_code": issue.issue_code,
                    "severity": issue.severity,
                    "scope": issue.scope,
                    "reference_id": issue.reference_id,
                    "message": issue.message,
                }
                for issue in self.issues
            ],
        }


class IntegrityScanner:
    def __init__(self, storage_provider: BaseStorageProvider | None = None) -> None:
        self.storage = storage_provider or LocalStorageProvider()

    def scan(
        self,
        *,
        exports_base_path: str = "exports",
        rerender_queue_file: str = r"D:\Zenith\data\rerender_queue.json",
        rerender_jobs_file: str = r"D:\Zenith\data\rerender_jobs.json",
    ) -> IntegrityScanResult:
        result = IntegrityScanResult()

        self._scan_exports(exports_base_path, result)
        self._scan_rerender_queue(rerender_queue_file, result)
        self._scan_rerender_jobs(rerender_jobs_file, result)

        return result

    def _scan_exports(self, exports_base_path: str, result: IntegrityScanResult) -> None:
        if not self.storage.exists(exports_base_path):
            return

        for channel_name in self.storage.list_dir(exports_base_path):
            channel_path = self.storage.join(exports_base_path, channel_name)

            if not self.storage.is_dir(channel_path):
                continue

            for job_id in self.storage.list_dir(channel_path):
                job_path = self.storage.join(channel_path, job_id)

                if not self.storage.is_dir(job_path):
                    continue

                job_file = self.storage.join(job_path, "job.json")
                video_file = self.storage.join(job_path, "video.mp4")
                thumbnail_file = self.storage.join(job_path, "thumbnail.jpg")

                has_job_file = self.storage.exists(job_file)
                has_video_file = self.storage.exists(video_file)
                has_thumbnail_file = self.storage.exists(thumbnail_file)

                if not has_job_file:
                    if has_video_file or has_thumbnail_file:
                        result.add_issue(
                            issue_code="orphan_export_folder",
                            severity="high",
                            scope="export",
                            reference_id=f"{channel_name}/{job_id}",
                            message="Exportordner enthält Artefakte, aber keine job.json",
                        )
                    continue

                try:
                    job_data = self.storage.read_json(job_file)
                except Exception as exc:
                    result.add_issue(
                        issue_code="broken_job_json",
                        severity="high",
                        scope="export",
                        reference_id=f"{channel_name}/{job_id}",
                        message=f"job.json ist nicht lesbar: {exc}",
                    )
                    continue

                result.export_jobs_seen += 1

                stored_job_id = str(job_data.get("job_id") or "")
                if stored_job_id != job_id:
                    result.add_issue(
                        issue_code="job_id_mismatch",
                        severity="medium",
                        scope="export",
                        reference_id=f"{channel_name}/{job_id}",
                        message=f"Ordnername {job_id} passt nicht zu job_id {stored_job_id}",
                    )

                stored_video_path = job_data.get("video_path")
                if stored_video_path and not self.storage.exists(str(stored_video_path)):
                    result.add_issue(
                        issue_code="missing_video_artifact",
                        severity="high",
                        scope="export",
                        reference_id=f"{channel_name}/{job_id}",
                        message="job.json referenziert ein fehlendes Video",
                    )

                stored_thumbnail_path = job_data.get("thumbnail_path")
                if stored_thumbnail_path and not self.storage.exists(str(stored_thumbnail_path)):
                    result.add_issue(
                        issue_code="missing_thumbnail_artifact",
                        severity="low",
                        scope="export",
                        reference_id=f"{channel_name}/{job_id}",
                        message="job.json referenziert ein fehlendes Thumbnail",
                    )

                if not has_video_file:
                    result.add_issue(
                        issue_code="missing_export_video_file",
                        severity="high",
                        scope="export",
                        reference_id=f"{channel_name}/{job_id}",
                        message="Exportordner enthält keine video.mp4",
                    )

                shorts = job_data.get("shorts") or []
                seen_short_ids: set[str] = set()

                for index, short in enumerate(shorts, start=1):
                    if not isinstance(short, dict):
                        result.add_issue(
                            issue_code="invalid_short_entry",
                            severity="medium",
                            scope="export",
                            reference_id=f"{channel_name}/{job_id}",
                            message=f"Short-Eintrag #{index} ist kein Objekt",
                        )
                        continue

                    short_id = str(short.get("short_id") or f"short_{index}")
                    short_path = short.get("path")

                    if short_id in seen_short_ids:
                        result.add_issue(
                            issue_code="duplicate_short_id",
                            severity="medium",
                            scope="export",
                            reference_id=f"{channel_name}/{job_id}",
                            message=f"Doppelte short_id gefunden: {short_id}",
                        )
                    else:
                        seen_short_ids.add(short_id)

                    if not short_path:
                        result.add_issue(
                            issue_code="short_missing_path",
                            severity="medium",
                            scope="export",
                            reference_id=f"{channel_name}/{job_id}",
                            message=f"Short {short_id} hat keinen path",
                        )
                        continue

                    if not self.storage.exists(str(short_path)):
                        result.add_issue(
                            issue_code="missing_short_artifact",
                            severity="medium",
                            scope="export",
                            reference_id=f"{channel_name}/{job_id}",
                            message=f"Short-Datei fehlt: {short_id}",
                        )

    def _scan_rerender_queue(self, rerender_queue_file: str, result: IntegrityScanResult) -> None:
        if not self.storage.exists(rerender_queue_file):
            return

        try:
            queue_data = self.storage.read_json(rerender_queue_file)
        except Exception as exc:
            result.add_issue(
                issue_code="broken_rerender_queue",
                severity="high",
                scope="rerender_queue",
                reference_id=rerender_queue_file,
                message=f"rerender_queue.json ist nicht lesbar: {exc}",
            )
            return

        if not isinstance(queue_data, list):
            result.add_issue(
                issue_code="invalid_rerender_queue_format",
                severity="high",
                scope="rerender_queue",
                reference_id=rerender_queue_file,
                message="rerender_queue.json ist keine Liste",
            )
            return

        result.rerender_queue_items_seen = len(queue_data)

        seen_source_ids: set[str] = set()

        for item in queue_data:
            if not isinstance(item, dict):
                result.add_issue(
                    issue_code="invalid_rerender_queue_entry",
                    severity="medium",
                    scope="rerender_queue",
                    reference_id=rerender_queue_file,
                    message="Queue-Eintrag ist kein Objekt",
                )
                continue

            source_job_id = str(item.get("job_id") or "")
            if not source_job_id:
                result.add_issue(
                    issue_code="missing_queue_job_id",
                    severity="medium",
                    scope="rerender_queue",
                    reference_id=rerender_queue_file,
                    message="Queue-Eintrag ohne job_id",
                )
                continue

            if source_job_id in seen_source_ids:
                result.add_issue(
                    issue_code="duplicate_rerender_queue_job",
                    severity="medium",
                    scope="rerender_queue",
                    reference_id=source_job_id,
                    message="Gleiche job_id mehrfach in rerender_queue",
                )
            else:
                seen_source_ids.add(source_job_id)

    def _scan_rerender_jobs(self, rerender_jobs_file: str, result: IntegrityScanResult) -> None:
        if not self.storage.exists(rerender_jobs_file):
            return

        try:
            rerender_jobs = self.storage.read_json(rerender_jobs_file)
        except Exception as exc:
            result.add_issue(
                issue_code="broken_rerender_jobs",
                severity="high",
                scope="rerender_jobs",
                reference_id=rerender_jobs_file,
                message=f"rerender_jobs.json ist nicht lesbar: {exc}",
            )
            return

        if not isinstance(rerender_jobs, list):
            result.add_issue(
                issue_code="invalid_rerender_jobs_format",
                severity="high",
                scope="rerender_jobs",
                reference_id=rerender_jobs_file,
                message="rerender_jobs.json ist keine Liste",
            )
            return

        result.rerender_jobs_seen = len(rerender_jobs)

        seen_active_sources: set[str] = set()

        for item in rerender_jobs:
            if not isinstance(item, dict):
                result.add_issue(
                    issue_code="invalid_rerender_job_entry",
                    severity="medium",
                    scope="rerender_jobs",
                    reference_id=rerender_jobs_file,
                    message="Rerender-Job-Eintrag ist kein Objekt",
                )
                continue

            rerender_job_id = str(item.get("rerender_job_id") or "unknown_rerender_job")
            source_job_id = str(item.get("source_job_id") or "")
            status = str(item.get("status") or "")

            if not source_job_id:
                result.add_issue(
                    issue_code="missing_rerender_source_job",
                    severity="medium",
                    scope="rerender_jobs",
                    reference_id=rerender_job_id,
                    message="Rerender-Job ohne source_job_id",
                )

            if status == "processing":
                result.add_issue(
                    issue_code="processing_rerender_requires_review",
                    severity="medium",
                    scope="rerender_jobs",
                    reference_id=rerender_job_id,
                    message="Rerender-Job steht auf processing und braucht manuelle Prüfung",
                )

            if status in {"pending", "processing", "scheduled_retry"} and source_job_id:
                if source_job_id in seen_active_sources:
                    result.add_issue(
                        issue_code="duplicate_active_rerender_job",
                        severity="high",
                        scope="rerender_jobs",
                        reference_id=source_job_id,
                        message="Mehrere aktive Rerender-Jobs für dieselbe source_job_id",
                    )
                else:
                    seen_active_sources.add(source_job_id)