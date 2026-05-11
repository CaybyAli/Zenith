from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RmsEnergyAudioSourceSelection:
    status: str
    selected_path: str | None = None
    selected_type: str | None = None
    exists: bool = False
    is_wav: bool = False
    source_priority: list[str] = field(default_factory=list)
    checked_sources: list[dict[str, Any]] = field(default_factory=list)
    allow_original_wav_fallback: bool = True
    requires_extraction: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "selected_path": self.selected_path,
            "selected_type": self.selected_type,
            "exists": self.exists,
            "is_wav": self.is_wav,
            "source_priority": list(self.source_priority),
            "checked_sources": [dict(s) for s in self.checked_sources],
            "allow_original_wav_fallback": self.allow_original_wav_fallback,
            "requires_extraction": self.requires_extraction,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RmsEnergyAudioSourceSelection:
        return cls(
            status=str(data.get("status", "unavailable")),
            selected_path=data.get("selected_path"),
            selected_type=data.get("selected_type"),
            exists=bool(data.get("exists", False)),
            is_wav=bool(data.get("is_wav", False)),
            source_priority=list(data.get("source_priority") or []),
            checked_sources=[dict(s) for s in (data.get("checked_sources") or [])],
            allow_original_wav_fallback=bool(data.get("allow_original_wav_fallback", True)),
            requires_extraction=bool(data.get("requires_extraction", False)),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(data.get("recommendation", "review")),
            metadata=dict(data.get("metadata") or {}),
        )
