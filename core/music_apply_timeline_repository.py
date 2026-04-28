from __future__ import annotations

import json
from pathlib import Path

from models.music_apply_segment import MusicApplySegment
from models.music_apply_timeline import MusicApplyTimeline


class MusicApplyTimelineRepository:
    def _file_path(self, export_path: str | Path) -> Path:
        return Path(export_path) / "music_apply_timeline.json"

    def _segment_to_dict(self, segment: MusicApplySegment) -> dict:
        return {
            "segment_id": segment.segment_id,
            "job_id": segment.job_id,
            "asset_id": segment.asset_id,
            "cue_kind": segment.cue_kind,
            "source_file_path": segment.source_file_path,
            "video_start_time": segment.video_start_time,
            "video_end_time": segment.video_end_time,
            "music_offset_start": segment.music_offset_start,
            "music_offset_end": segment.music_offset_end,
            "music_level": segment.music_level,
            "voice_priority": segment.voice_priority,
            "ducking_required": segment.ducking_required,
            "fade_in_seconds": segment.fade_in_seconds,
            "fade_out_seconds": segment.fade_out_seconds,
            "notes": list(segment.notes),
            "created_at": segment.created_at,
            "updated_at": segment.updated_at,
        }

    def _segment_from_dict(self, data: dict) -> MusicApplySegment:
        return MusicApplySegment(
            segment_id=str(data.get("segment_id")),
            job_id=str(data.get("job_id")),
            asset_id=str(data.get("asset_id", "")),
            cue_kind=str(data.get("cue_kind", "")),
            source_file_path=str(data.get("source_file_path", "")),
            video_start_time=float(data.get("video_start_time", 0.0)),
            video_end_time=float(data.get("video_end_time", 0.0)),
            music_offset_start=float(data.get("music_offset_start", 0.0)),
            music_offset_end=float(data.get("music_offset_end", 0.0)),
            music_level=float(data.get("music_level", 0.0)),
            voice_priority=float(data.get("voice_priority", 0.0)),
            ducking_required=bool(data.get("ducking_required", False)),
            fade_in_seconds=float(data.get("fade_in_seconds", 0.0)),
            fade_out_seconds=float(data.get("fade_out_seconds", 0.0)),
            notes=list(data.get("notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def _timeline_to_dict(self, timeline: MusicApplyTimeline) -> dict:
        return {
            "timeline_id": timeline.timeline_id,
            "job_id": timeline.job_id,
            "channel_type": timeline.channel_type,
            "segments": [
                self._segment_to_dict(segment)
                for segment in timeline.segments
            ],
            "timeline_score": timeline.timeline_score,
            "notes": list(timeline.notes),
            "created_at": timeline.created_at,
            "updated_at": timeline.updated_at,
        }

    def _timeline_from_dict(self, data: dict) -> MusicApplyTimeline:
        return MusicApplyTimeline(
            timeline_id=str(data.get("timeline_id")),
            job_id=str(data.get("job_id")),
            channel_type=str(data.get("channel_type", "")),
            segments=[
                self._segment_from_dict(item)
                for item in data.get("segments", [])
            ],
            timeline_score=float(data.get("timeline_score", 0.0)),
            notes=list(data.get("notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def save_timeline(
        self,
        export_path: str | Path,
        timeline: MusicApplyTimeline,
    ) -> str:
        file_path = self._file_path(export_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                self._timeline_to_dict(timeline),
                f,
                indent=4,
                ensure_ascii=False,
            )

        return str(file_path)

    def load_timeline(
        self,
        export_path: str | Path,
    ) -> MusicApplyTimeline | None:
        file_path = self._file_path(export_path)

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self._timeline_from_dict(data)