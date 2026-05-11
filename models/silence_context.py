from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SilenceSegmentContext:
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    previous_energy_score: float | None = None
    next_energy_score: float | None = None
    previous_content_value: float | None = None
    next_content_value: float | None = None
    previous_is_peak: bool = False
    next_is_peak: bool = False
    is_after_high_energy: bool = False
    is_before_high_energy: bool = False
    previous_has_speech: bool | None = None
    next_has_speech: bool | None = None
    source: str = "silence_context_builder"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "previous_energy_score": self.previous_energy_score,
            "next_energy_score": self.next_energy_score,
            "previous_content_value": self.previous_content_value,
            "next_content_value": self.next_content_value,
            "previous_is_peak": self.previous_is_peak,
            "next_is_peak": self.next_is_peak,
            "is_after_high_energy": self.is_after_high_energy,
            "is_before_high_energy": self.is_before_high_energy,
            "previous_has_speech": self.previous_has_speech,
            "next_has_speech": self.next_has_speech,
            "source": self.source,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SilenceSegmentContext:
        def _opt_float(val: Any) -> float | None:
            if val is None:
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        def _opt_bool(val: Any) -> bool | None:
            if val is None:
                return None
            return bool(val)

        return cls(
            start_seconds=float(data.get("start_seconds", 0.0)),
            end_seconds=float(data.get("end_seconds", 0.0)),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            previous_energy_score=_opt_float(data.get("previous_energy_score")),
            next_energy_score=_opt_float(data.get("next_energy_score")),
            previous_content_value=_opt_float(data.get("previous_content_value")),
            next_content_value=_opt_float(data.get("next_content_value")),
            previous_is_peak=bool(data.get("previous_is_peak", False)),
            next_is_peak=bool(data.get("next_is_peak", False)),
            is_after_high_energy=bool(data.get("is_after_high_energy", False)),
            is_before_high_energy=bool(data.get("is_before_high_energy", False)),
            previous_has_speech=_opt_bool(data.get("previous_has_speech")),
            next_has_speech=_opt_bool(data.get("next_has_speech")),
            source=str(data.get("source", "silence_context_builder")),
            warnings=list(data.get("warnings", [])),
            errors=list(data.get("errors", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class SilenceContextBuildResult:
    status: str
    source: str = "silence_context_builder"
    contexts: list[SilenceSegmentContext] = field(default_factory=list)
    context_count: int = 0
    high_energy_context_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "contexts": [c.to_dict() for c in self.contexts],
            "context_count": self.context_count,
            "high_energy_context_count": self.high_energy_context_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SilenceContextBuildResult:
        raw_contexts = data.get("contexts", [])
        contexts = [SilenceSegmentContext.from_dict(c) for c in raw_contexts]
        return cls(
            status=str(data.get("status", "unknown")),
            source=str(data.get("source", "silence_context_builder")),
            contexts=contexts,
            context_count=int(data.get("context_count", len(contexts))),
            high_energy_context_count=int(data.get("high_energy_context_count", 0)),
            warnings=list(data.get("warnings", [])),
            errors=list(data.get("errors", [])),
            metadata=dict(data.get("metadata", {})),
        )
