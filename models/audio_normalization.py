from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AudioLevelStats:
    peak_amplitude: float = 0.0
    rms: float = 0.0
    peak_dbfs: float | None = None
    rms_dbfs: float | None = None
    headroom_db: float | None = None
    dynamic_range_db: float | None = None
    clipping_sample_count: int = 0
    clipping_ratio: float = 0.0
    sample_count: int = 0
    duration_seconds: float = 0.0
    sample_rate: int | None = None
    channels: int | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "peak_amplitude": self.peak_amplitude,
            "rms": self.rms,
            "peak_dbfs": self.peak_dbfs,
            "rms_dbfs": self.rms_dbfs,
            "headroom_db": self.headroom_db,
            "dynamic_range_db": self.dynamic_range_db,
            "clipping_sample_count": self.clipping_sample_count,
            "clipping_ratio": self.clipping_ratio,
            "sample_count": self.sample_count,
            "duration_seconds": self.duration_seconds,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AudioLevelStats:
        def _opt_float(key: str) -> float | None:
            raw = data.get(key)
            if raw is None:
                return None
            try:
                return float(raw)
            except (TypeError, ValueError):
                return None

        def _opt_int(key: str) -> int | None:
            raw = data.get(key)
            if raw is None:
                return None
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None

        return cls(
            peak_amplitude=float(data.get("peak_amplitude", 0.0)),
            rms=float(data.get("rms", 0.0)),
            peak_dbfs=_opt_float("peak_dbfs"),
            rms_dbfs=_opt_float("rms_dbfs"),
            headroom_db=_opt_float("headroom_db"),
            dynamic_range_db=_opt_float("dynamic_range_db"),
            clipping_sample_count=int(data.get("clipping_sample_count", 0)),
            clipping_ratio=float(data.get("clipping_ratio", 0.0)),
            sample_count=int(data.get("sample_count", 0)),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            sample_rate=_opt_int("sample_rate"),
            channels=_opt_int("channels"),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class AudioNormalizationResult:
    status: str
    source: str = "audio_normalization_analyzer"
    input_path: str | None = None
    level_status: str = "unknown"
    stats: AudioLevelStats = field(default_factory=AudioLevelStats)
    target_rms_dbfs: float = -18.0
    target_peak_dbfs: float = -1.0
    recommended_gain_db: float = 0.0
    limited_gain_db: float = 0.0
    gain_limited_by_peak: bool = False
    would_clip_after_gain: bool = False
    normalization_needed: bool = False
    recommendation: str = "review"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "input_path": self.input_path,
            "level_status": self.level_status,
            "stats": self.stats.to_dict(),
            "target_rms_dbfs": self.target_rms_dbfs,
            "target_peak_dbfs": self.target_peak_dbfs,
            "recommended_gain_db": self.recommended_gain_db,
            "limited_gain_db": self.limited_gain_db,
            "gain_limited_by_peak": self.gain_limited_by_peak,
            "would_clip_after_gain": self.would_clip_after_gain,
            "normalization_needed": self.normalization_needed,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AudioNormalizationResult:
        stats_raw = data.get("stats")
        stats = AudioLevelStats.from_dict(stats_raw) if isinstance(stats_raw, dict) else AudioLevelStats()

        return cls(
            status=str(data.get("status", "unknown")),
            source=str(data.get("source", "audio_normalization_analyzer")),
            input_path=data.get("input_path"),
            level_status=str(data.get("level_status", "unknown")),
            stats=stats,
            target_rms_dbfs=float(data.get("target_rms_dbfs", -18.0)),
            target_peak_dbfs=float(data.get("target_peak_dbfs", -1.0)),
            recommended_gain_db=float(data.get("recommended_gain_db", 0.0)),
            limited_gain_db=float(data.get("limited_gain_db", 0.0)),
            gain_limited_by_peak=bool(data.get("gain_limited_by_peak", False)),
            would_clip_after_gain=bool(data.get("would_clip_after_gain", False)),
            normalization_needed=bool(data.get("normalization_needed", False)),
            recommendation=str(data.get("recommendation", "review")),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
