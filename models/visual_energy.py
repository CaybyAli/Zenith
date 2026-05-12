from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_VISUAL_SOURCES = "skipped_no_visual_sources"
STATUS_FAILED = "failed"

STATUS_VALUES = {
    STATUS_OK,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_SKIPPED_NO_VISUAL_SOURCES,
    STATUS_FAILED,
}

CLASSIFICATION_LOW_VISUAL_ENERGY = "low_visual_energy"
CLASSIFICATION_MEDIUM_VISUAL_ENERGY = "medium_visual_energy"
CLASSIFICATION_HIGH_VISUAL_ENERGY = "high_visual_energy"
CLASSIFICATION_PEAK_VISUAL_ENERGY = "peak_visual_energy"
CLASSIFICATION_TECHNICAL_WARNING = "technical_warning"
CLASSIFICATION_UNKNOWN = "unknown"

CLASSIFICATION_VALUES = {
    CLASSIFICATION_LOW_VISUAL_ENERGY,
    CLASSIFICATION_MEDIUM_VISUAL_ENERGY,
    CLASSIFICATION_HIGH_VISUAL_ENERGY,
    CLASSIFICATION_PEAK_VISUAL_ENERGY,
    CLASSIFICATION_TECHNICAL_WARNING,
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
class VisualEnergyPoint:
    time_seconds: float = 0.0
    visual_energy_score: float = 0.0
    motion_score: float = 0.0
    face_reaction_score: float = 0.0
    screen_content_score: float = 0.0
    scene_change_score: float = 0.0
    stutter_penalty_score: float = 0.0
    combined_video_score: float = 0.0
    classification: str = CLASSIFICATION_UNKNOWN
    confidence: float = 0.0
    source_counts: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_seconds": self.time_seconds,
            "visual_energy_score": self.visual_energy_score,
            "motion_score": self.motion_score,
            "face_reaction_score": self.face_reaction_score,
            "screen_content_score": self.screen_content_score,
            "scene_change_score": self.scene_change_score,
            "stutter_penalty_score": self.stutter_penalty_score,
            "combined_video_score": self.combined_video_score,
            "classification": self.classification,
            "confidence": self.confidence,
            "source_counts": dict(self.source_counts),
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "VisualEnergyPoint":
        if not isinstance(data, dict):
            data = {}

        return cls(
            time_seconds=_safe_float(data.get("time_seconds"), 0.0),
            visual_energy_score=_safe_float(data.get("visual_energy_score"), 0.0),
            motion_score=_safe_float(data.get("motion_score"), 0.0),
            face_reaction_score=_safe_float(data.get("face_reaction_score"), 0.0),
            screen_content_score=_safe_float(data.get("screen_content_score"), 0.0),
            scene_change_score=_safe_float(data.get("scene_change_score"), 0.0),
            stutter_penalty_score=_safe_float(data.get("stutter_penalty_score"), 0.0),
            combined_video_score=_safe_float(data.get("combined_video_score"), 0.0),
            classification=_safe_classification(data.get("classification")),
            confidence=_safe_float(data.get("confidence"), 0.0),
            source_counts=_safe_dict(data.get("source_counts")),
            metadata=_safe_dict(data.get("metadata")),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
        )


@dataclass
class VisualEnergySegment:
    start_seconds: float = 0.0
    end_seconds: float = 0.0
    duration_seconds: float = 0.0
    avg_visual_energy_score: float = 0.0
    max_visual_energy_score: float = 0.0
    min_visual_energy_score: float = 0.0
    classification: str = CLASSIFICATION_UNKNOWN
    recommendation: str = "review_unknown_visual_energy"
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "avg_visual_energy_score": self.avg_visual_energy_score,
            "max_visual_energy_score": self.max_visual_energy_score,
            "min_visual_energy_score": self.min_visual_energy_score,
            "classification": self.classification,
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "VisualEnergySegment":
        if not isinstance(data, dict):
            data = {}

        return cls(
            start_seconds=_safe_float(data.get("start_seconds"), 0.0),
            end_seconds=_safe_float(data.get("end_seconds"), 0.0),
            duration_seconds=_safe_float(data.get("duration_seconds"), 0.0),
            avg_visual_energy_score=_safe_float(
                data.get("avg_visual_energy_score"),
                0.0,
            ),
            max_visual_energy_score=_safe_float(
                data.get("max_visual_energy_score"),
                0.0,
            ),
            min_visual_energy_score=_safe_float(
                data.get("min_visual_energy_score"),
                0.0,
            ),
            classification=_safe_classification(data.get("classification")),
            recommendation=_safe_string(
                data.get("recommendation"),
                "review_unknown_visual_energy",
            ),
            metadata=_safe_dict(data.get("metadata")),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
        )


@dataclass
class VisualEnergyResult:
    status: str = STATUS_FAILED
    points: list[VisualEnergyPoint] = field(default_factory=list)
    segments: list[VisualEnergySegment] = field(default_factory=list)
    point_count: int = 0
    segment_count: int = 0
    high_energy_segment_count: int = 0
    low_energy_segment_count: int = 0
    technical_warning_segment_count: int = 0
    duration_seconds: float | None = None
    frame_sample_rate: float = 2.0
    recommendation: str = "review_unknown_visual_energy"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "points": [point.to_dict() for point in self.points],
            "segments": [segment.to_dict() for segment in self.segments],
            "point_count": self.point_count,
            "segment_count": self.segment_count,
            "high_energy_segment_count": self.high_energy_segment_count,
            "low_energy_segment_count": self.low_energy_segment_count,
            "technical_warning_segment_count": self.technical_warning_segment_count,
            "duration_seconds": self.duration_seconds,
            "frame_sample_rate": self.frame_sample_rate,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "VisualEnergyResult":
        if not isinstance(data, dict):
            data = {}

        points = [
            VisualEnergyPoint.from_dict(point_data)
            for point_data in _safe_dict_list(data.get("points"))
        ]
        segments = [
            VisualEnergySegment.from_dict(segment_data)
            for segment_data in _safe_dict_list(data.get("segments"))
        ]

        return cls(
            status=_safe_status(data.get("status")),
            points=points,
            segments=segments,
            point_count=_safe_int(data.get("point_count"), len(points)),
            segment_count=_safe_int(data.get("segment_count"), len(segments)),
            high_energy_segment_count=_safe_int(
                data.get("high_energy_segment_count"),
                sum(
                    1
                    for segment in segments
                    if segment.classification
                    in {
                        CLASSIFICATION_HIGH_VISUAL_ENERGY,
                        CLASSIFICATION_PEAK_VISUAL_ENERGY,
                    }
                ),
            ),
            low_energy_segment_count=_safe_int(
                data.get("low_energy_segment_count"),
                sum(
                    1
                    for segment in segments
                    if segment.classification == CLASSIFICATION_LOW_VISUAL_ENERGY
                ),
            ),
            technical_warning_segment_count=_safe_int(
                data.get("technical_warning_segment_count"),
                sum(
                    1
                    for segment in segments
                    if segment.classification == CLASSIFICATION_TECHNICAL_WARNING
                ),
            ),
            duration_seconds=_safe_optional_float(data.get("duration_seconds")),
            frame_sample_rate=_safe_float(data.get("frame_sample_rate"), 2.0),
            recommendation=_safe_string(
                data.get("recommendation"),
                "review_unknown_visual_energy",
            ),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            metadata=_safe_dict(data.get("metadata")),
        )
