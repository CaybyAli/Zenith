from __future__ import annotations

import os
import shutil

from core.local_music_selection_repository import LocalMusicSelectionRepository
from models.local_music_selection import LocalMusicSelection


def main() -> None:
    test_dir = os.path.join("tmp", "local_music_selection_repository_smoke")
    export_path = os.path.join(test_dir, "export")

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    selections = [
        LocalMusicSelection(
            selection_id="sel_001",
            job_id="job_local_music_selection_repo_smoke",
            channel_type="gaming_main",
            asset_id="music_001",
            cue_kind="intro_bed",
            match_score=0.97,
            start_time=10.0,
            end_time=24.0,
            notes=["repo selection"],
        ),
        LocalMusicSelection(
            selection_id="sel_002",
            job_id="job_local_music_selection_repo_smoke",
            channel_type="gaming_main",
            asset_id="music_002",
            cue_kind="peak_hit",
            match_score=0.96,
            start_time=50.0,
            end_time=72.0,
            notes=["repo selection"],
        ),
    ]

    repo = LocalMusicSelectionRepository()
    saved_path = repo.save_selections(export_path, selections)
    loaded = repo.load_selections(export_path)

    assert os.path.exists(saved_path)
    assert len(loaded) == 2
    assert loaded[0].asset_id == "music_001"
    assert loaded[1].cue_kind == "peak_hit"

    print("LOCAL MUSIC SELECTION REPOSITORY SMOKE TEST PASSED")
    print(
        {
            "saved_path": saved_path,
            "selections": len(loaded),
            "asset_ids": [selection.asset_id for selection in loaded],
        }
    )


if __name__ == "__main__":
    main()