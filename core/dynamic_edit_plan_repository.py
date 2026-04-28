from __future__ import annotations

import json
from pathlib import Path

from models.dynamic_edit_plan import DynamicEditPlan
from models.reaction_moment import ReactionMoment
from models.zoom_instruction import ZoomInstruction


class DynamicEditPlanRepository:
    def _file_path(self, export_path: str | Path) -> Path:
        return Path(export_path) / "dynamic_edit_plan.json"

    def _moment_to_dict(self, moment: ReactionMoment) -> dict:
        return {
            "moment_id": moment.moment_id,
            "job_id": moment.job_id,
            "timeline_id": moment.timeline_id,
            "segment_id": moment.segment_id,
            "start_time": moment.start_time,
            "end_time": moment.end_time,
            "reaction_kind": moment.reaction_kind,
            "intensity": moment.intensity,
            "confidence": moment.confidence,
            "notes": list(moment.notes),
            "created_at": moment.created_at,
            "updated_at": moment.updated_at,
        }

    def _moment_from_dict(self, data: dict) -> ReactionMoment:
        return ReactionMoment(
            moment_id=str(data.get("moment_id")),
            job_id=str(data.get("job_id")),
            timeline_id=str(data.get("timeline_id")),
            segment_id=str(data.get("segment_id")),
            start_time=float(data.get("start_time", 0.0)),
            end_time=float(data.get("end_time", 0.0)),
            reaction_kind=str(data.get("reaction_kind", "unknown")),
            intensity=float(data.get("intensity", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            notes=list(data.get("notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def _zoom_to_dict(self, zoom: ZoomInstruction) -> dict:
        return {
            "instruction_id": zoom.instruction_id,
            "job_id": zoom.job_id,
            "timeline_id": zoom.timeline_id,
            "segment_id": zoom.segment_id,
            "moment_id": zoom.moment_id,
            "zoom_kind": zoom.zoom_kind,
            "focus_kind": zoom.focus_kind,
            "intensity": zoom.intensity,
            "start_time": zoom.start_time,
            "end_time": zoom.end_time,
            "notes": list(zoom.notes),
            "created_at": zoom.created_at,
            "updated_at": zoom.updated_at,
        }

    def _zoom_from_dict(self, data: dict) -> ZoomInstruction:
        return ZoomInstruction(
            instruction_id=str(data.get("instruction_id")),
            job_id=str(data.get("job_id")),
            timeline_id=str(data.get("timeline_id")),
            segment_id=str(data.get("segment_id")),
            moment_id=data.get("moment_id"),
            zoom_kind=str(data.get("zoom_kind", "hold_frame")),
            focus_kind=str(data.get("focus_kind", "balanced")),
            intensity=float(data.get("intensity", 0.0)),
            start_time=float(data.get("start_time", 0.0)),
            end_time=float(data.get("end_time", 0.0)),
            notes=list(data.get("notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def _plan_to_dict(self, plan: DynamicEditPlan) -> dict:
        return {
            "plan_id": plan.plan_id,
            "job_id": plan.job_id,
            "timeline_id": plan.timeline_id,
            "reaction_moments": [
                self._moment_to_dict(moment)
                for moment in plan.reaction_moments
            ],
            "zoom_instructions": [
                self._zoom_to_dict(zoom)
                for zoom in plan.zoom_instructions
            ],
            "pacing_hints": list(plan.pacing_hints),
            "plan_score": plan.plan_score,
            "plan_notes": list(plan.plan_notes),
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
        }

    def _plan_from_dict(self, data: dict) -> DynamicEditPlan:
        return DynamicEditPlan(
            plan_id=str(data.get("plan_id")),
            job_id=str(data.get("job_id")),
            timeline_id=str(data.get("timeline_id")),
            reaction_moments=[
                self._moment_from_dict(item)
                for item in data.get("reaction_moments", [])
            ],
            zoom_instructions=[
                self._zoom_from_dict(item)
                for item in data.get("zoom_instructions", [])
            ],
            pacing_hints=list(data.get("pacing_hints", [])),
            plan_score=float(data.get("plan_score", 0.0)),
            plan_notes=list(data.get("plan_notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def save_plan(self, export_path: str | Path, plan: DynamicEditPlan) -> str:
        file_path = self._file_path(export_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                self._plan_to_dict(plan),
                f,
                indent=4,
                ensure_ascii=False,
            )

        return str(file_path)

    def load_plan(self, export_path: str | Path) -> DynamicEditPlan | None:
        file_path = self._file_path(export_path)

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self._plan_from_dict(data)