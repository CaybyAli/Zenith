from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ENGINE = "universal-moment-debug-report-v1"


def _clamp_score(value: object, fallback: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return round(max(0.0, min(1.0, numeric)), 3)


def _safe_seconds(value: object, fallback: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return round(max(0.0, numeric), 3)


def _clean_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [str(value)]
    try:
        return [str(item) for item in value if str(item)]
    except TypeError:
        return [str(value)]


def _clean_type_counts(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    cleaned: dict[str, int] = {}
    for key, raw_count in value.items():
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            count = 0
        if count > 0:
            cleaned[str(key or "unknown")] = count
    return dict(sorted(cleaned.items(), key=lambda item: (-item[1], item[0])))


@dataclass
class UniversalMomentSegmentDebug:
    segment_id: str = ""
    segment_role: str = "unknown"
    start_time: float = 0.0
    end_time: float = 0.001
    duration_seconds: float = 0.001

    overlapping_windows: int = 0
    dominant_moment_type: str = "unknown"
    top_moment_types: dict[str, int] = field(default_factory=dict)
    avg_moment_score: float = 0.0
    max_moment_score: float = 0.0

    avg_keep_score: float = 0.0
    avg_remove_score: float = 0.0
    avg_cut_risk_score: float = 0.0
    avg_zoom_risk_score: float = 0.0
    avg_private_talk_score: float = 0.0
    avg_boring_score: float = 0.0
    avg_peak_score: float = 0.0
    avg_tension_score: float = 0.0
    avg_post_reaction_score: float = 0.0

    has_keep_signal: bool = False
    has_remove_signal: bool = False
    has_cut_risk: bool = False
    has_zoom_risk: bool = False
    has_private_menu_risk: bool = False
    has_pre_context_need: bool = False
    has_post_context_need: bool = False

    segment_notes: list[str] = field(default_factory=list)
    universal_notes: list[str] = field(default_factory=list)
    diagnosis: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.segment_id = str(self.segment_id or "")
        self.segment_role = str(self.segment_role or "unknown")
        self.start_time = _safe_seconds(self.start_time)
        self.end_time = _safe_seconds(self.end_time, self.start_time + 0.001)
        if self.end_time <= self.start_time:
            self.end_time = round(self.start_time + 0.001, 3)
        self.duration_seconds = round(max(0.001, self.end_time - self.start_time), 3)

        self.overlapping_windows = max(0, int(self.overlapping_windows or 0))
        self.top_moment_types = _clean_type_counts(self.top_moment_types)
        if not self.dominant_moment_type or (
            self.dominant_moment_type == "unknown" and self.top_moment_types
        ):
            self.dominant_moment_type = next(iter(self.top_moment_types), "unknown")
        self.dominant_moment_type = str(self.dominant_moment_type or "unknown")

        for name in _SCORE_FIELDS:
            setattr(self, name, _clamp_score(getattr(self, name, 0.0)))

        self.has_keep_signal = bool(self.has_keep_signal)
        self.has_remove_signal = bool(self.has_remove_signal)
        self.has_cut_risk = bool(self.has_cut_risk)
        self.has_zoom_risk = bool(self.has_zoom_risk)
        self.has_private_menu_risk = bool(self.has_private_menu_risk)
        self.has_pre_context_need = bool(self.has_pre_context_need)
        self.has_post_context_need = bool(self.has_post_context_need)
        self.segment_notes = _clean_string_list(self.segment_notes)
        self.universal_notes = _clean_string_list(self.universal_notes)
        self.diagnosis = _clean_string_list(self.diagnosis)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "segment_id": self.segment_id,
            "segment_role": self.segment_role,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "overlapping_windows": self.overlapping_windows,
            "dominant_moment_type": self.dominant_moment_type,
            "top_moment_types": dict(self.top_moment_types),
            "has_keep_signal": self.has_keep_signal,
            "has_remove_signal": self.has_remove_signal,
            "has_cut_risk": self.has_cut_risk,
            "has_zoom_risk": self.has_zoom_risk,
            "has_private_menu_risk": self.has_private_menu_risk,
            "has_pre_context_need": self.has_pre_context_need,
            "has_post_context_need": self.has_post_context_need,
            "segment_notes": list(self.segment_notes),
            "universal_notes": list(self.universal_notes),
            "diagnosis": list(self.diagnosis),
        }
        for name in _SCORE_FIELDS:
            payload[name] = getattr(self, name)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UniversalMomentSegmentDebug":
        data = dict(data or {})
        kwargs = {name: data.get(name, 0.0) for name in _SCORE_FIELDS}
        return cls(
            segment_id=str(data.get("segment_id", "")),
            segment_role=str(data.get("segment_role", "unknown")),
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", data.get("start_time", 0.0)),
            duration_seconds=data.get("duration_seconds", 0.0),
            overlapping_windows=int(data.get("overlapping_windows", 0) or 0),
            dominant_moment_type=str(data.get("dominant_moment_type", "unknown")),
            top_moment_types=dict(data.get("top_moment_types") or {}),
            has_keep_signal=bool(data.get("has_keep_signal", False)),
            has_remove_signal=bool(data.get("has_remove_signal", False)),
            has_cut_risk=bool(data.get("has_cut_risk", False)),
            has_zoom_risk=bool(data.get("has_zoom_risk", False)),
            has_private_menu_risk=bool(data.get("has_private_menu_risk", False)),
            has_pre_context_need=bool(data.get("has_pre_context_need", False)),
            has_post_context_need=bool(data.get("has_post_context_need", False)),
            segment_notes=list(data.get("segment_notes") or []),
            universal_notes=list(data.get("universal_notes") or []),
            diagnosis=list(data.get("diagnosis") or []),
            **kwargs,
        )


@dataclass
class UniversalMomentDebugReport:
    job_id: str = ""
    engine: str = ENGINE
    segments: list[UniversalMomentSegmentDebug] = field(default_factory=list)
    total_segments: int = 0
    segments_with_cut_risk: int = 0
    segments_with_zoom_risk: int = 0
    segments_with_private_risk: int = 0
    segments_with_remove_signal: int = 0
    segments_with_keep_signal: int = 0
    avg_segment_moment_score: float = 0.0

    def __post_init__(self) -> None:
        self.job_id = str(self.job_id or "")
        self.engine = str(self.engine or ENGINE)
        self.segments = sorted(
            [
                segment
                if isinstance(segment, UniversalMomentSegmentDebug)
                else UniversalMomentSegmentDebug.from_dict(segment)
                for segment in (self.segments or [])
                if isinstance(segment, (UniversalMomentSegmentDebug, dict))
            ],
            key=lambda item: (item.start_time, item.end_time, item.segment_id),
        )
        self.total_segments = len(self.segments)
        self.segments_with_cut_risk = sum(segment.has_cut_risk for segment in self.segments)
        self.segments_with_zoom_risk = sum(segment.has_zoom_risk for segment in self.segments)
        self.segments_with_private_risk = sum(segment.has_private_menu_risk for segment in self.segments)
        self.segments_with_remove_signal = sum(segment.has_remove_signal for segment in self.segments)
        self.segments_with_keep_signal = sum(segment.has_keep_signal for segment in self.segments)
        self.avg_segment_moment_score = _clamp_score(
            sum(segment.avg_moment_score for segment in self.segments) / len(self.segments)
            if self.segments
            else 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "engine": self.engine,
            "segments": [segment.to_dict() for segment in self.segments],
            "total_segments": self.total_segments,
            "segments_with_cut_risk": self.segments_with_cut_risk,
            "segments_with_zoom_risk": self.segments_with_zoom_risk,
            "segments_with_private_risk": self.segments_with_private_risk,
            "segments_with_remove_signal": self.segments_with_remove_signal,
            "segments_with_keep_signal": self.segments_with_keep_signal,
            "avg_segment_moment_score": self.avg_segment_moment_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UniversalMomentDebugReport":
        data = dict(data or {})
        return cls(
            job_id=str(data.get("job_id", "")),
            engine=str(data.get("engine", ENGINE)),
            segments=[
                UniversalMomentSegmentDebug.from_dict(segment)
                for segment in data.get("segments", [])
                if isinstance(segment, dict)
            ],
            total_segments=int(data.get("total_segments", 0) or 0),
            segments_with_cut_risk=int(data.get("segments_with_cut_risk", 0) or 0),
            segments_with_zoom_risk=int(data.get("segments_with_zoom_risk", 0) or 0),
            segments_with_private_risk=int(data.get("segments_with_private_risk", 0) or 0),
            segments_with_remove_signal=int(data.get("segments_with_remove_signal", 0) or 0),
            segments_with_keep_signal=int(data.get("segments_with_keep_signal", 0) or 0),
            avg_segment_moment_score=data.get("avg_segment_moment_score", 0.0),
        )


_SCORE_FIELDS = (
    "avg_moment_score",
    "max_moment_score",
    "avg_keep_score",
    "avg_remove_score",
    "avg_cut_risk_score",
    "avg_zoom_risk_score",
    "avg_private_talk_score",
    "avg_boring_score",
    "avg_peak_score",
    "avg_tension_score",
    "avg_post_reaction_score",
)
