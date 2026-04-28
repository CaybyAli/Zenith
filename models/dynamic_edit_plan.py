from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from models.reaction_moment import ReactionMoment
from models.zoom_instruction import ZoomInstruction


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class DynamicEditPlan:
    plan_id: str
    job_id: str
    timeline_id: str

    reaction_moments: list[ReactionMoment] = field(default_factory=list)
    zoom_instructions: list[ZoomInstruction] = field(default_factory=list)
    pacing_hints: list[dict[str, Any]] = field(default_factory=list)

    plan_score: float = 0.0
    plan_notes: list[str] = field(default_factory=list)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()