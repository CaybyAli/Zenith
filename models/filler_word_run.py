from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FillerWordRunReport:
    status: str
    source: str = "filler_word_runner"
    transcript_source: str | None = None
    transcript_data_preview: dict[str, Any] = field(default_factory=dict)
    detection_result: dict[str, Any] = field(default_factory=dict)
    occurrences: list[dict[str, Any]] = field(default_factory=list)
    occurrence_count: int = 0
    remove_candidate_count: int = 0
    counts_by_filler_type: dict[str, int] = field(default_factory=dict)
    counts_by_language: dict[str, int] = field(default_factory=dict)
    total_filler_duration_seconds: float = 0.0
    transcript_word_count: int = 0
    filler_rate: float = 0.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "transcript_source": self.transcript_source,
            "transcript_data_preview": dict(self.transcript_data_preview),
            "detection_result": dict(self.detection_result),
            "occurrences": list(self.occurrences),
            "occurrence_count": self.occurrence_count,
            "remove_candidate_count": self.remove_candidate_count,
            "counts_by_filler_type": dict(self.counts_by_filler_type),
            "counts_by_language": dict(self.counts_by_language),
            "total_filler_duration_seconds": self.total_filler_duration_seconds,
            "transcript_word_count": self.transcript_word_count,
            "filler_rate": self.filler_rate,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FillerWordRunReport:
        if not isinstance(data, dict):
            data = {}

        def _safe_int(key: str, default: int = 0) -> int:
            try:
                return int(data.get(key, default))
            except (TypeError, ValueError):
                return default

        def _safe_float(key: str, default: float = 0.0) -> float:
            try:
                return float(data.get(key, default))
            except (TypeError, ValueError):
                return default

        def _safe_list(key: str) -> list:
            val = data.get(key, [])
            return list(val) if isinstance(val, list) else []

        def _safe_dict(key: str) -> dict:
            val = data.get(key, {})
            return dict(val) if isinstance(val, dict) else {}

        raw_cft = data.get("counts_by_filler_type", {})
        counts_by_filler_type: dict[str, int] = (
            {str(k): int(v) for k, v in raw_cft.items()}
            if isinstance(raw_cft, dict) else {}
        )

        raw_cl = data.get("counts_by_language", {})
        counts_by_language: dict[str, int] = (
            {str(k): int(v) for k, v in raw_cl.items()}
            if isinstance(raw_cl, dict) else {}
        )

        ts = data.get("transcript_source")
        transcript_source = str(ts) if ts is not None else None

        return cls(
            status=str(data.get("status", "unknown")),
            source=str(data.get("source", "filler_word_runner")),
            transcript_source=transcript_source,
            transcript_data_preview=_safe_dict("transcript_data_preview"),
            detection_result=_safe_dict("detection_result"),
            occurrences=_safe_list("occurrences"),
            occurrence_count=_safe_int("occurrence_count"),
            remove_candidate_count=_safe_int("remove_candidate_count"),
            counts_by_filler_type=counts_by_filler_type,
            counts_by_language=counts_by_language,
            total_filler_duration_seconds=_safe_float("total_filler_duration_seconds"),
            transcript_word_count=_safe_int("transcript_word_count"),
            filler_rate=_safe_float("filler_rate"),
            warnings=[str(w) for w in _safe_list("warnings")],
            errors=[str(e) for e in _safe_list("errors")],
            recommendation=str(data.get("recommendation", "review")),
            metadata=_safe_dict("metadata"),
        )
