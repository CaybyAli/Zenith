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
class SentenceBoundaryRunReport:
    status: str
    source: str = "sentence_boundary_runner"
    transcript_source: str | None = None
    sentence_boundary_result: dict[str, Any] = field(default_factory=dict)
    boundaries: list[dict[str, Any]] = field(default_factory=list)
    protection_zones: list[dict[str, Any]] = field(default_factory=list)
    boundary_count: int = 0
    protection_zone_count: int = 0
    complete_sentence_count: int = 0
    open_fragment_count: int = 0
    question_count: int = 0
    open_question_count: int = 0
    safe_boundary_count: int = 0
    unsafe_boundary_count: int = 0
    recommendation: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "transcript_source": self.transcript_source,
            "sentence_boundary_result": dict(self.sentence_boundary_result),
            "boundaries": [dict(item) for item in self.boundaries],
            "protection_zones": [dict(item) for item in self.protection_zones],
            "boundary_count": self.boundary_count,
            "protection_zone_count": self.protection_zone_count,
            "complete_sentence_count": self.complete_sentence_count,
            "open_fragment_count": self.open_fragment_count,
            "question_count": self.question_count,
            "open_question_count": self.open_question_count,
            "safe_boundary_count": self.safe_boundary_count,
            "unsafe_boundary_count": self.unsafe_boundary_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SentenceBoundaryRunReport":
        if not isinstance(data, dict):
            data = {}

        raw_boundaries = data.get("boundaries")
        raw_zones = data.get("protection_zones")
        boundaries = [
            dict(item) for item in raw_boundaries if isinstance(item, dict)
        ] if isinstance(raw_boundaries, list) else []
        zones = [
            dict(item) for item in raw_zones if isinstance(item, dict)
        ] if isinstance(raw_zones, list) else []

        return cls(
            status=str(data.get("status") or "failed"),
            source=str(data.get("source") or "sentence_boundary_runner"),
            transcript_source=(
                str(data.get("transcript_source"))
                if data.get("transcript_source") is not None
                else None
            ),
            sentence_boundary_result=_safe_dict(data.get("sentence_boundary_result")),
            boundaries=boundaries,
            protection_zones=zones,
            boundary_count=int(data.get("boundary_count", len(boundaries)) or 0),
            protection_zone_count=int(data.get("protection_zone_count", len(zones)) or 0),
            complete_sentence_count=int(data.get("complete_sentence_count", 0) or 0),
            open_fragment_count=int(data.get("open_fragment_count", 0) or 0),
            question_count=int(data.get("question_count", 0) or 0),
            open_question_count=int(data.get("open_question_count", 0) or 0),
            safe_boundary_count=int(data.get("safe_boundary_count", 0) or 0),
            unsafe_boundary_count=int(data.get("unsafe_boundary_count", 0) or 0),
            recommendation=(
                str(data.get("recommendation"))
                if data.get("recommendation") is not None
                else None
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            metadata=_safe_dict(data.get("metadata")),
        )
