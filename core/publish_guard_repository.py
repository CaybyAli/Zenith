from __future__ import annotations

from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider
from models.publish_guard_result import PublishGuardResult


class PublishGuardRepository:
    def __init__(self, storage_provider: BaseStorageProvider | None = None) -> None:
        self.storage = storage_provider or LocalStorageProvider()

    def save_results(
        self,
        export_path: str,
        guard_results: list[PublishGuardResult],
        results_filename: str = "publish_guard_results.json",
    ) -> str:
        self.storage.ensure_dir(export_path)

        results_file = self.storage.join(export_path, results_filename)
        payload = [result.to_dict() for result in guard_results]

        self.storage.write_json(results_file, payload, indent=4)

        print(f"[PublishGuardRepository] Saved guard results -> {results_file}")
        return results_file

    def load_results(
        self,
        export_path: str,
        results_filename: str = "publish_guard_results.json",
    ) -> list[PublishGuardResult]:
        results_file = self.storage.join(export_path, results_filename)

        if not self.storage.exists(results_file):
            return []

        payload = self.storage.read_json(results_file)

        if not isinstance(payload, list):
            raise ValueError(f"Invalid guard results payload in {results_file}")

        return [
            PublishGuardResult.from_dict(item)
            for item in payload
            if isinstance(item, dict)
        ]

    def get_result_by_platform(
        self,
        export_path: str,
        platform: str,
        results_filename: str = "publish_guard_results.json",
    ) -> PublishGuardResult | None:
        for result in self.load_results(export_path, results_filename=results_filename):
            if result.target_platform.value == platform:
                return result

        return None