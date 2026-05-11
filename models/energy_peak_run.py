from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EnergyPeakRunReport:
    status: str
    source: str = "energy_peak_runner"
    energy_timeline_source: str | None = None
    energy_timeline: list[dict[str, Any]] = field(default_factory=list)
    peak_detection_result: dict[str, Any] = field(default_factory=dict)
    peaks: list[dict[str, Any]] = field(default_factory=list)
    peak_count: int = 0
    high_energy_peak_count: int = 0
    local_max_peak_count: int = 0
    rise_peak_count: int = 0
    threshold_peak_count: int = 0
    peak_threshold: float = 0.85
    rise_threshold: float = 0.25
    min_peak_distance_seconds: float = 0.4
    max_peak_score: float = 0.0
    avg_peak_score: float = 0.0
    top_peak: dict[str, Any] = field(default_factory=dict)
    rms_context_adapter_result: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "energy_timeline_source": self.energy_timeline_source,
            "energy_timeline": list(self.energy_timeline),
            "peak_detection_result": dict(self.peak_detection_result),
            "peaks": list(self.peaks),
            "peak_count": self.peak_count,
            "high_energy_peak_count": self.high_energy_peak_count,
            "local_max_peak_count": self.local_max_peak_count,
            "rise_peak_count": self.rise_peak_count,
            "threshold_peak_count": self.threshold_peak_count,
            "peak_threshold": self.peak_threshold,
            "rise_threshold": self.rise_threshold,
            "min_peak_distance_seconds": self.min_peak_distance_seconds,
            "max_peak_score": self.max_peak_score,
            "avg_peak_score": self.avg_peak_score,
            "top_peak": dict(self.top_peak),
            "rms_context_adapter_result": dict(self.rms_context_adapter_result),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnergyPeakRunReport:
        et_source_raw = data.get("energy_timeline_source")
        energy_timeline_source: str | None = str(et_source_raw) if et_source_raw is not None else None

        raw_timeline = data.get("energy_timeline", [])
        energy_timeline: list[dict[str, Any]] = (
            [item for item in raw_timeline if isinstance(item, dict)]
            if isinstance(raw_timeline, list)
            else []
        )

        raw_peaks = data.get("peaks", [])
        peaks: list[dict[str, Any]] = (
            [p for p in raw_peaks if isinstance(p, dict)]
            if isinstance(raw_peaks, list)
            else []
        )

        return cls(
            status=str(data.get("status", "unknown")),
            source=str(data.get("source", "energy_peak_runner")),
            energy_timeline_source=energy_timeline_source,
            energy_timeline=energy_timeline,
            peak_detection_result=dict(data.get("peak_detection_result") or {}),
            peaks=peaks,
            peak_count=int(data.get("peak_count", 0)),
            high_energy_peak_count=int(data.get("high_energy_peak_count", 0)),
            local_max_peak_count=int(data.get("local_max_peak_count", 0)),
            rise_peak_count=int(data.get("rise_peak_count", 0)),
            threshold_peak_count=int(data.get("threshold_peak_count", 0)),
            peak_threshold=float(data.get("peak_threshold", 0.85)),
            rise_threshold=float(data.get("rise_threshold", 0.25)),
            min_peak_distance_seconds=float(data.get("min_peak_distance_seconds", 0.4)),
            max_peak_score=float(data.get("max_peak_score", 0.0)),
            avg_peak_score=float(data.get("avg_peak_score", 0.0)),
            top_peak=dict(data.get("top_peak") or {}),
            rms_context_adapter_result=dict(data.get("rms_context_adapter_result") or {}),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(data.get("recommendation", "review")),
            metadata=dict(data.get("metadata") or {}),
        )
