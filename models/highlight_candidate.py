from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class HighlightCandidate:
    candidate_id: str
    job_id: str

    start_time: float
    end_time: float
    highlight_score: float

    candidate_kind: str = "unknown"
    confidence: float = 0.0
    signal_tags: list[str] = field(default_factory=list)
    source: str | None = None
    notes: list[str] = field(default_factory=list)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    @property
    def duration(self) -> float:
        return max(0.0, round(self.end_time - self.start_time, 3))