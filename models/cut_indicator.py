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
class CutIndicator:
    indicator_id: str
    indicator_type: str
    start_seconds: float
    end_seconds: float
    score: float
    confidence: float
    source: str
    reason: str
    polarity: str
    channel_scope: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.indicator_id = str(self.indicator_id or "")
        self.indicator_type = str(self.indicator_type or "unknown")
        self.start_seconds = _safe_seconds(self.start_seconds)
        self.end_seconds = _safe_seconds(self.end_seconds, self.start_seconds)
        if self.end_seconds < self.start_seconds:
            self.end_seconds = self.start_seconds
        self.score = _clamp_score(self.score)
        self.confidence = _clamp_score(self.confidence)
        self.source = str(self.source or "unknown")
        self.reason = str(self.reason or "")
        self.polarity = self.polarity if self.polarity in {"positive", "negative", "neutral"} else "neutral"
        self.channel_scope = str(self.channel_scope or "all")
        self.metadata = dict(self.metadata or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "indicator_id": self.indicator_id,
            "indicator_type": self.indicator_type,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "score": self.score,
            "confidence": self.confidence,
            "source": self.source,
            "reason": self.reason,
            "polarity": self.polarity,
            "channel_scope": self.channel_scope,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CutIndicator":
        return cls(
            indicator_id=str(data.get("indicator_id", "")),
            indicator_type=str(data.get("indicator_type", "unknown")),
            start_seconds=data.get("start_seconds", 0.0),
            end_seconds=data.get("end_seconds", data.get("start_seconds", 0.0)),
            score=data.get("score", 0.0),
            confidence=data.get("confidence", 0.0),
            source=str(data.get("source", "unknown")),
            reason=str(data.get("reason", "")),
            polarity=str(data.get("polarity", "neutral")),
            channel_scope=str(data.get("channel_scope", "all")),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class CutIndicatorResult:
    indicators: list[CutIndicator] = field(default_factory=list)
    engine: str = "cut-indicator-builder-v1"
    skipped_reason: str | None = None

    @property
    def positive_count(self) -> int:
        return sum(indicator.polarity == "positive" for indicator in self.indicators)

    @property
    def negative_count(self) -> int:
        return sum(indicator.polarity == "negative" for indicator in self.indicators)

    @property
    def neutral_count(self) -> int:
        return sum(indicator.polarity == "neutral" for indicator in self.indicators)

    @property
    def average_score(self) -> float:
        if not self.indicators:
            return 0.0
        return round(sum(indicator.score for indicator in self.indicators) / len(self.indicators), 3)

    @property
    def max_score(self) -> float:
        return max((indicator.score for indicator in self.indicators), default=0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "indicators": [indicator.to_dict() for indicator in self.indicators],
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "average_score": self.average_score,
            "max_score": self.max_score,
            "engine": self.engine,
            "skipped_reason": self.skipped_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CutIndicatorResult":
        return cls(
            indicators=[
                CutIndicator.from_dict(indicator)
                for indicator in data.get("indicators", [])
                if isinstance(indicator, dict)
            ],
            engine=str(data.get("engine", "cut-indicator-builder-v1")),
            skipped_reason=data.get("skipped_reason"),
        )
