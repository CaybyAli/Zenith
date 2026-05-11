from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SilenceClassification:
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    classification: str
    remove_candidate: bool
    confidence: float
    reason: str
    rules_applied: list[str] = field(default_factory=list)
    source_segment: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "classification": self.classification,
            "remove_candidate": self.remove_candidate,
            "confidence": self.confidence,
            "reason": self.reason,
            "rules_applied": list(self.rules_applied),
            "source_segment": dict(self.source_segment),
            "context": dict(self.context),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SilenceClassification:
        return cls(
            start_seconds=float(data.get("start_seconds", 0.0)),
            end_seconds=float(data.get("end_seconds", 0.0)),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            classification=str(data.get("classification", "unknown")),
            remove_candidate=bool(data.get("remove_candidate", False)),
            confidence=float(data.get("confidence", 0.0)),
            reason=str(data.get("reason", "")),
            rules_applied=list(data.get("rules_applied", [])),
            source_segment=dict(data.get("source_segment", {})),
            context=dict(data.get("context", {})),
            warnings=list(data.get("warnings", [])),
            errors=list(data.get("errors", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class SilenceClassificationResult:
    status: str
    source: str = "adaptive_silence_classifier"
    classifications: list[SilenceClassification] = field(default_factory=list)
    classification_count: int = 0
    remove_candidate_count: int = 0
    keep_candidate_count: int = 0
    counts_by_classification: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "classifications": [c.to_dict() for c in self.classifications],
            "classification_count": self.classification_count,
            "remove_candidate_count": self.remove_candidate_count,
            "keep_candidate_count": self.keep_candidate_count,
            "counts_by_classification": dict(self.counts_by_classification),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SilenceClassificationResult:
        raw_classifications = data.get("classifications", [])
        classifications = [SilenceClassification.from_dict(c) for c in raw_classifications]
        return cls(
            status=str(data.get("status", "unknown")),
            source=str(data.get("source", "adaptive_silence_classifier")),
            classifications=classifications,
            classification_count=int(data.get("classification_count", len(classifications))),
            remove_candidate_count=int(data.get("remove_candidate_count", 0)),
            keep_candidate_count=int(data.get("keep_candidate_count", 0)),
            counts_by_classification=dict(data.get("counts_by_classification", {})),
            warnings=list(data.get("warnings", [])),
            errors=list(data.get("errors", [])),
            metadata=dict(data.get("metadata", {})),
        )
