from __future__ import annotations

import json
from pathlib import Path

from models.edit_timeline import EditTimeline
from models.timeline_segment import TimelineSegment


class EditTimelineRepository:
    def _file_path(self, export_path: str | Path) -> Path:
        return Path(export_path) / "edit_timeline.json"

    def _segment_to_dict(self, segment: TimelineSegment) -> dict:
        return {
            "segment_id": segment.segment_id,
            "job_id": segment.job_id,
            "candidate_id": segment.candidate_id,
            "start_time": segment.start_time,
            "end_time": segment.end_time,
            "segment_role": segment.segment_role,
            "selection_score": segment.selection_score,
            "notes": list(segment.notes),
            "source": segment.source,
            "created_at": segment.created_at,
            "updated_at": segment.updated_at,
        }

    def _segment_from_dict(self, data: dict) -> TimelineSegment:
        return TimelineSegment(
            segment_id=str(data.get("segment_id")),
            job_id=str(data.get("job_id")),
            candidate_id=data.get("candidate_id"),
            start_time=float(data.get("start_time", 0.0)),
            end_time=float(data.get("end_time", 0.0)),
            segment_role=str(data.get("segment_role", "bridge")),
            selection_score=float(data.get("selection_score", 0.0)),
            notes=list(data.get("notes", [])),
            source=data.get("source"),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def _timeline_to_dict(self, timeline: EditTimeline) -> dict:
        return {
            "timeline_id": timeline.timeline_id,
            "job_id": timeline.job_id,
            "target_duration": timeline.target_duration,
            "selected_segments": [
                self._segment_to_dict(segment)
                for segment in timeline.selected_segments
            ],
            "hook_segment_id": timeline.hook_segment_id,
            "peak_segment_ids": list(timeline.peak_segment_ids),
            "payoff_segment_id": timeline.payoff_segment_id,
            "timeline_score": timeline.timeline_score,
            "timeline_notes": list(timeline.timeline_notes),
            "created_at": timeline.created_at,
            "updated_at": timeline.updated_at,
        }

    def _timeline_from_dict(self, data: dict) -> EditTimeline:
        return EditTimeline(
            timeline_id=str(data.get("timeline_id")),
            job_id=str(data.get("job_id")),
            target_duration=float(data.get("target_duration", 0.0)),
            selected_segments=[
                self._segment_from_dict(item)
                for item in data.get("selected_segments", [])
            ],
            hook_segment_id=data.get("hook_segment_id"),
            peak_segment_ids=list(data.get("peak_segment_ids", [])),
            payoff_segment_id=data.get("payoff_segment_id"),
            timeline_score=float(data.get("timeline_score", 0.0)),
            timeline_notes=list(data.get("timeline_notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def save_timeline(
        self,
        export_path: str | Path,
        timeline: EditTimeline,
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

    def load_timeline(self, export_path: str | Path) -> EditTimeline | None:
        file_path = self._file_path(export_path)

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self._timeline_from_dict(data)