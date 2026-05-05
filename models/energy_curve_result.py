from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EnergyCurvePoint:
    point_id: str
    job_id: str
    start_seconds: float
    end_seconds: float
    energy_score: float
    signal_count: int
    dominant_signals: list[str] = field(default_factory=list)
    source_signal_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EnergyCurveResult:
    curve_id: str
    job_id: str
    points: list[EnergyCurvePoint] = field(default_factory=list)
    peak_points: list[EnergyCurvePoint] = field(default_factory=list)
    average_energy: float = 0.0
    max_energy: float = 0.0
    engine: str = "energy-curve-builder-v1"
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
