from __future__ import annotations

import os
from typing import Any

from models.job import Job
from shared.errors import NotFoundError, StorageError
from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


class JobStore:
    """
    Simple JSON file-based persistence for MVP.
    One file stores all jobs.
    """

    def __init__(
        self,
        db_path: str = "data/jobs.json",
        storage_provider: BaseStorageProvider | None = None,
    ) -> None:
        self.db_path = db_path
        self.storage = storage_provider or LocalStorageProvider()

        parent_dir = os.path.dirname(self.db_path)
        if parent_dir:
            self.storage.ensure_dir(parent_dir)

        if not self.storage.exists(self.db_path):
            self._write_raw({"jobs": {}})

    def create_job(self, job: Job) -> Job:
        data = self._read_raw()
        jobs = data["jobs"]

        if job.job_id in jobs:
            raise StorageError(f"Job already exists: {job.job_id}")

        jobs[job.job_id] = job.to_dict()
        self._write_raw(data)
        return job

    def update_job(self, job: Job) -> Job:
        data = self._read_raw()
        jobs = data["jobs"]

        if job.job_id not in jobs:
            raise NotFoundError(f"Job not found: {job.job_id}")

        job.touch()
        jobs[job.job_id] = job.to_dict()
        self._write_raw(data)
        return job

    def get_job(self, job_id: str) -> Job:
        data = self._read_raw()
        jobs = data["jobs"]

        if job_id not in jobs:
            raise NotFoundError(f"Job not found: {job_id}")

        return Job.from_dict(jobs[job_id])

    def list_jobs(self) -> list[Job]:
        data = self._read_raw()
        return [Job.from_dict(item) for item in data["jobs"].values()]

    def _read_raw(self) -> dict[str, Any]:
        try:
            return self.storage.read_json(self.db_path)
        except Exception as exc:
            raise StorageError(f"Could not read job store: {exc}") from exc

    def _write_raw(self, data: dict[str, Any]) -> None:
        try:
            self.storage.write_json(self.db_path, data, indent=2)
        except Exception as exc:
            raise StorageError(f"Could not write job store: {exc}") from exc