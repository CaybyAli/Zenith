from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TimelineSegment:
    segment_id: str
    job_id: str
    candidate_id: str | None

    start_time: float
    end_time: float
    segment_role: str
    selection_score: float

    notes: list[str] = field(default_factory=list)
    source: str | None = None

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    @property
    def duration(self) -> float:
        return max(0.0, round(self.end_time - self.start_time, 3))