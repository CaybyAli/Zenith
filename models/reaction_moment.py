from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ReactionMoment:
    moment_id: str
    job_id: str
    timeline_id: str
    segment_id: str

    start_time: float
    end_time: float
    reaction_kind: str
    intensity: float

    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    @property
    def duration(self) -> float:
        return max(0.0, round(self.end_time - self.start_time, 3))