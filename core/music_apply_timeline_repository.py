from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.music_apply_segment import MusicApplySegment
from models.music_apply_timeline import MusicApplyTimeline


class MusicApplyTimelineRepository:
    def _file_path(self, export_path: str | Path) -> Path:
        return Path(export_path) / "music_apply_timeline.json"

    def _segment_from_dict(self, data: dict[str, Any]) -> MusicApplySegment:
        segment_kwargs: dict[str, Any] = {
            "segment_id": str(data.get("segment_id", "")),
            "job_id": str(data.get("job_id", "")),
            "asset_id": str(data.get("asset_id", "")),
            "cue_kind": str(data.get("cue_kind", "")),
            "source_file_path": str(data.get("source_file_path", "")),
            "video_start_time": float(data.get("video_start_time", 0.0) or 0.0),
            "video_end_time": float(data.get("video_end_time", 0.0) or 0.0),
            "music_offset_start": float(data.get("music_offset_start", 0.0) or 0.0),
            "music_offset_end": float(data.get("music_offset_end", 0.0) or 0.0),
            "music_level": float(data.get("music_level", 0.0) or 0.0),
            "voice_priority": float(data.get("voice_priority", 0.0) or 0.0),
            "ducking_required": bool(data.get("ducking_required", False)),
            "fade_in_seconds": float(data.get("fade_in_seconds", 0.0) or 0.0),
            "fade_out_seconds": float(data.get("fade_out_seconds", 0.0) or 0.0),
            "notes": list(data.get("notes", [])),
        }
        if data.get("created_at") is not None:
            segment_kwargs["created_at"] = str(data["created_at"])
        if data.get("updated_at") is not None:
            segment_kwargs["updated_at"] = str(data["updated_at"])
        return MusicApplySegment(**segment_kwargs)

    def _timeline_from_dict(self, data: dict[str, Any]) -> MusicApplyTimeline:
        timeline_kwargs: dict[str, Any] = {
            "timeline_id": str(data.get("timeline_id", "")),
            "job_id": str(data.get("job_id", "")),
            "channel_type": str(data.get("channel_type", "")),
            "segments": [
                self._segment_from_dict(item)
                for item in data.get("segments", [])
            ],
            "timeline_score": float(data.get("timeline_score", 0.0) or 0.0),
            "notes": list(data.get("notes", [])),
        }
        if data.get("created_at") is not None:
            timeline_kwargs["created_at"] = str(data["created_at"])
        if data.get("updated_at") is not None:
            timeline_kwargs["updated_at"] = str(data["updated_at"])
        return MusicApplyTimeline(**timeline_kwargs)

    def load_timeline(self, export_path: str | Path) -> MusicApplyTimeline | None:
        file_path = self._file_path(export_path)

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self._timeline_from_dict(data)
