from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.stutter_detection import StutterDetectionResult
from models.stutter_detection_source import StutterDetectionSourceSelection


STUTTER_RUN_STATUS_OK = "ok"
STUTTER_RUN_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STUTTER_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE = "skipped_no_video_source"
STUTTER_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE = "blocked_missing_video_source"
STUTTER_RUN_STATUS_FAILED = "failed"


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


def _safe_optional_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


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
    return [dict(item) for item in value if isinstance(item, dict)]


@dataclass
class StutterDetectionRunReport:
    status: str
    source: str = "stutter_detection_runner"
    source_selection: StutterDetectionSourceSelection | None = None
    selected_path: str | None = None
    selected_type: str | None = None
    stutter_detection_result: StutterDetectionResult | None = None
    stutter_points: list[dict[str, Any]] = field(default_factory=list)
    stutter_segments: list[dict[str, Any]] = field(default_factory=list)
    point_count: int = 0
    segment_count: int = 0
    duplicate_candidate_count: int = 0
    stutter_segment_count: int = 0
    freeze_segment_count: int = 0
    duration_seconds: float | None = None
    frame_sample_rate: float = 10.0
    recommendation: str = "review"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "source_selection": (
                self.source_selection.to_dict() if self.source_selection else None
            ),
            "selected_path": self.selected_path,
            "selected_type": self.selected_type,
            "stutter_detection_result": (
                self.stutter_detection_result.to_dict()
                if self.stutter_detection_result
                else None
            ),
            "stutter_points": [dict(item) for item in self.stutter_points],
            "stutter_segments": [dict(item) for item in self.stutter_segments],
            "point_count": self.point_count,
            "segment_count": self.segment_count,
            "duplicate_candidate_count": self.duplicate_candidate_count,
            "stutter_segment_count": self.stutter_segment_count,
            "freeze_segment_count": self.freeze_segment_count,
            "duration_seconds": self.duration_seconds,
            "frame_sample_rate": self.frame_sample_rate,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "StutterDetectionRunReport":
        if not isinstance(data, dict):
            data = {}

        source_selection_data = data.get("source_selection")
        source_selection = None
        if isinstance(source_selection_data, dict):
            source_selection = StutterDetectionSourceSelection.from_dict(
                source_selection_data
            )

        stutter_detection_result_data = data.get("stutter_detection_result")
        stutter_detection_result = None
        if isinstance(stutter_detection_result_data, dict):
            stutter_detection_result = StutterDetectionResult.from_dict(
                stutter_detection_result_data
            )

        return cls(
            status=_safe_string(data.get("status"), STUTTER_RUN_STATUS_FAILED),
            source=_safe_string(data.get("source"), "stutter_detection_runner"),
            source_selection=source_selection,
            selected_path=_safe_optional_string(data.get("selected_path")),
            selected_type=_safe_optional_string(data.get("selected_type")),
            stutter_detection_result=stutter_detection_result,
            stutter_points=_safe_dict_list(data.get("stutter_points")),
            stutter_segments=_safe_dict_list(data.get("stutter_segments")),
            point_count=_safe_int(data.get("point_count"), 0),
            segment_count=_safe_int(data.get("segment_count"), 0),
            duplicate_candidate_count=_safe_int(
                data.get("duplicate_candidate_count"),
                0,
            ),
            stutter_segment_count=_safe_int(
                data.get("stutter_segment_count"),
                0,
            ),
            freeze_segment_count=_safe_int(data.get("freeze_segment_count"), 0),
            duration_seconds=_safe_optional_float(data.get("duration_seconds")),
            frame_sample_rate=_safe_float(data.get("frame_sample_rate"), 10.0),
            recommendation=_safe_string(data.get("recommendation"), "review"),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            metadata=_safe_dict(data.get("metadata")),
        )
