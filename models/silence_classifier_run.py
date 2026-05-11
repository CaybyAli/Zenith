from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SilenceClassifierRunReport:
    status: str
    source: str = "silence_classifier_runner"
    detection_status: str | None = None
    classification_status: str | None = None
    classification_result: dict[str, Any] = field(default_factory=dict)
    classifications: list[dict[str, Any]] = field(default_factory=list)
    classification_count: int = 0
    remove_candidate_count: int = 0
    keep_candidate_count: int = 0
    counts_by_classification: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "detection_status": self.detection_status,
            "classification_status": self.classification_status,
            "classification_result": dict(self.classification_result),
            "classifications": list(self.classifications),
            "classification_count": self.classification_count,
            "remove_candidate_count": self.remove_candidate_count,
            "keep_candidate_count": self.keep_candidate_count,
            "counts_by_classification": dict(self.counts_by_classification),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SilenceClassifierRunReport:
        return cls(
            status=str(data.get("status", "unknown")),
            source=str(data.get("source", "silence_classifier_runner")),
            detection_status=data.get("detection_status"),
            classification_status=data.get("classification_status"),
            classification_result=dict(data.get("classification_result") or {}),
            classifications=list(data.get("classifications") or []),
            classification_count=int(data.get("classification_count", 0)),
            remove_candidate_count=int(data.get("remove_candidate_count", 0)),
            keep_candidate_count=int(data.get("keep_candidate_count", 0)),
            counts_by_classification=dict(data.get("counts_by_classification") or {}),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(data.get("recommendation", "review")),
            metadata=dict(data.get("metadata") or {}),
        )
