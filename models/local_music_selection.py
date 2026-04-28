from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class LocalMusicSelection:
    selection_id: str
    job_id: str
    channel_type: str
    asset_id: str

    cue_kind: str
    match_score: float

    start_time: float
    end_time: float

    notes: list[str] = field(default_factory=list)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()