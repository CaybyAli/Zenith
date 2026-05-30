from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping


PLAY_SEGMENT_STATES = (
    "intro_menu_lobby",
    "active_play",
    "transition_dead_time",
    "replay_break",
    "unknown",
)

PLAY_SEGMENT_INTENSITIES = (
    "low",
    "medium",
    "high",
    "unknown",
)

IDLE_OR_MENU_STATES = (
    "intro_menu_lobby",
    "transition_dead_time",
    "replay_break",
    "unknown",
)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def validate_play_segment_state(state: str) -> str:
    if state not in PLAY_SEGMENT_STATES:
        raise ValueError(f"invalid play segment state: {state!r}")
    return state


def validate_play_segment_intensity(intensity: str) -> str:
    if intensity not in PLAY_SEGMENT_INTENSITIES:
        raise ValueError(f"invalid play segment intensity: {intensity!r}")
    return intensity


@dataclass(frozen=True)
class PlaySignalWindow:
    start_seconds: float
    end_seconds: float
    motion_score: float
    audio_activity: float
    audio_peak_score: float
    scene_change_score: float
    visual_stability: float
    edge_stability: float
    color_stability: float
    state: str
    intensity: str
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        return max(0.0, self.end_seconds - self.start_seconds)

    def to_dict(self) -> Dict[str, Any]:
        validate_play_segment_state(self.state)
        validate_play_segment_intensity(self.intensity)
        return {
            "start_seconds": round(float(self.start_seconds), 3),
            "end_seconds": round(float(self.end_seconds), 3),
            "duration_seconds": round(float(self.duration_seconds), 3),
            "motion_score": round(clamp01(self.motion_score), 4),
            "audio_activity": round(clamp01(self.audio_activity), 4),
            "audio_peak_score": round(clamp01(self.audio_peak_score), 4),
            "scene_change_score": round(clamp01(self.scene_change_score), 4),
            "visual_stability": round(clamp01(self.visual_stability), 4),
            "edge_stability": round(clamp01(self.edge_stability), 4),
            "color_stability": round(clamp01(self.color_stability), 4),
            "state": self.state,
            "intensity": self.intensity,
            "confidence": round(clamp01(self.confidence), 4),
            "evidence": dict(self.evidence),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class PlaySegment:
    start_seconds: float
    end_seconds: float
    state: str
    intensity: str
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    source_signal_counts: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        return max(0.0, self.end_seconds - self.start_seconds)

    def to_dict(self) -> Dict[str, Any]:
        validate_play_segment_state(self.state)
        validate_play_segment_intensity(self.intensity)
        return {
            "start_seconds": round(float(self.start_seconds), 3),
            "end_seconds": round(float(self.end_seconds), 3),
            "duration_seconds": round(float(self.duration_seconds), 3),
            "state": self.state,
            "intensity": self.intensity,
            "confidence": round(clamp01(self.confidence), 4),
            "evidence": dict(self.evidence),
            "source_signal_counts": dict(self.source_signal_counts),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class PlaySegmentDetectionResult:
    video_path: str
    video_duration_seconds: float
    analyzed_duration_seconds: float
    window_seconds: float
    taxonomy: List[str]
    intensity_values: List[str]
    raw_windows: List[PlaySignalWindow]
    segments: List[PlaySegment]
    review_candidates: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self, include_raw_windows: bool = False) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "video_path": self.video_path,
            "video_duration_seconds": round(float(self.video_duration_seconds), 3),
            "analyzed_duration_seconds": round(float(self.analyzed_duration_seconds), 3),
            "window_seconds": round(float(self.window_seconds), 3),
            "taxonomy": list(self.taxonomy),
            "intensity_values": list(self.intensity_values),
            "segments": [segment.to_dict() for segment in self.segments],
            "review_candidates": self.review_candidates,
            "warnings": list(self.warnings),
        }
        if include_raw_windows:
            data["raw_windows"] = [window.to_dict() for window in self.raw_windows]
        return data


def duration_by_state(
    segments: List[PlaySegment],
    start_seconds: float,
    end_seconds: float,
) -> Dict[str, float]:
    totals: Dict[str, float] = {state: 0.0 for state in PLAY_SEGMENT_STATES}
    for segment in segments:
        overlap_start = max(float(start_seconds), segment.start_seconds)
        overlap_end = min(float(end_seconds), segment.end_seconds)
        overlap = max(0.0, overlap_end - overlap_start)
        if overlap > 0:
            totals[segment.state] = totals.get(segment.state, 0.0) + overlap
    return totals


def dominant_state(
    segments: List[PlaySegment],
    start_seconds: float,
    end_seconds: float,
) -> str:
    totals = duration_by_state(segments, start_seconds, end_seconds)
    if not totals:
        return "unknown"
    return max(totals.items(), key=lambda item: item[1])[0]


def active_vs_idle_menu_share(
    segments: List[PlaySegment],
    start_seconds: float,
    end_seconds: float,
    exclude_ranges: List[Mapping[str, float]] | None = None,
) -> Dict[str, float]:
    exclude_ranges = list(exclude_ranges or [])
    active_seconds = 0.0
    idle_menu_seconds = 0.0

    for segment in segments:
        pieces = [(max(start_seconds, segment.start_seconds), min(end_seconds, segment.end_seconds))]
        for excluded in exclude_ranges:
            next_pieces = []
            ex_start = float(excluded["start_seconds"])
            ex_end = float(excluded["end_seconds"])
            for piece_start, piece_end in pieces:
                if piece_end <= piece_start:
                    continue
                if ex_end <= piece_start or ex_start >= piece_end:
                    next_pieces.append((piece_start, piece_end))
                    continue
                if piece_start < ex_start:
                    next_pieces.append((piece_start, min(ex_start, piece_end)))
                if ex_end < piece_end:
                    next_pieces.append((max(ex_end, piece_start), piece_end))
            pieces = next_pieces

        kept_seconds = sum(max(0.0, piece_end - piece_start) for piece_start, piece_end in pieces)
        if kept_seconds <= 0:
            continue

        if segment.state == "active_play":
            active_seconds += kept_seconds
        else:
            idle_menu_seconds += kept_seconds

    total = active_seconds + idle_menu_seconds
    return {
        "active_play_seconds": round(active_seconds, 3),
        "idle_menu_seconds": round(idle_menu_seconds, 3),
        "total_seconds": round(total, 3),
        "active_play_share": round(active_seconds / total, 4) if total else 0.0,
        "idle_menu_share": round(idle_menu_seconds / total, 4) if total else 0.0,
    }
