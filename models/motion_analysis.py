from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_VIDEO_SOURCE = "skipped_no_video_source"
STATUS_FAILED = "failed"

CLASSIFICATION_STATIC = "static"
CLASSIFICATION_LOW_MOTION = "low_motion"
CLASSIFICATION_MEDIUM_MOTION = "medium_motion"
CLASSIFICATION_HIGH_MOTION = "high_motion"
CLASSIFICATION_DEAD_VISUAL_CANDIDATE = "dead_visual_candidate"

RECOMMENDATION_NONE = "none"
RECOMMENDATION_REVIEW = "review"
RECOMMENDATION_REVIEW_OR_TRIM_DEAD_VISUAL = "review_or_trim_dead_visual"


@dataclass
class MotionPoint:
    time_seconds: float
    frame_index: int | None
    motion_score: float
    raw_motion_value: float
    classification: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_seconds": self.time_seconds,
            "frame_index": self.frame_index,
            "motion_score": self.motion_score,
            "raw_motion_value": self.raw_motion_value,
            "classification": self.classification,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MotionPoint":
        return cls(
            time_seconds=float(data.get("time_seconds", 0.0)),
            frame_index=data.get("frame_index"),
            motion_score=float(data.get("motion_score", 0.0)),
            raw_motion_value=float(data.get("raw_motion_value", 0.0)),
            classification=str(data.get("classification", CLASSIFICATION_STATIC)),
            confidence=float(data.get("confidence", 0.0)),
            metadata=dict(data.get("metadata") or {}),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
        )


@dataclass
class MotionSegment:
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    avg_motion_score: float
    max_motion_score: float
    classification: str
    recommendation: str
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "avg_motion_score": self.avg_motion_score,
            "max_motion_score": self.max_motion_score,
            "classification": self.classification,
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MotionSegment":
        return cls(
            start_seconds=float(data.get("start_seconds", 0.0)),
            end_seconds=float(data.get("end_seconds", 0.0)),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            avg_motion_score=float(data.get("avg_motion_score", 0.0)),
            max_motion_score=float(data.get("max_motion_score", 0.0)),
            classification=str(data.get("classification", CLASSIFICATION_STATIC)),
            recommendation=str(data.get("recommendation", RECOMMENDATION_NONE)),
            metadata=dict(data.get("metadata") or {}),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
        )


@dataclass
class MotionAnalysisResult:
    status: str
    input_path: str
    points: list[MotionPoint] = field(default_factory=list)
    segments: list[MotionSegment] = field(default_factory=list)
    point_count: int = 0
    segment_count: int = 0
    low_motion_segment_count: int = 0
    high_motion_segment_count: int = 0
    dead_visual_candidate_count: int = 0
    duration_seconds: float | None = None
    frame_sample_rate: float = 2.0
    recommendation: str = RECOMMENDATION_NONE
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
    def from_dict(cls, data: dict[str, Any]) -> "MotionAnalysisResult":
        points = [
            MotionPoint.from_dict(point_data)
            for point_data in data.get("points", []) or []
        ]

        segments = [
            MotionSegment.from_dict(segment_data)
            for segment_data in data.get("segments", []) or []
        ]

        duration_seconds = data.get("duration_seconds")
        if duration_seconds is not None:
            duration_seconds = float(duration_seconds)

        return cls(
            status=str(data.get("status", STATUS_FAILED)),
            input_path=str(data.get("input_path", "")),
            points=points,
            segments=segments,
            point_count=int(data.get("point_count", len(points))),
            segment_count=int(data.get("segment_count", len(segments))),
            low_motion_segment_count=int(data.get("low_motion_segment_count", 0)),
            high_motion_segment_count=int(data.get("high_motion_segment_count", 0)),
            dead_visual_candidate_count=int(
                data.get("dead_visual_candidate_count", 0)
            ),
            duration_seconds=duration_seconds,
            frame_sample_rate=float(data.get("frame_sample_rate", 2.0)),
            recommendation=str(data.get("recommendation", RECOMMENDATION_NONE)),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
