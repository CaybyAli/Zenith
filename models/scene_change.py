from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SCENE_STATUS_OK = "ok"
SCENE_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
SCENE_STATUS_SKIPPED_NO_VIDEO_SOURCE = "skipped_no_video_source"
SCENE_STATUS_FAILED = "failed"

SCENE_STATUS_VALUES = {
    SCENE_STATUS_OK,
    SCENE_STATUS_COMPLETED_WITH_WARNINGS,
    SCENE_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    SCENE_STATUS_FAILED,
}

CHANGE_TYPE_HARD = "hard_scene_change"
CHANGE_TYPE_SOFT = "soft_transition"
CHANGE_TYPE_FLASH = "flash_or_explosion_candidate"
CHANGE_TYPE_UNKNOWN = "unknown_scene_change"

CHANGE_TYPE_VALUES = {
    CHANGE_TYPE_HARD,
    CHANGE_TYPE_SOFT,
    CHANGE_TYPE_FLASH,
    CHANGE_TYPE_UNKNOWN,
}


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


def _safe_optional_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _safe_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


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


def _safe_change_type(value: Any) -> str:
    text = _safe_string(value, CHANGE_TYPE_UNKNOWN).strip()
    if text in CHANGE_TYPE_VALUES:
        return text
    return CHANGE_TYPE_UNKNOWN


def _safe_status(value: Any) -> str:
    text = _safe_string(value, SCENE_STATUS_FAILED).strip()
    if text in SCENE_STATUS_VALUES:
        return text
    return SCENE_STATUS_FAILED


@dataclass
class SceneChangePoint:
    time_seconds: float
    frame_index: int | None = None
    scene_score: float = 0.0
    change_type: str = CHANGE_TYPE_UNKNOWN
    confidence: float = 0.0
    is_false_positive_candidate: bool = False
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_seconds": self.time_seconds,
            "frame_index": self.frame_index,
            "scene_score": self.scene_score,
            "change_type": self.change_type,
            "confidence": self.confidence,
            "is_false_positive_candidate": self.is_false_positive_candidate,
            "reason": self.reason,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SceneChangePoint":
        if not isinstance(data, dict):
            data = {}

        return cls(
            time_seconds=_safe_float(data.get("time_seconds"), 0.0),
            frame_index=_safe_optional_int(data.get("frame_index")),
            scene_score=_safe_float(data.get("scene_score"), 0.0),
            change_type=_safe_change_type(data.get("change_type")),
            confidence=_safe_float(data.get("confidence"), 0.0),
            is_false_positive_candidate=_safe_bool(
                data.get("is_false_positive_candidate"), False
            ),
            reason=_safe_string(data.get("reason"), ""),
            metadata=_safe_dict(data.get("metadata")),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
        )


@dataclass
class SceneChangeResult:
    status: str
    input_path: str
    scene_changes: list[SceneChangePoint] = field(default_factory=list)
    scene_change_count: int = 0
    hard_change_count: int = 0
    soft_transition_count: int = 0
    false_positive_candidate_count: int = 0
    threshold: float = 0.30
    duration_seconds: float | None = None
    recommendation: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "input_path": self.input_path,
            "scene_changes": [point.to_dict() for point in self.scene_changes],
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
    def from_dict(cls, data: dict[str, Any] | None) -> "SceneChangeResult":
        if not isinstance(data, dict):
            data = {}

        raw_points = data.get("scene_changes")
        scene_changes: list[SceneChangePoint] = []
        if isinstance(raw_points, list):
            scene_changes = [
                SceneChangePoint.from_dict(item)
                for item in raw_points
                if isinstance(item, dict)
            ]

        scene_change_count = _safe_optional_int(data.get("scene_change_count"))
        if scene_change_count is None:
            scene_change_count = len(scene_changes)

        hard_change_count = _safe_optional_int(data.get("hard_change_count"))
        if hard_change_count is None:
            hard_change_count = sum(
                1 for point in scene_changes if point.change_type == CHANGE_TYPE_HARD
            )

        soft_transition_count = _safe_optional_int(data.get("soft_transition_count"))
        if soft_transition_count is None:
            soft_transition_count = sum(
                1 for point in scene_changes if point.change_type == CHANGE_TYPE_SOFT
            )

        false_positive_candidate_count = _safe_optional_int(
            data.get("false_positive_candidate_count")
        )
        if false_positive_candidate_count is None:
            false_positive_candidate_count = sum(
                1 for point in scene_changes if point.is_false_positive_candidate
            )

        return cls(
            status=_safe_status(data.get("status")),
            input_path=_safe_string(data.get("input_path"), ""),
            scene_changes=scene_changes,
            scene_change_count=scene_change_count,
            hard_change_count=hard_change_count,
            soft_transition_count=soft_transition_count,
            false_positive_candidate_count=false_positive_candidate_count,
            threshold=_safe_float(data.get("threshold"), 0.30),
            duration_seconds=_safe_optional_float(data.get("duration_seconds")),
            recommendation=_safe_string(data.get("recommendation"), ""),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            metadata=_safe_dict(data.get("metadata")),
        )
