from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_INPUTS = "skipped_no_inputs"
STATUS_FAILED = "failed"

VALUE_TIER_HIGH = "high"
VALUE_TIER_MEDIUM = "medium"
VALUE_TIER_LOW = "low"
VALUE_TIER_PROTECTED = "protected"
VALUE_TIER_TECHNICAL_WARNING = "technical_warning"
VALUE_TIER_UNKNOWN = "unknown"

REVIEW_LABEL_HIGH = "review_high_value_segment"
REVIEW_LABEL_MEDIUM = "review_mid_value_segment"
REVIEW_LABEL_LOW = "review_low_value_segment"
REVIEW_LABEL_PROTECTED = "review_protected_context"
REVIEW_LABEL_TECHNICAL_WARNING = "review_technical_warning"
REVIEW_LABEL_NONE = "no_content_value_priority"


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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
class ContentValueSegmentScore:
    segment_id: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    duration_seconds: float | None = None
    text: str = ""
    content_value_score: float = 0.0
    speech_value_score: float = 0.0
    keyword_value_score: float = 0.0
    interaction_value_score: float = 0.0
    visual_value_score: float = 0.0
    face_reaction_value_score: float = 0.0
    motion_value_score: float = 0.0
    screen_value_score: float = 0.0
    audio_value_score: float = 0.0
    story_context_score: float = 0.0
    dead_content_penalty_score: float = 0.0
    technical_penalty_score: float = 0.0
    protection_score: float = 0.0
    final_score: float = 0.0
    value_tier: str = VALUE_TIER_UNKNOWN
    review_label: str = REVIEW_LABEL_NONE
    is_high_value: bool = False
    is_mid_value: bool = False
    is_low_value: bool = False
    is_protected_context: bool = False
    is_hook_candidate: bool = False
    is_technical_warning: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)
    source_segment_index: int | None = None
    recommendation: str = REVIEW_LABEL_NONE
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "duration_seconds": self.duration_seconds,
            "text": self.text,
            "content_value_score": self.content_value_score,
            "speech_value_score": self.speech_value_score,
            "keyword_value_score": self.keyword_value_score,
            "interaction_value_score": self.interaction_value_score,
            "visual_value_score": self.visual_value_score,
            "face_reaction_value_score": self.face_reaction_value_score,
            "motion_value_score": self.motion_value_score,
            "screen_value_score": self.screen_value_score,
            "audio_value_score": self.audio_value_score,
            "story_context_score": self.story_context_score,
            "dead_content_penalty_score": self.dead_content_penalty_score,
            "technical_penalty_score": self.technical_penalty_score,
            "protection_score": self.protection_score,
            "final_score": self.final_score,
            "value_tier": self.value_tier,
            "review_label": self.review_label,
            "is_high_value": self.is_high_value,
            "is_mid_value": self.is_mid_value,
            "is_low_value": self.is_low_value,
            "is_protected_context": self.is_protected_context,
            "is_hook_candidate": self.is_hook_candidate,
            "is_technical_warning": self.is_technical_warning,
            "evidence": dict(self.evidence),
            "source_segment_index": self.source_segment_index,
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ContentValueSegmentScore":
        if not isinstance(data, dict):
            data = {}
        return cls(
            segment_id=str(data.get("segment_id") or ""),
            start_seconds=_safe_float_or_none(data.get("start_seconds")),
            end_seconds=_safe_float_or_none(data.get("end_seconds")),
            center_seconds=_safe_float_or_none(data.get("center_seconds")),
            duration_seconds=_safe_float_or_none(data.get("duration_seconds")),
            text=str(data.get("text") or ""),
            content_value_score=_safe_float(data.get("content_value_score"), 0.0),
            speech_value_score=_safe_float(data.get("speech_value_score"), 0.0),
            keyword_value_score=_safe_float(data.get("keyword_value_score"), 0.0),
            interaction_value_score=_safe_float(
                data.get("interaction_value_score"),
                0.0,
            ),
            visual_value_score=_safe_float(data.get("visual_value_score"), 0.0),
            face_reaction_value_score=_safe_float(
                data.get("face_reaction_value_score"),
                0.0,
            ),
            motion_value_score=_safe_float(data.get("motion_value_score"), 0.0),
            screen_value_score=_safe_float(data.get("screen_value_score"), 0.0),
            audio_value_score=_safe_float(data.get("audio_value_score"), 0.0),
            story_context_score=_safe_float(data.get("story_context_score"), 0.0),
            dead_content_penalty_score=_safe_float(
                data.get("dead_content_penalty_score"),
                0.0,
            ),
            technical_penalty_score=_safe_float(
                data.get("technical_penalty_score"),
                0.0,
            ),
            protection_score=_safe_float(data.get("protection_score"), 0.0),
            final_score=_safe_float(data.get("final_score"), 0.0),
            value_tier=str(data.get("value_tier") or VALUE_TIER_UNKNOWN),
            review_label=str(data.get("review_label") or REVIEW_LABEL_NONE),
            is_high_value=bool(data.get("is_high_value", False)),
            is_mid_value=bool(data.get("is_mid_value", False)),
            is_low_value=bool(data.get("is_low_value", False)),
            is_protected_context=bool(data.get("is_protected_context", False)),
            is_hook_candidate=bool(data.get("is_hook_candidate", False)),
            is_technical_warning=bool(data.get("is_technical_warning", False)),
            evidence=_safe_dict(data.get("evidence")),
            source_segment_index=_safe_int_or_none(data.get("source_segment_index")),
            recommendation=str(data.get("recommendation") or REVIEW_LABEL_NONE),
            metadata=_safe_dict(data.get("metadata")),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
        )


@dataclass
class ContentValueResult:
    status: str
    segment_scores: list[ContentValueSegmentScore] = field(default_factory=list)
    segment_score_count: int = 0
    high_value_count: int = 0
    mid_value_count: int = 0
    low_value_count: int = 0
    protected_context_count: int = 0
    hook_candidate_count: int = 0
    technical_warning_count: int = 0
    avg_content_value_score: float = 0.0
    max_content_value_score: float = 0.0
    min_content_value_score: float = 0.0
    recommendation: str = REVIEW_LABEL_NONE
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "segment_scores": [score.to_dict() for score in self.segment_scores],
            "segment_score_count": self.segment_score_count,
            "high_value_count": self.high_value_count,
            "mid_value_count": self.mid_value_count,
            "low_value_count": self.low_value_count,
            "protected_context_count": self.protected_context_count,
            "hook_candidate_count": self.hook_candidate_count,
            "technical_warning_count": self.technical_warning_count,
            "avg_content_value_score": self.avg_content_value_score,
            "max_content_value_score": self.max_content_value_score,
            "min_content_value_score": self.min_content_value_score,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ContentValueResult":
        if not isinstance(data, dict):
            data = {}
        raw_scores = data.get("segment_scores")
        scores = [
            ContentValueSegmentScore.from_dict(item)
            for item in raw_scores
            if isinstance(item, dict)
        ] if isinstance(raw_scores, list) else []
        return cls(
            status=str(data.get("status") or STATUS_FAILED),
            segment_scores=scores,
            segment_score_count=_safe_int(
                data.get("segment_score_count"),
                len(scores),
            ),
            high_value_count=_safe_int(data.get("high_value_count"), 0),
            mid_value_count=_safe_int(data.get("mid_value_count"), 0),
            low_value_count=_safe_int(data.get("low_value_count"), 0),
            protected_context_count=_safe_int(
                data.get("protected_context_count"),
                0,
            ),
            hook_candidate_count=_safe_int(data.get("hook_candidate_count"), 0),
            technical_warning_count=_safe_int(
                data.get("technical_warning_count"),
                0,
            ),
            avg_content_value_score=_safe_float(
                data.get("avg_content_value_score"),
                0.0,
            ),
            max_content_value_score=_safe_float(
                data.get("max_content_value_score"),
                0.0,
            ),
            min_content_value_score=_safe_float(
                data.get("min_content_value_score"),
                0.0,
            ),
            recommendation=str(data.get("recommendation") or REVIEW_LABEL_NONE),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            metadata=_safe_dict(data.get("metadata")),
        )
