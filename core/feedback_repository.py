from __future__ import annotations

from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider
from models.feedback_record import FeedbackRecord


class FeedbackRepository:
    def __init__(self, storage_provider: BaseStorageProvider | None = None) -> None:
        self.storage = storage_provider or LocalStorageProvider()

    def save_records(
        self,
        storage_path: str,
        records: list[FeedbackRecord],
        filename: str = "feedback_records.json",
    ) -> str:
        self.storage.ensure_dir(storage_path)

        feedback_file = self.storage.join(storage_path, filename)
        payload = [record.to_dict() for record in records]

        self.storage.write_json(feedback_file, payload, indent=4)

        print(
            f"[FeedbackRepository] Saved feedback records -> {feedback_file}"
        )
        return feedback_file

    def load_records(
        self,
        storage_path: str,
        filename: str = "feedback_records.json",
    ) -> list[FeedbackRecord]:
        feedback_file = self.storage.join(storage_path, filename)

        if not self.storage.exists(feedback_file):
            return []

        payload = self.storage.read_json(feedback_file)

        if not isinstance(payload, list):
            raise ValueError(f"Invalid feedback payload in {feedback_file}")

        return [
            FeedbackRecord.from_dict(item)
            for item in payload
            if isinstance(item, dict)
        ]

    def append_record(
        self,
        storage_path: str,
        record: FeedbackRecord,
        filename: str = "feedback_records.json",
    ) -> str:
        records = self.load_records(storage_path, filename=filename)
        records.append(record)
        return self.save_records(
            storage_path=storage_path,
            records=records,
            filename=filename,
        )