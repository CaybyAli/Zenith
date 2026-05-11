from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

FILLER_TYPES = frozenset({
    "hesitation",
    "discourse_marker",
    "phrase_filler",
    "repeated_word",
    "unknown",
})


@dataclass
class FillerWordOccurrence:
    text: str
    normalized_text: str
    filler_type: str
    language: str = "unknown"
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    duration_seconds: float | None = None
    confidence: float = 0.75
    remove_candidate: bool = True
    reason: str = ""
    source_segment_index: int | None = None
    source_word_index: int | None = None
    source_item: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "normalized_text": self.normalized_text,
            "filler_type": self.filler_type,
            "language": self.language,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "duration_seconds": self.duration_seconds,
            "confidence": self.confidence,
            "remove_candidate": self.remove_candidate,
            "reason": self.reason,
            "source_segment_index": self.source_segment_index,
            "source_word_index": self.source_word_index,
            "source_item": dict(self.source_item),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FillerWordOccurrence:
        if not isinstance(data, dict):
            data = {}

        def _opt_float(key: str) -> float | None:
            val = data.get(key)
            if val is None:
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        def _opt_int(key: str) -> int | None:
            val = data.get(key)
            if val is None:
                return None
            try:
                return int(val)
            except (TypeError, ValueError):
                return None

        raw_si = data.get("source_item", {})
        source_item: dict[str, Any] = raw_si if isinstance(raw_si, dict) else {}

        raw_warnings = data.get("warnings", [])
        warnings: list[str] = [str(w) for w in raw_warnings] if isinstance(raw_warnings, list) else []

        raw_errors = data.get("errors", [])
        errors: list[str] = [str(e) for e in raw_errors] if isinstance(raw_errors, list) else []

        raw_meta = data.get("metadata", {})
        metadata: dict[str, Any] = raw_meta if isinstance(raw_meta, dict) else {}

        return cls(
            text=str(data.get("text", "")),
            normalized_text=str(data.get("normalized_text", "")),
            filler_type=str(data.get("filler_type", "unknown")),
            language=str(data.get("language", "unknown")),
            start_seconds=_opt_float("start_seconds"),
            end_seconds=_opt_float("end_seconds"),
            center_seconds=_opt_float("center_seconds"),
            duration_seconds=_opt_float("duration_seconds"),
            confidence=float(data.get("confidence", 0.75)),
            remove_candidate=bool(data.get("remove_candidate", True)),
            reason=str(data.get("reason", "")),
            source_segment_index=_opt_int("source_segment_index"),
            source_word_index=_opt_int("source_word_index"),
            source_item=source_item,
            warnings=warnings,
            errors=errors,
            metadata=metadata,
        )


@dataclass
class FillerWordDetectionResult:
    status: str
    source: str = "filler_word_detector"
    occurrences: list[FillerWordOccurrence] = field(default_factory=list)
    occurrence_count: int = 0
    remove_candidate_count: int = 0
    counts_by_filler_type: dict[str, int] = field(default_factory=dict)
    counts_by_language: dict[str, int] = field(default_factory=dict)
    total_filler_duration_seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "occurrences": [o.to_dict() for o in self.occurrences],
            "occurrence_count": self.occurrence_count,
            "remove_candidate_count": self.remove_candidate_count,
            "counts_by_filler_type": dict(self.counts_by_filler_type),
            "counts_by_language": dict(self.counts_by_language),
            "total_filler_duration_seconds": self.total_filler_duration_seconds,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FillerWordDetectionResult:
        if not isinstance(data, dict):
            data = {}

        raw_occ = data.get("occurrences", [])
        occurrences: list[FillerWordOccurrence] = []
        if isinstance(raw_occ, list):
            for item in raw_occ:
                try:
                    if isinstance(item, dict):
                        occurrences.append(FillerWordOccurrence.from_dict(item))
                except Exception:
                    pass

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

        raw_warnings = data.get("warnings", [])
        warnings: list[str] = [str(w) for w in raw_warnings] if isinstance(raw_warnings, list) else []

        raw_errors = data.get("errors", [])
        errors: list[str] = [str(e) for e in raw_errors] if isinstance(raw_errors, list) else []

        raw_meta = data.get("metadata", {})
        metadata: dict[str, Any] = raw_meta if isinstance(raw_meta, dict) else {}

        try:
            total_dur = float(data.get("total_filler_duration_seconds", 0.0))
        except (TypeError, ValueError):
            total_dur = 0.0

        return cls(
            status=str(data.get("status", "unknown")),
            source=str(data.get("source", "filler_word_detector")),
            occurrences=occurrences,
            occurrence_count=int(data.get("occurrence_count", len(occurrences))),
            remove_candidate_count=int(data.get("remove_candidate_count", 0)),
            counts_by_filler_type=counts_by_filler_type,
            counts_by_language=counts_by_language,
            total_filler_duration_seconds=total_dur,
            warnings=warnings,
            errors=errors,
            metadata=metadata,
        )
