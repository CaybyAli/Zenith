from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shared.jarvis_enums import JarvisCommandType


@dataclass(slots=True, frozen=True)
class JarvisResponse:
    command_type: JarvisCommandType
    title: str
    summary: str
    details: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence_sections: list[dict[str, Any]] = field(default_factory=list)
    recommended_next_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_type": self.command_type.value,
            "title": self.title,
            "summary": self.summary,
            "details": list(self.details),
            "warnings": list(self.warnings),
            "evidence_sections": [dict(section) for section in self.evidence_sections],
            "recommended_next_steps": list(self.recommended_next_steps),
        }