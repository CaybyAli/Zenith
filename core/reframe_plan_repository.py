from __future__ import annotations

import json
from pathlib import Path

from models.framing_instruction import FramingInstruction
from models.reframe_plan import ReframePlan


class ReframePlanRepository:
    def _file_path(self, export_path: str | Path) -> Path:
        return Path(export_path) / "reframe_plan.json"

    def _instruction_to_dict(self, instruction: FramingInstruction) -> dict:
        return {
            "instruction_id": instruction.instruction_id,
            "job_id": instruction.job_id,
            "timeline_id": instruction.timeline_id,
            "segment_id": instruction.segment_id,
            "focus_kind": instruction.focus_kind,
            "layout_kind": instruction.layout_kind,
            "source_aspect_ratio": instruction.source_aspect_ratio,
            "target_aspect_ratio": instruction.target_aspect_ratio,
            "crop_window": dict(instruction.crop_window),
            "notes": list(instruction.notes),
            "metadata": dict(instruction.metadata),
            "created_at": instruction.created_at,
            "updated_at": instruction.updated_at,
        }

    def _instruction_from_dict(self, data: dict) -> FramingInstruction:
        return FramingInstruction(
            instruction_id=str(data.get("instruction_id")),
            job_id=str(data.get("job_id")),
            timeline_id=str(data.get("timeline_id")),
            segment_id=str(data.get("segment_id")),
            focus_kind=str(data.get("focus_kind", "unknown")),
            layout_kind=str(data.get("layout_kind", "full_gameplay")),
            source_aspect_ratio=str(data.get("source_aspect_ratio", "unknown")),
            target_aspect_ratio=str(data.get("target_aspect_ratio", "unknown")),
            crop_window=dict(data.get("crop_window", {})),
            notes=list(data.get("notes", [])),
            metadata=dict(data.get("metadata", {})),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def _plan_to_dict(self, plan: ReframePlan) -> dict:
        return {
            "plan_id": plan.plan_id,
            "job_id": plan.job_id,
            "timeline_id": plan.timeline_id,
            "source_aspect_ratio": plan.source_aspect_ratio,
            "primary_target_aspect_ratio": plan.primary_target_aspect_ratio,
            "secondary_target_aspect_ratio": plan.secondary_target_aspect_ratio,
            "instructions": [
                self._instruction_to_dict(instruction)
                for instruction in plan.instructions
            ],
            "plan_notes": list(plan.plan_notes),
            "plan_score": plan.plan_score,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
        }

    def _plan_from_dict(self, data: dict) -> ReframePlan:
        return ReframePlan(
            plan_id=str(data.get("plan_id")),
            job_id=str(data.get("job_id")),
            timeline_id=str(data.get("timeline_id")),
            source_aspect_ratio=str(data.get("source_aspect_ratio", "unknown")),
            primary_target_aspect_ratio=str(
                data.get("primary_target_aspect_ratio", "unknown")
            ),
            secondary_target_aspect_ratio=data.get("secondary_target_aspect_ratio"),
            instructions=[
                self._instruction_from_dict(item)
                for item in data.get("instructions", [])
            ],
            plan_notes=list(data.get("plan_notes", [])),
            plan_score=float(data.get("plan_score", 0.0)),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def save_plan(
        self,
        export_path: str | Path,
        plan: ReframePlan,
    ) -> str:
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

    def load_plan(self, export_path: str | Path) -> ReframePlan | None:
        file_path = self._file_path(export_path)

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self._plan_from_dict(data)