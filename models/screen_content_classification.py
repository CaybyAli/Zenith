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

SCREEN_TYPE_GAMEPLAY = "gameplay"
SCREEN_TYPE_MENU = "menu"
SCREEN_TYPE_LOBBY = "lobby"
SCREEN_TYPE_LOADING = "loading"
SCREEN_TYPE_SCOREBOARD = "scoreboard"
SCREEN_TYPE_DEATH_SCREEN = "death_screen"
SCREEN_TYPE_VICTORY_SCREEN = "victory_screen"
SCREEN_TYPE_BLACK_SCREEN = "black_screen"
SCREEN_TYPE_INTRO_OUTRO_CANDIDATE = "intro_outro_candidate"
SCREEN_TYPE_UNKNOWN = "unknown"

SCREEN_TYPE_VALUES = {
    SCREEN_TYPE_GAMEPLAY,
    SCREEN_TYPE_MENU,
    SCREEN_TYPE_LOBBY,
    SCREEN_TYPE_LOADING,
    SCREEN_TYPE_SCOREBOARD,
    SCREEN_TYPE_DEATH_SCREEN,
    SCREEN_TYPE_VICTORY_SCREEN,
    SCREEN_TYPE_BLACK_SCREEN,
    SCREEN_TYPE_INTRO_OUTRO_CANDIDATE,
    SCREEN_TYPE_UNKNOWN,
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


def _safe_screen_type(value: Any) -> str:
    text = _safe_string(value, SCREEN_TYPE_UNKNOWN).strip()
    if text in SCREEN_TYPE_VALUES:
        return text
    return SCREEN_TYPE_UNKNOWN


@dataclass
class ScreenContentPoint:
    time_seconds: float
    frame_index: int | None = None
    screen_type: str = SCREEN_TYPE_UNKNOWN
    confidence: float = 0.0
    brightness_score: float = 0.0
    saturation_score: float = 0.0
    edge_density_score: float = 0.0
    motion_context_score: float = 0.0
    text_like_region_score: float = 0.0
    ui_density_score: float = 0.0
    is_review_candidate: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_seconds": self.time_seconds,
            "frame_index": self.frame_index,
            "screen_type": self.screen_type,
            "confidence": self.confidence,
            "brightness_score": self.brightness_score,
            "saturation_score": self.saturation_score,
            "edge_density_score": self.edge_density_score,
            "motion_context_score": self.motion_context_score,
            "text_like_region_score": self.text_like_region_score,
            "ui_density_score": self.ui_density_score,
            "is_review_candidate": self.is_review_candidate,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ScreenContentPoint":
        if not isinstance(data, dict):
            data = {}

        return cls(
            time_seconds=_safe_float(data.get("time_seconds"), 0.0),
            frame_index=_safe_optional_int(data.get("frame_index")),
            screen_type=_safe_screen_type(data.get("screen_type")),
            confidence=_safe_float(data.get("confidence"), 0.0),
            brightness_score=_safe_float(data.get("brightness_score"), 0.0),
            saturation_score=_safe_float(data.get("saturation_score"), 0.0),
            edge_density_score=_safe_float(data.get("edge_density_score"), 0.0),
            motion_context_score=_safe_float(data.get("motion_context_score"), 0.0),
            text_like_region_score=_safe_float(
                data.get("text_like_region_score"),
                0.0,
            ),
            ui_density_score=_safe_float(data.get("ui_density_score"), 0.0),
            is_review_candidate=_safe_bool(data.get("is_review_candidate"), False),
            metadata=_safe_dict(data.get("metadata")),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
        )


@dataclass
class ScreenContentSegment:
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    screen_type: str = SCREEN_TYPE_UNKNOWN
    avg_confidence: float = 0.0
    max_confidence: float = 0.0
    point_count: int = 0
    recommendation: str = "review_unknown_screen_content"
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "screen_type": self.screen_type,
            "avg_confidence": self.avg_confidence,
            "max_confidence": self.max_confidence,
            "point_count": self.point_count,
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ScreenContentSegment":
        if not isinstance(data, dict):
            data = {}

        return cls(
            start_seconds=_safe_float(data.get("start_seconds"), 0.0),
            end_seconds=_safe_float(data.get("end_seconds"), 0.0),
            duration_seconds=_safe_float(data.get("duration_seconds"), 0.0),
            screen_type=_safe_screen_type(data.get("screen_type")),
            avg_confidence=_safe_float(data.get("avg_confidence"), 0.0),
            max_confidence=_safe_float(data.get("max_confidence"), 0.0),
            point_count=_safe_int(data.get("point_count"), 0),
            recommendation=_safe_string(
                data.get("recommendation"),
                "review_unknown_screen_content",
            ),
            metadata=_safe_dict(data.get("metadata")),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
        )


@dataclass
class ScreenContentClassificationResult:
    status: str
    input_path: str
    points: list[ScreenContentPoint] = field(default_factory=list)
    segments: list[ScreenContentSegment] = field(default_factory=list)
    point_count: int = 0
    segment_count: int = 0
    gameplay_segment_count: int = 0
    menu_segment_count: int = 0
    loading_segment_count: int = 0
    scoreboard_segment_count: int = 0
    death_screen_segment_count: int = 0
    victory_screen_segment_count: int = 0
    black_screen_segment_count: int = 0
    duration_seconds: float | None = None
    frame_sample_rate: float = 2.0
    recommendation: str = "review_unknown_screen_content"
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
            "gameplay_segment_count": self.gameplay_segment_count,
            "menu_segment_count": self.menu_segment_count,
            "loading_segment_count": self.loading_segment_count,
            "scoreboard_segment_count": self.scoreboard_segment_count,
            "death_screen_segment_count": self.death_screen_segment_count,
            "victory_screen_segment_count": self.victory_screen_segment_count,
            "black_screen_segment_count": self.black_screen_segment_count,
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
    ) -> "ScreenContentClassificationResult":
        if not isinstance(data, dict):
            data = {}

        points = [
            ScreenContentPoint.from_dict(point_data)
            for point_data in _safe_dict_list(data.get("points"))
        ]
        segments = [
            ScreenContentSegment.from_dict(segment_data)
            for segment_data in _safe_dict_list(data.get("segments"))
        ]

        return cls(
            status=_safe_status(data.get("status")),
            input_path=_safe_string(data.get("input_path"), ""),
            points=points,
            segments=segments,
            point_count=_safe_int(data.get("point_count"), len(points)),
            segment_count=_safe_int(data.get("segment_count"), len(segments)),
            gameplay_segment_count=_safe_int(
                data.get("gameplay_segment_count"),
                sum(1 for segment in segments if segment.screen_type == SCREEN_TYPE_GAMEPLAY),
            ),
            menu_segment_count=_safe_int(
                data.get("menu_segment_count"),
                sum(
                    1
                    for segment in segments
                    if segment.screen_type in {SCREEN_TYPE_MENU, SCREEN_TYPE_LOBBY}
                ),
            ),
            loading_segment_count=_safe_int(
                data.get("loading_segment_count"),
                sum(1 for segment in segments if segment.screen_type == SCREEN_TYPE_LOADING),
            ),
            scoreboard_segment_count=_safe_int(
                data.get("scoreboard_segment_count"),
                sum(1 for segment in segments if segment.screen_type == SCREEN_TYPE_SCOREBOARD),
            ),
            death_screen_segment_count=_safe_int(
                data.get("death_screen_segment_count"),
                sum(1 for segment in segments if segment.screen_type == SCREEN_TYPE_DEATH_SCREEN),
            ),
            victory_screen_segment_count=_safe_int(
                data.get("victory_screen_segment_count"),
                sum(1 for segment in segments if segment.screen_type == SCREEN_TYPE_VICTORY_SCREEN),
            ),
            black_screen_segment_count=_safe_int(
                data.get("black_screen_segment_count"),
                sum(1 for segment in segments if segment.screen_type == SCREEN_TYPE_BLACK_SCREEN),
            ),
            duration_seconds=_safe_optional_float(data.get("duration_seconds")),
            frame_sample_rate=_safe_float(data.get("frame_sample_rate"), 2.0),
            recommendation=_safe_string(
                data.get("recommendation"),
                "review_unknown_screen_content",
            ),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            metadata=_safe_dict(data.get("metadata")),
        )
