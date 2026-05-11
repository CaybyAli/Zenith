from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _safe_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    return text


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


def _safe_optional_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any, default: int = 0) -> int:
    converted = _safe_optional_int(value)
    if converted is None:
        return default
    return converted


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
class BeatDetectionRunReport:
    status: str
    source: str = "beat_detection_runner"
    source_selection: dict[str, Any] = field(default_factory=dict)
    selected_path: str | None = None
    selected_type: str | None = None
    beat_detection_result: dict[str, Any] = field(default_factory=dict)
    beats: list[dict[str, Any]] = field(default_factory=list)
    beat_count: int = 0
    estimated_bpm: float | None = None
    average_beat_interval_seconds: float | None = None
    duration_seconds: float = 0.0
    sample_rate: int | None = None
    channels: int | None = None
    energy_frame_count: int = 0
    peak_threshold: float = 1.35
    min_beat_distance_seconds: float = 0.25
    max_beat_strength: float = 0.0
    avg_beat_strength: float = 0.0
    top_beat: dict[str, Any] = field(default_factory=dict)
    recommendation: str = "review"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "source_selection": dict(self.source_selection),
            "selected_path": self.selected_path,
            "selected_type": self.selected_type,
            "beat_detection_result": dict(self.beat_detection_result),
            "beats": [dict(beat) for beat in self.beats],
            "beat_count": self.beat_count,
            "estimated_bpm": self.estimated_bpm,
            "average_beat_interval_seconds": self.average_beat_interval_seconds,
            "duration_seconds": self.duration_seconds,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "energy_frame_count": self.energy_frame_count,
            "peak_threshold": self.peak_threshold,
            "min_beat_distance_seconds": self.min_beat_distance_seconds,
            "max_beat_strength": self.max_beat_strength,
            "avg_beat_strength": self.avg_beat_strength,
            "top_beat": dict(self.top_beat),
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "BeatDetectionRunReport":
        if not isinstance(data, dict):
            data = {}

        return cls(
            status=_safe_string(data.get("status"), "failed"),
            source=_safe_string(data.get("source"), "beat_detection_runner"),
            source_selection=_safe_dict(data.get("source_selection")),
            selected_path=_safe_optional_string(data.get("selected_path")),
            selected_type=_safe_optional_string(data.get("selected_type")),
            beat_detection_result=_safe_dict(data.get("beat_detection_result")),
            beats=_safe_dict_list(data.get("beats")),
            beat_count=_safe_int(data.get("beat_count"), 0),
            estimated_bpm=_safe_optional_float(data.get("estimated_bpm")),
            average_beat_interval_seconds=_safe_optional_float(
                data.get("average_beat_interval_seconds")
            ),
            duration_seconds=_safe_float(data.get("duration_seconds"), 0.0),
            sample_rate=_safe_optional_int(data.get("sample_rate")),
            channels=_safe_optional_int(data.get("channels")),
            energy_frame_count=_safe_int(data.get("energy_frame_count"), 0),
            peak_threshold=_safe_float(data.get("peak_threshold"), 1.35),
            min_beat_distance_seconds=_safe_float(
                data.get("min_beat_distance_seconds"), 0.25
            ),
            max_beat_strength=_safe_float(data.get("max_beat_strength"), 0.0),
            avg_beat_strength=_safe_float(data.get("avg_beat_strength"), 0.0),
            top_beat=_safe_dict(data.get("top_beat")),
            recommendation=_safe_string(data.get("recommendation"), "review"),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            metadata=_safe_dict(data.get("metadata")),
        )
