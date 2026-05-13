from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClipDurationRecommendation:
    recommendation_id: str
    source_item_id: str | None = None
    segment_id: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    duration_seconds: float | None = None
    proposed_action: str = "review"
    duration_status: str = "unknown_review"
    recommended_min_duration_seconds: float = 0.0
    recommended_max_duration_seconds: float = 0.0
    recommended_target_duration_seconds: float | None = None
    suggested_start_seconds: float | None = None
    suggested_end_seconds: float | None = None
    suggested_duration_seconds: float | None = None
    adjustment_seconds: float = 0.0
    confidence: float = 0.0
    priority: str = "low"
    is_too_short: bool = False
    is_too_long: bool = False
    is_duration_ok: bool = False
    is_protected: bool = False
    is_censor_keep: bool = False
    is_review_required: bool = True
    is_invalid_timing: bool = False
    reason: str = ""
    decision_basis: dict[str, Any] = field(default_factory=dict)
    source_signal_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "source_item_id": self.source_item_id,
            "segment_id": self.segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "duration_seconds": self.duration_seconds,
            "proposed_action": self.proposed_action,
            "duration_status": self.duration_status,
            "recommended_min_duration_seconds": self.recommended_min_duration_seconds,
            "recommended_max_duration_seconds": self.recommended_max_duration_seconds,
            "recommended_target_duration_seconds": self.recommended_target_duration_seconds,
            "suggested_start_seconds": self.suggested_start_seconds,
            "suggested_end_seconds": self.suggested_end_seconds,
            "suggested_duration_seconds": self.suggested_duration_seconds,
            "adjustment_seconds": self.adjustment_seconds,
            "confidence": self.confidence,
            "priority": self.priority,
            "is_too_short": self.is_too_short,
            "is_too_long": self.is_too_long,
            "is_duration_ok": self.is_duration_ok,
            "is_protected": self.is_protected,
            "is_censor_keep": self.is_censor_keep,
            "is_review_required": self.is_review_required,
            "is_invalid_timing": self.is_invalid_timing,
            "reason": self.reason,
            "decision_basis": dict(self.decision_basis),
            "source_signal_ids": list(self.source_signal_ids),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ClipDurationRecommendation":
        data = data or {}
        return cls(
            recommendation_id=str(data.get("recommendation_id", "")),
            source_item_id=data.get("source_item_id"),
            segment_id=data.get("segment_id"),
            start_seconds=data.get("start_seconds"),
            end_seconds=data.get("end_seconds"),
            center_seconds=data.get("center_seconds"),
            duration_seconds=data.get("duration_seconds"),
            proposed_action=str(data.get("proposed_action", "review")),
            duration_status=str(data.get("duration_status", "unknown_review")),
            recommended_min_duration_seconds=float(data.get("recommended_min_duration_seconds", 0.0)),
            recommended_max_duration_seconds=float(data.get("recommended_max_duration_seconds", 0.0)),
            recommended_target_duration_seconds=data.get("recommended_target_duration_seconds"),
            suggested_start_seconds=data.get("suggested_start_seconds"),
            suggested_end_seconds=data.get("suggested_end_seconds"),
            suggested_duration_seconds=data.get("suggested_duration_seconds"),
            adjustment_seconds=float(data.get("adjustment_seconds", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            priority=str(data.get("priority", "low")),
            is_too_short=bool(data.get("is_too_short", False)),
            is_too_long=bool(data.get("is_too_long", False)),
            is_duration_ok=bool(data.get("is_duration_ok", False)),
            is_protected=bool(data.get("is_protected", False)),
            is_censor_keep=bool(data.get("is_censor_keep", False)),
            is_review_required=bool(data.get("is_review_required", True)),
            is_invalid_timing=bool(data.get("is_invalid_timing", False)),
            reason=str(data.get("reason", "")),
            decision_basis=dict(data.get("decision_basis", {}) or {}),
            source_signal_ids=list(data.get("source_signal_ids", []) or []),
            warnings=list(data.get("warnings", []) or []),
            errors=list(data.get("errors", []) or []),
            metadata=dict(data.get("metadata", {}) or {}),
        )


@dataclass
class ClipDurationOptimizationPlan:
    status: str = "skipped_no_cut_list_items"
    recommendations: list[ClipDurationRecommendation] = field(default_factory=list)
    recommendation_count: int = 0
    duration_ok_count: int = 0
    too_short_count: int = 0
    too_long_count: int = 0
    trim_review_count: int = 0
    extend_review_count: int = 0
    protect_duration_count: int = 0
    censor_keep_count: int = 0
    technical_review_count: int = 0
    invalid_timing_count: int = 0
    recommendation: str = "clip_duration_skipped_no_cut_list_items"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "recommendations": [item.to_dict() for item in self.recommendations],
            "recommendation_count": self.recommendation_count,
            "duration_ok_count": self.duration_ok_count,
            "too_short_count": self.too_short_count,
            "too_long_count": self.too_long_count,
            "trim_review_count": self.trim_review_count,
            "extend_review_count": self.extend_review_count,
            "protect_duration_count": self.protect_duration_count,
            "censor_keep_count": self.censor_keep_count,
            "technical_review_count": self.technical_review_count,
            "invalid_timing_count": self.invalid_timing_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ClipDurationOptimizationPlan":
        data = data or {}
        recommendations = [
            ClipDurationRecommendation.from_dict(item)
            for item in data.get("recommendations", []) or []
        ]

        return cls(
            status=str(data.get("status", "skipped_no_cut_list_items")),
            recommendations=recommendations,
            recommendation_count=int(data.get("recommendation_count", len(recommendations))),
            duration_ok_count=int(data.get("duration_ok_count", 0)),
            too_short_count=int(data.get("too_short_count", 0)),
            too_long_count=int(data.get("too_long_count", 0)),
            trim_review_count=int(data.get("trim_review_count", 0)),
            extend_review_count=int(data.get("extend_review_count", 0)),
            protect_duration_count=int(data.get("protect_duration_count", 0)),
            censor_keep_count=int(data.get("censor_keep_count", 0)),
            technical_review_count=int(data.get("technical_review_count", 0)),
            invalid_timing_count=int(data.get("invalid_timing_count", 0)),
            recommendation=str(data.get("recommendation", "clip_duration_skipped_no_cut_list_items")),
            warnings=list(data.get("warnings", []) or []),
            errors=list(data.get("errors", []) or []),
            metadata=dict(data.get("metadata", {}) or {}),
        )
