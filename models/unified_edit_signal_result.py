from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UnifiedEditSignalResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    source_counts: dict[str, int] = field(default_factory=dict)
    type_counts: dict[str, int] = field(default_factory=dict)
    priority_counts: dict[str, int] = field(default_factory=dict)
    duplicate_count: int = 0
    max_signal_score: float = 0.0
    avg_signal_score: float = 0.0
    timeline_coverage_seconds: float = 0.0
    recommendation: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": list(self.signals),
            "signal_count": int(self.signal_count),
            "source_counts": dict(self.source_counts),
            "type_counts": dict(self.type_counts),
            "priority_counts": dict(self.priority_counts),
            "duplicate_count": int(self.duplicate_count),
            "max_signal_score": float(self.max_signal_score),
            "avg_signal_score": float(self.avg_signal_score),
            "timeline_coverage_seconds": float(self.timeline_coverage_seconds),
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    def summary(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signal_count": int(self.signal_count),
            "source_counts": dict(self.source_counts),
            "type_counts": dict(self.type_counts),
            "priority_counts": dict(self.priority_counts),
            "duplicate_count": int(self.duplicate_count),
            "max_signal_score": float(self.max_signal_score),
            "avg_signal_score": float(self.avg_signal_score),
            "timeline_coverage_seconds": float(self.timeline_coverage_seconds),
            "recommendation": self.recommendation,
        }
