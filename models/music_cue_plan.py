from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from models.audio_cue import AudioCue
from models.audio_mix_instruction import AudioMixInstruction


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class MusicCuePlan:
    plan_id: str
    job_id: str
    timeline_id: str

    audio_cues: list[AudioCue] = field(default_factory=list)
    audio_mix_instructions: list[AudioMixInstruction] = field(default_factory=list)

    plan_score: float = 0.0
    notes: list[str] = field(default_factory=list)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()