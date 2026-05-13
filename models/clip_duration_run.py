from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.clip_duration import (
    ClipDurationOptimizationPlan,
    ClipDurationRecommendation,
)


@dataclass
class ClipDurationRunReport:
    status: str = "skipped_no_cut_list_items"
    source: str = "clip_duration_optimizer"
    clip_duration_plan: ClipDurationOptimizationPlan | None = None
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
            "source": self.source,
            "clip_duration_plan": (
                self.clip_duration_plan.to_dict()
                if self.clip_duration_plan is not None
                else None
            ),
            "recommendations": [
                recommendation.to_dict()
                for recommendation in self.recommendations
            ],
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
    def from_dict(cls, data: dict[str, Any] | None) -> "ClipDurationRunReport":
        data = data or {}

        plan_data = data.get("clip_duration_plan")
        clip_duration_plan = (
            ClipDurationOptimizationPlan.from_dict(plan_data)
            if isinstance(plan_data, dict)
            else None
        )

        recommendations = [
            ClipDurationRecommendation.from_dict(item)
            for item in data.get("recommendations", []) or []
            if isinstance(item, dict)
        ]

        return cls(
            status=str(data.get("status", "skipped_no_cut_list_items")),
            source=str(data.get("source", "clip_duration_optimizer")),
            clip_duration_plan=clip_duration_plan,
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
            recommendation=str(
                data.get(
                    "recommendation",
                    "clip_duration_skipped_no_cut_list_items",
                )
            ),
            warnings=list(data.get("warnings", []) or []),
            errors=list(data.get("errors", []) or []),
            metadata=dict(data.get("metadata", {}) or {}),
        )
