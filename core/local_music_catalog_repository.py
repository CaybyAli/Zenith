from __future__ import annotations

import json
from pathlib import Path

from models.local_music_asset import LocalMusicAsset


class LocalMusicCatalogRepository:
    def __init__(self, catalog_path: str | Path = "data/music_catalogs/gaming_main_music_catalog.json") -> None:
        self.catalog_path = Path(catalog_path)

    def _asset_to_dict(self, asset: LocalMusicAsset) -> dict:
        return {
            "asset_id": asset.asset_id,
            "channel_type": asset.channel_type,
            "title": asset.title,
            "file_path": asset.file_path,
            "duration_seconds": asset.duration_seconds,
            "energy_level": asset.energy_level,
            "mood_tags": list(asset.mood_tags),
            "cue_kinds": list(asset.cue_kinds),
            "source_provider": asset.source_provider,
            "active": asset.active,
            "notes": list(asset.notes),
            "created_at": asset.created_at,
            "updated_at": asset.updated_at,
        }

    def _asset_from_dict(self, data: dict) -> LocalMusicAsset:
        return LocalMusicAsset(
            asset_id=str(data.get("asset_id")),
            channel_type=str(data.get("channel_type", "gaming_main")),
            title=str(data.get("title", "")),
            file_path=str(data.get("file_path", "")),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            energy_level=float(data.get("energy_level", 0.0)),
            mood_tags=list(data.get("mood_tags", [])),
            cue_kinds=list(data.get("cue_kinds", [])),
            source_provider=str(data.get("source_provider", "epidemic_local")),
            active=bool(data.get("active", True)),
            notes=list(data.get("notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def save_assets(self, assets: list[LocalMusicAsset]) -> str:
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "assets": [self._asset_to_dict(asset) for asset in assets],
        }

        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)

        return str(self.catalog_path)

    def load_assets(self) -> list[LocalMusicAsset]:
        if not self.catalog_path.exists():
            return []

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [
            self._asset_from_dict(item)
            for item in data.get("assets", [])
        ]