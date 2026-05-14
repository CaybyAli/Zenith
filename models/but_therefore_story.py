from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


STORY_STATUS_READY = "story_analysis_ready"
STORY_STATUS_READY_WITH_WARNINGS = "story_analysis_ready_with_warnings"
STORY_STATUS_NO_TIMELINE_ITEMS = "no_timeline_items"
STORY_STATUS_BLOCKED = "blocked"
STORY_STATUS_FAILED = "failed"

STORY_ROLE_BUT = "but_moment"
STORY_ROLE_THEREFORE = "therefore_moment"
STORY_ROLE_AND = "and_moment"
STORY_ROLE_SETUP = "setup_moment"
STORY_ROLE_PAYOFF = "payoff_moment"
STORY_ROLE_REACTION = "reaction_moment"
STORY_ROLE_PROTECTED = "protected_story_moment"
STORY_ROLE_CENSOR_REVIEW = "censor_story_review"
STORY_ROLE_CONTINUITY_BLOCKED = "continuity_story_blocked"
STORY_ROLE_UNKNOWN = "unknown_story_moment"

STORY_SUGGESTION_TOO_MANY_AND = "too_many_and_moments"
STORY_SUGGESTION_WEAK_RATIO = "weak_but_therefore_ratio"
STORY_SUGGESTION_ORPHAN_REACTION = "orphan_reaction"
STORY_SUGGESTION_MISSING_PAYOFF = "missing_payoff"
STORY_SUGGESTION_FLOW_BREAK = "story_flow_break"
STORY_SUGGESTION_SETUP_WITHOUT_PAYOFF = "setup_without_payoff"
STORY_SUGGESTION_PAYOFF_WITHOUT_SETUP = "payoff_without_setup"
STORY_SUGGESTION_STRONG_CHAIN = "strong_story_chain"
STORY_SUGGESTION_CENSOR_REVIEW = "censor_story_review_required"
STORY_SUGGESTION_PROTECTED_PRESERVED = "protected_story_preserved"
STORY_SUGGESTION_CONTINUITY_BLOCKED = "continuity_story_blocked"

STORY_RECOMMENDATION_READY = "review_but_therefore_story"
STORY_RECOMMENDATION_WARNINGS = "review_but_therefore_story_warnings"
STORY_RECOMMENDATION_NO_TIMELINE = "provide_review_timeline_items"
STORY_RECOMMENDATION_BLOCKED = "review_story_blockers"
STORY_RECOMMENDATION_FAILED = "review_story_failure"

TRANSITION_QUALITY_STRONG = "strong_story_transition"
TRANSITION_QUALITY_OK = "ok_story_transition"
TRANSITION_QUALITY_WEAK = "weak_story_transition"
TRANSITION_QUALITY_BLOCKED = "blocked_story_transition"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_story_moment_id() -> str:
    return f"story_moment_{uuid.uuid4().hex[:12]}"


def new_story_transition_id() -> str:
    return f"story_transition_{uuid.uuid4().hex[:12]}"


def new_story_report_id() -> str:
    return f"but_therefore_story_report_{uuid.uuid4().hex[:12]}"


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


def clamp_score(value: Any) -> float:
    score = _safe_float(value, 0.0)
    return max(0.0, min(1.0, score))


def story_review_metadata() -> dict[str, Any]:
    return {
        "phase": "2B-42",
        "block": "block7_story_pacing",
        "review_only": True,
        "but_therefore_story_only": True,
        "media_unchanged": True,
        "no_execution_in_2b_42": True,
        "no_render_in_2b_42": True,
        "no_timeline_reorder_in_2b_42": True,
        "no_story_apply_in_2b_42": True,
        "no_and_moment_remove_in_2b_42": True,
    }


@dataclass
class StoryMoment:
    moment_id: str = field(default_factory=new_story_moment_id)
    source_item_id: str | None = None
    source_segment_id: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float = 0.0
    story_role: str = STORY_ROLE_UNKNOWN
    story_score: float = 0.0
    conflict_score: float = 0.0
    consequence_score: float = 0.0
    reaction_score: float = 0.0
    neutral_score: float = 0.0
    evidence: list[str] = field(default_factory=list)
    review_required: bool = True
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.story_score = clamp_score(self.story_score)
        self.conflict_score = clamp_score(self.conflict_score)
        self.consequence_score = clamp_score(self.consequence_score)
        self.reaction_score = clamp_score(self.reaction_score)
        self.neutral_score = clamp_score(self.neutral_score)
        self.metadata.update(story_review_metadata())

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        return {
            "moment_id": self.moment_id,
            "source_item_id": self.source_item_id,
            "source_segment_id": self.source_segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "story_role": self.story_role,
            "story_score": self.story_score,
            "conflict_score": self.conflict_score,
            "consequence_score": self.consequence_score,
            "reaction_score": self.reaction_score,
            "neutral_score": self.neutral_score,
            "evidence": list(self.evidence or []),
            "review_required": self.review_required,
            "warnings": list(self.warnings or []),
            "blocking_reasons": list(self.blocking_reasons or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "StoryMoment":
        data = data or {}
        moment = cls(
            moment_id=str(data.get("moment_id") or new_story_moment_id()),
            source_item_id=data.get("source_item_id"),
            source_segment_id=data.get("source_segment_id"),
            start_seconds=_safe_optional_float(data.get("start_seconds")),
            end_seconds=_safe_optional_float(data.get("end_seconds")),
            duration_seconds=_safe_float(data.get("duration_seconds"), 0.0),
            story_role=str(data.get("story_role") or STORY_ROLE_UNKNOWN),
            story_score=_safe_float(data.get("story_score"), 0.0),
            conflict_score=_safe_float(data.get("conflict_score"), 0.0),
            consequence_score=_safe_float(data.get("consequence_score"), 0.0),
            reaction_score=_safe_float(data.get("reaction_score"), 0.0),
            neutral_score=_safe_float(data.get("neutral_score"), 0.0),
            evidence=[str(item) for item in _safe_list(data.get("evidence"))],
            review_required=True,
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            blocking_reasons=[
                str(item) for item in _safe_list(data.get("blocking_reasons"))
            ],
            metadata=_safe_dict(data.get("metadata")),
        )
        moment.enforce_review_only()
        return moment


@dataclass
class StoryTransition:
    transition_id: str = field(default_factory=new_story_transition_id)
    from_moment_id: str | None = None
    to_moment_id: str | None = None
    from_role: str = STORY_ROLE_UNKNOWN
    to_role: str = STORY_ROLE_UNKNOWN
    transition_quality: str = TRANSITION_QUALITY_OK
    transition_score: float = 0.0
    issue_type: str | None = None
    review_required: bool = True
    can_auto_fix: bool = False
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.can_auto_fix = False
        self.transition_score = clamp_score(self.transition_score)
        self.metadata.update(story_review_metadata())

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        return {
            "transition_id": self.transition_id,
            "from_moment_id": self.from_moment_id,
            "to_moment_id": self.to_moment_id,
            "from_role": self.from_role,
            "to_role": self.to_role,
            "transition_quality": self.transition_quality,
            "transition_score": self.transition_score,
            "issue_type": self.issue_type,
            "review_required": self.review_required,
            "can_auto_fix": self.can_auto_fix,
            "warnings": list(self.warnings or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "StoryTransition":
        data = data or {}
        transition = cls(
            transition_id=str(
                data.get("transition_id") or new_story_transition_id()
            ),
            from_moment_id=data.get("from_moment_id"),
            to_moment_id=data.get("to_moment_id"),
            from_role=str(data.get("from_role") or STORY_ROLE_UNKNOWN),
            to_role=str(data.get("to_role") or STORY_ROLE_UNKNOWN),
            transition_quality=str(
                data.get("transition_quality") or TRANSITION_QUALITY_OK
            ),
            transition_score=_safe_float(data.get("transition_score"), 0.0),
            issue_type=data.get("issue_type"),
            review_required=True,
            can_auto_fix=False,
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            metadata=_safe_dict(data.get("metadata")),
        )
        transition.enforce_review_only()
        return transition


@dataclass
class ButThereforeStoryReport:
    report_id: str = field(default_factory=new_story_report_id)
    job_id: str | None = None
    status: str = STORY_STATUS_NO_TIMELINE_ITEMS
    moments: list[StoryMoment] = field(default_factory=list)
    transitions: list[StoryTransition] = field(default_factory=list)
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    total_moments: int = 0
    but_count: int = 0
    therefore_count: int = 0
    and_count: int = 0
    reaction_count: int = 0
    payoff_count: int = 0
    strong_story_count: int = 0
    but_therefore_ratio: float = 0.0
    story_flow_score: float = 0.0
    and_streak_max: int = 0
    orphan_reaction_count: int = 0
    missing_payoff_count: int = 0
    review_required: bool = True
    can_apply_story_changes: bool = False
    can_remove_and_moments: bool = False
    can_reorder_timeline: bool = False
    can_trim: bool = False
    can_extend: bool = False
    can_render: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str = STORY_RECOMMENDATION_NO_TIMELINE
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.can_apply_story_changes = False
        self.can_remove_and_moments = False
        self.can_reorder_timeline = False
        self.can_trim = False
        self.can_extend = False
        self.can_render = False

        for moment in self.moments:
            moment.enforce_review_only()
        for transition in self.transitions:
            transition.enforce_review_only()

        self.metadata.update(story_review_metadata())

    def refresh_metrics(self) -> None:
        self.total_moments = len(self.moments)
        self.but_count = sum(1 for item in self.moments if item.story_role == STORY_ROLE_BUT)
        self.therefore_count = sum(
            1 for item in self.moments if item.story_role == STORY_ROLE_THEREFORE
        )
        self.and_count = sum(1 for item in self.moments if item.story_role == STORY_ROLE_AND)
        self.reaction_count = sum(
            1 for item in self.moments if item.story_role == STORY_ROLE_REACTION
        )
        self.payoff_count = sum(
            1 for item in self.moments if item.story_role == STORY_ROLE_PAYOFF
        )
        self.strong_story_count = (
            self.but_count
            + self.therefore_count
            + self.reaction_count
            + self.payoff_count
        )

        if self.total_moments > 0:
            self.but_therefore_ratio = round(
                self.strong_story_count / self.total_moments,
                6,
            )
        else:
            self.but_therefore_ratio = 0.0

        if self.transitions:
            self.story_flow_score = round(
                sum(item.transition_score for item in self.transitions)
                / len(self.transitions),
                6,
            )
        else:
            self.story_flow_score = 0.0

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        self.refresh_metrics()
        return {
            "report_id": self.report_id,
            "job_id": self.job_id,
            "status": self.status,
            "moments": [item.to_dict() for item in self.moments],
            "transitions": [item.to_dict() for item in self.transitions],
            "suggestions": list(self.suggestions or []),
            "total_moments": self.total_moments,
            "but_count": self.but_count,
            "therefore_count": self.therefore_count,
            "and_count": self.and_count,
            "reaction_count": self.reaction_count,
            "payoff_count": self.payoff_count,
            "strong_story_count": self.strong_story_count,
            "but_therefore_ratio": self.but_therefore_ratio,
            "story_flow_score": self.story_flow_score,
            "and_streak_max": self.and_streak_max,
            "orphan_reaction_count": self.orphan_reaction_count,
            "missing_payoff_count": self.missing_payoff_count,
            "review_required": self.review_required,
            "can_apply_story_changes": self.can_apply_story_changes,
            "can_remove_and_moments": self.can_remove_and_moments,
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
    def from_dict(cls, data: dict[str, Any] | None) -> "ButThereforeStoryReport":
        data = data or {}
        report = cls(
            report_id=str(data.get("report_id") or new_story_report_id()),
            job_id=data.get("job_id"),
            status=str(data.get("status") or STORY_STATUS_NO_TIMELINE_ITEMS),
            moments=[
                StoryMoment.from_dict(item)
                for item in data.get("moments", []) or []
                if isinstance(item, dict)
            ],
            transitions=[
                StoryTransition.from_dict(item)
                for item in data.get("transitions", []) or []
                if isinstance(item, dict)
            ],
            suggestions=[
                dict(item)
                for item in data.get("suggestions", []) or []
                if isinstance(item, dict)
            ],
            total_moments=int(data.get("total_moments", 0) or 0),
            but_count=int(data.get("but_count", 0) or 0),
            therefore_count=int(data.get("therefore_count", 0) or 0),
            and_count=int(data.get("and_count", 0) or 0),
            reaction_count=int(data.get("reaction_count", 0) or 0),
            payoff_count=int(data.get("payoff_count", 0) or 0),
            strong_story_count=int(data.get("strong_story_count", 0) or 0),
            but_therefore_ratio=_safe_float(data.get("but_therefore_ratio"), 0.0),
            story_flow_score=_safe_float(data.get("story_flow_score"), 0.0),
            and_streak_max=int(data.get("and_streak_max", 0) or 0),
            orphan_reaction_count=int(data.get("orphan_reaction_count", 0) or 0),
            missing_payoff_count=int(data.get("missing_payoff_count", 0) or 0),
            review_required=True,
            can_apply_story_changes=False,
            can_remove_and_moments=False,
            can_reorder_timeline=False,
            can_trim=False,
            can_extend=False,
            can_render=False,
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            blocking_reasons=[
                str(item) for item in _safe_list(data.get("blocking_reasons"))
            ],
            recommendation=str(
                data.get("recommendation") or STORY_RECOMMENDATION_NO_TIMELINE
            ),
            created_at=str(data.get("created_at") or utc_now_iso()),
            metadata=_safe_dict(data.get("metadata")),
        )
        report.enforce_review_only()
        report.refresh_metrics()
        return report
