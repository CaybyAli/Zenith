from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _safe_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


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


@dataclass
class BeatPoint:
    time_seconds: float
    strength: float = 0.0
    confidence: float = 0.0
    energy: float = 0.0
    local_energy: float = 0.0
    average_energy: float = 0.0
    source_index: int | None = None
    is_downbeat_candidate: bool = False
    bpm_context: float | None = None
    reason: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_seconds": self.time_seconds,
            "strength": self.strength,
            "confidence": self.confidence,
            "energy": self.energy,
            "local_energy": self.local_energy,
            "average_energy": self.average_energy,
            "source_index": self.source_index,
            "is_downbeat_candidate": self.is_downbeat_candidate,
            "bpm_context": self.bpm_context,
            "reason": self.reason,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "BeatPoint":
        if not isinstance(data, dict):
            data = {}

        return cls(
            time_seconds=_safe_float(data.get("time_seconds"), 0.0),
            strength=_safe_float(data.get("strength"), 0.0),
            confidence=_safe_float(data.get("confidence"), 0.0),
            energy=_safe_float(data.get("energy"), 0.0),
            local_energy=_safe_float(data.get("local_energy"), 0.0),
            average_energy=_safe_float(data.get("average_energy"), 0.0),
            source_index=_safe_optional_int(data.get("source_index")),
            is_downbeat_candidate=_safe_bool(data.get("is_downbeat_candidate"), False),
            bpm_context=_safe_optional_float(data.get("bpm_context")),
            reason=_safe_string(data.get("reason"), ""),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            metadata=_safe_dict(data.get("metadata")),
        )


@dataclass
class BeatDetectionResult:
    status: str
    source: str = "beat_detector"
    input_path: str | None = None
    beats: list[BeatPoint] = field(default_factory=list)
    beat_count: int = 0
    estimated_bpm: float | None = None
    average_beat_interval_seconds: float | None = None
    duration_seconds: float = 0.0
    sample_rate: int | None = None
    channels: int | None = None
    energy_frame_count: int = 0
    peak_threshold: float = 1.35
    min_beat_distance_seconds: float = 0.25
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "input_path": self.input_path,
            "beats": [beat.to_dict() for beat in self.beats],
            "beat_count": self.beat_count,
            "estimated_bpm": self.estimated_bpm,
            "average_beat_interval_seconds": self.average_beat_interval_seconds,
            "duration_seconds": self.duration_seconds,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "energy_frame_count": self.energy_frame_count,
            "peak_threshold": self.peak_threshold,
            "min_beat_distance_seconds": self.min_beat_distance_seconds,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "BeatDetectionResult":
        if not isinstance(data, dict):
            data = {}

        raw_beats = data.get("beats")
        beats: list[BeatPoint] = []
        if isinstance(raw_beats, list):
            beats = [
                BeatPoint.from_dict(item)
                for item in raw_beats
                if isinstance(item, dict)
            ]

        beat_count = _safe_optional_int(data.get("beat_count"))
        if beat_count is None:
            beat_count = len(beats)

        return cls(
            status=_safe_string(data.get("status"), "failed"),
            source=_safe_string(data.get("source"), "beat_detector"),
            input_path=(
                None
                if data.get("input_path") is None
                else _safe_string(data.get("input_path"))
            ),
            beats=beats,
            beat_count=beat_count,
            estimated_bpm=_safe_optional_float(data.get("estimated_bpm")),
            average_beat_interval_seconds=_safe_optional_float(
                data.get("average_beat_interval_seconds")
            ),
            duration_seconds=_safe_float(data.get("duration_seconds"), 0.0),
            sample_rate=_safe_optional_int(data.get("sample_rate")),
            channels=_safe_optional_int(data.get("channels")),
            energy_frame_count=_safe_optional_int(data.get("energy_frame_count")) or 0,
            peak_threshold=_safe_float(data.get("peak_threshold"), 1.35),
            min_beat_distance_seconds=_safe_float(
                data.get("min_beat_distance_seconds"), 0.25
            ),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            metadata=_safe_dict(data.get("metadata")),
        )
