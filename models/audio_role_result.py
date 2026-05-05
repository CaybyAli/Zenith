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
class AudioRoleWindow:
    window_id: str
    start_seconds: float
    end_seconds: float
    role_type: str
    score: float
    confidence: float
    reason: str
    source_signal_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.window_id = str(self.window_id or "")
        self.start_seconds = _safe_seconds(self.start_seconds)
        self.end_seconds = _safe_seconds(self.end_seconds, self.start_seconds)
        if self.end_seconds < self.start_seconds:
            self.end_seconds = self.start_seconds
        self.role_type = str(self.role_type or "unknown")
        self.score = _clamp_score(self.score)
        self.confidence = _clamp_score(self.confidence)
        self.reason = str(self.reason or "")
        self.source_signal_ids = [str(item) for item in (self.source_signal_ids or [])]
        self.metadata = dict(self.metadata or {})

    @property
    def duration_seconds(self) -> float:
        return round(max(0.0, self.end_seconds - self.start_seconds), 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "role_type": self.role_type,
            "score": self.score,
            "confidence": self.confidence,
            "reason": self.reason,
            "source_signal_ids": self.source_signal_ids,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AudioRoleWindow":
        return cls(
            window_id=str(data.get("window_id", "")),
            start_seconds=data.get("start_seconds", 0.0),
            end_seconds=data.get("end_seconds", data.get("start_seconds", 0.0)),
            role_type=str(data.get("role_type", "unknown")),
            score=data.get("score", 0.0),
            confidence=data.get("confidence", 0.0),
            reason=str(data.get("reason", "")),
            source_signal_ids=list(data.get("source_signal_ids") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class AudioRoleResult:
    windows: list[AudioRoleWindow] = field(default_factory=list)
    engine: str = "audio-role-indicator-builder-v1"
    skipped_reason: str | None = None

    @property
    def role_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for window in self.windows:
            counts[window.role_type] = counts.get(window.role_type, 0) + 1
        return counts

    @property
    def positive_count(self) -> int:
        return sum(
            window.role_type
            not in {"silence_or_dead_air", "speech_cut_risk_audio", "speech_active"}
            for window in self.windows
        )

    @property
    def negative_count(self) -> int:
        return sum(
            window.role_type in {"silence_or_dead_air", "speech_cut_risk_audio"}
            for window in self.windows
        )

    @property
    def neutral_count(self) -> int:
        return sum(window.role_type == "speech_active" for window in self.windows)

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
            "role_counts": self.role_counts,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "average_score": self.average_score,
            "max_score": self.max_score,
            "engine": self.engine,
            "skipped_reason": self.skipped_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AudioRoleResult":
        return cls(
            windows=[
                AudioRoleWindow.from_dict(window)
                for window in data.get("windows", [])
                if isinstance(window, dict)
            ],
            engine=str(data.get("engine", "audio-role-indicator-builder-v1")),
            skipped_reason=data.get("skipped_reason"),
        )
