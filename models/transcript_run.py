from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TranscriptRunReport:
    status: str
    source_path: str | None = None
    source_type: str | None = None
    source_selection: dict[str, Any] = field(default_factory=dict)
    engine: str | None = None
    language: str | None = None
    segments: list[dict[str, Any]] = field(default_factory=list)
    full_text: str = ""
    segment_count: int = 0
    duration_seconds: float = 0.0
    word_count: int = 0
    recommendation: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "source_selection": dict(self.source_selection),
            "engine": self.engine,
            "language": self.language,
            "segments": list(self.segments),
            "full_text": self.full_text,
            "segment_count": self.segment_count,
            "duration_seconds": self.duration_seconds,
            "word_count": self.word_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }
