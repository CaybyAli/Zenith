from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shared.jarvis_enums import JarvisCommandType


@dataclass(slots=True, frozen=True)
class JarvisCommand:
    raw_text: str
    command_type: JarvisCommandType
    normalized_query: str
    filters: dict[str, Any] = field(default_factory=dict)
    requested_scope: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "command_type": self.command_type.value,
            "normalized_query": self.normalized_query,
            "filters": dict(self.filters),
            "requested_scope": self.requested_scope,
        }