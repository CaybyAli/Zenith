from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


FACE_SOURCE_STATUS_SELECTED = "selected"
FACE_SOURCE_STATUS_SELECTED_FALLBACK = "selected_fallback"
FACE_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE = "skipped_no_video_source"
FACE_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE = "blocked_missing_video_source"
FACE_SOURCE_STATUS_FAILED = "failed"

FACE_SELECTED_TYPE_RAW_VIDEO_PATH = "raw_video_path"
FACE_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH = "preprocessing_source_path"
FACE_SELECTED_TYPE_FALLBACK_VIDEO_PATH = "fallback_video_path"
FACE_SELECTED_TYPE_NONE = "none"


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


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _safe_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return [str(value)]


def _safe_checked_sources(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


@dataclass
class FaceReactionSourceSelection:
    status: str
    selected_path: str | None = None
    selected_type: str | None = FACE_SELECTED_TYPE_NONE
    checked_sources: list[dict[str, Any]] = field(default_factory=list)
    source_exists: bool = False
    recommendation: str = "review"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "selected_path": self.selected_path,
            "selected_type": self.selected_type,
            "checked_sources": [dict(item) for item in self.checked_sources],
            "source_exists": self.source_exists,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "FaceReactionSourceSelection":
        if not isinstance(data, dict):
            data = {}

        return cls(
            status=_safe_string(data.get("status"), FACE_SOURCE_STATUS_FAILED),
            selected_path=_safe_optional_string(data.get("selected_path")),
            selected_type=_safe_optional_string(data.get("selected_type"))
            or FACE_SELECTED_TYPE_NONE,
            checked_sources=_safe_checked_sources(data.get("checked_sources")),
            source_exists=_safe_bool(data.get("source_exists"), False),
            recommendation=_safe_string(data.get("recommendation"), "review"),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            metadata=_safe_dict(data.get("metadata")),
        )
