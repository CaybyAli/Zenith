from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


EMOTIONAL_ARC_STATUS_READY = "arc_analysis_ready"
EMOTIONAL_ARC_STATUS_READY_WITH_WARNINGS = "arc_analysis_ready_with_warnings"
EMOTIONAL_ARC_STATUS_NO_TIMELINE_ITEMS = "no_timeline_items"
EMOTIONAL_ARC_STATUS_BLOCKED = "blocked"
EMOTIONAL_ARC_STATUS_FAILED = "failed"

EMOTIONAL_ARC_RECOMMENDATION_READY = "emotional_arc_review_ready"
EMOTIONAL_ARC_RECOMMENDATION_REVIEW = "review_emotional_arc_suggestions"
EMOTIONAL_ARC_RECOMMENDATION_BLOCKED = "review_emotional_arc_blockers"
EMOTIONAL_ARC_RECOMMENDATION_NO_ITEMS = "provide_review_timeline_items"
EMOTIONAL_ARC_RECOMMENDATION_FAILED = "review_emotional_arc_failure"

EMOTIONAL_ARC_PHASES = [
    "hook",
    "setup",
    "build_up",
    "first_highlight",
    "calm",
    "tension",
    "climax",
    "reaction",
    "wind_down",
    "outro",
]

EMOTIONAL_ARC_TARGET_SCORES = {
    "hook": 0.95,
    "setup": 0.55,
    "build_up": 0.65,
    "first_highlight": 0.85,
    "calm": 0.45,
    "tension": 0.70,
    "climax": 1.00,
    "reaction": 0.80,
    "wind_down": 0.50,
    "outro": 0.40,
}

EMOTIONAL_ARC_PHASE_RANGES = {
    "hook": (0.00, 0.08),
    "setup": (0.08, 0.18),
    "build_up": (0.18, 0.32),
    "first_highlight": (0.32, 0.45),
    "calm": (0.45, 0.55),
    "tension": (0.55, 0.70),
    "climax": (0.70, 0.84),
    "reaction": (0.84, 0.92),
    "wind_down": (0.92, 0.98),
    "outro": (0.98, 1.00),
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_emotional_arc_point_id() -> str:
    return f"emotional_arc_point_{uuid.uuid4().hex[:12]}"


def new_emotional_arc_suggestion_id() -> str:
    return f"emotional_arc_suggestion_{uuid.uuid4().hex[:12]}"


def new_emotional_arc_report_id() -> str:
    return f"emotional_arc_report_{uuid.uuid4().hex[:12]}"


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass
class EmotionalArcPoint:
    point_id: str = field(default_factory=new_emotional_arc_point_id)
    source_item_id: str | None = None
    source_segment_id: str | None = None

    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float = 0.0

    timeline_position_ratio: float = 0.0
    actual_energy_score: float = 0.0
    target_energy_score: float = 0.0
    deviation_score: float = 0.0

    arc_phase: str = "setup"
    label: str = ""
    review_required: bool = True
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.metadata.update(
            {
                "review_only": True,
                "emotional_arc_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_38": True,
                "no_render_in_2b_38": True,
                "no_timeline_reorder_in_2b_38": True,
                "no_arc_apply_in_2b_38": True,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        return {
            "point_id": self.point_id,
            "source_item_id": self.source_item_id,
            "source_segment_id": self.source_segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "timeline_position_ratio": self.timeline_position_ratio,
            "actual_energy_score": self.actual_energy_score,
            "target_energy_score": self.target_energy_score,
            "deviation_score": self.deviation_score,
            "arc_phase": self.arc_phase,
            "label": self.label,
            "review_required": self.review_required,
            "warnings": list(self.warnings or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EmotionalArcPoint":
        data = data or {}
        point = cls(
            point_id=str(data.get("point_id") or new_emotional_arc_point_id()),
            source_item_id=data.get("source_item_id"),
            source_segment_id=data.get("source_segment_id"),
            start_seconds=_safe_optional_float(data.get("start_seconds")),
            end_seconds=_safe_optional_float(data.get("end_seconds")),
            duration_seconds=_safe_float(data.get("duration_seconds"), 0.0),
            timeline_position_ratio=_safe_float(
                data.get("timeline_position_ratio"),
                0.0,
            ),
            actual_energy_score=_safe_float(data.get("actual_energy_score"), 0.0),
            target_energy_score=_safe_float(data.get("target_energy_score"), 0.0),
            deviation_score=_safe_float(data.get("deviation_score"), 0.0),
            arc_phase=str(data.get("arc_phase") or "setup"),
            label=str(data.get("label") or ""),
            review_required=True,
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            metadata=_safe_dict(data.get("metadata")),
        )
        point.enforce_review_only()
        return point


@dataclass
class EmotionalArcSuggestion:
    suggestion_id: str = field(default_factory=new_emotional_arc_suggestion_id)
    suggestion_type: str = ""
    source_item_id: str | None = None
    arc_phase: str | None = None
    severity: str = "medium"
    reason: str = ""
    review_required: bool = True
    can_auto_apply: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.can_auto_apply = False
        self.metadata.update(
            {
                "review_only": True,
                "emotional_arc_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_38": True,
                "no_render_in_2b_38": True,
                "no_timeline_reorder_in_2b_38": True,
                "no_arc_apply_in_2b_38": True,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        return {
            "suggestion_id": self.suggestion_id,
            "suggestion_type": self.suggestion_type,
            "source_item_id": self.source_item_id,
            "arc_phase": self.arc_phase,
            "severity": self.severity,
            "reason": self.reason,
            "review_required": self.review_required,
            "can_auto_apply": self.can_auto_apply,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EmotionalArcSuggestion":
        data = data or {}
        suggestion = cls(
            suggestion_id=str(
                data.get("suggestion_id") or new_emotional_arc_suggestion_id()
            ),
            suggestion_type=str(data.get("suggestion_type") or ""),
            source_item_id=data.get("source_item_id"),
            arc_phase=data.get("arc_phase"),
            severity=str(data.get("severity") or "medium"),
            reason=str(data.get("reason") or ""),
            review_required=True,
            can_auto_apply=False,
            metadata=_safe_dict(data.get("metadata")),
        )
        suggestion.enforce_review_only()
        return suggestion


@dataclass
class EmotionalArcReport:
    report_id: str = field(default_factory=new_emotional_arc_report_id)
    job_id: str | None = None
    status: str = EMOTIONAL_ARC_STATUS_NO_TIMELINE_ITEMS

    arc_points: list[EmotionalArcPoint] = field(default_factory=list)
    suggestions: list[EmotionalArcSuggestion] = field(default_factory=list)
    actual_curve: list[dict[str, Any]] = field(default_factory=list)
    target_curve: list[dict[str, Any]] = field(default_factory=list)

    average_deviation: float = 0.0
    max_deviation: float = 0.0
    flatness_score: float = 0.0
    hook_strength_score: float = 0.0
    climax_strength_score: float = 0.0
    breathing_room_score: float = 0.0

    review_required: bool = True
    can_apply_arc: bool = False
    can_reorder_timeline: bool = False
    can_trim: bool = False
    can_extend: bool = False
    can_render: bool = False

    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str = EMOTIONAL_ARC_RECOMMENDATION_NO_ITEMS
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.can_apply_arc = False
        self.can_reorder_timeline = False
        self.can_trim = False
        self.can_extend = False
        self.can_render = False

        for point in self.arc_points:
            point.enforce_review_only()
        for suggestion in self.suggestions:
            suggestion.enforce_review_only()

        self.metadata.update(
            {
                "phase": "2B-38",
                "block": "block7_story_pacing",
                "review_only": True,
                "emotional_arc_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_38": True,
                "no_render_in_2b_38": True,
                "no_timeline_reorder_in_2b_38": True,
                "no_arc_apply_in_2b_38": True,
            }
        )

    def refresh_curves(self) -> None:
        self.target_curve = [
            {
                "arc_phase": phase,
                "target_energy_score": EMOTIONAL_ARC_TARGET_SCORES[phase],
                "position_range": EMOTIONAL_ARC_PHASE_RANGES[phase],
            }
            for phase in EMOTIONAL_ARC_PHASES
        ]
        self.actual_curve = [
            {
                "point_id": point.point_id,
                "source_item_id": point.source_item_id,
                "source_segment_id": point.source_segment_id,
                "timeline_position_ratio": point.timeline_position_ratio,
                "arc_phase": point.arc_phase,
                "actual_energy_score": point.actual_energy_score,
                "target_energy_score": point.target_energy_score,
                "deviation_score": point.deviation_score,
            }
            for point in self.arc_points
        ]

    def refresh_metrics(self) -> None:
        self.refresh_curves()
        deviations = [
            float(point.deviation_score or 0.0)
            for point in self.arc_points
        ]
        scores = [
            float(point.actual_energy_score or 0.0)
            for point in self.arc_points
        ]

        self.average_deviation = (
            round(sum(deviations) / len(deviations), 6) if deviations else 0.0
        )
        self.max_deviation = round(max(deviations), 6) if deviations else 0.0
        self.flatness_score = (
            round(1.0 - (max(scores) - min(scores)), 6) if scores else 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        self.refresh_metrics()
        return {
            "report_id": self.report_id,
            "job_id": self.job_id,
            "status": self.status,
            "arc_points": [point.to_dict() for point in self.arc_points],
            "suggestions": [
                suggestion.to_dict()
                for suggestion in self.suggestions
            ],
            "actual_curve": [dict(item) for item in self.actual_curve],
            "target_curve": [dict(item) for item in self.target_curve],
            "average_deviation": self.average_deviation,
            "max_deviation": self.max_deviation,
            "flatness_score": self.flatness_score,
            "hook_strength_score": self.hook_strength_score,
            "climax_strength_score": self.climax_strength_score,
            "breathing_room_score": self.breathing_room_score,
            "review_required": self.review_required,
            "can_apply_arc": self.can_apply_arc,
            "can_reorder_timeline": self.can_reorder_timeline,
            "can_trim": self.can_trim,
            "can_extend": self.can_extend,
            "can_render": self.can_render,
            "warnings": list(self.warnings or []),
            "blocking_reasons": list(self.blocking_reasons or []),
            "recommendation": self.recommendation,
            "created_at": self.created_at,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EmotionalArcReport":
        data = data or {}
        points = [
            EmotionalArcPoint.from_dict(item)
            for item in data.get("arc_points", []) or []
            if isinstance(item, dict)
        ]
        suggestions = [
            EmotionalArcSuggestion.from_dict(item)
            for item in data.get("suggestions", []) or []
            if isinstance(item, dict)
        ]
        report = cls(
            report_id=str(data.get("report_id") or new_emotional_arc_report_id()),
            job_id=data.get("job_id"),
            status=str(data.get("status") or EMOTIONAL_ARC_STATUS_NO_TIMELINE_ITEMS),
            arc_points=points,
            suggestions=suggestions,
            actual_curve=[
                dict(item)
                for item in data.get("actual_curve", []) or []
                if isinstance(item, dict)
            ],
            target_curve=[
                dict(item)
                for item in data.get("target_curve", []) or []
                if isinstance(item, dict)
            ],
            average_deviation=_safe_float(data.get("average_deviation"), 0.0),
            max_deviation=_safe_float(data.get("max_deviation"), 0.0),
            flatness_score=_safe_float(data.get("flatness_score"), 0.0),
            hook_strength_score=_safe_float(data.get("hook_strength_score"), 0.0),
            climax_strength_score=_safe_float(
                data.get("climax_strength_score"),
                0.0,
            ),
            breathing_room_score=_safe_float(
                data.get("breathing_room_score"),
                0.0,
            ),
            review_required=True,
            can_apply_arc=False,
            can_reorder_timeline=False,
            can_trim=False,
            can_extend=False,
            can_render=False,
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            blocking_reasons=[
                str(item)
                for item in _safe_list(data.get("blocking_reasons"))
            ],
            recommendation=str(
                data.get("recommendation")
                or EMOTIONAL_ARC_RECOMMENDATION_NO_ITEMS
            ),
            created_at=str(data.get("created_at") or utc_now_iso()),
            metadata=_safe_dict(data.get("metadata")),
        )
        report.enforce_review_only()
        report.refresh_metrics()
        return report
