from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


TRANSITION_DECISION_STATUS_OK = "ok"
TRANSITION_DECISION_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
TRANSITION_DECISION_STATUS_SKIPPED_NO_CLIP_DURATION_RECOMMENDATIONS = (
    "skipped_no_clip_duration_recommendations"
)
TRANSITION_DECISION_STATUS_SKIPPED_NO_CUT_LIST_ITEMS = "skipped_no_cut_list_items"
TRANSITION_DECISION_STATUS_FAILED = "failed"

TRANSITION_TYPE_HARD_CUT_REVIEW = "hard_cut_review"
TRANSITION_TYPE_J_CUT_REVIEW = "j_cut_review"
TRANSITION_TYPE_L_CUT_REVIEW = "l_cut_review"
TRANSITION_TYPE_QUICK_FADE_REVIEW = "quick_fade_review"
TRANSITION_TYPE_NO_CUT_PROTECT = "no_cut_protect"
TRANSITION_TYPE_CENSOR_SAFE_KEEP = "censor_safe_keep"
TRANSITION_TYPE_TECHNICAL_TRANSITION_REVIEW = "technical_transition_review"
TRANSITION_TYPE_UNKNOWN_REVIEW = "transition_unknown_review"

TRANSITION_PRIORITY_HIGH = "high"
TRANSITION_PRIORITY_MEDIUM = "medium"
TRANSITION_PRIORITY_LOW = "low"


@dataclass
class TransitionDecision:
    decision_id: str
    source_item_id: str | None = None
    segment_id: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    duration_seconds: float | None = None
    transition_type: str = TRANSITION_TYPE_UNKNOWN_REVIEW
    transition_confidence: float = 0.0
    priority: str = TRANSITION_PRIORITY_LOW
    proposed_action: str = "review_transition"
    cut_list_action: str | None = None
    duration_status: str | None = None
    murch_score: float = 0.0
    is_protected: bool = False
    is_censor_keep: bool = False
    is_technical_review: bool = False
    is_scene_change_aligned: bool = False
    is_beat_aligned: bool = False
    is_sentence_safe: bool = False
    is_dialogue_context: bool = False
    reason: str = ""
    decision_basis: dict[str, Any] = field(default_factory=dict)
    source_signal_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "source_item_id": self.source_item_id,
            "segment_id": self.segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "duration_seconds": self.duration_seconds,
            "transition_type": self.transition_type,
            "transition_confidence": self.transition_confidence,
            "priority": self.priority,
            "proposed_action": self.proposed_action,
            "cut_list_action": self.cut_list_action,
            "duration_status": self.duration_status,
            "murch_score": self.murch_score,
            "is_protected": self.is_protected,
            "is_censor_keep": self.is_censor_keep,
            "is_technical_review": self.is_technical_review,
            "is_scene_change_aligned": self.is_scene_change_aligned,
            "is_beat_aligned": self.is_beat_aligned,
            "is_sentence_safe": self.is_sentence_safe,
            "is_dialogue_context": self.is_dialogue_context,
            "reason": self.reason,
            "decision_basis": dict(self.decision_basis or {}),
            "source_signal_ids": list(self.source_signal_ids or []),
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TransitionDecision":
        data = data or {}

        return cls(
            decision_id=str(data.get("decision_id") or ""),
            source_item_id=data.get("source_item_id"),
            segment_id=data.get("segment_id"),
            start_seconds=data.get("start_seconds"),
            end_seconds=data.get("end_seconds"),
            center_seconds=data.get("center_seconds"),
            duration_seconds=data.get("duration_seconds"),
            transition_type=str(
                data.get("transition_type") or TRANSITION_TYPE_UNKNOWN_REVIEW
            ),
            transition_confidence=float(data.get("transition_confidence") or 0.0),
            priority=str(data.get("priority") or TRANSITION_PRIORITY_LOW),
            proposed_action=str(data.get("proposed_action") or "review_transition"),
            cut_list_action=data.get("cut_list_action"),
            duration_status=data.get("duration_status"),
            murch_score=float(data.get("murch_score") or 0.0),
            is_protected=bool(data.get("is_protected", False)),
            is_censor_keep=bool(data.get("is_censor_keep", False)),
            is_technical_review=bool(data.get("is_technical_review", False)),
            is_scene_change_aligned=bool(data.get("is_scene_change_aligned", False)),
            is_beat_aligned=bool(data.get("is_beat_aligned", False)),
            is_sentence_safe=bool(data.get("is_sentence_safe", False)),
            is_dialogue_context=bool(data.get("is_dialogue_context", False)),
            reason=str(data.get("reason") or ""),
            decision_basis=dict(data.get("decision_basis") or {}),
            source_signal_ids=list(data.get("source_signal_ids") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class TransitionDecisionPlan:
    status: str = TRANSITION_DECISION_STATUS_SKIPPED_NO_CLIP_DURATION_RECOMMENDATIONS
    decisions: list[TransitionDecision] = field(default_factory=list)
    decision_count: int = 0
    hard_cut_review_count: int = 0
    j_cut_review_count: int = 0
    l_cut_review_count: int = 0
    quick_fade_review_count: int = 0
    no_cut_protect_count: int = 0
    censor_safe_keep_count: int = 0
    technical_transition_review_count: int = 0
    unknown_review_count: int = 0
    recommendation: str = "transition_decision_skipped_no_inputs"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.decision_count = len(self.decisions)
        self.hard_cut_review_count = sum(
            1
            for item in self.decisions
            if item.transition_type == TRANSITION_TYPE_HARD_CUT_REVIEW
        )
        self.j_cut_review_count = sum(
            1
            for item in self.decisions
            if item.transition_type == TRANSITION_TYPE_J_CUT_REVIEW
        )
        self.l_cut_review_count = sum(
            1
            for item in self.decisions
            if item.transition_type == TRANSITION_TYPE_L_CUT_REVIEW
        )
        self.quick_fade_review_count = sum(
            1
            for item in self.decisions
            if item.transition_type == TRANSITION_TYPE_QUICK_FADE_REVIEW
        )
        self.no_cut_protect_count = sum(
            1
            for item in self.decisions
            if item.transition_type == TRANSITION_TYPE_NO_CUT_PROTECT
        )
        self.censor_safe_keep_count = sum(
            1
            for item in self.decisions
            if item.transition_type == TRANSITION_TYPE_CENSOR_SAFE_KEEP
        )
        self.technical_transition_review_count = sum(
            1
            for item in self.decisions
            if item.transition_type == TRANSITION_TYPE_TECHNICAL_TRANSITION_REVIEW
        )
        self.unknown_review_count = sum(
            1
            for item in self.decisions
            if item.transition_type == TRANSITION_TYPE_UNKNOWN_REVIEW
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()

        return {
            "status": self.status,
            "decisions": [item.to_dict() for item in self.decisions],
            "decision_count": self.decision_count,
            "hard_cut_review_count": self.hard_cut_review_count,
            "j_cut_review_count": self.j_cut_review_count,
            "l_cut_review_count": self.l_cut_review_count,
            "quick_fade_review_count": self.quick_fade_review_count,
            "no_cut_protect_count": self.no_cut_protect_count,
            "censor_safe_keep_count": self.censor_safe_keep_count,
            "technical_transition_review_count": self.technical_transition_review_count,
            "unknown_review_count": self.unknown_review_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TransitionDecisionPlan":
        data = data or {}
        decisions = [
            TransitionDecision.from_dict(item)
            for item in data.get("decisions", []) or []
        ]

        plan = cls(
            status=str(
                data.get("status")
                or TRANSITION_DECISION_STATUS_SKIPPED_NO_CLIP_DURATION_RECOMMENDATIONS
            ),
            decisions=decisions,
            recommendation=str(
                data.get("recommendation") or "transition_decision_skipped_no_inputs"
            ),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
        plan.refresh_counts()
        return plan
