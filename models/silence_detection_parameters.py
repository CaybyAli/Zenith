from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SilenceDetectionParameters:
    threshold_db: float
    min_duration_seconds: float
    require_existing_audio: bool = True
    source_priority: list[str] = field(default_factory=list)
    profile_id: str | None = None
    quality_mode: str | None = None
    resolved_from: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold_db": self.threshold_db,
            "min_duration_seconds": self.min_duration_seconds,
            "require_existing_audio": self.require_existing_audio,
            "source_priority": list(self.source_priority),
            "profile_id": self.profile_id,
            "quality_mode": self.quality_mode,
            "resolved_from": dict(self.resolved_from),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SilenceDetectionParameters:
        threshold_raw = data.get("threshold_db", -40.0)
        try:
            threshold_db = float(threshold_raw)
        except (TypeError, ValueError):
            threshold_db = -40.0

        duration_raw = data.get("min_duration_seconds", 0.4)
        try:
            min_duration_seconds = float(duration_raw)
        except (TypeError, ValueError):
            min_duration_seconds = 0.4

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

        return cls(
            threshold_db=threshold_db,
            min_duration_seconds=min_duration_seconds,
            require_existing_audio=require_existing_audio,
            source_priority=list(data.get("source_priority") or []),
            profile_id=data.get("profile_id"),
            quality_mode=data.get("quality_mode"),
            resolved_from=dict(data.get("resolved_from") or {}),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
