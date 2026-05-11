from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RmsEnergyPoint:
    start_seconds: float
    end_seconds: float
    center_seconds: float
    rms: float
    normalized_energy: float
    dbfs: float | None = None
    sample_count: int = 0
    is_silent: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "rms": self.rms,
            "normalized_energy": self.normalized_energy,
            "dbfs": self.dbfs,
            "sample_count": self.sample_count,
            "is_silent": self.is_silent,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RmsEnergyPoint:
        dbfs_raw = data.get("dbfs")
        dbfs: float | None = None
        if dbfs_raw is not None:
            try:
                dbfs = float(dbfs_raw)
            except (TypeError, ValueError):
                dbfs = None

        return cls(
            start_seconds=float(data.get("start_seconds", 0.0)),
            end_seconds=float(data.get("end_seconds", 0.0)),
            center_seconds=float(data.get("center_seconds", 0.0)),
            rms=float(data.get("rms", 0.0)),
            normalized_energy=float(data.get("normalized_energy", 0.0)),
            dbfs=dbfs,
            sample_count=int(data.get("sample_count", 0)),
            is_silent=bool(data.get("is_silent", False)),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class RmsEnergyTimelineResult:
    status: str
    source: str = "rms_energy_analyzer"
    source_path: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    duration_seconds: float = 0.0
    frame_ms: float = 10.0
    hop_ms: float = 5.0
    points: list[RmsEnergyPoint] = field(default_factory=list)
    point_count: int = 0
    min_rms: float = 0.0
    max_rms: float = 0.0
    avg_rms: float = 0.0
    min_normalized_energy: float = 0.0
    max_normalized_energy: float = 0.0
    avg_normalized_energy: float = 0.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "source_path": self.source_path,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "duration_seconds": self.duration_seconds,
            "frame_ms": self.frame_ms,
            "hop_ms": self.hop_ms,
            "points": [p.to_dict() for p in self.points],
            "point_count": self.point_count,
            "min_rms": self.min_rms,
            "max_rms": self.max_rms,
            "avg_rms": self.avg_rms,
            "min_normalized_energy": self.min_normalized_energy,
            "max_normalized_energy": self.max_normalized_energy,
            "avg_normalized_energy": self.avg_normalized_energy,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RmsEnergyTimelineResult:
        raw_points = data.get("points", [])
        points = [RmsEnergyPoint.from_dict(p) for p in raw_points]

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

        return cls(
            status=str(data.get("status", "unknown")),
            source=str(data.get("source", "rms_energy_analyzer")),
            source_path=data.get("source_path"),
            sample_rate=sample_rate,
            channels=channels,
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            frame_ms=float(data.get("frame_ms", 10.0)),
            hop_ms=float(data.get("hop_ms", 5.0)),
            points=points,
            point_count=int(data.get("point_count", len(points))),
            min_rms=float(data.get("min_rms", 0.0)),
            max_rms=float(data.get("max_rms", 0.0)),
            avg_rms=float(data.get("avg_rms", 0.0)),
            min_normalized_energy=float(data.get("min_normalized_energy", 0.0)),
            max_normalized_energy=float(data.get("max_normalized_energy", 0.0)),
            avg_normalized_energy=float(data.get("avg_normalized_energy", 0.0)),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
