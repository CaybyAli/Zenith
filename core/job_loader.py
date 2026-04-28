from __future__ import annotations

from models.job import Job
from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


class JobLoader:
    def __init__(self, storage_provider: BaseStorageProvider | None = None) -> None:
        self.storage = storage_provider or LocalStorageProvider()

    def load_all_jobs(self, base_path: str = "exports"):
        jobs = []

        if not self.storage.exists(base_path):
            return jobs

        for channel_name in self.storage.list_dir(base_path):
            channel_path = self.storage.join(base_path, channel_name)

            if not self.storage.is_dir(channel_path):
                continue

            for job_id in self.storage.list_dir(channel_path):
                job_path = self.storage.join(channel_path, job_id)

                if not self.storage.is_dir(job_path):
                    continue

                job_file = self.storage.join(job_path, "job.json")

                if self.storage.exists(job_file):
                    try:
                        job_data = self.storage.read_json(job_file)
                        job = Job.from_dict(job_data)
                        jobs.append(job)
                    except Exception as e:
                        print(f"[JobLoader] Fehler bei Job {job_id}: {e}")

        return jobs