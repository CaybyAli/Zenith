from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ReactionSignalThresholds:
    event_mic_rise_db: float
    event_fusion_score: float
    medium_mic_rise_db: float
    high_mic_rise_db: float
    facecam_motion_hint: float
    precision_negative_false_positive_count: int
    high_medium_recall_ratio: float
    any_reaction_recall_ratio: float


@dataclass(frozen=True)
class ReactionSignalEvidence:
    time_seconds: float
    timestamp: str
    mic_audio_rise_db: float
    mic_peak_over_baseline_db: float
    facecam_change: float
    gameplay_rise_db: float
    gameplay_peak_dbfs: float
    fusion_score: float
    g6_state: str
    g6_intensity: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReactionSignalWindow:
    time_seconds: float
    timestamp: str
    reaction_event: bool
    reaction_intensity: str
    confidence: float
    evidence: ReactionSignalEvidence

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence"] = self.evidence.to_dict()
        return data
