from __future__ import annotations

import os
import shutil

from core.local_music_catalog_repository import LocalMusicCatalogRepository
from models.local_music_asset import LocalMusicAsset


def main() -> None:
    test_dir = os.path.join("tmp", "local_music_catalog_repository_smoke")
    catalog_path = os.path.join(test_dir, "gaming_main_music_catalog.json")

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    assets = [
        LocalMusicAsset(
            asset_id="music_001",
            channel_type="gaming_main",
            title="Main Intro Bed",
            file_path="assets/audio/gaming_main/music/main_intro_bed.mp3",
            duration_seconds=94.5,
            energy_level=0.62,
            mood_tags=["focused", "clean"],
            cue_kinds=["intro_bed", "transition_bed"],
            notes=["local epidemic download"],
        ),
        LocalMusicAsset(
            asset_id="music_002",
            channel_type="gaming_main",
            title="Main Peak Hit",
            file_path="assets/audio/gaming_main/music/main_peak_hit.mp3",
            duration_seconds=71.0,
            energy_level=0.91,
            mood_tags=["hype", "impact"],
            cue_kinds=["peak_hit", "build_up"],
            notes=["local epidemic download"],
        ),
    ]

    repo = LocalMusicCatalogRepository(catalog_path=catalog_path)
    saved_path = repo.save_assets(assets)
    loaded_assets = repo.load_assets()

    assert os.path.exists(saved_path)
    assert len(loaded_assets) == 2
    assert loaded_assets[0].channel_type == "gaming_main"
    assert loaded_assets[0].source_provider == "epidemic_local"
    assert loaded_assets[1].cue_kinds == ["peak_hit", "build_up"]

    print("LOCAL MUSIC CATALOG REPOSITORY SMOKE TEST PASSED")
    print(
        {
            "saved_path": saved_path,
            "assets": len(loaded_assets),
            "titles": [asset.title for asset in loaded_assets],
        }
    )


if __name__ == "__main__":
    main()