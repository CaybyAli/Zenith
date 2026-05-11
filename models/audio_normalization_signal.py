from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AudioNormalizationSignalAdapterResult:
    status: str
    source: str = "audio_normalization_signal_adapter"

    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
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
            "signal_count": int(self.signal_count),
            "high_priority_signal_count": int(self.high_priority_signal_count),
            "signal_types": dict(self.signal_types),
            "max_signal_score": float(self.max_signal_score),
            "avg_signal_score": float(self.avg_signal_score),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AudioNormalizationSignalAdapterResult":
        if not isinstance(data, dict):
            return cls(
                status="failed",
                errors=["AudioNormalizationSignalAdapterResult.from_dict expected a dict."],
                recommendation="retry_or_fix_audio_plan",
            )

        signals = data.get("signals", [])
        if not isinstance(signals, list):
            signals = []

        signal_types = data.get("signal_types", {})
        if not isinstance(signal_types, dict):
            signal_types = {}

        warnings = data.get("warnings", [])
        if not isinstance(warnings, list):
            warnings = [str(warnings)]

        errors = data.get("errors", [])
        if not isinstance(errors, list):
            errors = [str(errors)]

        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {"raw_metadata": metadata}

        return cls(
            status=str(data.get("status", "ok")),
            source=str(data.get("source", "audio_normalization_signal_adapter")),
            signals=signals,
            signal_count=int(data.get("signal_count", len(signals)) or 0),
            high_priority_signal_count=int(data.get("high_priority_signal_count", 0) or 0),
            signal_types=signal_types,
            max_signal_score=float(data.get("max_signal_score", 0.0) or 0.0),
            avg_signal_score=float(data.get("avg_signal_score", 0.0) or 0.0),
            warnings=warnings,
            errors=errors,
            recommendation=str(data.get("recommendation", "review")),
            metadata=metadata,
        )
        
