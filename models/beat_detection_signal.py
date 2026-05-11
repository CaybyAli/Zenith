from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _safe_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_optional_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_string_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item) for item in value]

    if isinstance(value, tuple):
        return [str(item) for item in value]

    return [str(value)]


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    return {}


def _safe_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    result: list[dict[str, Any]] = []

    for item in value:
        if isinstance(item, dict):
            result.append(dict(item))

    return result


@dataclass
class BeatDetectionSignalAdapterResult:
    status: str
    source: str = "beat_detection_signal_adapter"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    high_priority_signal_count: int = 0
    signal_types: dict[str, int] = field(default_factory=dict)
    max_signal_score: float = 0.0
    avg_signal_score: float = 0.0
    beat_count: int = 0
    estimated_bpm: float | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "high_priority_signal_count": self.high_priority_signal_count,
            "signal_types": dict(self.signal_types),
            "max_signal_score": self.max_signal_score,
            "avg_signal_score": self.avg_signal_score,
            "beat_count": self.beat_count,
            "estimated_bpm": self.estimated_bpm,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "BeatDetectionSignalAdapterResult":
        if not isinstance(data, dict):
            data = {}

        return cls(
            status=_safe_string(data.get("status"), "failed"),
            source=_safe_string(data.get("source"), "beat_detection_signal_adapter"),
            signals=_safe_dict_list(data.get("signals")),
            signal_count=_safe_int(data.get("signal_count"), 0),
            high_priority_signal_count=_safe_int(
                data.get("high_priority_signal_count"), 0
            ),
            signal_types=_safe_dict(data.get("signal_types")),
            max_signal_score=_safe_float(data.get("max_signal_score"), 0.0),
            avg_signal_score=_safe_float(data.get("avg_signal_score"), 0.0),
            beat_count=_safe_int(data.get("beat_count"), 0),
            estimated_bpm=_safe_optional_float(data.get("estimated_bpm")),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            recommendation=_safe_string(data.get("recommendation"), "review"),
            metadata=_safe_dict(data.get("metadata")),
        )
