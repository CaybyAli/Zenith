from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS = "skipped_no_transcript_segments"
STATUS_FAILED = "failed"

SEVERITY_MILD = "mild"
SEVERITY_SEVERE = "severe"
SEVERITY_UNKNOWN = "unknown"

CATEGORY_GAMING_FRUSTRATION = "gaming_frustration"
CATEGORY_SEVERE_PROFANITY = "severe_profanity"
CATEGORY_SEXUALIZED_PROFANITY = "sexualized_profanity"
CATEGORY_TARGETED_INSULT_CANDIDATE = "targeted_insult_candidate"
CATEGORY_UNKNOWN = "unknown"

CENSOR_ACTION_NONE = "none"
CENSOR_ACTION_SFX_OVERLAY_CANDIDATE = "censor_sfx_overlay_candidate"

TIMING_SOURCE_WORD_TIMESTAMP = "word_timestamp"
TIMING_SOURCE_SEGMENT_FALLBACK = "segment_fallback"
TIMING_SOURCE_UNKNOWN = "unknown"

REPLACEMENT_SFX_QUACK = "quack"
REPLACEMENT_SFX_DOLPHIN = "dolphin"
REPLACEMENT_SFX_BEEP = "beep"
REPLACEMENT_SFX_OPTIONS = (
    REPLACEMENT_SFX_QUACK,
    REPLACEMENT_SFX_DOLPHIN,
    REPLACEMENT_SFX_BEEP,
)


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
class ProfanityCensorMatch:
    match_id: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    duration_seconds: float | None = None
    text: str = ""
    matched_text: str = ""
    normalized_match: str = ""
    severity: str = SEVERITY_UNKNOWN
    category: str = CATEGORY_UNKNOWN
    censor_required: bool = False
    censor_action: str = CENSOR_ACTION_NONE
    replacement_sfx: str | None = None
    timing_source: str = TIMING_SOURCE_UNKNOWN
    confidence: float = 0.0
    source_segment_index: int | None = None
    source_word_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "duration_seconds": self.duration_seconds,
            "text": self.text,
            "matched_text": self.matched_text,
            "normalized_match": self.normalized_match,
            "severity": self.severity,
            "category": self.category,
            "censor_required": self.censor_required,
            "censor_action": self.censor_action,
            "replacement_sfx": self.replacement_sfx,
            "timing_source": self.timing_source,
            "confidence": self.confidence,
            "source_segment_index": self.source_segment_index,
            "source_word_index": self.source_word_index,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ProfanityCensorMatch":
        if not isinstance(data, dict):
            data = {}
        return cls(
            match_id=str(data.get("match_id") or ""),
            start_seconds=_safe_float_or_none(data.get("start_seconds")),
            end_seconds=_safe_float_or_none(data.get("end_seconds")),
            center_seconds=_safe_float_or_none(data.get("center_seconds")),
            duration_seconds=_safe_float_or_none(data.get("duration_seconds")),
            text=str(data.get("text") or ""),
            matched_text=str(data.get("matched_text") or ""),
            normalized_match=str(data.get("normalized_match") or ""),
            severity=str(data.get("severity") or SEVERITY_UNKNOWN),
            category=str(data.get("category") or CATEGORY_UNKNOWN),
            censor_required=bool(data.get("censor_required", False)),
            censor_action=str(data.get("censor_action") or CENSOR_ACTION_NONE),
            replacement_sfx=(
                str(data.get("replacement_sfx"))
                if data.get("replacement_sfx") is not None
                else None
            ),
            timing_source=str(data.get("timing_source") or TIMING_SOURCE_UNKNOWN),
            confidence=_safe_float(data.get("confidence"), 0.0),
            source_segment_index=_safe_int_or_none(
                data.get("source_segment_index")
            ),
            source_word_index=_safe_int_or_none(data.get("source_word_index")),
            metadata=_safe_dict(data.get("metadata")),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
        )


@dataclass
class ProfanityCensorSegmentResult:
    segment_id: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float | None = None
    text: str = ""
    match_count: int = 0
    severe_match_count: int = 0
    mild_match_count: int = 0
    censor_required_count: int = 0
    preferred_replacement_sfx: str | None = None
    recommendation: str = "no_profanity_censor_candidates"
    matches: list[dict[str, Any]] = field(default_factory=list)
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
            "match_count": self.match_count,
            "severe_match_count": self.severe_match_count,
            "mild_match_count": self.mild_match_count,
            "censor_required_count": self.censor_required_count,
            "preferred_replacement_sfx": self.preferred_replacement_sfx,
            "recommendation": self.recommendation,
            "matches": [dict(item) for item in self.matches],
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ProfanityCensorSegmentResult":
        if not isinstance(data, dict):
            data = {}
        raw_matches = data.get("matches")
        matches = [
            dict(item) for item in raw_matches if isinstance(item, dict)
        ] if isinstance(raw_matches, list) else []
        return cls(
            segment_id=str(data.get("segment_id") or ""),
            start_seconds=_safe_float_or_none(data.get("start_seconds")),
            end_seconds=_safe_float_or_none(data.get("end_seconds")),
            duration_seconds=_safe_float_or_none(data.get("duration_seconds")),
            text=str(data.get("text") or ""),
            match_count=_safe_int(data.get("match_count"), len(matches)),
            severe_match_count=_safe_int(data.get("severe_match_count"), 0),
            mild_match_count=_safe_int(data.get("mild_match_count"), 0),
            censor_required_count=_safe_int(
                data.get("censor_required_count"),
                0,
            ),
            preferred_replacement_sfx=(
                str(data.get("preferred_replacement_sfx"))
                if data.get("preferred_replacement_sfx") is not None
                else None
            ),
            recommendation=str(
                data.get("recommendation")
                or "no_profanity_censor_candidates"
            ),
            matches=matches,
            metadata=_safe_dict(data.get("metadata")),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
        )


@dataclass
class ProfanityCensorResult:
    status: str
    matches: list[ProfanityCensorMatch] = field(default_factory=list)
    segment_results: list[ProfanityCensorSegmentResult] = field(default_factory=list)
    match_count: int = 0
    severe_match_count: int = 0
    mild_match_count: int = 0
    censor_required_count: int = 0
    word_level_match_count: int = 0
    segment_fallback_match_count: int = 0
    recommendation: str = "no_profanity_censor_candidates"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "matches": [match.to_dict() for match in self.matches],
            "segment_results": [
                segment_result.to_dict()
                for segment_result in self.segment_results
            ],
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
    def from_dict(cls, data: dict[str, Any] | None) -> "ProfanityCensorResult":
        if not isinstance(data, dict):
            data = {}
        raw_matches = data.get("matches")
        matches = [
            ProfanityCensorMatch.from_dict(item)
            for item in raw_matches
            if isinstance(item, dict)
        ] if isinstance(raw_matches, list) else []
        raw_segment_results = data.get("segment_results")
        segment_results = [
            ProfanityCensorSegmentResult.from_dict(item)
            for item in raw_segment_results
            if isinstance(item, dict)
        ] if isinstance(raw_segment_results, list) else []
        return cls(
            status=str(data.get("status") or STATUS_FAILED),
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
            recommendation=str(
                data.get("recommendation")
                or "no_profanity_censor_candidates"
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            metadata=_safe_dict(data.get("metadata")),
        )
