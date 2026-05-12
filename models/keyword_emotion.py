from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS = "skipped_no_transcript_segments"
STATUS_FAILED = "failed"

CATEGORY_HYPE = "hype"
CATEGORY_FRUSTRATION = "frustration"
CATEGORY_SHOCK = "shock"
CATEGORY_LAUGH = "laugh"
CATEGORY_QUESTION = "question"
CATEGORY_CALLOUT = "callout"
CATEGORY_GAMEPLAY = "gameplay"
CATEGORY_NEUTRAL = "neutral"
CATEGORY_UNKNOWN = "unknown"

LANGUAGE_DE = "de"
LANGUAGE_EN = "en"
LANGUAGE_TR = "tr"
LANGUAGE_MIXED = "mixed"
LANGUAGE_UNKNOWN = "unknown"


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
class KeywordEmotionMatch:
    match_id: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    text: str = ""
    matched_keyword: str = ""
    normalized_keyword: str = ""
    category: str = CATEGORY_UNKNOWN
    language: str = LANGUAGE_UNKNOWN
    intensity: float = 0.0
    confidence: float = 0.0
    source_segment_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "text": self.text,
            "matched_keyword": self.matched_keyword,
            "normalized_keyword": self.normalized_keyword,
            "category": self.category,
            "language": self.language,
            "intensity": self.intensity,
            "confidence": self.confidence,
            "source_segment_index": self.source_segment_index,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "KeywordEmotionMatch":
        if not isinstance(data, dict):
            data = {}
        return cls(
            match_id=str(data.get("match_id") or ""),
            start_seconds=_safe_float_or_none(data.get("start_seconds")),
            end_seconds=_safe_float_or_none(data.get("end_seconds")),
            center_seconds=_safe_float_or_none(data.get("center_seconds")),
            text=str(data.get("text") or ""),
            matched_keyword=str(data.get("matched_keyword") or ""),
            normalized_keyword=str(data.get("normalized_keyword") or ""),
            category=str(data.get("category") or CATEGORY_UNKNOWN),
            language=str(data.get("language") or LANGUAGE_UNKNOWN),
            intensity=float(data.get("intensity", 0.0) or 0.0),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            source_segment_index=_safe_int_or_none(data.get("source_segment_index")),
            metadata=_safe_dict(data.get("metadata")),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
        )


@dataclass
class KeywordEmotionSegmentScore:
    segment_id: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float | None = None
    text: str = ""
    categories: dict[str, float] = field(default_factory=dict)
    dominant_category: str = CATEGORY_NEUTRAL
    emotion_score: float = 0.0
    hype_score: float = 0.0
    frustration_score: float = 0.0
    shock_score: float = 0.0
    laugh_score: float = 0.0
    question_score: float = 0.0
    overall_keyword_score: float = 0.0
    match_count: int = 0
    recommendation: str = "no_keyword_priority"
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
            "categories": dict(self.categories),
            "dominant_category": self.dominant_category,
            "emotion_score": self.emotion_score,
            "hype_score": self.hype_score,
            "frustration_score": self.frustration_score,
            "shock_score": self.shock_score,
            "laugh_score": self.laugh_score,
            "question_score": self.question_score,
            "overall_keyword_score": self.overall_keyword_score,
            "match_count": self.match_count,
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "KeywordEmotionSegmentScore":
        if not isinstance(data, dict):
            data = {}
        categories = data.get("categories")
        return cls(
            segment_id=str(data.get("segment_id") or ""),
            start_seconds=_safe_float_or_none(data.get("start_seconds")),
            end_seconds=_safe_float_or_none(data.get("end_seconds")),
            duration_seconds=_safe_float_or_none(data.get("duration_seconds")),
            text=str(data.get("text") or ""),
            categories={
                str(key): float(value)
                for key, value in categories.items()
            } if isinstance(categories, dict) else {},
            dominant_category=str(data.get("dominant_category") or CATEGORY_NEUTRAL),
            emotion_score=float(data.get("emotion_score", 0.0) or 0.0),
            hype_score=float(data.get("hype_score", 0.0) or 0.0),
            frustration_score=float(data.get("frustration_score", 0.0) or 0.0),
            shock_score=float(data.get("shock_score", 0.0) or 0.0),
            laugh_score=float(data.get("laugh_score", 0.0) or 0.0),
            question_score=float(data.get("question_score", 0.0) or 0.0),
            overall_keyword_score=float(data.get("overall_keyword_score", 0.0) or 0.0),
            match_count=int(data.get("match_count", 0) or 0),
            recommendation=str(data.get("recommendation") or "no_keyword_priority"),
            metadata=_safe_dict(data.get("metadata")),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
        )


@dataclass
class KeywordEmotionResult:
    status: str
    matches: list[KeywordEmotionMatch] = field(default_factory=list)
    segment_scores: list[KeywordEmotionSegmentScore] = field(default_factory=list)
    match_count: int = 0
    segment_score_count: int = 0
    hype_match_count: int = 0
    frustration_match_count: int = 0
    shock_match_count: int = 0
    laugh_match_count: int = 0
    question_match_count: int = 0
    high_value_segment_count: int = 0
    recommendation: str = "no_keyword_priority"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "matches": [match.to_dict() for match in self.matches],
            "segment_scores": [score.to_dict() for score in self.segment_scores],
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
    def from_dict(cls, data: dict[str, Any] | None) -> "KeywordEmotionResult":
        if not isinstance(data, dict):
            data = {}
        raw_matches = data.get("matches")
        raw_scores = data.get("segment_scores")
        matches = [
            KeywordEmotionMatch.from_dict(item)
            for item in raw_matches
            if isinstance(item, dict)
        ] if isinstance(raw_matches, list) else []
        scores = [
            KeywordEmotionSegmentScore.from_dict(item)
            for item in raw_scores
            if isinstance(item, dict)
        ] if isinstance(raw_scores, list) else []
        return cls(
            status=str(data.get("status") or STATUS_FAILED),
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
            recommendation=str(data.get("recommendation") or "no_keyword_priority"),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            metadata=_safe_dict(data.get("metadata")),
        )
