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
class GameplayStateWindow:
    window_id: str = ""
    start_seconds: float = 0.0
    end_seconds: float = 0.001
    state_type: str = "unknown"
    score: float = 0.0
    confidence: float = 0.0
    motion_score: float = 0.0
    scene_change_score: float = 0.0
    visual_activity_score: float = 0.0
    reason: str = ""
    source_signals: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.window_id = str(self.window_id or "")
        self.start_seconds = _safe_seconds(self.start_seconds)
        self.end_seconds = _safe_seconds(self.end_seconds, self.start_seconds + 0.001)
        if self.end_seconds <= self.start_seconds:
            self.end_seconds = round(self.start_seconds + 0.001, 3)
        self.state_type = str(self.state_type or "unknown")
        self.score = _clamp_score(self.score)
        self.confidence = _clamp_score(self.confidence)
        self.motion_score = _clamp_score(self.motion_score)
        self.scene_change_score = _clamp_score(self.scene_change_score)
        self.visual_activity_score = _clamp_score(self.visual_activity_score)
        self.reason = str(self.reason or "")
        self.source_signals = [str(item) for item in (self.source_signals or [])]
        self.metadata = dict(self.metadata or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "state_type": self.state_type,
            "score": self.score,
            "confidence": self.confidence,
            "motion_score": self.motion_score,
            "scene_change_score": self.scene_change_score,
            "visual_activity_score": self.visual_activity_score,
            "reason": self.reason,
            "source_signals": list(self.source_signals),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameplayStateWindow":
        return cls(
            window_id=str(data.get("window_id", "")),
            start_seconds=data.get("start_seconds", 0.0),
            end_seconds=data.get("end_seconds", data.get("start_seconds", 0.0)),
            state_type=str(data.get("state_type", "unknown")),
            score=data.get("score", 0.0),
            confidence=data.get("confidence", 0.0),
            motion_score=data.get("motion_score", 0.0),
            scene_change_score=data.get("scene_change_score", 0.0),
            visual_activity_score=data.get("visual_activity_score", 0.0),
            reason=str(data.get("reason", "")),
            source_signals=list(data.get("source_signals") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class GameplayStateResult:
    windows: list[GameplayStateWindow] = field(default_factory=list)
    total_windows: int = 0
    state_counts: dict[str, int] = field(default_factory=dict)
    avg_score: float = 0.0
    max_score: float = 0.0
    engine: str = "gameplay-state-analyzer-v1"
    skipped_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.windows = sorted(
            [
                window if isinstance(window, GameplayStateWindow) else GameplayStateWindow.from_dict(window)
                for window in (self.windows or [])
                if isinstance(window, (GameplayStateWindow, dict))
            ],
            key=lambda item: (item.start_seconds, item.end_seconds, item.state_type, item.window_id),
        )
        self.total_windows = len(self.windows)
        counts: dict[str, int] = {}
        for window in self.windows:
            counts[window.state_type] = counts.get(window.state_type, 0) + 1
        self.state_counts = counts
        self.avg_score = _clamp_score(
            sum(window.score for window in self.windows) / len(self.windows)
            if self.windows
            else 0.0
        )
        self.max_score = _clamp_score(max((window.score for window in self.windows), default=0.0))
        self.engine = str(self.engine or "gameplay-state-analyzer-v1")
        self.metadata = dict(self.metadata or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "windows": [window.to_dict() for window in self.windows],
            "total_windows": self.total_windows,
            "state_counts": dict(self.state_counts),
            "avg_score": self.avg_score,
            "max_score": self.max_score,
            "engine": self.engine,
            "skipped_reason": self.skipped_reason,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameplayStateResult":
        return cls(
            windows=[
                GameplayStateWindow.from_dict(window)
                for window in data.get("windows", [])
                if isinstance(window, dict)
            ],
            total_windows=int(data.get("total_windows", 0) or 0),
            state_counts=dict(data.get("state_counts") or {}),
            avg_score=data.get("avg_score", 0.0),
            max_score=data.get("max_score", 0.0),
            engine=str(data.get("engine", "gameplay-state-analyzer-v1")),
            skipped_reason=data.get("skipped_reason"),
            metadata=dict(data.get("metadata") or {}),
        )
