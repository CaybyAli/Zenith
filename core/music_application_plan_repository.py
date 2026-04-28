from __future__ import annotations

import json
from pathlib import Path

from models.music_application_instruction import MusicApplicationInstruction
from models.music_application_plan import MusicApplicationPlan


class MusicApplicationPlanRepository:
    def _file_path(self, export_path: str | Path) -> Path:
        return Path(export_path) / "music_application_plan.json"

    def _instruction_to_dict(self, instruction: MusicApplicationInstruction) -> dict:
        return {
            "instruction_id": instruction.instruction_id,
            "job_id": instruction.job_id,
            "channel_type": instruction.channel_type,
            "asset_id": instruction.asset_id,
            "cue_kind": instruction.cue_kind,
            "source_file_path": instruction.source_file_path,
            "start_time": instruction.start_time,
            "end_time": instruction.end_time,
            "music_level": instruction.music_level,
            "voice_priority": instruction.voice_priority,
            "ducking_required": instruction.ducking_required,
            "fade_in_seconds": instruction.fade_in_seconds,
            "fade_out_seconds": instruction.fade_out_seconds,
            "notes": list(instruction.notes),
            "created_at": instruction.created_at,
            "updated_at": instruction.updated_at,
        }

    def _instruction_from_dict(self, data: dict) -> MusicApplicationInstruction:
        return MusicApplicationInstruction(
            instruction_id=str(data.get("instruction_id")),
            job_id=str(data.get("job_id")),
            channel_type=str(data.get("channel_type", "")),
            asset_id=str(data.get("asset_id", "")),
            cue_kind=str(data.get("cue_kind", "")),
            source_file_path=str(data.get("source_file_path", "")),
            start_time=float(data.get("start_time", 0.0)),
            end_time=float(data.get("end_time", 0.0)),
            music_level=float(data.get("music_level", 0.0)),
            voice_priority=float(data.get("voice_priority", 0.0)),
            ducking_required=bool(data.get("ducking_required", False)),
            fade_in_seconds=float(data.get("fade_in_seconds", 0.0)),
            fade_out_seconds=float(data.get("fade_out_seconds", 0.0)),
            notes=list(data.get("notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def _plan_to_dict(self, plan: MusicApplicationPlan) -> dict:
        return {
            "plan_id": plan.plan_id,
            "job_id": plan.job_id,
            "channel_type": plan.channel_type,
            "instructions": [
                self._instruction_to_dict(instruction)
                for instruction in plan.instructions
            ],
            "application_score": plan.application_score,
            "notes": list(plan.notes),
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
        }

    def _plan_from_dict(self, data: dict) -> MusicApplicationPlan:
        return MusicApplicationPlan(
            plan_id=str(data.get("plan_id")),
            job_id=str(data.get("job_id")),
            channel_type=str(data.get("channel_type", "")),
            instructions=[
                self._instruction_from_dict(item)
                for item in data.get("instructions", [])
            ],
            application_score=float(data.get("application_score", 0.0)),
            notes=list(data.get("notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def save_plan(self, export_path: str | Path, plan: MusicApplicationPlan) -> str:
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

    def load_plan(self, export_path: str | Path) -> MusicApplicationPlan | None:
        file_path = self._file_path(export_path)

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self._plan_from_dict(data)