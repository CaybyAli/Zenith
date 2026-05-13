from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.murch_scoring import MurchScoringResult, MurchSegmentScore


@dataclass
class MurchScoringRunReport:
    status: str = "ok"
    source: str = "murch_scoring"
    murch_scoring_result: MurchScoringResult | None = None
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
            "source": self.source,
            "murch_scoring_result": (
                self.murch_scoring_result.to_dict()
                if self.murch_scoring_result is not None
                else None
            ),
            "segment_scores": [
                segment_score.to_dict()
                for segment_score in self.segment_scores
            ],
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
    def from_dict(cls, data: dict[str, Any] | None) -> "MurchScoringRunReport":
        if not isinstance(data, dict):
            data = {}

        result_data = data.get("murch_scoring_result")
        result = (
            MurchScoringResult.from_dict(result_data)
            if isinstance(result_data, dict)
            else None
        )

        segment_scores = [
            MurchSegmentScore.from_dict(segment_score_data)
            for segment_score_data in data.get("segment_scores") or []
            if isinstance(segment_score_data, dict)
        ]

        if not segment_scores and result is not None:
            segment_scores = list(result.segment_scores)

        return cls(
            status=str(data.get("status") or "ok"),
            source=str(data.get("source") or "murch_scoring"),
            murch_scoring_result=result,
            segment_scores=segment_scores,
            segment_score_count=int(
                data.get("segment_score_count", len(segment_scores)) or 0
            ),
            high_score_count=int(data.get("high_score_count") or 0),
            medium_score_count=int(data.get("medium_score_count") or 0),
            low_score_count=int(data.get("low_score_count") or 0),
            protected_context_count=int(data.get("protected_context_count") or 0),
            censor_required_count=int(data.get("censor_required_count") or 0),
            technical_warning_count=int(data.get("technical_warning_count") or 0),
            avg_murch_score=float(data.get("avg_murch_score") or 0.0),
            max_murch_score=float(data.get("max_murch_score") or 0.0),
            min_murch_score=float(data.get("min_murch_score") or 0.0),
            recommendation=str(
                data.get("recommendation") or "review_murch_scoring_result"
            ),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
