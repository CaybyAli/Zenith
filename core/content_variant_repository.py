from __future__ import annotations

from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider
from models.content_variant import ContentVariant


class ContentVariantRepository:
    def __init__(self, storage_provider: BaseStorageProvider | None = None) -> None:
        self.storage = storage_provider or LocalStorageProvider()

    def save_variants(
        self,
        export_path: str,
        variants: list[ContentVariant],
    ) -> str:
        self.storage.ensure_dir(export_path)

        variants_file = self.storage.join(export_path, "variants.json")
        payload = [variant.to_dict() for variant in variants]

        self.storage.write_json(variants_file, payload, indent=4)

        print(f"[ContentVariantRepository] Saved variants -> {variants_file}")
        return variants_file

    def load_variants(self, export_path: str) -> list[ContentVariant]:
        variants_file = self.storage.join(export_path, "variants.json")

        if not self.storage.exists(variants_file):
            return []

        payload = self.storage.read_json(variants_file)

        if not isinstance(payload, list):
            raise ValueError(f"Invalid variants payload in {variants_file}")

        return [
            ContentVariant.from_dict(item)
            for item in payload
            if isinstance(item, dict)
        ]

    def get_variant_by_platform(
        self,
        export_path: str,
        platform: str,
    ) -> ContentVariant | None:
        for variant in self.load_variants(export_path):
            if variant.target_platform.value == platform:
                return variant

        return None