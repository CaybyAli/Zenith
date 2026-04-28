from __future__ import annotations

from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider
from models.platform_raw_metrics import PlatformRawMetrics


class PlatformRawMetricsRepository:
    def __init__(self, storage_provider: BaseStorageProvider | None = None) -> None:
        self.storage = storage_provider or LocalStorageProvider()

    def save_snapshots(
        self,
        storage_path: str,
        snapshots: list[PlatformRawMetrics],
        filename: str = "platform_raw_metrics.json",
    ) -> str:
        self.storage.ensure_dir(storage_path)

        metrics_file = self.storage.join(storage_path, filename)
        payload = [snapshot.to_dict() for snapshot in snapshots]

        self.storage.write_json(metrics_file, payload, indent=4)

        print(
            f"[PlatformRawMetricsRepository] Saved raw metrics -> {metrics_file}"
        )
        return metrics_file

    def load_snapshots(
        self,
        storage_path: str,
        filename: str = "platform_raw_metrics.json",
    ) -> list[PlatformRawMetrics]:
        metrics_file = self.storage.join(storage_path, filename)

        if not self.storage.exists(metrics_file):
            return []

        payload = self.storage.read_json(metrics_file)

        if not isinstance(payload, list):
            raise ValueError(f"Invalid raw metrics payload in {metrics_file}")

        return [
            PlatformRawMetrics.from_dict(item)
            for item in payload
            if isinstance(item, dict)
        ]

    def append_snapshot(
        self,
        storage_path: str,
        snapshot: PlatformRawMetrics,
        filename: str = "platform_raw_metrics.json",
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
        filename: str = "platform_raw_metrics.json",
    ) -> PlatformRawMetrics | None:
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