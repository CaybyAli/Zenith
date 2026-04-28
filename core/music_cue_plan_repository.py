from __future__ import annotations

import json
from pathlib import Path

from models.audio_cue import AudioCue
from models.audio_mix_instruction import AudioMixInstruction
from models.music_cue_plan import MusicCuePlan


class MusicCuePlanRepository:
    def _file_path(self, export_path: str | Path) -> Path:
        return Path(export_path) / "music_cue_plan.json"

    def _audio_cue_to_dict(self, cue: AudioCue) -> dict:
        return {
            "cue_id": cue.cue_id,
            "job_id": cue.job_id,
            "timeline_id": cue.timeline_id,
            "segment_id": cue.segment_id,
            "cue_kind": cue.cue_kind,
            "start_time": cue.start_time,
            "end_time": cue.end_time,
            "intensity": cue.intensity,
            "priority": cue.priority,
            "notes": list(cue.notes),
            "created_at": cue.created_at,
            "updated_at": cue.updated_at,
        }

    def _audio_cue_from_dict(self, data: dict) -> AudioCue:
        return AudioCue(
            cue_id=str(data.get("cue_id")),
            job_id=str(data.get("job_id")),
            timeline_id=str(data.get("timeline_id")),
            segment_id=str(data.get("segment_id")),
            cue_kind=str(data.get("cue_kind", "transition_bed")),
            start_time=float(data.get("start_time", 0.0)),
            end_time=float(data.get("end_time", 0.0)),
            intensity=float(data.get("intensity", 0.0)),
            priority=float(data.get("priority", 0.0)),
            notes=list(data.get("notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def _mix_instruction_to_dict(self, instruction: AudioMixInstruction) -> dict:
        return {
            "instruction_id": instruction.instruction_id,
            "segment_id": instruction.segment_id,
            "voice_priority": instruction.voice_priority,
            "music_level": instruction.music_level,
            "ducking_required": instruction.ducking_required,
            "notes": list(instruction.notes),
            "created_at": instruction.created_at,
            "updated_at": instruction.updated_at,
        }

    def _mix_instruction_from_dict(self, data: dict) -> AudioMixInstruction:
        return AudioMixInstruction(
            instruction_id=str(data.get("instruction_id")),
            segment_id=str(data.get("segment_id")),
            voice_priority=float(data.get("voice_priority", 0.0)),
            music_level=float(data.get("music_level", 0.0)),
            ducking_required=bool(data.get("ducking_required", False)),
            notes=list(data.get("notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def _plan_to_dict(self, plan: MusicCuePlan) -> dict:
        return {
            "plan_id": plan.plan_id,
            "job_id": plan.job_id,
            "timeline_id": plan.timeline_id,
            "audio_cues": [self._audio_cue_to_dict(cue) for cue in plan.audio_cues],
            "audio_mix_instructions": [
                self._mix_instruction_to_dict(instruction)
                for instruction in plan.audio_mix_instructions
            ],
            "plan_score": plan.plan_score,
            "notes": list(plan.notes),
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
        }

    def _plan_from_dict(self, data: dict) -> MusicCuePlan:
        return MusicCuePlan(
            plan_id=str(data.get("plan_id")),
            job_id=str(data.get("job_id")),
            timeline_id=str(data.get("timeline_id")),
            audio_cues=[
                self._audio_cue_from_dict(item)
                for item in data.get("audio_cues", [])
            ],
            audio_mix_instructions=[
                self._mix_instruction_from_dict(item)
                for item in data.get("audio_mix_instructions", [])
            ],
            plan_score=float(data.get("plan_score", 0.0)),
            notes=list(data.get("notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def save_plan(self, export_path: str | Path, plan: MusicCuePlan) -> str:
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

    def load_plan(self, export_path: str | Path) -> MusicCuePlan | None:
        file_path = self._file_path(export_path)

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self._plan_from_dict(data)