from __future__ import annotations

from dataclasses import dataclass, field


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 3)


@dataclass
class GameplayVisionWindow:
    start_seconds: float
    end_seconds: float
    motion_score: float
    action_score: float
    scene_change_score: float
    label: str
    reason: str

    def __post_init__(self) -> None:
        self.start_seconds = round(max(0.0, float(self.start_seconds)), 3)
        self.end_seconds = round(max(self.start_seconds + 0.001, float(self.end_seconds)), 3)
        self.motion_score = _clamp_score(self.motion_score)
        self.action_score = _clamp_score(self.action_score)
        self.scene_change_score = _clamp_score(self.scene_change_score)
        self.label = str(self.label or "unknown")
        self.reason = str(self.reason or "")

    def to_dict(self) -> dict[str, object]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "motion_score": self.motion_score,
            "action_score": self.action_score,
            "scene_change_score": self.scene_change_score,
            "label": self.label,
            "reason": self.reason,
        }


@dataclass
class GameplayVisionResult:
    windows: list[GameplayVisionWindow] = field(default_factory=list)
    action_windows: list[GameplayVisionWindow] = field(default_factory=list)
    average_action_score: float = 0.0
    max_action_score: float = 0.0
    engine: str = "gameplay-vision-analyzer-v1"
    skipped_reason: str | None = None

    def __post_init__(self) -> None:
        self.average_action_score = _clamp_score(self.average_action_score)
        self.max_action_score = _clamp_score(self.max_action_score)

    @property
    def is_empty(self) -> bool:
        return not self.windows

    def to_dict(self) -> dict[str, object]:
        return {
            "windows": [window.to_dict() for window in self.windows],
            "action_windows": [window.to_dict() for window in self.action_windows],
            "average_action_score": self.average_action_score,
            "max_action_score": self.max_action_score,
            "engine": self.engine,
            "skipped_reason": self.skipped_reason,
        }
