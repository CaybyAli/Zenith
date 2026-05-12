from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _safe_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_optional_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return [str(value)]


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _safe_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            result.append(dict(item))
    return result


@dataclass
class SceneChangeRunReport:
    status: str
    source: str = "scene_change_runner"
    source_selection: dict[str, Any] = field(default_factory=dict)
    selected_path: str | None = None
    selected_type: str | None = None
    scene_change_result: dict[str, Any] = field(default_factory=dict)
    scene_changes: list[dict[str, Any]] = field(default_factory=list)
    scene_change_count: int = 0
    hard_change_count: int = 0
    soft_transition_count: int = 0
    false_positive_candidate_count: int = 0
    threshold: float = 0.30
    duration_seconds: float | None = None
    recommendation: str = "review"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "source_selection": dict(self.source_selection),
            "selected_path": self.selected_path,
            "selected_type": self.selected_type,
            "scene_change_result": dict(self.scene_change_result),
            "scene_changes": [dict(sc) for sc in self.scene_changes],
            "scene_change_count": self.scene_change_count,
            "hard_change_count": self.hard_change_count,
            "soft_transition_count": self.soft_transition_count,
            "false_positive_candidate_count": self.false_positive_candidate_count,
            "threshold": self.threshold,
            "duration_seconds": self.duration_seconds,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SceneChangeRunReport":
        if not isinstance(data, dict):
            data = {}
        return cls(
            status=_safe_string(data.get("status"), "failed"),
            source=_safe_string(data.get("source"), "scene_change_runner"),
            source_selection=_safe_dict(data.get("source_selection")),
            selected_path=_safe_optional_string(data.get("selected_path")),
            selected_type=_safe_optional_string(data.get("selected_type")),
            scene_change_result=_safe_dict(data.get("scene_change_result")),
            scene_changes=_safe_dict_list(data.get("scene_changes")),
            scene_change_count=_safe_int(data.get("scene_change_count"), 0),
            hard_change_count=_safe_int(data.get("hard_change_count"), 0),
            soft_transition_count=_safe_int(data.get("soft_transition_count"), 0),
            false_positive_candidate_count=_safe_int(
                data.get("false_positive_candidate_count"), 0
            ),
            threshold=_safe_float(data.get("threshold"), 0.30),
            duration_seconds=_safe_optional_float(data.get("duration_seconds")),
            recommendation=_safe_string(data.get("recommendation"), "review"),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            metadata=_safe_dict(data.get("metadata")),
        )
