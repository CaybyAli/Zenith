from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ENGINE = "universal-moment-brain-v1"


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


@dataclass
class UniversalMomentWindow:
    window_id: str = ""
    start_seconds: float = 0.0
    end_seconds: float = 0.001
    duration_seconds: float = 0.001

    visual_action_score: float = 0.0
    gameplay_motion_score: float = 0.0
    scene_change_score: float = 0.0
    speech_score: float = 0.0
    primary_speech_score: float = 0.0
    secondary_speech_score: float = 0.0
    shout_score: float = 0.0
    reaction_score: float = 0.0
    facecam_emotion_score: float = 0.0
    menu_wait_score: float = 0.0
    dead_time_score: float = 0.0
    private_talk_score: float = 0.0
    tension_score: float = 0.0
    pre_action_score: float = 0.0
    peak_score: float = 0.0
    post_peak_reaction_score: float = 0.0
    boring_score: float = 0.0
    cut_risk_score: float = 0.0
    zoom_risk_score: float = 0.0
    moment_score: float = 0.0

    moment_type: str = "unknown"

    should_keep: bool = False
    should_remove: bool = False
    needs_pre_context: bool = False
    needs_post_context: bool = False
    speech_boundary_risk: bool = False
    zoom_boundary_risk: bool = False
    menu_private_risk: bool = False
    action_context_risk: bool = False

    source_signals: list[str] = field(default_factory=list)
    source_notes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.window_id = str(self.window_id or "")
        self.start_seconds = _safe_seconds(self.start_seconds)
        self.end_seconds = _safe_seconds(self.end_seconds, self.start_seconds + 0.001)
        if self.end_seconds <= self.start_seconds:
            self.end_seconds = round(self.start_seconds + 0.001, 3)
        self.duration_seconds = round(max(0.001, self.end_seconds - self.start_seconds), 3)

        for name in _SCORE_FIELDS:
            setattr(self, name, _clamp_score(getattr(self, name, 0.0)))

        self.moment_type = str(self.moment_type or "unknown")
        self.should_keep = bool(self.should_keep)
        self.should_remove = bool(self.should_remove)
        self.needs_pre_context = bool(self.needs_pre_context)
        self.needs_post_context = bool(self.needs_post_context)
        self.speech_boundary_risk = bool(self.speech_boundary_risk)
        self.zoom_boundary_risk = bool(self.zoom_boundary_risk)
        self.menu_private_risk = bool(self.menu_private_risk)
        self.action_context_risk = bool(self.action_context_risk)
        self.source_signals = _clean_string_list(self.source_signals)
        self.source_notes = _clean_string_list(self.source_notes)
        self.confidence = _clamp_score(self.confidence)
        self.metadata = dict(self.metadata or {})

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "window_id": self.window_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "moment_type": self.moment_type,
            "should_keep": self.should_keep,
            "should_remove": self.should_remove,
            "needs_pre_context": self.needs_pre_context,
            "needs_post_context": self.needs_post_context,
            "speech_boundary_risk": self.speech_boundary_risk,
            "zoom_boundary_risk": self.zoom_boundary_risk,
            "menu_private_risk": self.menu_private_risk,
            "action_context_risk": self.action_context_risk,
            "source_signals": list(self.source_signals),
            "source_notes": list(self.source_notes),
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }
        for name in _SCORE_FIELDS:
            payload[name] = getattr(self, name)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UniversalMomentWindow":
        data = dict(data or {})
        kwargs = {name: data.get(name, 0.0) for name in _SCORE_FIELDS}
        return cls(
            window_id=str(data.get("window_id", "")),
            start_seconds=data.get("start_seconds", 0.0),
            end_seconds=data.get("end_seconds", data.get("start_seconds", 0.0)),
            duration_seconds=data.get("duration_seconds", 0.0),
            moment_type=str(data.get("moment_type", "unknown")),
            should_keep=bool(data.get("should_keep", False)),
            should_remove=bool(data.get("should_remove", False)),
            needs_pre_context=bool(data.get("needs_pre_context", False)),
            needs_post_context=bool(data.get("needs_post_context", False)),
            speech_boundary_risk=bool(data.get("speech_boundary_risk", False)),
            zoom_boundary_risk=bool(data.get("zoom_boundary_risk", False)),
            menu_private_risk=bool(data.get("menu_private_risk", False)),
            action_context_risk=bool(data.get("action_context_risk", False)),
            source_signals=list(data.get("source_signals") or []),
            source_notes=list(data.get("source_notes") or []),
            confidence=data.get("confidence", 0.0),
            metadata=dict(data.get("metadata") or {}),
            **kwargs,
        )


@dataclass
class UniversalMomentResult:
    windows: list[UniversalMomentWindow] = field(default_factory=list)
    engine: str = ENGINE
    total_windows: int = 0
    avg_moment_score: float = 0.0
    max_moment_score: float = 0.0
    keep_windows: int = 0
    remove_windows: int = 0
    cut_risk_windows: int = 0
    zoom_risk_windows: int = 0

    def __post_init__(self) -> None:
        self.windows = sorted(
            [
                window
                if isinstance(window, UniversalMomentWindow)
                else UniversalMomentWindow.from_dict(window)
                for window in (self.windows or [])
                if isinstance(window, (UniversalMomentWindow, dict))
            ],
            key=lambda item: (item.start_seconds, item.end_seconds, item.window_id),
        )
        self.engine = str(self.engine or ENGINE)
        self.total_windows = len(self.windows)
        self.avg_moment_score = _clamp_score(
            sum(window.moment_score for window in self.windows) / len(self.windows)
            if self.windows
            else 0.0
        )
        self.max_moment_score = _clamp_score(
            max((window.moment_score for window in self.windows), default=0.0)
        )
        self.keep_windows = sum(window.should_keep for window in self.windows)
        self.remove_windows = sum(window.should_remove for window in self.windows)
        self.cut_risk_windows = sum(window.cut_risk_score >= 0.55 for window in self.windows)
        self.zoom_risk_windows = sum(window.zoom_risk_score >= 0.55 for window in self.windows)

    def to_dict(self) -> dict[str, Any]:
        return {
            "windows": [window.to_dict() for window in self.windows],
            "engine": self.engine,
            "total_windows": self.total_windows,
            "avg_moment_score": self.avg_moment_score,
            "max_moment_score": self.max_moment_score,
            "keep_windows": self.keep_windows,
            "remove_windows": self.remove_windows,
            "cut_risk_windows": self.cut_risk_windows,
            "zoom_risk_windows": self.zoom_risk_windows,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UniversalMomentResult":
        data = dict(data or {})
        return cls(
            windows=[
                UniversalMomentWindow.from_dict(window)
                for window in data.get("windows", [])
                if isinstance(window, dict)
            ],
            engine=str(data.get("engine", ENGINE)),
            total_windows=int(data.get("total_windows", 0) or 0),
            avg_moment_score=data.get("avg_moment_score", 0.0),
            max_moment_score=data.get("max_moment_score", 0.0),
            keep_windows=int(data.get("keep_windows", 0) or 0),
            remove_windows=int(data.get("remove_windows", 0) or 0),
            cut_risk_windows=int(data.get("cut_risk_windows", 0) or 0),
            zoom_risk_windows=int(data.get("zoom_risk_windows", 0) or 0),
        )


_SCORE_FIELDS = (
    "visual_action_score",
    "gameplay_motion_score",
    "scene_change_score",
    "speech_score",
    "primary_speech_score",
    "secondary_speech_score",
    "shout_score",
    "reaction_score",
    "facecam_emotion_score",
    "menu_wait_score",
    "dead_time_score",
    "private_talk_score",
    "tension_score",
    "pre_action_score",
    "peak_score",
    "post_peak_reaction_score",
    "boring_score",
    "cut_risk_score",
    "zoom_risk_score",
    "moment_score",
)
