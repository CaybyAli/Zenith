from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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


@dataclass
class KeywordEmotionRunReport:
    status: str
    source: str = "keyword_emotion_runner"
    transcript_source: str | None = None
    keyword_emotion_result: dict[str, Any] = field(default_factory=dict)
    matches: list[dict[str, Any]] = field(default_factory=list)
    segment_scores: list[dict[str, Any]] = field(default_factory=list)
    match_count: int = 0
    segment_score_count: int = 0
    hype_match_count: int = 0
    frustration_match_count: int = 0
    shock_match_count: int = 0
    laugh_match_count: int = 0
    question_match_count: int = 0
    high_value_segment_count: int = 0
    recommendation: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "transcript_source": self.transcript_source,
            "keyword_emotion_result": dict(self.keyword_emotion_result),
            "matches": [dict(item) for item in self.matches],
            "segment_scores": [dict(item) for item in self.segment_scores],
            "match_count": self.match_count,
            "segment_score_count": self.segment_score_count,
            "hype_match_count": self.hype_match_count,
            "frustration_match_count": self.frustration_match_count,
            "shock_match_count": self.shock_match_count,
            "laugh_match_count": self.laugh_match_count,
            "question_match_count": self.question_match_count,
            "high_value_segment_count": self.high_value_segment_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "KeywordEmotionRunReport":
        if not isinstance(data, dict):
            data = {}

        raw_matches = data.get("matches")
        raw_scores = data.get("segment_scores")
        matches = [
            dict(item) for item in raw_matches if isinstance(item, dict)
        ] if isinstance(raw_matches, list) else []
        scores = [
            dict(item) for item in raw_scores if isinstance(item, dict)
        ] if isinstance(raw_scores, list) else []

        return cls(
            status=str(data.get("status") or "failed"),
            source=str(data.get("source") or "keyword_emotion_runner"),
            transcript_source=(
                str(data.get("transcript_source"))
                if data.get("transcript_source") is not None
                else None
            ),
            keyword_emotion_result=_safe_dict(data.get("keyword_emotion_result")),
            matches=matches,
            segment_scores=scores,
            match_count=int(data.get("match_count", len(matches)) or 0),
            segment_score_count=int(data.get("segment_score_count", len(scores)) or 0),
            hype_match_count=int(data.get("hype_match_count", 0) or 0),
            frustration_match_count=int(data.get("frustration_match_count", 0) or 0),
            shock_match_count=int(data.get("shock_match_count", 0) or 0),
            laugh_match_count=int(data.get("laugh_match_count", 0) or 0),
            question_match_count=int(data.get("question_match_count", 0) or 0),
            high_value_segment_count=int(data.get("high_value_segment_count", 0) or 0),
            recommendation=(
                str(data.get("recommendation"))
                if data.get("recommendation") is not None
                else None
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            metadata=_safe_dict(data.get("metadata")),
        )
