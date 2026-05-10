from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SilenceSegment:
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    threshold_db: float | None = None
    source: str = "ffmpeg_silencedetect"
    classification: str = "unclassified"
    remove_candidate: bool = False
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "threshold_db": self.threshold_db,
            "source": self.source,
            "classification": self.classification,
            "remove_candidate": self.remove_candidate,
            "confidence": self.confidence,
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SilenceSegment:
        return cls(
            start_seconds=float(data.get("start_seconds", 0.0)),
            end_seconds=float(data.get("end_seconds", 0.0)),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            threshold_db=data.get("threshold_db"),
            source=str(data.get("source", "ffmpeg_silencedetect")),
            classification=str(data.get("classification", "unclassified")),
            remove_candidate=bool(data.get("remove_candidate", False)),
            confidence=float(data.get("confidence", 1.0)),
            warnings=list(data.get("warnings", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class SilenceDetectionResult:
    source_path: str
    status: str
    engine: str = "ffmpeg_silencedetect"
    threshold_db: float | None = None
    min_duration_seconds: float | None = None
    segments: list[SilenceSegment] = field(default_factory=list)
    segment_count: int = 0
    total_silence_seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    raw_output_tail: str | None = None
    command_preview: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "status": self.status,
            "engine": self.engine,
            "threshold_db": self.threshold_db,
            "min_duration_seconds": self.min_duration_seconds,
            "segments": [s.to_dict() for s in self.segments],
            "segment_count": self.segment_count,
            "total_silence_seconds": self.total_silence_seconds,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "raw_output_tail": self.raw_output_tail,
            "command_preview": list(self.command_preview),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SilenceDetectionResult:
        raw_segments = data.get("segments", [])
        segments = [SilenceSegment.from_dict(s) for s in raw_segments]
        return cls(
            source_path=str(data.get("source_path", "")),
            status=str(data.get("status", "unknown")),
            engine=str(data.get("engine", "ffmpeg_silencedetect")),
            threshold_db=data.get("threshold_db"),
            min_duration_seconds=data.get("min_duration_seconds"),
            segments=segments,
            segment_count=int(data.get("segment_count", len(segments))),
            total_silence_seconds=float(data.get("total_silence_seconds", 0.0)),
            warnings=list(data.get("warnings", [])),
            errors=list(data.get("errors", [])),
            raw_output_tail=data.get("raw_output_tail"),
            command_preview=list(data.get("command_preview", [])),
            metadata=dict(data.get("metadata", {})),
        )
