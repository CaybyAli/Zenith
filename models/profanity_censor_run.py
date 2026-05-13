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
class ProfanityCensorRunReport:
    status: str
    source: str = "profanity_censor_runner"
    profanity_censor_result: dict[str, Any] = field(default_factory=dict)
    matches: list[dict[str, Any]] = field(default_factory=list)
    segment_results: list[dict[str, Any]] = field(default_factory=list)
    match_count: int = 0
    severe_match_count: int = 0
    mild_match_count: int = 0
    censor_required_count: int = 0
    word_level_match_count: int = 0
    segment_fallback_match_count: int = 0
    recommendation: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "profanity_censor_result": dict(self.profanity_censor_result),
            "matches": [dict(item) for item in self.matches],
            "segment_results": [dict(item) for item in self.segment_results],
            "match_count": self.match_count,
            "severe_match_count": self.severe_match_count,
            "mild_match_count": self.mild_match_count,
            "censor_required_count": self.censor_required_count,
            "word_level_match_count": self.word_level_match_count,
            "segment_fallback_match_count": self.segment_fallback_match_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ProfanityCensorRunReport":
        if not isinstance(data, dict):
            data = {}
        raw_matches = data.get("matches")
        matches = [
            dict(item) for item in raw_matches if isinstance(item, dict)
        ] if isinstance(raw_matches, list) else []
        raw_segments = data.get("segment_results")
        segment_results = [
            dict(item) for item in raw_segments if isinstance(item, dict)
        ] if isinstance(raw_segments, list) else []
        return cls(
            status=str(data.get("status") or "failed"),
            source=str(data.get("source") or "profanity_censor_runner"),
            profanity_censor_result=_safe_dict(
                data.get("profanity_censor_result")
            ),
            matches=matches,
            segment_results=segment_results,
            match_count=_safe_int(data.get("match_count"), len(matches)),
            severe_match_count=_safe_int(data.get("severe_match_count"), 0),
            mild_match_count=_safe_int(data.get("mild_match_count"), 0),
            censor_required_count=_safe_int(
                data.get("censor_required_count"),
                0,
            ),
            word_level_match_count=_safe_int(
                data.get("word_level_match_count"),
                0,
            ),
            segment_fallback_match_count=_safe_int(
                data.get("segment_fallback_match_count"),
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
