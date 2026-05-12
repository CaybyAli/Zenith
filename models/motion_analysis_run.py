from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.motion_analysis import MotionAnalysisResult
from models.motion_analysis_source import MotionAnalysisSourceSelection


MOTION_RUN_STATUS_OK = "ok"
MOTION_RUN_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
MOTION_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE = "skipped_no_video_source"
MOTION_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE = "blocked_missing_video_source"
MOTION_RUN_STATUS_FAILED = "failed"


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
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
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

    items: list[dict[str, Any]] = []

    for item in value:
        if isinstance(item, dict):
            items.append(dict(item))

    return items


@dataclass
class MotionAnalysisRunReport:
    status: str
    source: str = "motion_analysis_runner"
    source_selection: MotionAnalysisSourceSelection | None = None
    selected_path: str | None = None
    selected_type: str | None = None
    motion_analysis_result: MotionAnalysisResult | None = None
    motion_points: list[dict[str, Any]] = field(default_factory=list)
    motion_segments: list[dict[str, Any]] = field(default_factory=list)
    point_count: int = 0
    segment_count: int = 0
    low_motion_segment_count: int = 0
    high_motion_segment_count: int = 0
    dead_visual_candidate_count: int = 0
    duration_seconds: float | None = None
    frame_sample_rate: float = 2.0
    recommendation: str = "none"
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
            "motion_analysis_result": (
                self.motion_analysis_result.to_dict()
                if self.motion_analysis_result
                else None
            ),
            "motion_points": [dict(item) for item in self.motion_points],
            "motion_segments": [dict(item) for item in self.motion_segments],
            "point_count": self.point_count,
            "segment_count": self.segment_count,
            "low_motion_segment_count": self.low_motion_segment_count,
            "high_motion_segment_count": self.high_motion_segment_count,
            "dead_visual_candidate_count": self.dead_visual_candidate_count,
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
    ) -> "MotionAnalysisRunReport":
        if not isinstance(data, dict):
            data = {}

        source_selection_data = data.get("source_selection")
        source_selection = None
        if isinstance(source_selection_data, dict):
            source_selection = MotionAnalysisSourceSelection.from_dict(
                source_selection_data
            )

        motion_analysis_result_data = data.get("motion_analysis_result")
        motion_analysis_result = None
        if isinstance(motion_analysis_result_data, dict):
            motion_analysis_result = MotionAnalysisResult.from_dict(
                motion_analysis_result_data
            )

        return cls(
            status=_safe_string(data.get("status"), MOTION_RUN_STATUS_FAILED),
            source=_safe_string(data.get("source"), "motion_analysis_runner"),
            source_selection=source_selection,
            selected_path=_safe_optional_string(data.get("selected_path")),
            selected_type=_safe_optional_string(data.get("selected_type")),
            motion_analysis_result=motion_analysis_result,
            motion_points=_safe_dict_list(data.get("motion_points")),
            motion_segments=_safe_dict_list(data.get("motion_segments")),
            point_count=_safe_int(data.get("point_count"), 0),
            segment_count=_safe_int(data.get("segment_count"), 0),
            low_motion_segment_count=_safe_int(
                data.get("low_motion_segment_count"),
                0,
            ),
            high_motion_segment_count=_safe_int(
                data.get("high_motion_segment_count"),
                0,
            ),
            dead_visual_candidate_count=_safe_int(
                data.get("dead_visual_candidate_count"),
                0,
            ),
            duration_seconds=_safe_optional_float(data.get("duration_seconds")),
            frame_sample_rate=_safe_float(data.get("frame_sample_rate"), 2.0),
            recommendation=_safe_string(data.get("recommendation"), "none"),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            metadata=_safe_dict(data.get("metadata")),
        )
