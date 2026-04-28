from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class FramingInstruction:
    instruction_id: str
    job_id: str
    timeline_id: str
    segment_id: str

    focus_kind: str
    layout_kind: str

    source_aspect_ratio: str
    target_aspect_ratio: str

    crop_window: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()