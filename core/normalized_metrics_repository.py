from __future__ import annotations

from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider
from models.normalized_metrics_snapshot import NormalizedMetricsSnapshot


class NormalizedMetricsRepository:
    def __init__(self, storage_provider: BaseStorageProvider | None = None) -> None:
        self.storage = storage_provider or LocalStorageProvider()

    def save_snapshots(
        self,
        storage_path: str,
        snapshots: list[NormalizedMetricsSnapshot],
        filename: str = "normalized_metrics_snapshots.json",
    ) -> str:
        self.storage.ensure_dir(storage_path)

        metrics_file = self.storage.join(storage_path, filename)
        payload = [snapshot.to_dict() for snapshot in snapshots]

        self.storage.write_json(metrics_file, payload, indent=4)

        print(
            "[NormalizedMetricsRepository] "
            f"Saved normalized metrics -> {metrics_file}"
        )
        return metrics_file

    def load_snapshots(
        self,
        storage_path: str,
        filename: str = "normalized_metrics_snapshots.json",
    ) -> list[NormalizedMetricsSnapshot]:
        metrics_file = self.storage.join(storage_path, filename)

        if not self.storage.exists(metrics_file):
            return []

        payload = self.storage.read_json(metrics_file)

        if not isinstance(payload, list):
            raise ValueError(
                f"Invalid normalized metrics payload in {metrics_file}"
            )

        return [
            NormalizedMetricsSnapshot.from_dict(item)
            for item in payload
            if isinstance(item, dict)
        ]

    def append_snapshot(
        self,
        storage_path: str,
        snapshot: NormalizedMetricsSnapshot,
        filename: str = "normalized_metrics_snapshots.json",
    ) -> str:
        snapshots = self.load_snapshots(storage_path, filename=filename)
        snapshots.append(snapshot)
        return self.save_snapshots(
            storage_path=storage_path,
            snapshots=snapshots,
            filename=filename,
        )

    def get_latest_snapshot(
        self,
        storage_path: str,
        variant_id: str,
        target_platform: str,
        filename: str = "normalized_metrics_snapshots.json",
    ) -> NormalizedMetricsSnapshot | None:
        matching_snapshots = [
            snapshot
            for snapshot in self.load_snapshots(storage_path, filename=filename)
            if (
                snapshot.variant_id == variant_id
                and snapshot.target_platform.value == target_platform
            )
        ]

        if not matching_snapshots:
            return None

        matching_snapshots.sort(
            key=lambda snapshot: snapshot.synced_at or "",
            reverse=True,
        )
        return matching_snapshots[0]