from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def _safe_seconds(value: object, fallback: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return round(max(0.0, numeric), 3)


def _clamp_score(value: object, fallback: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return round(max(0.0, min(1.0, numeric)), 3)


class RoundPhase(str, Enum):
    ACTIVE_ROUND = "active_round"
    GOAL_REPLAY = "goal_replay"
    ROUND_END = "round_end"
    MENU_WAIT = "menu_wait"
    QUEUE_WAIT = "queue_wait"
    COUNTDOWN_KICKOFF = "countdown_kickoff"
    UNKNOWN = "unknown"


@dataclass
class RoundPhaseWindow:
    start_seconds: float
    end_seconds: float
    phase: RoundPhase
    confidence: float
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.start_seconds = _safe_seconds(self.start_seconds)
        self.end_seconds = _safe_seconds(self.end_seconds, self.start_seconds)
        if self.end_seconds < self.start_seconds:
            self.end_seconds = self.start_seconds
        if not isinstance(self.phase, RoundPhase):
            self.phase = RoundPhase(str(self.phase))
        self.confidence = _clamp_score(self.confidence)
        self.evidence = dict(self.evidence or {})

    @property
    def duration_seconds(self) -> float:
        return round(max(0.0, self.end_seconds - self.start_seconds), 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "phase": self.phase.value,
            "confidence": self.confidence,
            "evidence": dict(self.evidence),
        }


@dataclass
class RoundPhaseResult:
    windows: list[RoundPhaseWindow] = field(default_factory=list)
    engine: str = "round-phase-detector-v1"
    skipped_reason: str | None = None

    @property
    def phase_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for window in self.windows:
            counts[window.phase.value] = counts.get(window.phase.value, 0) + 1
        return counts

    def phase_at(self, seconds: float) -> RoundPhaseWindow | None:
        for window in self.windows:
            if window.start_seconds <= seconds < window.end_seconds:
                return window
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "windows": [window.to_dict() for window in self.windows],
            "phase_counts": self.phase_counts,
            "engine": self.engine,
            "skipped_reason": self.skipped_reason,
        }
