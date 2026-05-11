from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RmsEnergyRunReport:
    status: str
    source: str = "rms_energy_runner"
    source_selection: dict[str, Any] = field(default_factory=dict)
    energy_timeline_result: dict[str, Any] = field(default_factory=dict)
    selected_path: str | None = None
    selected_type: str | None = None
    timeline_status: str | None = None
    point_count: int = 0
    duration_seconds: float = 0.0
    sample_rate: int | None = None
    channels: int | None = None
    frame_ms: float = 10.0
    hop_ms: float = 5.0
    min_rms: float = 0.0
    max_rms: float = 0.0
    avg_rms: float = 0.0
    min_normalized_energy: float = 0.0
    max_normalized_energy: float = 0.0
    avg_normalized_energy: float = 0.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "source_selection": dict(self.source_selection),
            "energy_timeline_result": dict(self.energy_timeline_result),
            "selected_path": self.selected_path,
            "selected_type": self.selected_type,
            "timeline_status": self.timeline_status,
            "point_count": self.point_count,
            "duration_seconds": self.duration_seconds,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "frame_ms": self.frame_ms,
            "hop_ms": self.hop_ms,
            "min_rms": self.min_rms,
            "max_rms": self.max_rms,
            "avg_rms": self.avg_rms,
            "min_normalized_energy": self.min_normalized_energy,
            "max_normalized_energy": self.max_normalized_energy,
            "avg_normalized_energy": self.avg_normalized_energy,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RmsEnergyRunReport:
        sample_rate_raw = data.get("sample_rate")
        sample_rate: int | None = None
        if sample_rate_raw is not None:
            try:
                sample_rate = int(sample_rate_raw)
            except (TypeError, ValueError):
                sample_rate = None

        channels_raw = data.get("channels")
        channels: int | None = None
        if channels_raw is not None:
            try:
                channels = int(channels_raw)
            except (TypeError, ValueError):
                channels = None

        timeline_status_raw = data.get("timeline_status")
        timeline_status: str | None = str(timeline_status_raw) if timeline_status_raw is not None else None

        return cls(
            status=str(data.get("status", "failed")),
            source=str(data.get("source", "rms_energy_runner")),
            source_selection=dict(data.get("source_selection") or {}),
            energy_timeline_result=dict(data.get("energy_timeline_result") or {}),
            selected_path=data.get("selected_path"),
            selected_type=data.get("selected_type"),
            timeline_status=timeline_status,
            point_count=int(data.get("point_count", 0)),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=float(data.get("frame_ms", 10.0)),
            hop_ms=float(data.get("hop_ms", 5.0)),
            min_rms=float(data.get("min_rms", 0.0)),
            max_rms=float(data.get("max_rms", 0.0)),
            avg_rms=float(data.get("avg_rms", 0.0)),
            min_normalized_energy=float(data.get("min_normalized_energy", 0.0)),
            max_normalized_energy=float(data.get("max_normalized_energy", 0.0)),
            avg_normalized_energy=float(data.get("avg_normalized_energy", 0.0)),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(data.get("recommendation", "review")),
            metadata=dict(data.get("metadata") or {}),
        )
