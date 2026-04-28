from __future__ import annotations

from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider
from models.performance_attribution_snapshot import PerformanceAttributionSnapshot


class PerformanceAttributionRepository:
    def __init__(self, storage_provider: BaseStorageProvider | None = None) -> None:
        self.storage = storage_provider or LocalStorageProvider()

    def save_snapshots(
        self,
        storage_path: str,
        snapshots: list[PerformanceAttributionSnapshot],
        filename: str = "performance_attribution_snapshots.json",
    ) -> str:
        self.storage.ensure_dir(storage_path)

        attribution_file = self.storage.join(storage_path, filename)
        payload = [snapshot.to_dict() for snapshot in snapshots]

        self.storage.write_json(attribution_file, payload, indent=4)

        print(
            "[PerformanceAttributionRepository] "
            f"Saved attribution snapshots -> {attribution_file}"
        )
        return attribution_file

    def load_snapshots(
        self,
        storage_path: str,
        filename: str = "performance_attribution_snapshots.json",
    ) -> list[PerformanceAttributionSnapshot]:
        attribution_file = self.storage.join(storage_path, filename)

        if not self.storage.exists(attribution_file):
            return []

        payload = self.storage.read_json(attribution_file)

        if not isinstance(payload, list):
            raise ValueError(
                f"Invalid attribution payload in {attribution_file}"
            )

        return [
            PerformanceAttributionSnapshot.from_dict(item)
            for item in payload
            if isinstance(item, dict)
        ]

    def append_snapshot(
        self,
        storage_path: str,
        snapshot: PerformanceAttributionSnapshot,
        filename: str = "performance_attribution_snapshots.json",
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
        filename: str = "performance_attribution_snapshots.json",
    ) -> PerformanceAttributionSnapshot | None:
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