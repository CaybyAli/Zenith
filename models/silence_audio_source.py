from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SilenceAudioSourceSelection:
    selected_path: str | None
    source_type: str
    status: str
    exists: bool
    checked_paths: list[str] = field(default_factory=list)
    preferred_order: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "use_selected"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_path": self.selected_path,
            "source_type": self.source_type,
            "status": self.status,
            "exists": self.exists,
            "checked_paths": list(self.checked_paths),
            "preferred_order": list(self.preferred_order),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SilenceAudioSourceSelection:
        return cls(
            selected_path=data.get("selected_path"),
            source_type=str(data.get("source_type", "none")),
            status=str(data.get("status", "unavailable")),
            exists=bool(data.get("exists", False)),
            checked_paths=list(data.get("checked_paths") or []),
            preferred_order=list(data.get("preferred_order") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(data.get("recommendation", "use_selected")),
            metadata=dict(data.get("metadata") or {}),
        )
