from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EnergyPeakSignalAdapterResult:
    status: str
    source: str = "energy_peak_signal_adapter"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    peak_count: int = 0
    high_priority_signal_count: int = 0
    signal_types: dict[str, int] = field(default_factory=dict)
    max_signal_score: float = 0.0
    avg_signal_score: float = 0.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "signals": list(self.signals),
            "signal_count": self.signal_count,
            "peak_count": self.peak_count,
            "high_priority_signal_count": self.high_priority_signal_count,
            "signal_types": dict(self.signal_types),
            "max_signal_score": self.max_signal_score,
            "avg_signal_score": self.avg_signal_score,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnergyPeakSignalAdapterResult:
        raw_signals = data.get("signals", [])
        signals: list[dict[str, Any]] = (
            [s for s in raw_signals if isinstance(s, dict)]
            if isinstance(raw_signals, list)
            else []
        )
        raw_signal_types = data.get("signal_types", {})
        signal_types: dict[str, int] = (
            {str(k): int(v) for k, v in raw_signal_types.items()}
            if isinstance(raw_signal_types, dict)
            else {}
        )
        return cls(
            status=str(data.get("status", "unknown")),
            source=str(data.get("source", "energy_peak_signal_adapter")),
            signals=signals,
            signal_count=int(data.get("signal_count", len(signals))),
            peak_count=int(data.get("peak_count", 0)),
            high_priority_signal_count=int(data.get("high_priority_signal_count", 0)),
            signal_types=signal_types,
            max_signal_score=float(data.get("max_signal_score", 0.0)),
            avg_signal_score=float(data.get("avg_signal_score", 0.0)),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(data.get("recommendation", "review")),
            metadata=dict(data.get("metadata") or {}),
        )
