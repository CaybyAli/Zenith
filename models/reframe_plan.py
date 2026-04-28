from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from models.framing_instruction import FramingInstruction


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ReframePlan:
    plan_id: str
    job_id: str
    timeline_id: str

    source_aspect_ratio: str
    primary_target_aspect_ratio: str
    secondary_target_aspect_ratio: str | None = None

    instructions: list[FramingInstruction] = field(default_factory=list)
    plan_notes: list[str] = field(default_factory=list)
    plan_score: float = 0.0

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()