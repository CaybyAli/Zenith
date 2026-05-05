from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _clamp_score(value: object, fallback: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return round(max(0.0, min(1.0, numeric)), 3)


def _safe_seconds(value: object, fallback: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return round(max(0.0, numeric), 3)


@dataclass
class GameplayEventWindow:
    event_id: str
    start_seconds: float
    end_seconds: float
    event_type: str
    score: float
    confidence: float
    reason: str
    source_window_ids: list[str] = field(default_factory=list)
    source_signal_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.event_id = str(self.event_id or "")
        self.start_seconds = _safe_seconds(self.start_seconds)
        self.end_seconds = _safe_seconds(self.end_seconds, self.start_seconds)
        if self.end_seconds < self.start_seconds:
            self.end_seconds = self.start_seconds
        self.event_type = str(self.event_type or "unknown")
        self.score = _clamp_score(self.score)
        self.confidence = _clamp_score(self.confidence)
        self.reason = str(self.reason or "")
        self.source_window_ids = [str(item) for item in (self.source_window_ids or [])]
        self.source_signal_ids = [str(item) for item in (self.source_signal_ids or [])]
        self.metadata = dict(self.metadata or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "event_type": self.event_type,
            "score": self.score,
            "confidence": self.confidence,
            "reason": self.reason,
            "source_window_ids": self.source_window_ids,
            "source_signal_ids": self.source_signal_ids,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameplayEventWindow":
        return cls(
            event_id=str(data.get("event_id", "")),
            start_seconds=data.get("start_seconds", 0.0),
            end_seconds=data.get("end_seconds", data.get("start_seconds", 0.0)),
            event_type=str(data.get("event_type", "unknown")),
            score=data.get("score", 0.0),
            confidence=data.get("confidence", 0.0),
            reason=str(data.get("reason", "")),
            source_window_ids=list(data.get("source_window_ids") or []),
            source_signal_ids=list(data.get("source_signal_ids") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class GameplayEventResult:
    windows: list[GameplayEventWindow] = field(default_factory=list)
    engine: str = "gameplay-event-indicator-builder-v1"
    skipped_reason: str | None = None

    @property
    def event_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for window in self.windows:
            counts[window.event_type] = counts.get(window.event_type, 0) + 1
        return counts

    @property
    def positive_count(self) -> int:
        return sum(
            window.event_type in {"high_action_burst", "sustained_action", "goal_or_save_like_flash"}
            for window in self.windows
        )

    @property
    def negative_count(self) -> int:
        return sum(
            window.event_type in {"round_end_dead_time", "menu_or_idle", "low_gameplay_value"}
            for window in self.windows
        )

    @property
    def neutral_count(self) -> int:
        return len(self.windows) - self.positive_count - self.negative_count

    @property
    def average_score(self) -> float:
        if not self.windows:
            return 0.0
        return round(sum(window.score for window in self.windows) / len(self.windows), 3)

    @property
    def max_score(self) -> float:
        return max((window.score for window in self.windows), default=0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "windows": [window.to_dict() for window in self.windows],
            "event_counts": self.event_counts,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "average_score": self.average_score,
            "max_score": self.max_score,
            "engine": self.engine,
            "skipped_reason": self.skipped_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameplayEventResult":
        return cls(
            windows=[
                GameplayEventWindow.from_dict(window)
                for window in data.get("windows", [])
                if isinstance(window, dict)
            ],
            engine=str(data.get("engine", "gameplay-event-indicator-builder-v1")),
            skipped_reason=data.get("skipped_reason"),
        )
