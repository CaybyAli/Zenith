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


@dataclass
class DeadContentRunReport:
    status: str
    source: str = "dead_content_runner"
    dead_content_result: dict[str, Any] = field(default_factory=dict)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    segment_scores: list[dict[str, Any]] = field(default_factory=list)
    candidate_count: int = 0
    segment_score_count: int = 0
    dead_air_candidate_count: int = 0
    low_value_candidate_count: int = 0
    filler_pause_candidate_count: int = 0
    loading_or_menu_candidate_count: int = 0
    private_or_meta_candidate_count: int = 0
    protected_candidate_count: int = 0
    high_confidence_candidate_count: int = 0
    recommendation: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "dead_content_result": dict(self.dead_content_result),
            "candidates": [dict(item) for item in self.candidates],
            "segment_scores": [dict(item) for item in self.segment_scores],
            "candidate_count": self.candidate_count,
            "segment_score_count": self.segment_score_count,
            "dead_air_candidate_count": self.dead_air_candidate_count,
            "low_value_candidate_count": self.low_value_candidate_count,
            "filler_pause_candidate_count": self.filler_pause_candidate_count,
            "loading_or_menu_candidate_count": self.loading_or_menu_candidate_count,
            "private_or_meta_candidate_count": self.private_or_meta_candidate_count,
            "protected_candidate_count": self.protected_candidate_count,
            "high_confidence_candidate_count": self.high_confidence_candidate_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "DeadContentRunReport":
        if not isinstance(data, dict):
            data = {}
        raw_candidates = data.get("candidates")
        raw_segment_scores = data.get("segment_scores")
        candidates = [
            dict(item) for item in raw_candidates if isinstance(item, dict)
        ] if isinstance(raw_candidates, list) else []
        segment_scores = [
            dict(item) for item in raw_segment_scores if isinstance(item, dict)
        ] if isinstance(raw_segment_scores, list) else []
        return cls(
            status=str(data.get("status") or "failed"),
            source=str(data.get("source") or "dead_content_runner"),
            dead_content_result=_safe_dict(data.get("dead_content_result")),
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
            recommendation=(
                str(data.get("recommendation"))
                if data.get("recommendation") is not None
                else None
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            metadata=_safe_dict(data.get("metadata")),
        )
