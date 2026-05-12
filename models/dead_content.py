from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_INPUTS = "skipped_no_inputs"
STATUS_FAILED = "failed"

CANDIDATE_TYPE_DEAD_AIR = "dead_air_candidate"
CANDIDATE_TYPE_LOW_VALUE = "low_value_content_candidate"
CANDIDATE_TYPE_FILLER_PAUSE = "filler_pause_candidate"
CANDIDATE_TYPE_LOADING_OR_MENU = "loading_or_menu_candidate"
CANDIDATE_TYPE_LOW_VISUAL_DEAD = "low_visual_dead_candidate"
CANDIDATE_TYPE_PRIVATE_OR_META = "private_or_meta_review_candidate"
CANDIDATE_TYPE_PROTECTED_CONTEXT = "protected_context_candidate"
CANDIDATE_TYPE_UNKNOWN = "unknown"


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _safe_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass
class DeadContentCandidate:
    candidate_id: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    duration_seconds: float | None = None
    text: str = ""
    candidate_type: str = CANDIDATE_TYPE_UNKNOWN
    dead_content_score: float = 0.0
    confidence: float = 0.0
    review_required: bool = True
    protected_by_context: bool = False
    protection_reasons: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    source_segment_index: int | None = None
    recommendation: str = "no_dead_content_priority"
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "duration_seconds": self.duration_seconds,
            "text": self.text,
            "candidate_type": self.candidate_type,
            "dead_content_score": self.dead_content_score,
            "confidence": self.confidence,
            "review_required": self.review_required,
            "protected_by_context": self.protected_by_context,
            "protection_reasons": list(self.protection_reasons),
            "evidence": dict(self.evidence),
            "source_segment_index": self.source_segment_index,
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "DeadContentCandidate":
        if not isinstance(data, dict):
            data = {}
        return cls(
            candidate_id=str(data.get("candidate_id") or ""),
            start_seconds=_safe_float_or_none(data.get("start_seconds")),
            end_seconds=_safe_float_or_none(data.get("end_seconds")),
            center_seconds=_safe_float_or_none(data.get("center_seconds")),
            duration_seconds=_safe_float_or_none(data.get("duration_seconds")),
            text=str(data.get("text") or ""),
            candidate_type=str(data.get("candidate_type") or CANDIDATE_TYPE_UNKNOWN),
            dead_content_score=_safe_float(data.get("dead_content_score"), 0.0),
            confidence=_safe_float(data.get("confidence"), 0.0),
            review_required=bool(data.get("review_required", True)),
            protected_by_context=bool(data.get("protected_by_context", False)),
            protection_reasons=[
                str(item) for item in _safe_list(data.get("protection_reasons"))
            ],
            evidence=_safe_dict(data.get("evidence")),
            source_segment_index=_safe_int_or_none(data.get("source_segment_index")),
            recommendation=str(data.get("recommendation") or "no_dead_content_priority"),
            metadata=_safe_dict(data.get("metadata")),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
        )


@dataclass
class DeadContentSegmentScore:
    segment_id: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float | None = None
    text: str = ""
    dead_content_score: float = 0.0
    content_value_score: float = 0.0
    silence_score: float = 0.0
    low_visual_score: float = 0.0
    low_keyword_score: float = 0.0
    low_interaction_score: float = 0.0
    filler_score: float = 0.0
    screen_penalty_score: float = 0.0
    context_protection_score: float = 0.0
    candidate_type: str = CANDIDATE_TYPE_UNKNOWN
    review_required: bool = False
    protected_by_context: bool = False
    recommendation: str = "no_dead_content_priority"
    evidence: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "text": self.text,
            "dead_content_score": self.dead_content_score,
            "content_value_score": self.content_value_score,
            "silence_score": self.silence_score,
            "low_visual_score": self.low_visual_score,
            "low_keyword_score": self.low_keyword_score,
            "low_interaction_score": self.low_interaction_score,
            "filler_score": self.filler_score,
            "screen_penalty_score": self.screen_penalty_score,
            "context_protection_score": self.context_protection_score,
            "candidate_type": self.candidate_type,
            "review_required": self.review_required,
            "protected_by_context": self.protected_by_context,
            "recommendation": self.recommendation,
            "evidence": dict(self.evidence),
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "DeadContentSegmentScore":
        if not isinstance(data, dict):
            data = {}
        return cls(
            segment_id=str(data.get("segment_id") or ""),
            start_seconds=_safe_float_or_none(data.get("start_seconds")),
            end_seconds=_safe_float_or_none(data.get("end_seconds")),
            duration_seconds=_safe_float_or_none(data.get("duration_seconds")),
            text=str(data.get("text") or ""),
            dead_content_score=_safe_float(data.get("dead_content_score"), 0.0),
            content_value_score=_safe_float(data.get("content_value_score"), 0.0),
            silence_score=_safe_float(data.get("silence_score"), 0.0),
            low_visual_score=_safe_float(data.get("low_visual_score"), 0.0),
            low_keyword_score=_safe_float(data.get("low_keyword_score"), 0.0),
            low_interaction_score=_safe_float(
                data.get("low_interaction_score"),
                0.0,
            ),
            filler_score=_safe_float(data.get("filler_score"), 0.0),
            screen_penalty_score=_safe_float(data.get("screen_penalty_score"), 0.0),
            context_protection_score=_safe_float(
                data.get("context_protection_score"),
                0.0,
            ),
            candidate_type=str(data.get("candidate_type") or CANDIDATE_TYPE_UNKNOWN),
            review_required=bool(data.get("review_required", False)),
            protected_by_context=bool(data.get("protected_by_context", False)),
            recommendation=str(data.get("recommendation") or "no_dead_content_priority"),
            evidence=_safe_dict(data.get("evidence")),
            metadata=_safe_dict(data.get("metadata")),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
        )


@dataclass
class DeadContentDetectionResult:
    status: str
    candidates: list[DeadContentCandidate] = field(default_factory=list)
    segment_scores: list[DeadContentSegmentScore] = field(default_factory=list)
    candidate_count: int = 0
    segment_score_count: int = 0
    dead_air_candidate_count: int = 0
    low_value_candidate_count: int = 0
    filler_pause_candidate_count: int = 0
    loading_or_menu_candidate_count: int = 0
    private_or_meta_candidate_count: int = 0
    protected_candidate_count: int = 0
    high_confidence_candidate_count: int = 0
    recommendation: str = "no_dead_content_priority"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "segment_scores": [score.to_dict() for score in self.segment_scores],
            "candidate_count": self.candidate_count,
            "segment_score_count": self.segment_score_count,
            "dead_air_candidate_count": self.dead_air_candidate_count,
            "low_value_candidate_count": self.low_value_candidate_count,
            "filler_pause_candidate_count": self.filler_pause_candidate_count,
            "loading_or_menu_candidate_count": (
                self.loading_or_menu_candidate_count
            ),
            "private_or_meta_candidate_count": self.private_or_meta_candidate_count,
            "protected_candidate_count": self.protected_candidate_count,
            "high_confidence_candidate_count": self.high_confidence_candidate_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "DeadContentDetectionResult":
        if not isinstance(data, dict):
            data = {}
        raw_candidates = data.get("candidates")
        raw_segment_scores = data.get("segment_scores")
        candidates = [
            DeadContentCandidate.from_dict(item)
            for item in raw_candidates
            if isinstance(item, dict)
        ] if isinstance(raw_candidates, list) else []
        segment_scores = [
            DeadContentSegmentScore.from_dict(item)
            for item in raw_segment_scores
            if isinstance(item, dict)
        ] if isinstance(raw_segment_scores, list) else []
        return cls(
            status=str(data.get("status") or STATUS_FAILED),
            candidates=candidates,
            segment_scores=segment_scores,
            candidate_count=_safe_int(data.get("candidate_count"), len(candidates)),
            segment_score_count=_safe_int(
                data.get("segment_score_count"),
                len(segment_scores),
            ),
            dead_air_candidate_count=_safe_int(
                data.get("dead_air_candidate_count"),
                0,
            ),
            low_value_candidate_count=_safe_int(
                data.get("low_value_candidate_count"),
                0,
            ),
            filler_pause_candidate_count=_safe_int(
                data.get("filler_pause_candidate_count"),
                0,
            ),
            loading_or_menu_candidate_count=_safe_int(
                data.get("loading_or_menu_candidate_count"),
                0,
            ),
            private_or_meta_candidate_count=_safe_int(
                data.get("private_or_meta_candidate_count"),
                0,
            ),
            protected_candidate_count=_safe_int(
                data.get("protected_candidate_count"),
                0,
            ),
            high_confidence_candidate_count=_safe_int(
                data.get("high_confidence_candidate_count"),
                0,
            ),
            recommendation=str(data.get("recommendation") or "no_dead_content_priority"),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            metadata=_safe_dict(data.get("metadata")),
        )
