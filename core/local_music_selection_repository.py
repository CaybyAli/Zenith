from __future__ import annotations

import json
from pathlib import Path

from models.local_music_selection import LocalMusicSelection


class LocalMusicSelectionRepository:
    def _file_path(self, export_path: str | Path) -> Path:
        return Path(export_path) / "local_music_selections.json"

    def _selection_to_dict(self, selection: LocalMusicSelection) -> dict:
        return {
            "selection_id": selection.selection_id,
            "job_id": selection.job_id,
            "channel_type": selection.channel_type,
            "asset_id": selection.asset_id,
            "cue_kind": selection.cue_kind,
            "match_score": selection.match_score,
            "start_time": selection.start_time,
            "end_time": selection.end_time,
            "notes": list(selection.notes),
            "created_at": selection.created_at,
            "updated_at": selection.updated_at,
        }

    def _selection_from_dict(self, data: dict) -> LocalMusicSelection:
        return LocalMusicSelection(
            selection_id=str(data.get("selection_id")),
            job_id=str(data.get("job_id")),
            channel_type=str(data.get("channel_type", "")),
            asset_id=str(data.get("asset_id", "")),
            cue_kind=str(data.get("cue_kind", "")),
            match_score=float(data.get("match_score", 0.0)),
            start_time=float(data.get("start_time", 0.0)),
            end_time=float(data.get("end_time", 0.0)),
            notes=list(data.get("notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def save_selections(
        self,
        export_path: str | Path,
        selections: list[LocalMusicSelection],
    ) -> str:
        file_path = self._file_path(export_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "selections": [
                self._selection_to_dict(selection)
                for selection in selections
            ]
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)

        return str(file_path)

    def load_selections(
        self,
        export_path: str | Path,
    ) -> list[LocalMusicSelection]:
        file_path = self._file_path(export_path)

        if not file_path.exists():
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [
            self._selection_from_dict(item)
            for item in data.get("selections", [])
        ]