from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class JarvisPresence:
    title: str
    subtitle: str
    presence_state: str
    alert_level: str
    focus_label: str
    status_line: str
    workspace_label: str
    actor_label: str
    role_label: str
    is_remote: bool
    highlight_metrics: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "presence_state": self.presence_state,
            "alert_level": self.alert_level,
            "focus_label": self.focus_label,
            "status_line": self.status_line,
            "workspace_label": self.workspace_label,
            "actor_label": self.actor_label,
            "role_label": self.role_label,
            "is_remote": self.is_remote,
            "highlight_metrics": [dict(item) for item in self.highlight_metrics],
        }