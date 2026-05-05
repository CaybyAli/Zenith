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


POSITIVE_FACE_TYPES = {
    "facecam_reaction_spike",
    "facecam_motion_spike",
    "expression_change_like",
    "mouth_open_like",
    "smile_like",
    "shock_like",
    "laugh_like_face",
    "head_movement_like",
    "thumbnail_face_candidate",
}
NEGATIVE_FACE_TYPES = {"low_facecam_value"}


@dataclass
class FacecamEmotionWindow:
    emotion_id: str
    start_seconds: float
    end_seconds: float
    emotion_type: str
    score: float
    confidence: float
    reason: str
    source_window_ids: list[str] = field(default_factory=list)
    source_signal_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.emotion_id = str(self.emotion_id or "")
        self.start_seconds = _safe_seconds(self.start_seconds)
        self.end_seconds = _safe_seconds(self.end_seconds, self.start_seconds)
        if self.end_seconds < self.start_seconds:
            self.end_seconds = self.start_seconds
        self.emotion_type = str(self.emotion_type or "unknown")
        self.score = _clamp_score(self.score)
        self.confidence = _clamp_score(self.confidence)
        self.reason = str(self.reason or "")
        self.source_window_ids = [str(item) for item in (self.source_window_ids or [])]
        self.source_signal_ids = [str(item) for item in (self.source_signal_ids or [])]
        self.metadata = dict(self.metadata or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "emotion_id": self.emotion_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "emotion_type": self.emotion_type,
            "score": self.score,
            "confidence": self.confidence,
            "reason": self.reason,
            "source_window_ids": self.source_window_ids,
            "source_signal_ids": self.source_signal_ids,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FacecamEmotionWindow":
        return cls(
            emotion_id=str(data.get("emotion_id", "")),
            start_seconds=data.get("start_seconds", 0.0),
            end_seconds=data.get("end_seconds", data.get("start_seconds", 0.0)),
            emotion_type=str(data.get("emotion_type", "unknown")),
            score=data.get("score", 0.0),
            confidence=data.get("confidence", 0.0),
            reason=str(data.get("reason", "")),
            source_window_ids=list(data.get("source_window_ids") or []),
            source_signal_ids=list(data.get("source_signal_ids") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class FacecamEmotionResult:
    windows: list[FacecamEmotionWindow] = field(default_factory=list)
    emotion_counts: dict[str, int] = field(default_factory=dict)
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    average_score: float = 0.0
    max_score: float = 0.0
    engine: str = "facecam-emotion-indicator-builder-v1"
    skipped_reason: str | None = None

    def __post_init__(self) -> None:
        self.emotion_counts = self._computed_counts()
        self.positive_count = sum(
            window.emotion_type in POSITIVE_FACE_TYPES for window in self.windows
        )
        self.negative_count = sum(
            window.emotion_type in NEGATIVE_FACE_TYPES for window in self.windows
        )
        self.neutral_count = len(self.windows) - self.positive_count - self.negative_count
        if self.windows:
            self.average_score = round(
                sum(window.score for window in self.windows) / len(self.windows),
                3,
            )
            self.max_score = max(window.score for window in self.windows)
        else:
            self.average_score = 0.0
            self.max_score = 0.0

    def _computed_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for window in self.windows:
            counts[window.emotion_type] = counts.get(window.emotion_type, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "windows": [window.to_dict() for window in self.windows],
            "emotion_counts": self.emotion_counts,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "average_score": self.average_score,
            "max_score": self.max_score,
            "engine": self.engine,
            "skipped_reason": self.skipped_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FacecamEmotionResult":
        return cls(
            windows=[
                FacecamEmotionWindow.from_dict(window)
                for window in data.get("windows", [])
                if isinstance(window, dict)
            ],
            engine=str(data.get("engine", "facecam-emotion-indicator-builder-v1")),
            skipped_reason=data.get("skipped_reason"),
        )
