from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AudioNormalizationSourceSelection:
    status: str
    selected_path: str | None = None
    selected_type: str | None = None
    source_priority: list[str] = field(default_factory=list)
    checked_sources: list[dict[str, Any]] = field(default_factory=list)
    requires_extraction: bool = False
    require_existing_file: bool = True
    is_wav_source: bool = False
    source_exists: bool = False
    original_source_path: str | None = None
    preprocessing_manifest_path: str | None = None
    recommendation: str = "review"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "selected_path": self.selected_path,
            "selected_type": self.selected_type,
            "source_priority": list(self.source_priority),
            "checked_sources": [dict(s) for s in self.checked_sources],
            "requires_extraction": self.requires_extraction,
            "require_existing_file": self.require_existing_file,
            "is_wav_source": self.is_wav_source,
            "source_exists": self.source_exists,
            "original_source_path": self.original_source_path,
            "preprocessing_manifest_path": self.preprocessing_manifest_path,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AudioNormalizationSourceSelection:
        return cls(
            status=str(data.get("status", "unavailable")),
            selected_path=data.get("selected_path"),
            selected_type=data.get("selected_type"),
            source_priority=list(data.get("source_priority") or []),
            checked_sources=[dict(s) for s in (data.get("checked_sources") or [])],
            requires_extraction=bool(data.get("requires_extraction", False)),
            require_existing_file=bool(data.get("require_existing_file", True)),
            is_wav_source=bool(data.get("is_wav_source", False)),
            source_exists=bool(data.get("source_exists", False)),
            original_source_path=data.get("original_source_path"),
            preprocessing_manifest_path=data.get("preprocessing_manifest_path"),
            recommendation=str(data.get("recommendation", "review")),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
