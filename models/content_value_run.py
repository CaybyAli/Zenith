from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class ContentValueRunReport:
    status: str
    source: str = "content_value_runner"
    content_value_result: dict[str, Any] = field(default_factory=dict)
    segment_scores: list[dict[str, Any]] = field(default_factory=list)
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
    recommendation: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "content_value_result": dict(self.content_value_result),
            "segment_scores": [dict(item) for item in self.segment_scores],
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
    def from_dict(cls, data: dict[str, Any] | None) -> "ContentValueRunReport":
        if not isinstance(data, dict):
            data = {}
        raw_segment_scores = data.get("segment_scores")
        segment_scores = [
            dict(item) for item in raw_segment_scores if isinstance(item, dict)
        ] if isinstance(raw_segment_scores, list) else []
        return cls(
            status=str(data.get("status") or "failed"),
            source=str(data.get("source") or "content_value_runner"),
            content_value_result=_safe_dict(data.get("content_value_result")),
            segment_scores=segment_scores,
            segment_score_count=_safe_int(
                data.get("segment_score_count"),
                len(segment_scores),
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
            recommendation=(
                str(data.get("recommendation"))
                if data.get("recommendation") is not None
                else None
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            metadata=_safe_dict(data.get("metadata")),
        )
