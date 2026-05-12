from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS = "skipped_no_transcript_segments"
STATUS_FAILED = "failed"

INTERACTION_TYPE_MONOLOGUE = "monologue"
INTERACTION_TYPE_INTERACTION = "interaction"
INTERACTION_TYPE_QUESTION_ANSWER = "question_answer"
INTERACTION_TYPE_CHAT_REACTION = "chat_reaction"
INTERACTION_TYPE_CALLOUT = "callout"
INTERACTION_TYPE_COMMENTARY = "commentary"
INTERACTION_TYPE_PRIVATE_OR_META_CANDIDATE = "private_or_meta_candidate"
INTERACTION_TYPE_UNKNOWN = "unknown"


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


def _safe_bool(value: Any) -> bool:
    return bool(value)


@dataclass
class InteractionClassificationPoint:
    interaction_id: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    text: str = ""
    normalized_text: str = ""
    interaction_type: str = INTERACTION_TYPE_UNKNOWN
    confidence: float = 0.0
    context_needed: bool = False
    is_question: bool = False
    is_answer_candidate: bool = False
    is_chat_reaction_candidate: bool = False
    is_private_or_meta_candidate: bool = False
    source_segment_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "text": self.text,
            "normalized_text": self.normalized_text,
            "interaction_type": self.interaction_type,
            "confidence": self.confidence,
            "context_needed": self.context_needed,
            "is_question": self.is_question,
            "is_answer_candidate": self.is_answer_candidate,
            "is_chat_reaction_candidate": self.is_chat_reaction_candidate,
            "is_private_or_meta_candidate": self.is_private_or_meta_candidate,
            "source_segment_index": self.source_segment_index,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "InteractionClassificationPoint":
        if not isinstance(data, dict):
            data = {}
        return cls(
            interaction_id=str(data.get("interaction_id") or ""),
            start_seconds=_safe_float_or_none(data.get("start_seconds")),
            end_seconds=_safe_float_or_none(data.get("end_seconds")),
            center_seconds=_safe_float_or_none(data.get("center_seconds")),
            text=str(data.get("text") or ""),
            normalized_text=str(data.get("normalized_text") or ""),
            interaction_type=str(
                data.get("interaction_type") or INTERACTION_TYPE_UNKNOWN
            ),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            context_needed=_safe_bool(data.get("context_needed")),
            is_question=_safe_bool(data.get("is_question")),
            is_answer_candidate=_safe_bool(data.get("is_answer_candidate")),
            is_chat_reaction_candidate=_safe_bool(
                data.get("is_chat_reaction_candidate")
            ),
            is_private_or_meta_candidate=_safe_bool(
                data.get("is_private_or_meta_candidate")
            ),
            source_segment_index=_safe_int_or_none(data.get("source_segment_index")),
            metadata=_safe_dict(data.get("metadata")),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
        )


@dataclass
class InteractionSegmentClassification:
    segment_id: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float | None = None
    text: str = ""
    interaction_type: str = INTERACTION_TYPE_UNKNOWN
    confidence: float = 0.0
    monologue_score: float = 0.0
    interaction_score: float = 0.0
    question_answer_score: float = 0.0
    chat_reaction_score: float = 0.0
    callout_score: float = 0.0
    commentary_score: float = 0.0
    private_or_meta_score: float = 0.0
    context_needed: bool = False
    recommendation: str = "review_unknown_interaction_type"
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
            "interaction_type": self.interaction_type,
            "confidence": self.confidence,
            "monologue_score": self.monologue_score,
            "interaction_score": self.interaction_score,
            "question_answer_score": self.question_answer_score,
            "chat_reaction_score": self.chat_reaction_score,
            "callout_score": self.callout_score,
            "commentary_score": self.commentary_score,
            "private_or_meta_score": self.private_or_meta_score,
            "context_needed": self.context_needed,
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "InteractionSegmentClassification":
        if not isinstance(data, dict):
            data = {}
        return cls(
            segment_id=str(data.get("segment_id") or ""),
            start_seconds=_safe_float_or_none(data.get("start_seconds")),
            end_seconds=_safe_float_or_none(data.get("end_seconds")),
            duration_seconds=_safe_float_or_none(data.get("duration_seconds")),
            text=str(data.get("text") or ""),
            interaction_type=str(
                data.get("interaction_type") or INTERACTION_TYPE_UNKNOWN
            ),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            monologue_score=float(data.get("monologue_score", 0.0) or 0.0),
            interaction_score=float(data.get("interaction_score", 0.0) or 0.0),
            question_answer_score=float(
                data.get("question_answer_score", 0.0) or 0.0
            ),
            chat_reaction_score=float(data.get("chat_reaction_score", 0.0) or 0.0),
            callout_score=float(data.get("callout_score", 0.0) or 0.0),
            commentary_score=float(data.get("commentary_score", 0.0) or 0.0),
            private_or_meta_score=float(
                data.get("private_or_meta_score", 0.0) or 0.0
            ),
            context_needed=_safe_bool(data.get("context_needed")),
            recommendation=str(
                data.get("recommendation") or "review_unknown_interaction_type"
            ),
            metadata=_safe_dict(data.get("metadata")),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
        )


@dataclass
class InteractionClassificationResult:
    status: str
    points: list[InteractionClassificationPoint] = field(default_factory=list)
    segment_classifications: list[InteractionSegmentClassification] = field(
        default_factory=list
    )
    point_count: int = 0
    segment_classification_count: int = 0
    monologue_count: int = 0
    interaction_count: int = 0
    question_answer_count: int = 0
    chat_reaction_count: int = 0
    callout_count: int = 0
    commentary_count: int = 0
    private_or_meta_count: int = 0
    context_needed_count: int = 0
    recommendation: str = "review_unknown_interaction_type"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "points": [point.to_dict() for point in self.points],
            "segment_classifications": [
                classification.to_dict()
                for classification in self.segment_classifications
            ],
            "point_count": self.point_count,
            "segment_classification_count": self.segment_classification_count,
            "monologue_count": self.monologue_count,
            "interaction_count": self.interaction_count,
            "question_answer_count": self.question_answer_count,
            "chat_reaction_count": self.chat_reaction_count,
            "callout_count": self.callout_count,
            "commentary_count": self.commentary_count,
            "private_or_meta_count": self.private_or_meta_count,
            "context_needed_count": self.context_needed_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "InteractionClassificationResult":
        if not isinstance(data, dict):
            data = {}
        raw_points = data.get("points")
        raw_classifications = data.get("segment_classifications")
        points = [
            InteractionClassificationPoint.from_dict(item)
            for item in raw_points
            if isinstance(item, dict)
        ] if isinstance(raw_points, list) else []
        classifications = [
            InteractionSegmentClassification.from_dict(item)
            for item in raw_classifications
            if isinstance(item, dict)
        ] if isinstance(raw_classifications, list) else []
        return cls(
            status=str(data.get("status") or STATUS_FAILED),
            points=points,
            segment_classifications=classifications,
            point_count=int(data.get("point_count", len(points)) or 0),
            segment_classification_count=int(
                data.get("segment_classification_count", len(classifications)) or 0
            ),
            monologue_count=int(data.get("monologue_count", 0) or 0),
            interaction_count=int(data.get("interaction_count", 0) or 0),
            question_answer_count=int(data.get("question_answer_count", 0) or 0),
            chat_reaction_count=int(data.get("chat_reaction_count", 0) or 0),
            callout_count=int(data.get("callout_count", 0) or 0),
            commentary_count=int(data.get("commentary_count", 0) or 0),
            private_or_meta_count=int(data.get("private_or_meta_count", 0) or 0),
            context_needed_count=int(data.get("context_needed_count", 0) or 0),
            recommendation=str(
                data.get("recommendation") or "review_unknown_interaction_type"
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            metadata=_safe_dict(data.get("metadata")),
        )
