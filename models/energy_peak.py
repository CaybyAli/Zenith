from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EnergyPeak:
    start_seconds: float
    end_seconds: float
    center_seconds: float
    energy_score: float
    peak_score: float
    peak_type: str
    confidence: float
    reason: str
    source_index: int | None = None
    is_local_maximum: bool = False
    rise_delta: float = 0.0
    fall_delta: float = 0.0
    window_energy_before: float | None = None
    window_energy_after: float | None = None
    source_item: dict[str, Any] = field(default_factory=dict)
    rules_applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "energy_score": self.energy_score,
            "peak_score": self.peak_score,
            "peak_type": self.peak_type,
            "confidence": self.confidence,
            "reason": self.reason,
            "source_index": self.source_index,
            "is_local_maximum": self.is_local_maximum,
            "rise_delta": self.rise_delta,
            "fall_delta": self.fall_delta,
            "window_energy_before": self.window_energy_before,
            "window_energy_after": self.window_energy_after,
            "source_item": dict(self.source_item),
            "rules_applied": list(self.rules_applied),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnergyPeak:
        source_index_raw = data.get("source_index")
        source_index: int | None = None
        if source_index_raw is not None:
            try:
                source_index = int(source_index_raw)
            except (TypeError, ValueError):
                source_index = None

        window_before_raw = data.get("window_energy_before")
        window_before: float | None = None
        if window_before_raw is not None:
            try:
                window_before = float(window_before_raw)
            except (TypeError, ValueError):
                window_before = None

        window_after_raw = data.get("window_energy_after")
        window_after: float | None = None
        if window_after_raw is not None:
            try:
                window_after = float(window_after_raw)
            except (TypeError, ValueError):
                window_after = None

        return cls(
            start_seconds=float(data.get("start_seconds", 0.0)),
            end_seconds=float(data.get("end_seconds", 0.0)),
            center_seconds=float(data.get("center_seconds", 0.0)),
            energy_score=float(data.get("energy_score", 0.0)),
            peak_score=float(data.get("peak_score", 0.0)),
            peak_type=str(data.get("peak_type", "unknown")),
            confidence=float(data.get("confidence", 0.0)),
            reason=str(data.get("reason", "")),
            source_index=source_index,
            is_local_maximum=bool(data.get("is_local_maximum", False)),
            rise_delta=float(data.get("rise_delta", 0.0)),
            fall_delta=float(data.get("fall_delta", 0.0)),
            window_energy_before=window_before,
            window_energy_after=window_after,
            source_item=dict(data.get("source_item") or {}),
            rules_applied=list(data.get("rules_applied") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class EnergyPeakDetectionResult:
    status: str
    source: str = "energy_peak_detector"
    peaks: list[EnergyPeak] = field(default_factory=list)
    peak_count: int = 0
    high_energy_peak_count: int = 0
    local_max_peak_count: int = 0
    rise_peak_count: int = 0
    threshold_peak_count: int = 0
    peak_threshold: float = 0.85
    min_peak_distance_seconds: float = 0.4
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "peaks": [p.to_dict() for p in self.peaks],
            "peak_count": self.peak_count,
            "high_energy_peak_count": self.high_energy_peak_count,
            "local_max_peak_count": self.local_max_peak_count,
            "rise_peak_count": self.rise_peak_count,
            "threshold_peak_count": self.threshold_peak_count,
            "peak_threshold": self.peak_threshold,
            "min_peak_distance_seconds": self.min_peak_distance_seconds,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnergyPeakDetectionResult:
        raw_peaks = data.get("peaks", [])
        peaks = [EnergyPeak.from_dict(p) for p in raw_peaks if isinstance(p, dict)]
        return cls(
            status=str(data.get("status", "unknown")),
            source=str(data.get("source", "energy_peak_detector")),
            peaks=peaks,
            peak_count=int(data.get("peak_count", len(peaks))),
            high_energy_peak_count=int(data.get("high_energy_peak_count", 0)),
            local_max_peak_count=int(data.get("local_max_peak_count", 0)),
            rise_peak_count=int(data.get("rise_peak_count", 0)),
            threshold_peak_count=int(data.get("threshold_peak_count", 0)),
            peak_threshold=float(data.get("peak_threshold", 0.85)),
            min_peak_distance_seconds=float(data.get("min_peak_distance_seconds", 0.4)),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
