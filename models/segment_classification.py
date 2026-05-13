from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_UNIFIED_SIGNALS = "skipped_no_unified_signals"
STATUS_FAILED = "failed"

SEGMENT_TYPE_HIGHLIGHT = "highlight"
SEGMENT_TYPE_HOOK_CANDIDATE = "hook_candidate"
SEGMENT_TYPE_STRONG_MOMENT = "strong_moment"
SEGMENT_TYPE_NORMAL_CONTENT = "normal_content"
SEGMENT_TYPE_TRANSITION = "transition"
SEGMENT_TYPE_FILLER = "filler"
SEGMENT_TYPE_DEAD_CANDIDATE = "dead_candidate"
SEGMENT_TYPE_PROTECTED_CONTEXT = "protected_context"
SEGMENT_TYPE_CENSOR_REQUIRED_SEGMENT = "censor_required_segment"
SEGMENT_TYPE_TECHNICAL_WARNING = "technical_warning"
SEGMENT_TYPE_UNKNOWN = "unknown"


@dataclass
class SegmentClassification:
    segment_id: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    duration_seconds: float | None = None
    segment_type: str = SEGMENT_TYPE_UNKNOWN
    confidence: float = 0.0
    segment_score: float = 0.0
    content_value_score: float = 0.0
    dead_content_score: float = 0.0
    protection_score: float = 0.0
    technical_risk_score: float = 0.0
    hook_candidate_score: float = 0.0
    censor_required: bool = False
    is_highlight_candidate: bool = False
    is_hook_candidate: bool = False
    is_protected_context: bool = False
    is_dead_candidate: bool = False
    is_transition_candidate: bool = False
    is_technical_warning: bool = False
    recommendation: str = "review_segment"
    evidence: dict[str, Any] = field(default_factory=dict)
    source_signal_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "duration_seconds": self.duration_seconds,
            "segment_type": self.segment_type,
            "confidence": self.confidence,
            "segment_score": self.segment_score,
            "content_value_score": self.content_value_score,
            "dead_content_score": self.dead_content_score,
            "protection_score": self.protection_score,
            "technical_risk_score": self.technical_risk_score,
            "hook_candidate_score": self.hook_candidate_score,
            "censor_required": self.censor_required,
            "is_highlight_candidate": self.is_highlight_candidate,
            "is_hook_candidate": self.is_hook_candidate,
            "is_protected_context": self.is_protected_context,
            "is_dead_candidate": self.is_dead_candidate,
            "is_transition_candidate": self.is_transition_candidate,
            "is_technical_warning": self.is_technical_warning,
            "recommendation": self.recommendation,
            "evidence": dict(self.evidence),
            "source_signal_ids": list(self.source_signal_ids),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SegmentClassification":
        if not isinstance(data, dict):
            data = {}

        return cls(
            segment_id=str(data.get("segment_id") or ""),
            start_seconds=data.get("start_seconds"),
            end_seconds=data.get("end_seconds"),
            center_seconds=data.get("center_seconds"),
            duration_seconds=data.get("duration_seconds"),
            segment_type=str(data.get("segment_type") or SEGMENT_TYPE_UNKNOWN),
            confidence=float(data.get("confidence") or 0.0),
            segment_score=float(data.get("segment_score") or 0.0),
            content_value_score=float(data.get("content_value_score") or 0.0),
            dead_content_score=float(data.get("dead_content_score") or 0.0),
            protection_score=float(data.get("protection_score") or 0.0),
            technical_risk_score=float(data.get("technical_risk_score") or 0.0),
            hook_candidate_score=float(data.get("hook_candidate_score") or 0.0),
            censor_required=bool(data.get("censor_required", False)),
            is_highlight_candidate=bool(data.get("is_highlight_candidate", False)),
            is_hook_candidate=bool(data.get("is_hook_candidate", False)),
            is_protected_context=bool(data.get("is_protected_context", False)),
            is_dead_candidate=bool(data.get("is_dead_candidate", False)),
            is_transition_candidate=bool(data.get("is_transition_candidate", False)),
            is_technical_warning=bool(data.get("is_technical_warning", False)),
            recommendation=str(data.get("recommendation") or "review_segment"),
            evidence=dict(data.get("evidence") or {}),
            source_signal_ids=list(data.get("source_signal_ids") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class SegmentClassificationResult:
    status: str = STATUS_OK
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
    def from_dict(cls, data: dict[str, Any] | None) -> "SegmentClassificationResult":
        if not isinstance(data, dict):
            data = {}

        segments = [
            SegmentClassification.from_dict(segment_data)
            for segment_data in data.get("segments") or []
        ]

        return cls(
            status=str(data.get("status") or STATUS_OK),
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
            recommendation=str(data.get("recommendation") or "review_segment_classification"),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
