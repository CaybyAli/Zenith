from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RmsEnergyContextAdapterResult:
    status: str
    source: str = "rms_energy_context_adapter"
    energy_timeline: list[dict[str, Any]] = field(default_factory=list)
    point_count: int = 0
    peak_count: int = 0
    silent_count: int = 0
    peak_threshold: float = 0.85
    min_energy_score: float = 0.0
    max_energy_score: float = 0.0
    avg_energy_score: float = 0.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "energy_timeline": list(self.energy_timeline),
            "point_count": self.point_count,
            "peak_count": self.peak_count,
            "silent_count": self.silent_count,
            "peak_threshold": self.peak_threshold,
            "min_energy_score": self.min_energy_score,
            "max_energy_score": self.max_energy_score,
            "avg_energy_score": self.avg_energy_score,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RmsEnergyContextAdapterResult:
        raw_timeline = data.get("energy_timeline", [])
        energy_timeline: list[dict[str, Any]] = (
            list(raw_timeline) if isinstance(raw_timeline, list) else []
        )
        return cls(
            status=str(data.get("status", "unknown")),
            source=str(data.get("source", "rms_energy_context_adapter")),
            energy_timeline=energy_timeline,
            point_count=int(data.get("point_count", 0)),
            peak_count=int(data.get("peak_count", 0)),
            silent_count=int(data.get("silent_count", 0)),
            peak_threshold=float(data.get("peak_threshold", 0.85)),
            min_energy_score=float(data.get("min_energy_score", 0.0)),
            max_energy_score=float(data.get("max_energy_score", 0.0)),
            avg_energy_score=float(data.get("avg_energy_score", 0.0)),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
