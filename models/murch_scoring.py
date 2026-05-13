from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_SEGMENTS = "skipped_no_segments"
STATUS_FAILED = "failed"

MURCH_TIER_HIGH = "high"
MURCH_TIER_MEDIUM = "medium"
MURCH_TIER_LOW = "low"
MURCH_TIER_PROTECTED = "protected"
MURCH_TIER_TECHNICAL_WARNING = "technical_warning"
MURCH_TIER_UNKNOWN = "unknown"


@dataclass
class MurchScoreBreakdown:
    emotion_score: float = 0.0
    story_score: float = 0.0
    rhythm_score: float = 0.0
    eye_trace_score: float = 0.0
    screen_direction_score: float = 0.0
    spatial_continuity_score: float = 0.0
    weighted_score: float = 0.0
    weights: dict[str, float] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "emotion_score": self.emotion_score,
            "story_score": self.story_score,
            "rhythm_score": self.rhythm_score,
            "eye_trace_score": self.eye_trace_score,
            "screen_direction_score": self.screen_direction_score,
            "spatial_continuity_score": self.spatial_continuity_score,
            "weighted_score": self.weighted_score,
            "weights": dict(self.weights),
            "evidence": dict(self.evidence),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "MurchScoreBreakdown":
        if not isinstance(data, dict):
            data = {}

        return cls(
            emotion_score=float(data.get("emotion_score") or 0.0),
            story_score=float(data.get("story_score") or 0.0),
            rhythm_score=float(data.get("rhythm_score") or 0.0),
            eye_trace_score=float(data.get("eye_trace_score") or 0.0),
            screen_direction_score=float(data.get("screen_direction_score") or 0.0),
            spatial_continuity_score=float(data.get("spatial_continuity_score") or 0.0),
            weighted_score=float(data.get("weighted_score") or 0.0),
            weights=dict(data.get("weights") or {}),
            evidence=dict(data.get("evidence") or {}),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class MurchSegmentScore:
    segment_id: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    duration_seconds: float | None = None
    segment_type: str = "unknown"
    murch_score: float = 0.0
    murch_tier: str = MURCH_TIER_UNKNOWN
    emotion_score: float = 0.0
    story_score: float = 0.0
    rhythm_score: float = 0.0
    eye_trace_score: float = 0.0
    screen_direction_score: float = 0.0
    spatial_continuity_score: float = 0.0
    protection_score: float = 0.0
    risk_score: float = 0.0
    dead_content_risk_score: float = 0.0
    technical_risk_score: float = 0.0
    censor_required: bool = False
    is_high_murch_score: bool = False
    is_medium_murch_score: bool = False
    is_low_murch_score: bool = False
    is_protected_context: bool = False
    is_censor_required: bool = False
    recommendation: str = "review_murch_score_segment"
    evidence: dict[str, Any] = field(default_factory=dict)
    source_segment_id: str | None = None
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
            "murch_score": self.murch_score,
            "murch_tier": self.murch_tier,
            "emotion_score": self.emotion_score,
            "story_score": self.story_score,
            "rhythm_score": self.rhythm_score,
            "eye_trace_score": self.eye_trace_score,
            "screen_direction_score": self.screen_direction_score,
            "spatial_continuity_score": self.spatial_continuity_score,
            "protection_score": self.protection_score,
            "risk_score": self.risk_score,
            "dead_content_risk_score": self.dead_content_risk_score,
            "technical_risk_score": self.technical_risk_score,
            "censor_required": self.censor_required,
            "is_high_murch_score": self.is_high_murch_score,
            "is_medium_murch_score": self.is_medium_murch_score,
            "is_low_murch_score": self.is_low_murch_score,
            "is_protected_context": self.is_protected_context,
            "is_censor_required": self.is_censor_required,
            "recommendation": self.recommendation,
            "evidence": dict(self.evidence),
            "source_segment_id": self.source_segment_id,
            "source_signal_ids": list(self.source_signal_ids),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "MurchSegmentScore":
        if not isinstance(data, dict):
            data = {}

        return cls(
            segment_id=str(data.get("segment_id") or ""),
            start_seconds=data.get("start_seconds"),
            end_seconds=data.get("end_seconds"),
            center_seconds=data.get("center_seconds"),
            duration_seconds=data.get("duration_seconds"),
            segment_type=str(data.get("segment_type") or "unknown"),
            murch_score=float(data.get("murch_score") or 0.0),
            murch_tier=str(data.get("murch_tier") or MURCH_TIER_UNKNOWN),
            emotion_score=float(data.get("emotion_score") or 0.0),
            story_score=float(data.get("story_score") or 0.0),
            rhythm_score=float(data.get("rhythm_score") or 0.0),
            eye_trace_score=float(data.get("eye_trace_score") or 0.0),
            screen_direction_score=float(data.get("screen_direction_score") or 0.0),
            spatial_continuity_score=float(data.get("spatial_continuity_score") or 0.0),
            protection_score=float(data.get("protection_score") or 0.0),
            risk_score=float(data.get("risk_score") or 0.0),
            dead_content_risk_score=float(data.get("dead_content_risk_score") or 0.0),
            technical_risk_score=float(data.get("technical_risk_score") or 0.0),
            censor_required=bool(data.get("censor_required", False)),
            is_high_murch_score=bool(data.get("is_high_murch_score", False)),
            is_medium_murch_score=bool(data.get("is_medium_murch_score", False)),
            is_low_murch_score=bool(data.get("is_low_murch_score", False)),
            is_protected_context=bool(data.get("is_protected_context", False)),
            is_censor_required=bool(data.get("is_censor_required", False)),
            recommendation=str(data.get("recommendation") or "review_murch_score_segment"),
            evidence=dict(data.get("evidence") or {}),
            source_segment_id=data.get("source_segment_id"),
            source_signal_ids=list(data.get("source_signal_ids") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class MurchScoringResult:
    status: str = STATUS_OK
    segment_scores: list[MurchSegmentScore] = field(default_factory=list)
    segment_score_count: int = 0
    high_score_count: int = 0
    medium_score_count: int = 0
    low_score_count: int = 0
    protected_context_count: int = 0
    censor_required_count: int = 0
    technical_warning_count: int = 0
    avg_murch_score: float = 0.0
    max_murch_score: float = 0.0
    min_murch_score: float = 0.0
    recommendation: str = "review_murch_scoring_result"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "segment_scores": [segment_score.to_dict() for segment_score in self.segment_scores],
            "segment_score_count": self.segment_score_count,
            "high_score_count": self.high_score_count,
            "medium_score_count": self.medium_score_count,
            "low_score_count": self.low_score_count,
            "protected_context_count": self.protected_context_count,
            "censor_required_count": self.censor_required_count,
            "technical_warning_count": self.technical_warning_count,
            "avg_murch_score": self.avg_murch_score,
            "max_murch_score": self.max_murch_score,
            "min_murch_score": self.min_murch_score,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "MurchScoringResult":
        if not isinstance(data, dict):
            data = {}

        segment_scores = [
            MurchSegmentScore.from_dict(segment_score_data)
            for segment_score_data in data.get("segment_scores") or []
        ]

        return cls(
            status=str(data.get("status") or STATUS_OK),
            segment_scores=segment_scores,
            segment_score_count=int(data.get("segment_score_count", len(segment_scores)) or 0),
            high_score_count=int(data.get("high_score_count") or 0),
            medium_score_count=int(data.get("medium_score_count") or 0),
            low_score_count=int(data.get("low_score_count") or 0),
            protected_context_count=int(data.get("protected_context_count") or 0),
            censor_required_count=int(data.get("censor_required_count") or 0),
            technical_warning_count=int(data.get("technical_warning_count") or 0),
            avg_murch_score=float(data.get("avg_murch_score") or 0.0),
            max_murch_score=float(data.get("max_murch_score") or 0.0),
            min_murch_score=float(data.get("min_murch_score") or 0.0),
            recommendation=str(data.get("recommendation") or "review_murch_scoring_result"),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
