from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


PATTERN_INTERRUPT_STATUS_READY = "pattern_interrupt_analysis_ready"
PATTERN_INTERRUPT_STATUS_READY_WITH_WARNINGS = (
    "pattern_interrupt_ready_with_warnings"
)
PATTERN_INTERRUPT_STATUS_NO_TIMELINE_ITEMS = "no_timeline_items"
PATTERN_INTERRUPT_STATUS_BLOCKED = "blocked"
PATTERN_INTERRUPT_STATUS_FAILED = "failed"

PATTERN_INTERRUPT_RECOMMENDATION_READY = "pattern_interrupt_review_ready"
PATTERN_INTERRUPT_RECOMMENDATION_REVIEW = "review_pattern_interrupt_suggestions"
PATTERN_INTERRUPT_RECOMMENDATION_BLOCKED = "review_pattern_interrupt_blockers"
PATTERN_INTERRUPT_RECOMMENDATION_NO_ITEMS = "provide_review_timeline_items"
PATTERN_INTERRUPT_RECOMMENDATION_FAILED = "review_pattern_interrupt_failure"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_pattern_interrupt_window_id() -> str:
    return f"pattern_interrupt_window_{uuid.uuid4().hex[:12]}"


def new_pattern_interrupt_suggestion_id() -> str:
    return f"pattern_interrupt_suggestion_{uuid.uuid4().hex[:12]}"


def new_pattern_interrupt_report_id() -> str:
    return f"pattern_interrupt_report_{uuid.uuid4().hex[:12]}"


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
class PatternInterruptWindow:
    window_id: str = field(default_factory=new_pattern_interrupt_window_id)
    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float = 0.0
    item_ids: list[str] = field(default_factory=list)
    average_energy_score: float = 0.0
    average_cut_rate: float = 0.0
    energy_variation_score: float = 0.0
    pacing_variation_score: float = 0.0
    visual_variation_score: float = 0.0
    reaction_presence_score: float = 0.0
    monotony_score: float = 0.0
    interrupt_needed: bool = False
    recommended_interrupt_type: str | None = None
    review_required: bool = True
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.metadata.update(
            {
                "phase": "2B-40",
                "block": "block7_story_pacing",
                "review_only": True,
                "pattern_interrupt_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_40": True,
                "no_render_in_2b_40": True,
                "no_timeline_reorder_in_2b_40": True,
                "no_pattern_apply_in_2b_40": True,
                "no_zoom_insert_in_2b_40": True,
                "no_text_overlay_insert_in_2b_40": True,
                "no_sfx_insert_in_2b_40": True,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        return {
            "window_id": self.window_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "item_ids": list(self.item_ids or []),
            "average_energy_score": self.average_energy_score,
            "average_cut_rate": self.average_cut_rate,
            "energy_variation_score": self.energy_variation_score,
            "pacing_variation_score": self.pacing_variation_score,
            "visual_variation_score": self.visual_variation_score,
            "reaction_presence_score": self.reaction_presence_score,
            "monotony_score": self.monotony_score,
            "interrupt_needed": self.interrupt_needed,
            "recommended_interrupt_type": self.recommended_interrupt_type,
            "review_required": self.review_required,
            "warnings": list(self.warnings or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PatternInterruptWindow":
        data = data or {}
        window = cls(
            window_id=str(
                data.get("window_id") or new_pattern_interrupt_window_id()
            ),
            start_seconds=_safe_optional_float(data.get("start_seconds")),
            end_seconds=_safe_optional_float(data.get("end_seconds")),
            duration_seconds=_safe_float(data.get("duration_seconds"), 0.0),
            item_ids=[str(item) for item in _safe_list(data.get("item_ids"))],
            average_energy_score=_safe_float(
                data.get("average_energy_score"),
                0.0,
            ),
            average_cut_rate=_safe_float(data.get("average_cut_rate"), 0.0),
            energy_variation_score=_safe_float(
                data.get("energy_variation_score"),
                0.0,
            ),
            pacing_variation_score=_safe_float(
                data.get("pacing_variation_score"),
                0.0,
            ),
            visual_variation_score=_safe_float(
                data.get("visual_variation_score"),
                0.0,
            ),
            reaction_presence_score=_safe_float(
                data.get("reaction_presence_score"),
                0.0,
            ),
            monotony_score=_safe_float(data.get("monotony_score"), 0.0),
            interrupt_needed=bool(data.get("interrupt_needed", False)),
            recommended_interrupt_type=data.get("recommended_interrupt_type"),
            review_required=True,
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            metadata=_safe_dict(data.get("metadata")),
        )
        window.enforce_review_only()
        return window


@dataclass
class PatternInterruptSuggestion:
    suggestion_id: str = field(default_factory=new_pattern_interrupt_suggestion_id)
    suggestion_type: str = ""
    source_window_id: str | None = None
    source_item_id: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    severity: str = "medium"
    reason: str = ""
    review_required: bool = True
    can_auto_apply: bool = False
    can_insert_zoom: bool = False
    can_insert_text_overlay: bool = False
    can_insert_sfx: bool = False
    can_reorder_timeline: bool = False
    can_render: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.can_auto_apply = False
        self.can_insert_zoom = False
        self.can_insert_text_overlay = False
        self.can_insert_sfx = False
        self.can_reorder_timeline = False
        self.can_render = False
        self.metadata.update(
            {
                "phase": "2B-40",
                "block": "block7_story_pacing",
                "review_only": True,
                "pattern_interrupt_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_40": True,
                "no_render_in_2b_40": True,
                "no_timeline_reorder_in_2b_40": True,
                "no_pattern_apply_in_2b_40": True,
                "no_zoom_insert_in_2b_40": True,
                "no_text_overlay_insert_in_2b_40": True,
                "no_sfx_insert_in_2b_40": True,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        return {
            "suggestion_id": self.suggestion_id,
            "suggestion_type": self.suggestion_type,
            "source_window_id": self.source_window_id,
            "source_item_id": self.source_item_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "severity": self.severity,
            "reason": self.reason,
            "review_required": self.review_required,
            "can_auto_apply": self.can_auto_apply,
            "can_insert_zoom": self.can_insert_zoom,
            "can_insert_text_overlay": self.can_insert_text_overlay,
            "can_insert_sfx": self.can_insert_sfx,
            "can_reorder_timeline": self.can_reorder_timeline,
            "can_render": self.can_render,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PatternInterruptSuggestion":
        data = data or {}
        suggestion = cls(
            suggestion_id=str(
                data.get("suggestion_id")
                or new_pattern_interrupt_suggestion_id()
            ),
            suggestion_type=str(data.get("suggestion_type") or ""),
            source_window_id=data.get("source_window_id"),
            source_item_id=data.get("source_item_id"),
            start_seconds=_safe_optional_float(data.get("start_seconds")),
            end_seconds=_safe_optional_float(data.get("end_seconds")),
            severity=str(data.get("severity") or "medium"),
            reason=str(data.get("reason") or ""),
            review_required=True,
            can_auto_apply=False,
            can_insert_zoom=False,
            can_insert_text_overlay=False,
            can_insert_sfx=False,
            can_reorder_timeline=False,
            can_render=False,
            metadata=_safe_dict(data.get("metadata")),
        )
        suggestion.enforce_review_only()
        return suggestion


@dataclass
class PatternInterruptReport:
    report_id: str = field(default_factory=new_pattern_interrupt_report_id)
    job_id: str | None = None
    status: str = PATTERN_INTERRUPT_STATUS_NO_TIMELINE_ITEMS
    windows: list[PatternInterruptWindow] = field(default_factory=list)
    suggestions: list[PatternInterruptSuggestion] = field(default_factory=list)
    total_windows: int = 0
    interrupt_needed_count: int = 0
    monotony_score: float = 0.0
    average_window_duration_seconds: float = 0.0
    recommended_interrupt_count: int = 0
    review_required: bool = True
    can_apply_interrupts: bool = False
    can_insert_zoom: bool = False
    can_insert_text_overlay: bool = False
    can_insert_sfx: bool = False
    can_reorder_timeline: bool = False
    can_trim: bool = False
    can_extend: bool = False
    can_render: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str = PATTERN_INTERRUPT_RECOMMENDATION_NO_ITEMS
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.can_apply_interrupts = False
        self.can_insert_zoom = False
        self.can_insert_text_overlay = False
        self.can_insert_sfx = False
        self.can_reorder_timeline = False
        self.can_trim = False
        self.can_extend = False
        self.can_render = False

        for window in self.windows:
            window.enforce_review_only()
        for suggestion in self.suggestions:
            suggestion.enforce_review_only()

        self.metadata.update(
            {
                "phase": "2B-40",
                "block": "block7_story_pacing",
                "review_only": True,
                "pattern_interrupt_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_40": True,
                "no_render_in_2b_40": True,
                "no_timeline_reorder_in_2b_40": True,
                "no_pattern_apply_in_2b_40": True,
                "no_zoom_insert_in_2b_40": True,
                "no_text_overlay_insert_in_2b_40": True,
                "no_sfx_insert_in_2b_40": True,
            }
        )

    def refresh_metrics(self) -> None:
        self.total_windows = len(self.windows)
        self.interrupt_needed_count = sum(
            1 for window in self.windows if bool(window.interrupt_needed)
        )
        self.recommended_interrupt_count = len(self.suggestions)

        durations = [
            float(window.duration_seconds or 0.0)
            for window in self.windows
            if float(window.duration_seconds or 0.0) > 0.0
        ]
        monotony_scores = [
            float(window.monotony_score or 0.0)
            for window in self.windows
        ]

        self.average_window_duration_seconds = (
            round(sum(durations) / len(durations), 6) if durations else 0.0
        )
        self.monotony_score = (
            round(sum(monotony_scores) / len(monotony_scores), 6)
            if monotony_scores
            else 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        self.refresh_metrics()
        return {
            "report_id": self.report_id,
            "job_id": self.job_id,
            "status": self.status,
            "windows": [window.to_dict() for window in self.windows],
            "suggestions": [
                suggestion.to_dict() for suggestion in self.suggestions
            ],
            "total_windows": self.total_windows,
            "interrupt_needed_count": self.interrupt_needed_count,
            "monotony_score": self.monotony_score,
            "average_window_duration_seconds": (
                self.average_window_duration_seconds
            ),
            "recommended_interrupt_count": self.recommended_interrupt_count,
            "review_required": self.review_required,
            "can_apply_interrupts": self.can_apply_interrupts,
            "can_insert_zoom": self.can_insert_zoom,
            "can_insert_text_overlay": self.can_insert_text_overlay,
            "can_insert_sfx": self.can_insert_sfx,
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
    def from_dict(cls, data: dict[str, Any] | None) -> "PatternInterruptReport":
        data = data or {}
        windows = [
            PatternInterruptWindow.from_dict(item)
            for item in data.get("windows", []) or []
            if isinstance(item, dict)
        ]
        suggestions = [
            PatternInterruptSuggestion.from_dict(item)
            for item in data.get("suggestions", []) or []
            if isinstance(item, dict)
        ]
        report = cls(
            report_id=str(
                data.get("report_id") or new_pattern_interrupt_report_id()
            ),
            job_id=data.get("job_id"),
            status=str(
                data.get("status") or PATTERN_INTERRUPT_STATUS_NO_TIMELINE_ITEMS
            ),
            windows=windows,
            suggestions=suggestions,
            total_windows=int(data.get("total_windows", 0) or 0),
            interrupt_needed_count=int(
                data.get("interrupt_needed_count", 0) or 0
            ),
            monotony_score=_safe_float(data.get("monotony_score"), 0.0),
            average_window_duration_seconds=_safe_float(
                data.get("average_window_duration_seconds"),
                0.0,
            ),
            recommended_interrupt_count=int(
                data.get("recommended_interrupt_count", 0) or 0
            ),
            review_required=True,
            can_apply_interrupts=False,
            can_insert_zoom=False,
            can_insert_text_overlay=False,
            can_insert_sfx=False,
            can_reorder_timeline=False,
            can_trim=False,
            can_extend=False,
            can_render=False,
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            blocking_reasons=[
                str(item) for item in _safe_list(data.get("blocking_reasons"))
            ],
            recommendation=str(
                data.get("recommendation")
                or PATTERN_INTERRUPT_RECOMMENDATION_NO_ITEMS
            ),
            created_at=str(data.get("created_at") or utc_now_iso()),
            metadata=_safe_dict(data.get("metadata")),
        )
        report.enforce_review_only()
        report.refresh_metrics()
        return report
