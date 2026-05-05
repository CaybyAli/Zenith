from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_WEIGHT_MIN = -2.0
_WEIGHT_MAX = 2.0


def _clamp_weight(value: float) -> float:
    return round(max(_WEIGHT_MIN, min(_WEIGHT_MAX, float(value))), 4)


@dataclass
class CutScoringProfile:
    profile_name: str
    channel_type: str
    description: str
    indicator_weights: dict[str, float] = field(default_factory=dict)
    positive_indicator_types: list[str] = field(default_factory=list)
    negative_indicator_types: list[str] = field(default_factory=list)
    neutral_indicator_types: list[str] = field(default_factory=list)
    min_segment_duration_seconds: float = 3.0
    max_segment_duration_seconds: float = 30.0
    target_pacing: str = "balanced"
    speech_safety_weight: float = 1.0
    gameplay_weight: float = 1.0
    facecam_weight: float = 1.0
    audio_reaction_weight: float = 1.0
    story_weight: float = 1.0
    dead_air_penalty_weight: float = 1.0
    micro_cut_penalty_weight: float = 1.0
    duplicate_penalty_weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.indicator_weights = {
            k: _clamp_weight(v) for k, v in (self.indicator_weights or {}).items()
        }

    def get_weight(self, indicator_type: str, default: float = 0.0) -> float:
        return self.indicator_weights.get(indicator_type, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "channel_type": self.channel_type,
            "description": self.description,
            "indicator_weights": dict(self.indicator_weights),
            "positive_indicator_types": list(self.positive_indicator_types),
            "negative_indicator_types": list(self.negative_indicator_types),
            "neutral_indicator_types": list(self.neutral_indicator_types),
            "min_segment_duration_seconds": self.min_segment_duration_seconds,
            "max_segment_duration_seconds": self.max_segment_duration_seconds,
            "target_pacing": self.target_pacing,
            "speech_safety_weight": self.speech_safety_weight,
            "gameplay_weight": self.gameplay_weight,
            "facecam_weight": self.facecam_weight,
            "audio_reaction_weight": self.audio_reaction_weight,
            "story_weight": self.story_weight,
            "dead_air_penalty_weight": self.dead_air_penalty_weight,
            "micro_cut_penalty_weight": self.micro_cut_penalty_weight,
            "duplicate_penalty_weight": self.duplicate_penalty_weight,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CutScoringProfile":
        return cls(
            profile_name=str(data.get("profile_name", "default")),
            channel_type=str(data.get("channel_type", "default")),
            description=str(data.get("description", "")),
            indicator_weights=dict(data.get("indicator_weights") or {}),
            positive_indicator_types=list(data.get("positive_indicator_types") or []),
            negative_indicator_types=list(data.get("negative_indicator_types") or []),
            neutral_indicator_types=list(data.get("neutral_indicator_types") or []),
            min_segment_duration_seconds=float(data.get("min_segment_duration_seconds", 3.0)),
            max_segment_duration_seconds=float(data.get("max_segment_duration_seconds", 30.0)),
            target_pacing=str(data.get("target_pacing", "balanced")),
            speech_safety_weight=float(data.get("speech_safety_weight", 1.0)),
            gameplay_weight=float(data.get("gameplay_weight", 1.0)),
            facecam_weight=float(data.get("facecam_weight", 1.0)),
            audio_reaction_weight=float(data.get("audio_reaction_weight", 1.0)),
            story_weight=float(data.get("story_weight", 1.0)),
            dead_air_penalty_weight=float(data.get("dead_air_penalty_weight", 1.0)),
            micro_cut_penalty_weight=float(data.get("micro_cut_penalty_weight", 1.0)),
            duplicate_penalty_weight=float(data.get("duplicate_penalty_weight", 1.0)),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class CutScoringProfileResult:
    profile: CutScoringProfile
    engine: str = "channel-cut-profile-v1"
    skipped_reason: str | None = None
