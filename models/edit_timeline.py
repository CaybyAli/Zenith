from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from models.timeline_segment import TimelineSegment


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class EditTimeline:
    timeline_id: str
    job_id: str

    target_duration: float
    selected_segments: list[TimelineSegment] = field(default_factory=list)

    hook_segment_id: str | None = None
    peak_segment_ids: list[str] = field(default_factory=list)
    payoff_segment_id: str | None = None

    timeline_score: float = 0.0
    timeline_notes: list[str] = field(default_factory=list)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    @property
    def total_selected_duration(self) -> float:
        return round(sum(segment.duration for segment in self.selected_segments), 3)