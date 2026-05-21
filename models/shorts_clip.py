from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from models.shorts_reframe_plan import ShortsReframePlan

ShortsClipStatus = Literal["planned", "rendered", "failed"]


@dataclass(slots=True)
class ShortsClip:
    source_job_id: str
    source_start_time: float
    source_end_time: float
    planned_duration: float
    reframe_plan: ShortsReframePlan | None = None
    hook_score: float = 0.0
    llm_rationale: str = ""
    status: ShortsClipStatus = "planned"
    clip_index: int = 0
    output_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reframe_plan"] = (
            self.reframe_plan.to_dict()
            if self.reframe_plan is not None
            else None
        )
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ShortsClip":
        raw = dict(data or {})
        reframe_raw = raw.get("reframe_plan")
        return cls(
            source_job_id=str(raw.get("source_job_id") or ""),
            source_start_time=float(raw.get("source_start_time", 0.0) or 0.0),
            source_end_time=float(raw.get("source_end_time", 0.0) or 0.0),
            planned_duration=float(raw.get("planned_duration", 0.0) or 0.0),
            reframe_plan=(
                ShortsReframePlan.from_dict(reframe_raw)
                if isinstance(reframe_raw, dict)
                else None
            ),
            hook_score=float(raw.get("hook_score", 0.0) or 0.0),
            llm_rationale=str(raw.get("llm_rationale") or ""),
            status=raw.get("status", "planned"),
            clip_index=int(raw.get("clip_index", 0) or 0),
            output_path=str(raw.get("output_path") or ""),
        )
