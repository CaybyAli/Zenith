from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class LocalMusicAsset:
    asset_id: str
    channel_type: str

    title: str
    file_path: str
    duration_seconds: float

    energy_level: float
    mood_tags: list[str] = field(default_factory=list)
    cue_kinds: list[str] = field(default_factory=list)

    source_provider: str = "epidemic_local"
    active: bool = True
    notes: list[str] = field(default_factory=list)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()