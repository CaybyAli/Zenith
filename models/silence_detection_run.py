from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SilenceDetectionRunReport:
    status: str
    source_path: str | None = None
    source_type: str | None = None
    threshold_db: float | None = None
    min_duration_seconds: float | None = None
    require_existing_audio: bool = True
    audio_source_selection: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    detection_result: dict[str, Any] = field(default_factory=dict)
    segment_count: int = 0
    total_silence_seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "use_result"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "threshold_db": self.threshold_db,
            "min_duration_seconds": self.min_duration_seconds,
            "require_existing_audio": self.require_existing_audio,
            "audio_source_selection": dict(self.audio_source_selection),
            "parameters": dict(self.parameters),
            "detection_result": dict(self.detection_result),
            "segment_count": self.segment_count,
            "total_silence_seconds": self.total_silence_seconds,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SilenceDetectionRunReport:
        threshold_raw = data.get("threshold_db")
        try:
            threshold_db = float(threshold_raw) if threshold_raw is not None else None
        except (TypeError, ValueError):
            threshold_db = None

        duration_raw = data.get("min_duration_seconds")
        try:
            min_duration_seconds = float(duration_raw) if duration_raw is not None else None
        except (TypeError, ValueError):
            min_duration_seconds = None

        req_raw = data.get("require_existing_audio", True)
        if isinstance(req_raw, bool):
            require_existing_audio = req_raw
        elif isinstance(req_raw, str):
            require_existing_audio = req_raw.strip().lower() not in ("false", "no", "0", "")
        else:
            try:
                require_existing_audio = bool(int(req_raw))
            except (TypeError, ValueError):
                require_existing_audio = True

        try:
            segment_count = int(data.get("segment_count", 0) or 0)
        except (TypeError, ValueError):
            segment_count = 0

        try:
            total_silence_seconds = float(data.get("total_silence_seconds", 0.0) or 0.0)
        except (TypeError, ValueError):
            total_silence_seconds = 0.0

        return cls(
            status=str(data.get("status", "unknown")),
            source_path=data.get("source_path"),
            source_type=data.get("source_type"),
            threshold_db=threshold_db,
            min_duration_seconds=min_duration_seconds,
            require_existing_audio=require_existing_audio,
            audio_source_selection=dict(data.get("audio_source_selection") or {}),
            parameters=dict(data.get("parameters") or {}),
            detection_result=dict(data.get("detection_result") or {}),
            segment_count=segment_count,
            total_silence_seconds=total_silence_seconds,
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(data.get("recommendation", "use_result")),
            metadata=dict(data.get("metadata") or {}),
        )
