from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from models.music_apply_segment import MusicApplySegment


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class MusicApplyTimeline:
    timeline_id: str
    job_id: str
    channel_type: str

    segments: list[MusicApplySegment] = field(default_factory=list)

    timeline_score: float = 0.0
    notes: list[str] = field(default_factory=list)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()