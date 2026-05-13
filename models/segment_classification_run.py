from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.segment_classification import (
    SegmentClassification,
    SegmentClassificationResult,
)


@dataclass
class SegmentClassificationRunReport:
    status: str = "ok"
    source: str = "segment_classifier"
    segment_classification_result: SegmentClassificationResult | None = None
    segments: list[SegmentClassification] = field(default_factory=list)
    segment_count: int = 0
    highlight_count: int = 0
    hook_candidate_count: int = 0
    protected_context_count: int = 0
    dead_candidate_count: int = 0
    filler_count: int = 0
    transition_count: int = 0
    censor_required_count: int = 0
    technical_warning_count: int = 0
    recommendation: str = "review_segment_classification"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "segment_classification_result": (
                self.segment_classification_result.to_dict()
                if self.segment_classification_result is not None
                else None
            ),
            "segments": [segment.to_dict() for segment in self.segments],
            "segment_count": self.segment_count,
            "highlight_count": self.highlight_count,
            "hook_candidate_count": self.hook_candidate_count,
            "protected_context_count": self.protected_context_count,
            "dead_candidate_count": self.dead_candidate_count,
            "filler_count": self.filler_count,
            "transition_count": self.transition_count,
            "censor_required_count": self.censor_required_count,
            "technical_warning_count": self.technical_warning_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SegmentClassificationRunReport":
        if not isinstance(data, dict):
            data = {}

        result_data = data.get("segment_classification_result")
        result = (
            SegmentClassificationResult.from_dict(result_data)
            if isinstance(result_data, dict)
            else None
        )

        segments = [
            SegmentClassification.from_dict(segment_data)
            for segment_data in data.get("segments") or []
            if isinstance(segment_data, dict)
        ]

        if not segments and result is not None:
            segments = list(result.segments)

        return cls(
            status=str(data.get("status") or "ok"),
            source=str(data.get("source") or "segment_classifier"),
            segment_classification_result=result,
            segments=segments,
            segment_count=int(data.get("segment_count", len(segments)) or 0),
            highlight_count=int(data.get("highlight_count") or 0),
            hook_candidate_count=int(data.get("hook_candidate_count") or 0),
            protected_context_count=int(data.get("protected_context_count") or 0),
            dead_candidate_count=int(data.get("dead_candidate_count") or 0),
            filler_count=int(data.get("filler_count") or 0),
            transition_count=int(data.get("transition_count") or 0),
            censor_required_count=int(data.get("censor_required_count") or 0),
            technical_warning_count=int(data.get("technical_warning_count") or 0),
            recommendation=str(
                data.get("recommendation") or "review_segment_classification"
            ),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
