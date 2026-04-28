from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.queue_entry import QueueEntry
from shared.errors import NotFoundError, StorageError


class QueueStore:
    def __init__(
        self,
        queue_entries_path: str = "data/queue_entries.json",
    ) -> None:
        self.queue_entries_path = Path(queue_entries_path)
        self.queue_entries_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.queue_entries_path.exists():
            self._write_raw({"queue_entries": {}})

    def create_queue_entry(self, queue_entry: QueueEntry) -> QueueEntry:
        data = self._read_raw()
        queue_entries = data["queue_entries"]

        for existing in queue_entries.values():
            existing_entry = QueueEntry.from_dict(existing)
            if existing_entry.dedupe_key == queue_entry.dedupe_key:
                return existing_entry

        if queue_entry.queue_entry_id in queue_entries:
            raise StorageError(f"Queue entry already exists: {queue_entry.queue_entry_id}")

        queue_entries[queue_entry.queue_entry_id] = queue_entry.to_dict()
        self._write_raw(data)
        return queue_entry

    def update_queue_entry(self, queue_entry: QueueEntry) -> QueueEntry:
        data = self._read_raw()
        queue_entries = data["queue_entries"]

        if queue_entry.queue_entry_id not in queue_entries:
            raise NotFoundError(f"Queue entry not found: {queue_entry.queue_entry_id}")

        queue_entry.touch()
        queue_entries[queue_entry.queue_entry_id] = queue_entry.to_dict()
        self._write_raw(data)
        return queue_entry

    def get_queue_entry(self, queue_entry_id: str) -> QueueEntry:
        data = self._read_raw()
        queue_entries = data["queue_entries"]

        if queue_entry_id not in queue_entries:
            raise NotFoundError(f"Queue entry not found: {queue_entry_id}")

        return QueueEntry.from_dict(queue_entries[queue_entry_id])

    def get_by_dedupe_key(self, dedupe_key: str) -> QueueEntry:
        data = self._read_raw()
        queue_entries = data["queue_entries"]

        for item in queue_entries.values():
            queue_entry = QueueEntry.from_dict(item)
            if queue_entry.dedupe_key == dedupe_key:
                return queue_entry

        raise NotFoundError(f"Queue entry not found for dedupe_key: {dedupe_key}")

    def list_queue_entries(self) -> list[QueueEntry]:
        data = self._read_raw()
        return [QueueEntry.from_dict(item) for item in data["queue_entries"].values()]

    def _read_raw(self) -> dict[str, Any]:
        try:
            with self.queue_entries_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            raise StorageError(f"Could not read queue store: {exc}") from exc

    def _write_raw(self, data: dict[str, Any]) -> None:
        try:
            with self.queue_entries_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            raise StorageError(f"Could not write queue store: {exc}") from exc