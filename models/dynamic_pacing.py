from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


DYNAMIC_PACING_STATUS_READY = "pacing_analysis_ready"
DYNAMIC_PACING_STATUS_READY_WITH_WARNINGS = "pacing_analysis_ready_with_warnings"
DYNAMIC_PACING_STATUS_NO_TIMELINE_ITEMS = "no_timeline_items"
DYNAMIC_PACING_STATUS_BLOCKED = "blocked"
DYNAMIC_PACING_STATUS_FAILED = "failed"

DYNAMIC_PACING_RECOMMENDATION_READY = "dynamic_pacing_review_ready"
DYNAMIC_PACING_RECOMMENDATION_REVIEW = "review_dynamic_pacing_suggestions"
DYNAMIC_PACING_RECOMMENDATION_BLOCKED = "review_dynamic_pacing_blockers"
DYNAMIC_PACING_RECOMMENDATION_NO_ITEMS = "provide_review_timeline_items"
DYNAMIC_PACING_RECOMMENDATION_FAILED = "review_dynamic_pacing_failure"

PACING_STATUS_GOOD = "good_pacing_match"
PACING_STATUS_TOO_SLOW = "pacing_too_slow_for_energy"
PACING_STATUS_TOO_FAST = "pacing_too_fast_for_energy"
PACING_STATUS_CLIP_TOO_LONG = "clip_too_long_review"
PACING_STATUS_CLIP_TOO_SHORT = "clip_too_short_review"
PACING_STATUS_UNKNOWN = "pacing_unknown_review"
PACING_STATUS_CENSOR_REVIEW = "censor_pacing_review_required"
PACING_STATUS_PROTECTED_PRESERVED = "protected_pacing_preserved"
PACING_STATUS_CONTINUITY_BLOCKED = "continuity_pacing_blocked"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_pacing_segment_id() -> str:
    return f"pacing_segment_{uuid.uuid4().hex[:12]}"


def new_pacing_suggestion_id() -> str:
    return f"pacing_suggestion_{uuid.uuid4().hex[:12]}"


def new_dynamic_pacing_report_id() -> str:
    return f"dynamic_pacing_report_{uuid.uuid4().hex[:12]}"


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


def target_cut_rate_for_energy(energy_score: float) -> tuple[float, float]:
    if energy_score >= 0.80:
        return 20.0, 40.0
    if energy_score >= 0.50:
        return 10.0, 20.0
    return 4.0, 10.0


def _target_range_dict(value: Any) -> dict[str, float]:
    if isinstance(value, dict):
        return {
            "min": _safe_float(value.get("min"), 0.0),
            "max": _safe_float(value.get("max"), 0.0),
        }
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return {
            "min": _safe_float(value[0], 0.0),
            "max": _safe_float(value[1], 0.0),
        }
    return {"min": 0.0, "max": 0.0}


@dataclass
class PacingSegment:
    segment_id: str = field(default_factory=new_pacing_segment_id)
    source_item_id: str | None = None
    source_segment_id: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float = 0.0
    energy_score: float = 0.0
    arc_phase: str = "unknown"
    target_cut_rate_min: float = 0.0
    target_cut_rate_max: float = 0.0
    actual_cut_rate: float = 0.0
    pacing_status: str = PACING_STATUS_UNKNOWN
    review_required: bool = True
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.metadata.update(
            {
                "review_only": True,
                "dynamic_pacing_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_39": True,
                "no_render_in_2b_39": True,
                "no_timeline_reorder_in_2b_39": True,
                "no_pacing_apply_in_2b_39": True,
                "no_split_merge_trim_extend_in_2b_39": True,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        return {
            "segment_id": self.segment_id,
            "source_item_id": self.source_item_id,
            "source_segment_id": self.source_segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "energy_score": self.energy_score,
            "arc_phase": self.arc_phase,
            "target_cut_rate_min": self.target_cut_rate_min,
            "target_cut_rate_max": self.target_cut_rate_max,
            "actual_cut_rate": self.actual_cut_rate,
            "pacing_status": self.pacing_status,
            "review_required": self.review_required,
            "warnings": list(self.warnings or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PacingSegment":
        data = data or {}
        segment = cls(
            segment_id=str(data.get("segment_id") or new_pacing_segment_id()),
            source_item_id=data.get("source_item_id"),
            source_segment_id=data.get("source_segment_id"),
            start_seconds=_safe_optional_float(data.get("start_seconds")),
            end_seconds=_safe_optional_float(data.get("end_seconds")),
            duration_seconds=_safe_float(data.get("duration_seconds"), 0.0),
            energy_score=_safe_float(data.get("energy_score"), 0.0),
            arc_phase=str(data.get("arc_phase") or "unknown"),
            target_cut_rate_min=_safe_float(
                data.get("target_cut_rate_min"),
                0.0,
            ),
            target_cut_rate_max=_safe_float(
                data.get("target_cut_rate_max"),
                0.0,
            ),
            actual_cut_rate=_safe_float(data.get("actual_cut_rate"), 0.0),
            pacing_status=str(data.get("pacing_status") or PACING_STATUS_UNKNOWN),
            review_required=True,
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            metadata=_safe_dict(data.get("metadata")),
        )
        segment.enforce_review_only()
        return segment


@dataclass
class PacingSuggestion:
    suggestion_id: str = field(default_factory=new_pacing_suggestion_id)
    suggestion_type: str = ""
    source_item_id: str | None = None
    source_segment_id: str | None = None
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
                "dynamic_pacing_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_39": True,
                "no_render_in_2b_39": True,
                "no_timeline_reorder_in_2b_39": True,
                "no_pacing_apply_in_2b_39": True,
                "no_split_merge_trim_extend_in_2b_39": True,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        return {
            "suggestion_id": self.suggestion_id,
            "suggestion_type": self.suggestion_type,
            "source_item_id": self.source_item_id,
            "source_segment_id": self.source_segment_id,
            "severity": self.severity,
            "reason": self.reason,
            "review_required": self.review_required,
            "can_auto_apply": self.can_auto_apply,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PacingSuggestion":
        data = data or {}
        suggestion = cls(
            suggestion_id=str(data.get("suggestion_id") or new_pacing_suggestion_id()),
            suggestion_type=str(data.get("suggestion_type") or ""),
            source_item_id=data.get("source_item_id"),
            source_segment_id=data.get("source_segment_id"),
            severity=str(data.get("severity") or "medium"),
            reason=str(data.get("reason") or ""),
            review_required=True,
            can_auto_apply=False,
            metadata=_safe_dict(data.get("metadata")),
        )
        suggestion.enforce_review_only()
        return suggestion


@dataclass
class DynamicPacingReport:
    report_id: str = field(default_factory=new_dynamic_pacing_report_id)
    job_id: str | None = None
    status: str = DYNAMIC_PACING_STATUS_NO_TIMELINE_ITEMS
    pacing_segments: list[PacingSegment] = field(default_factory=list)
    suggestions: list[PacingSuggestion] = field(default_factory=list)
    average_cut_rate: float = 0.0
    target_cut_rate_range: dict[str, float] = field(
        default_factory=lambda: {"min": 0.0, "max": 0.0}
    )
    pacing_match_score: float = 0.0
    monotony_score: float = 0.0
    breathing_room_score: float = 0.0
    fast_run_count: int = 0
    slow_run_count: int = 0
    review_required: bool = True
    can_apply_pacing: bool = False
    can_split_clips: bool = False
    can_merge_clips: bool = False
    can_trim: bool = False
    can_extend: bool = False
    can_reorder_timeline: bool = False
    can_render: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str = DYNAMIC_PACING_RECOMMENDATION_NO_ITEMS
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.can_apply_pacing = False
        self.can_split_clips = False
        self.can_merge_clips = False
        self.can_trim = False
        self.can_extend = False
        self.can_reorder_timeline = False
        self.can_render = False

        for segment in self.pacing_segments:
            segment.enforce_review_only()
        for suggestion in self.suggestions:
            suggestion.enforce_review_only()

        self.metadata.update(
            {
                "phase": "2B-39",
                "block": "block7_story_pacing",
                "review_only": True,
                "dynamic_pacing_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_39": True,
                "no_render_in_2b_39": True,
                "no_timeline_reorder_in_2b_39": True,
                "no_pacing_apply_in_2b_39": True,
                "no_split_merge_trim_extend_in_2b_39": True,
            }
        )

    def refresh_metrics(self) -> None:
        cut_rates = [
            float(segment.actual_cut_rate or 0.0)
            for segment in self.pacing_segments
            if float(segment.actual_cut_rate or 0.0) > 0.0
        ]
        self.average_cut_rate = (
            round(sum(cut_rates) / len(cut_rates), 6) if cut_rates else 0.0
        )

        target_mins = [
            float(segment.target_cut_rate_min or 0.0)
            for segment in self.pacing_segments
            if float(segment.target_cut_rate_min or 0.0) > 0.0
        ]
        target_maxes = [
            float(segment.target_cut_rate_max or 0.0)
            for segment in self.pacing_segments
            if float(segment.target_cut_rate_max or 0.0) > 0.0
        ]
        self.target_cut_rate_range = {
            "min": round(min(target_mins), 6) if target_mins else 0.0,
            "max": round(max(target_maxes), 6) if target_maxes else 0.0,
        }

        scorable = [
            segment
            for segment in self.pacing_segments
            if segment.pacing_status
            not in {
                PACING_STATUS_UNKNOWN,
                PACING_STATUS_CENSOR_REVIEW,
                PACING_STATUS_PROTECTED_PRESERVED,
                PACING_STATUS_CONTINUITY_BLOCKED,
            }
        ]
        good_count = sum(
            1 for segment in scorable if segment.pacing_status == PACING_STATUS_GOOD
        )
        self.pacing_match_score = (
            round(good_count / len(scorable), 6) if scorable else 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        self.refresh_metrics()
        return {
            "report_id": self.report_id,
            "job_id": self.job_id,
            "status": self.status,
            "pacing_segments": [
                segment.to_dict() for segment in self.pacing_segments
            ],
            "suggestions": [
                suggestion.to_dict() for suggestion in self.suggestions
            ],
            "average_cut_rate": self.average_cut_rate,
            "target_cut_rate_range": dict(self.target_cut_rate_range or {}),
            "pacing_match_score": self.pacing_match_score,
            "monotony_score": self.monotony_score,
            "breathing_room_score": self.breathing_room_score,
            "fast_run_count": self.fast_run_count,
            "slow_run_count": self.slow_run_count,
            "review_required": self.review_required,
            "can_apply_pacing": self.can_apply_pacing,
            "can_split_clips": self.can_split_clips,
            "can_merge_clips": self.can_merge_clips,
            "can_trim": self.can_trim,
            "can_extend": self.can_extend,
            "can_reorder_timeline": self.can_reorder_timeline,
            "can_render": self.can_render,
            "warnings": list(self.warnings or []),
            "blocking_reasons": list(self.blocking_reasons or []),
            "recommendation": self.recommendation,
            "created_at": self.created_at,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "DynamicPacingReport":
        data = data or {}
        segments = [
            PacingSegment.from_dict(item)
            for item in data.get("pacing_segments", []) or []
            if isinstance(item, dict)
        ]
        suggestions = [
            PacingSuggestion.from_dict(item)
            for item in data.get("suggestions", []) or []
            if isinstance(item, dict)
        ]
        report = cls(
            report_id=str(data.get("report_id") or new_dynamic_pacing_report_id()),
            job_id=data.get("job_id"),
            status=str(
                data.get("status") or DYNAMIC_PACING_STATUS_NO_TIMELINE_ITEMS
            ),
            pacing_segments=segments,
            suggestions=suggestions,
            average_cut_rate=_safe_float(data.get("average_cut_rate"), 0.0),
            target_cut_rate_range=_target_range_dict(
                data.get("target_cut_rate_range")
            ),
            pacing_match_score=_safe_float(data.get("pacing_match_score"), 0.0),
            monotony_score=_safe_float(data.get("monotony_score"), 0.0),
            breathing_room_score=_safe_float(
                data.get("breathing_room_score"),
                0.0,
            ),
            fast_run_count=int(data.get("fast_run_count", 0) or 0),
            slow_run_count=int(data.get("slow_run_count", 0) or 0),
            review_required=True,
            can_apply_pacing=False,
            can_split_clips=False,
            can_merge_clips=False,
            can_trim=False,
            can_extend=False,
            can_reorder_timeline=False,
            can_render=False,
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            blocking_reasons=[
                str(item) for item in _safe_list(data.get("blocking_reasons"))
            ],
            recommendation=str(
                data.get("recommendation")
                or DYNAMIC_PACING_RECOMMENDATION_NO_ITEMS
            ),
            created_at=str(data.get("created_at") or utc_now_iso()),
            metadata=_safe_dict(data.get("metadata")),
        )
        report.enforce_review_only()
        report.refresh_metrics()
        return report
