from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS = "skipped_no_transcript_segments"
STATUS_FAILED = "failed"

BOUNDARY_SAFE_SENTENCE = "safe_sentence_boundary"
BOUNDARY_UNSAFE_SENTENCE = "unsafe_sentence_boundary"
BOUNDARY_COMPLETE_SENTENCE = "complete_sentence"
BOUNDARY_OPEN_FRAGMENT = "open_sentence_fragment"
BOUNDARY_QUESTION = "question_boundary"
BOUNDARY_ANSWER_CANDIDATE = "answer_candidate"
BOUNDARY_OPEN_QUESTION = "open_question"
BOUNDARY_UNKNOWN = "unknown"

PROTECTION_NONE = "none"
PROTECTION_SOFT = "soft"
PROTECTION_HARD = "hard"
PROTECTION_REVIEW = "review"

ZONE_PROTECT_SENTENCE = "protect_sentence"
ZONE_PROTECT_OPEN_FRAGMENT = "protect_open_fragment"
ZONE_PROTECT_QUESTION_CONTEXT = "protect_question_context"
ZONE_PROTECT_ANSWER_CONTEXT = "protect_answer_context"
ZONE_REVIEW_BOUNDARY = "review_boundary"


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


def _safe_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass
class SentenceBoundaryPoint:
    boundary_id: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    text: str = ""
    normalized_text: str = ""
    boundary_type: str = BOUNDARY_UNKNOWN
    protection_level: str = PROTECTION_REVIEW
    is_complete_sentence: bool = False
    is_question: bool = False
    is_answer_candidate: bool = False
    is_open_fragment: bool = False
    confidence: float = 0.0
    recommendation: str = "review_sentence_boundary"
    source_segment_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "text": self.text,
            "normalized_text": self.normalized_text,
            "boundary_type": self.boundary_type,
            "protection_level": self.protection_level,
            "is_complete_sentence": self.is_complete_sentence,
            "is_question": self.is_question,
            "is_answer_candidate": self.is_answer_candidate,
            "is_open_fragment": self.is_open_fragment,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
            "source_segment_index": self.source_segment_index,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SentenceBoundaryPoint":
        if not isinstance(data, dict):
            data = {}
        return cls(
            boundary_id=str(data.get("boundary_id") or ""),
            start_seconds=_safe_float_or_none(data.get("start_seconds")),
            end_seconds=_safe_float_or_none(data.get("end_seconds")),
            center_seconds=_safe_float_or_none(data.get("center_seconds")),
            text=str(data.get("text") or ""),
            normalized_text=str(data.get("normalized_text") or ""),
            boundary_type=str(data.get("boundary_type") or BOUNDARY_UNKNOWN),
            protection_level=str(data.get("protection_level") or PROTECTION_REVIEW),
            is_complete_sentence=bool(data.get("is_complete_sentence", False)),
            is_question=bool(data.get("is_question", False)),
            is_answer_candidate=bool(data.get("is_answer_candidate", False)),
            is_open_fragment=bool(data.get("is_open_fragment", False)),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            recommendation=str(data.get("recommendation") or "review_sentence_boundary"),
            source_segment_index=_safe_int_or_none(data.get("source_segment_index")),
            metadata=_safe_dict(data.get("metadata")),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
        )


@dataclass
class SentenceBoundaryProtectionZone:
    zone_id: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float | None = None
    zone_type: str = ZONE_REVIEW_BOUNDARY
    protection_level: str = PROTECTION_REVIEW
    reason: str = "review_sentence_boundary"
    confidence: float = 0.0
    source_boundary_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "zone_type": self.zone_type,
            "protection_level": self.protection_level,
            "reason": self.reason,
            "confidence": self.confidence,
            "source_boundary_ids": list(self.source_boundary_ids),
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SentenceBoundaryProtectionZone":
        if not isinstance(data, dict):
            data = {}
        return cls(
            zone_id=str(data.get("zone_id") or ""),
            start_seconds=_safe_float_or_none(data.get("start_seconds")),
            end_seconds=_safe_float_or_none(data.get("end_seconds")),
            duration_seconds=_safe_float_or_none(data.get("duration_seconds")),
            zone_type=str(data.get("zone_type") or ZONE_REVIEW_BOUNDARY),
            protection_level=str(data.get("protection_level") or PROTECTION_REVIEW),
            reason=str(data.get("reason") or "review_sentence_boundary"),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            source_boundary_ids=[
                str(item) for item in _safe_list(data.get("source_boundary_ids"))
            ],
            metadata=_safe_dict(data.get("metadata")),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
        )


@dataclass
class SentenceBoundaryResult:
    status: str
    boundaries: list[SentenceBoundaryPoint] = field(default_factory=list)
    protection_zones: list[SentenceBoundaryProtectionZone] = field(default_factory=list)
    boundary_count: int = 0
    protection_zone_count: int = 0
    complete_sentence_count: int = 0
    open_fragment_count: int = 0
    question_count: int = 0
    open_question_count: int = 0
    safe_boundary_count: int = 0
    unsafe_boundary_count: int = 0
    recommendation: str = "review_sentence_boundaries"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "boundaries": [boundary.to_dict() for boundary in self.boundaries],
            "protection_zones": [zone.to_dict() for zone in self.protection_zones],
            "boundary_count": self.boundary_count,
            "protection_zone_count": self.protection_zone_count,
            "complete_sentence_count": self.complete_sentence_count,
            "open_fragment_count": self.open_fragment_count,
            "question_count": self.question_count,
            "open_question_count": self.open_question_count,
            "safe_boundary_count": self.safe_boundary_count,
            "unsafe_boundary_count": self.unsafe_boundary_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SentenceBoundaryResult":
        if not isinstance(data, dict):
            data = {}
        raw_boundaries = data.get("boundaries")
        raw_zones = data.get("protection_zones")
        boundaries = [
            SentenceBoundaryPoint.from_dict(item)
            for item in raw_boundaries
            if isinstance(item, dict)
        ] if isinstance(raw_boundaries, list) else []
        zones = [
            SentenceBoundaryProtectionZone.from_dict(item)
            for item in raw_zones
            if isinstance(item, dict)
        ] if isinstance(raw_zones, list) else []
        return cls(
            status=str(data.get("status") or STATUS_FAILED),
            boundaries=boundaries,
            protection_zones=zones,
            boundary_count=int(data.get("boundary_count", len(boundaries)) or 0),
            protection_zone_count=int(
                data.get("protection_zone_count", len(zones)) or 0
            ),
            complete_sentence_count=int(data.get("complete_sentence_count", 0) or 0),
            open_fragment_count=int(data.get("open_fragment_count", 0) or 0),
            question_count=int(data.get("question_count", 0) or 0),
            open_question_count=int(data.get("open_question_count", 0) or 0),
            safe_boundary_count=int(data.get("safe_boundary_count", 0) or 0),
            unsafe_boundary_count=int(data.get("unsafe_boundary_count", 0) or 0),
            recommendation=str(
                data.get("recommendation") or "review_sentence_boundaries"
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            metadata=_safe_dict(data.get("metadata")),
        )
