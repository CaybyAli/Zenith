from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_VIDEO_SOURCE = "skipped_no_video_source"
STATUS_FAILED = "failed"

STATUS_VALUES = {
    STATUS_OK,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_SKIPPED_NO_VIDEO_SOURCE,
    STATUS_FAILED,
}

CLASSIFICATION_NORMAL_FRAME = "normal_frame"
CLASSIFICATION_DUPLICATE_FRAME_CANDIDATE = "duplicate_frame_candidate"
CLASSIFICATION_STUTTER_SEGMENT = "stutter_segment"
CLASSIFICATION_FREEZE_SEGMENT = "freeze_segment"
CLASSIFICATION_ENCODING_DROP_CANDIDATE = "encoding_drop_candidate"
CLASSIFICATION_UNKNOWN = "unknown"

CLASSIFICATION_VALUES = {
    CLASSIFICATION_NORMAL_FRAME,
    CLASSIFICATION_DUPLICATE_FRAME_CANDIDATE,
    CLASSIFICATION_STUTTER_SEGMENT,
    CLASSIFICATION_FREEZE_SEGMENT,
    CLASSIFICATION_ENCODING_DROP_CANDIDATE,
    CLASSIFICATION_UNKNOWN,
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


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


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


def _safe_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _safe_status(value: Any) -> str:
    text = _safe_string(value, STATUS_FAILED).strip()
    if text in STATUS_VALUES:
        return text
    return STATUS_FAILED


def _safe_classification(value: Any) -> str:
    text = _safe_string(value, CLASSIFICATION_UNKNOWN).strip()
    if text in CLASSIFICATION_VALUES:
        return text
    return CLASSIFICATION_UNKNOWN


@dataclass
class StutterFramePoint:
    time_seconds: float
    frame_index: int | None = None
    frame_hash: str = ""
    previous_frame_hash: str | None = None
    duplicate_score: float = 0.0
    difference_score: float = 1.0
    is_duplicate_candidate: bool = False
    classification: str = CLASSIFICATION_NORMAL_FRAME
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_seconds": self.time_seconds,
            "frame_index": self.frame_index,
            "frame_hash": self.frame_hash,
            "previous_frame_hash": self.previous_frame_hash,
            "duplicate_score": self.duplicate_score,
            "difference_score": self.difference_score,
            "is_duplicate_candidate": self.is_duplicate_candidate,
            "classification": self.classification,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "StutterFramePoint":
        if not isinstance(data, dict):
            data = {}

        return cls(
            time_seconds=_safe_float(data.get("time_seconds"), 0.0),
            frame_index=_safe_optional_int(data.get("frame_index")),
            frame_hash=_safe_string(data.get("frame_hash"), ""),
            previous_frame_hash=(
                _safe_string(data.get("previous_frame_hash"))
                if data.get("previous_frame_hash") is not None
                else None
            ),
            duplicate_score=_safe_float(data.get("duplicate_score"), 0.0),
            difference_score=_safe_float(data.get("difference_score"), 1.0),
            is_duplicate_candidate=_safe_bool(
                data.get("is_duplicate_candidate"),
                False,
            ),
            classification=_safe_classification(data.get("classification")),
            confidence=_safe_float(data.get("confidence"), 0.0),
            metadata=_safe_dict(data.get("metadata")),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
        )


@dataclass
class StutterSegment:
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    start_frame_index: int | None = None
    end_frame_index: int | None = None
    duplicate_frame_count: int = 0
    avg_duplicate_score: float = 0.0
    max_duplicate_score: float = 0.0
    classification: str = CLASSIFICATION_UNKNOWN
    recommendation: str = "review"
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "start_frame_index": self.start_frame_index,
            "end_frame_index": self.end_frame_index,
            "duplicate_frame_count": self.duplicate_frame_count,
            "avg_duplicate_score": self.avg_duplicate_score,
            "max_duplicate_score": self.max_duplicate_score,
            "classification": self.classification,
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "StutterSegment":
        if not isinstance(data, dict):
            data = {}

        return cls(
            start_seconds=_safe_float(data.get("start_seconds"), 0.0),
            end_seconds=_safe_float(data.get("end_seconds"), 0.0),
            duration_seconds=_safe_float(data.get("duration_seconds"), 0.0),
            start_frame_index=_safe_optional_int(data.get("start_frame_index")),
            end_frame_index=_safe_optional_int(data.get("end_frame_index")),
            duplicate_frame_count=_safe_int(data.get("duplicate_frame_count"), 0),
            avg_duplicate_score=_safe_float(data.get("avg_duplicate_score"), 0.0),
            max_duplicate_score=_safe_float(data.get("max_duplicate_score"), 0.0),
            classification=_safe_classification(data.get("classification")),
            recommendation=_safe_string(data.get("recommendation"), "review"),
            metadata=_safe_dict(data.get("metadata")),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
        )


@dataclass
class StutterDetectionResult:
    status: str
    input_path: str
    points: list[StutterFramePoint] = field(default_factory=list)
    segments: list[StutterSegment] = field(default_factory=list)
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
            "input_path": self.input_path,
            "points": [point.to_dict() for point in self.points],
            "segments": [segment.to_dict() for segment in self.segments],
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
    ) -> "StutterDetectionResult":
        if not isinstance(data, dict):
            data = {}

        points = [
            StutterFramePoint.from_dict(point_data)
            for point_data in _safe_dict_list(data.get("points"))
        ]
        segments = [
            StutterSegment.from_dict(segment_data)
            for segment_data in _safe_dict_list(data.get("segments"))
        ]

        return cls(
            status=_safe_status(data.get("status")),
            input_path=_safe_string(data.get("input_path"), ""),
            points=points,
            segments=segments,
            point_count=_safe_int(data.get("point_count"), len(points)),
            segment_count=_safe_int(data.get("segment_count"), len(segments)),
            duplicate_candidate_count=_safe_int(
                data.get("duplicate_candidate_count"),
                sum(1 for point in points if point.is_duplicate_candidate),
            ),
            stutter_segment_count=_safe_int(
                data.get("stutter_segment_count"),
                sum(
                    1
                    for segment in segments
                    if segment.classification == CLASSIFICATION_STUTTER_SEGMENT
                ),
            ),
            freeze_segment_count=_safe_int(
                data.get("freeze_segment_count"),
                sum(
                    1
                    for segment in segments
                    if segment.classification == CLASSIFICATION_FREEZE_SEGMENT
                ),
            ),
            duration_seconds=_safe_optional_float(data.get("duration_seconds")),
            frame_sample_rate=_safe_float(data.get("frame_sample_rate"), 10.0),
            recommendation=_safe_string(data.get("recommendation"), "review"),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            metadata=_safe_dict(data.get("metadata")),
        )
