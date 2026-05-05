from __future__ import annotations

from dataclasses import dataclass, field


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 3)


@dataclass
class FacecamReactionWindow:
    start_seconds: float
    end_seconds: float
    reaction_score: float
    motion_score: float
    expression_change_score: float
    label: str
    reason: str

    def __post_init__(self) -> None:
        self.start_seconds = round(max(0.0, float(self.start_seconds)), 3)
        self.end_seconds = round(max(self.start_seconds + 0.001, float(self.end_seconds)), 3)
        self.reaction_score = _clamp_score(self.reaction_score)
        self.motion_score = _clamp_score(self.motion_score)
        self.expression_change_score = _clamp_score(self.expression_change_score)
        self.label = str(self.label or "unknown")
        self.reason = str(self.reason or "")

    def to_dict(self) -> dict[str, object]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "reaction_score": self.reaction_score,
            "motion_score": self.motion_score,
            "expression_change_score": self.expression_change_score,
            "label": self.label,
            "reason": self.reason,
        }


@dataclass
class FacecamReactionResult:
    windows: list[FacecamReactionWindow] = field(default_factory=list)
    reaction_windows: list[FacecamReactionWindow] = field(default_factory=list)
    average_reaction_score: float = 0.0
    max_reaction_score: float = 0.0
    engine: str = "facecam-reaction-analyzer-v1"
    skipped_reason: str | None = None

    def __post_init__(self) -> None:
        self.average_reaction_score = _clamp_score(self.average_reaction_score)
        self.max_reaction_score = _clamp_score(self.max_reaction_score)

    @property
    def is_empty(self) -> bool:
        return not self.windows

    def to_dict(self) -> dict[str, object]:
        return {
            "windows": [window.to_dict() for window in self.windows],
            "reaction_windows": [window.to_dict() for window in self.reaction_windows],
            "average_reaction_score": self.average_reaction_score,
            "max_reaction_score": self.max_reaction_score,
            "engine": self.engine,
            "skipped_reason": self.skipped_reason,
        }
