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

REACTION_NONE = "none"
REACTION_NEUTRAL_FACE = "neutral_face"
REACTION_MOUTH_OPEN_CANDIDATE = "mouth_open_candidate"
REACTION_LAUGH_CANDIDATE = "laugh_candidate"
REACTION_SHOCK_CANDIDATE = "shock_candidate"
REACTION_HYPE_CANDIDATE = "hype_candidate"
REACTION_EXPRESSIVE_CANDIDATE = "expressive_reaction_candidate"
REACTION_UNKNOWN = "unknown"

REACTION_TYPE_VALUES = {
    REACTION_NONE,
    REACTION_NEUTRAL_FACE,
    REACTION_MOUTH_OPEN_CANDIDATE,
    REACTION_LAUGH_CANDIDATE,
    REACTION_SHOCK_CANDIDATE,
    REACTION_HYPE_CANDIDATE,
    REACTION_EXPRESSIVE_CANDIDATE,
    REACTION_UNKNOWN,
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


def _safe_reaction_type(value: Any) -> str:
    text = _safe_string(value, REACTION_UNKNOWN).strip()
    if text in REACTION_TYPE_VALUES:
        return text
    return REACTION_UNKNOWN


@dataclass
class FaceReactionPoint:
    time_seconds: float
    frame_index: int | None = None
    face_detected: bool = False
    face_count: int = 0
    primary_face_box: dict[str, Any] = field(default_factory=dict)
    face_area_ratio: float = 0.0
    mouth_open_score: float = 0.0
    eye_open_score: float = 0.0
    expressiveness_score: float = 0.0
    reaction_type: str = REACTION_NONE
    reaction_score: float = 0.0
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_seconds": self.time_seconds,
            "frame_index": self.frame_index,
            "face_detected": self.face_detected,
            "face_count": self.face_count,
            "primary_face_box": dict(self.primary_face_box),
            "face_area_ratio": self.face_area_ratio,
            "mouth_open_score": self.mouth_open_score,
            "eye_open_score": self.eye_open_score,
            "expressiveness_score": self.expressiveness_score,
            "reaction_type": self.reaction_type,
            "reaction_score": self.reaction_score,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "FaceReactionPoint":
        if not isinstance(data, dict):
            data = {}

        return cls(
            time_seconds=_safe_float(data.get("time_seconds"), 0.0),
            frame_index=_safe_optional_int(data.get("frame_index")),
            face_detected=_safe_bool(data.get("face_detected"), False),
            face_count=_safe_int(data.get("face_count"), 0),
            primary_face_box=_safe_dict(data.get("primary_face_box")),
            face_area_ratio=_safe_float(data.get("face_area_ratio"), 0.0),
            mouth_open_score=_safe_float(data.get("mouth_open_score"), 0.0),
            eye_open_score=_safe_float(data.get("eye_open_score"), 0.0),
            expressiveness_score=_safe_float(data.get("expressiveness_score"), 0.0),
            reaction_type=_safe_reaction_type(data.get("reaction_type")),
            reaction_score=_safe_float(data.get("reaction_score"), 0.0),
            confidence=_safe_float(data.get("confidence"), 0.0),
            metadata=_safe_dict(data.get("metadata")),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
        )


@dataclass
class FaceReactionSegment:
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    avg_reaction_score: float
    max_reaction_score: float
    avg_face_area_ratio: float
    reaction_type: str
    recommendation: str
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "avg_reaction_score": self.avg_reaction_score,
            "max_reaction_score": self.max_reaction_score,
            "avg_face_area_ratio": self.avg_face_area_ratio,
            "reaction_type": self.reaction_type,
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "FaceReactionSegment":
        if not isinstance(data, dict):
            data = {}

        return cls(
            start_seconds=_safe_float(data.get("start_seconds"), 0.0),
            end_seconds=_safe_float(data.get("end_seconds"), 0.0),
            duration_seconds=_safe_float(data.get("duration_seconds"), 0.0),
            avg_reaction_score=_safe_float(data.get("avg_reaction_score"), 0.0),
            max_reaction_score=_safe_float(data.get("max_reaction_score"), 0.0),
            avg_face_area_ratio=_safe_float(data.get("avg_face_area_ratio"), 0.0),
            reaction_type=_safe_reaction_type(data.get("reaction_type")),
            recommendation=_safe_string(data.get("recommendation"), "review"),
            metadata=_safe_dict(data.get("metadata")),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
        )


@dataclass
class FaceReactionAnalysisResult:
    status: str
    input_path: str
    points: list[FaceReactionPoint] = field(default_factory=list)
    segments: list[FaceReactionSegment] = field(default_factory=list)
    point_count: int = 0
    segment_count: int = 0
    face_detected_point_count: int = 0
    reaction_candidate_count: int = 0
    high_reaction_segment_count: int = 0
    duration_seconds: float | None = None
    frame_sample_rate: float = 2.0
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
            "face_detected_point_count": self.face_detected_point_count,
            "reaction_candidate_count": self.reaction_candidate_count,
            "high_reaction_segment_count": self.high_reaction_segment_count,
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
    ) -> "FaceReactionAnalysisResult":
        if not isinstance(data, dict):
            data = {}

        points = [
            FaceReactionPoint.from_dict(point_data)
            for point_data in _safe_dict_list(data.get("points"))
        ]
        segments = [
            FaceReactionSegment.from_dict(segment_data)
            for segment_data in _safe_dict_list(data.get("segments"))
        ]

        point_count = _safe_int(data.get("point_count"), len(points))
        segment_count = _safe_int(data.get("segment_count"), len(segments))

        face_detected_point_count = _safe_int(
            data.get("face_detected_point_count"),
            sum(1 for point in points if point.face_detected),
        )
        reaction_candidate_count = _safe_int(
            data.get("reaction_candidate_count"),
            sum(
                1
                for point in points
                if point.reaction_type
                not in {REACTION_NONE, REACTION_NEUTRAL_FACE, REACTION_UNKNOWN}
            ),
        )
        high_reaction_segment_count = _safe_int(
            data.get("high_reaction_segment_count"),
            len(segments),
        )

        return cls(
            status=_safe_status(data.get("status")),
            input_path=_safe_string(data.get("input_path"), ""),
            points=points,
            segments=segments,
            point_count=point_count,
            segment_count=segment_count,
            face_detected_point_count=face_detected_point_count,
            reaction_candidate_count=reaction_candidate_count,
            high_reaction_segment_count=high_reaction_segment_count,
            duration_seconds=_safe_optional_float(data.get("duration_seconds")),
            frame_sample_rate=_safe_float(data.get("frame_sample_rate"), 2.0),
            recommendation=_safe_string(data.get("recommendation"), "review"),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            metadata=_safe_dict(data.get("metadata")),
        )
