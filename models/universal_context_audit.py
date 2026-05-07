from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ENGINE = "universal-context-audit-v1"

RELATIONS = {
    "none",
    "setup_context",
    "payoff_context",
    "action_continuation",
    "speech_continuation",
    "menu_continuation",
    "private_talk_continuation",
    "boring_continuation",
    "weak_relation",
    "unknown",
}

BOUNDARY_TYPES = {
    "clean",
    "speech_cut_risk",
    "action_cut_risk",
    "zoom_cut_risk",
    "menu_jump",
    "micro_gap",
    "hard_jump",
    "unknown",
}

CONTEXT_DECISIONS = {
    "keep_as_setup",
    "keep_as_payoff",
    "keep_context_chain",
    "private_menu_block_candidate",
    "boring_bridge_candidate",
    "boundary_protect",
    "edge_trim_candidate",
    "needs_human_review",
    "safe",
    "unknown",
}


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


def _clean_string(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _clean_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        text = str(value)
        return [text] if text else []
    try:
        return [str(item) for item in value if str(item)]
    except TypeError:
        text = str(value)
        return [text] if text else []


@dataclass
class UniversalSegmentContextAudit:
    segment_id: str = ""
    segment_role: str = "unknown"
    start_time: float = 0.0
    end_time: float = 0.001
    duration_seconds: float = 0.001
    segment_index: int = 0

    previous_segment_id: str | None = None
    next_segment_id: str | None = None

    previous_relation: str = "none"
    next_relation: str = "none"

    previous_boundary_risk: bool = False
    next_boundary_risk: bool = False
    previous_boundary_type: str = "clean"
    next_boundary_type: str = "clean"

    previous_context_strength: float = 0.0
    next_context_strength: float = 0.0
    setup_score: float = 0.0
    payoff_score: float = 0.0
    neighbor_keep_score: float = 0.0
    neighbor_remove_score: float = 0.0
    context_conflict_score: float = 0.0
    edge_trim_safety_score: float = 0.0

    context_decision: str = "unknown"

    should_merge_with_previous: bool = False
    should_merge_with_next: bool = False
    should_protect_previous_boundary: bool = False
    should_protect_next_boundary: bool = False
    can_consider_start_trim_later: bool = False
    can_consider_end_trim_later: bool = False
    should_not_auto_remove: bool = True

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.segment_id = str(self.segment_id or "")
        self.segment_role = str(self.segment_role or "unknown")
        self.start_time = _safe_seconds(self.start_time)
        self.end_time = _safe_seconds(self.end_time, self.start_time + 0.001)
        if self.end_time <= self.start_time:
            self.end_time = round(self.start_time + 0.001, 3)
        self.duration_seconds = round(max(0.001, self.end_time - self.start_time), 3)
        try:
            self.segment_index = max(0, int(self.segment_index or 0))
        except (TypeError, ValueError):
            self.segment_index = 0

        self.previous_segment_id = _clean_string(self.previous_segment_id)
        self.next_segment_id = _clean_string(self.next_segment_id)

        self.previous_relation = self._relation(self.previous_relation, fallback="none")
        self.next_relation = self._relation(self.next_relation, fallback="none")
        self.previous_boundary_risk = bool(self.previous_boundary_risk)
        self.next_boundary_risk = bool(self.next_boundary_risk)
        self.previous_boundary_type = self._boundary(self.previous_boundary_type)
        self.next_boundary_type = self._boundary(self.next_boundary_type)

        for name in _SCORE_FIELDS:
            setattr(self, name, _clamp_score(getattr(self, name, 0.0)))

        self.context_decision = str(self.context_decision or "unknown")
        if self.context_decision not in CONTEXT_DECISIONS:
            self.context_decision = "unknown"

        self.should_merge_with_previous = bool(self.should_merge_with_previous)
        self.should_merge_with_next = bool(self.should_merge_with_next)
        self.should_protect_previous_boundary = bool(self.should_protect_previous_boundary)
        self.should_protect_next_boundary = bool(self.should_protect_next_boundary)
        self.can_consider_start_trim_later = bool(self.can_consider_start_trim_later)
        self.can_consider_end_trim_later = bool(self.can_consider_end_trim_later)
        self.should_not_auto_remove = bool(self.should_not_auto_remove)
        self.reasons = _clean_string_list(self.reasons)
        self.warnings = _clean_string_list(self.warnings)
        self.notes = _clean_string_list(self.notes)

    def _relation(self, value: object, *, fallback: str) -> str:
        text = str(value or fallback)
        return text if text in RELATIONS else fallback

    def _boundary(self, value: object) -> str:
        text = str(value or "clean")
        return text if text in BOUNDARY_TYPES else "unknown"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "segment_id": self.segment_id,
            "segment_role": self.segment_role,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "segment_index": self.segment_index,
            "previous_segment_id": self.previous_segment_id,
            "next_segment_id": self.next_segment_id,
            "previous_relation": self.previous_relation,
            "next_relation": self.next_relation,
            "previous_boundary_risk": self.previous_boundary_risk,
            "next_boundary_risk": self.next_boundary_risk,
            "previous_boundary_type": self.previous_boundary_type,
            "next_boundary_type": self.next_boundary_type,
            "context_decision": self.context_decision,
            "should_merge_with_previous": self.should_merge_with_previous,
            "should_merge_with_next": self.should_merge_with_next,
            "should_protect_previous_boundary": self.should_protect_previous_boundary,
            "should_protect_next_boundary": self.should_protect_next_boundary,
            "can_consider_start_trim_later": self.can_consider_start_trim_later,
            "can_consider_end_trim_later": self.can_consider_end_trim_later,
            "should_not_auto_remove": self.should_not_auto_remove,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "notes": list(self.notes),
        }
        for name in _SCORE_FIELDS:
            payload[name] = getattr(self, name)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UniversalSegmentContextAudit":
        data = dict(data or {})
        kwargs = {name: data.get(name, 0.0) for name in _SCORE_FIELDS}
        return cls(
            segment_id=str(data.get("segment_id", "")),
            segment_role=str(data.get("segment_role", "unknown")),
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", data.get("start_time", 0.0)),
            duration_seconds=data.get("duration_seconds", 0.0),
            segment_index=int(data.get("segment_index", 0) or 0),
            previous_segment_id=data.get("previous_segment_id"),
            next_segment_id=data.get("next_segment_id"),
            previous_relation=str(data.get("previous_relation", "none")),
            next_relation=str(data.get("next_relation", "none")),
            previous_boundary_risk=bool(data.get("previous_boundary_risk", False)),
            next_boundary_risk=bool(data.get("next_boundary_risk", False)),
            previous_boundary_type=str(data.get("previous_boundary_type", "clean")),
            next_boundary_type=str(data.get("next_boundary_type", "clean")),
            context_decision=str(data.get("context_decision", "unknown")),
            should_merge_with_previous=bool(data.get("should_merge_with_previous", False)),
            should_merge_with_next=bool(data.get("should_merge_with_next", False)),
            should_protect_previous_boundary=bool(data.get("should_protect_previous_boundary", False)),
            should_protect_next_boundary=bool(data.get("should_protect_next_boundary", False)),
            can_consider_start_trim_later=bool(data.get("can_consider_start_trim_later", False)),
            can_consider_end_trim_later=bool(data.get("can_consider_end_trim_later", False)),
            should_not_auto_remove=bool(data.get("should_not_auto_remove", True)),
            reasons=list(data.get("reasons") or []),
            warnings=list(data.get("warnings") or []),
            notes=list(data.get("notes") or []),
            **kwargs,
        )


@dataclass
class UniversalContextAuditReport:
    job_id: str = ""
    engine: str = ENGINE
    segments: list[UniversalSegmentContextAudit] = field(default_factory=list)
    total_segments: int = 0
    keep_as_setup: int = 0
    keep_as_payoff: int = 0
    keep_context_chain: int = 0
    private_menu_block_candidate: int = 0
    boring_bridge_candidate: int = 0
    boundary_protect: int = 0
    edge_trim_candidate: int = 0
    needs_human_review: int = 0
    avg_context_conflict_score: float = 0.0

    def __post_init__(self) -> None:
        self.job_id = str(self.job_id or "")
        self.engine = str(self.engine or ENGINE)
        self.segments = sorted(
            [
                segment
                if isinstance(segment, UniversalSegmentContextAudit)
                else UniversalSegmentContextAudit.from_dict(segment)
                for segment in (self.segments or [])
                if isinstance(segment, (UniversalSegmentContextAudit, dict))
            ],
            key=lambda item: (item.start_time, item.end_time, item.segment_id),
        )
        self.total_segments = len(self.segments)
        self.keep_as_setup = self._count("keep_as_setup")
        self.keep_as_payoff = self._count("keep_as_payoff")
        self.keep_context_chain = self._count("keep_context_chain")
        self.private_menu_block_candidate = self._count("private_menu_block_candidate")
        self.boring_bridge_candidate = self._count("boring_bridge_candidate")
        self.boundary_protect = self._count("boundary_protect")
        self.edge_trim_candidate = self._count("edge_trim_candidate")
        self.needs_human_review = self._count("needs_human_review")
        self.avg_context_conflict_score = _clamp_score(
            sum(item.context_conflict_score for item in self.segments) / len(self.segments)
            if self.segments
            else 0.0
        )

    def _count(self, decision: str) -> int:
        return sum(segment.context_decision == decision for segment in self.segments)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "engine": self.engine,
            "segments": [segment.to_dict() for segment in self.segments],
            "total_segments": self.total_segments,
            "keep_as_setup": self.keep_as_setup,
            "keep_as_payoff": self.keep_as_payoff,
            "keep_context_chain": self.keep_context_chain,
            "private_menu_block_candidate": self.private_menu_block_candidate,
            "boring_bridge_candidate": self.boring_bridge_candidate,
            "boundary_protect": self.boundary_protect,
            "edge_trim_candidate": self.edge_trim_candidate,
            "needs_human_review": self.needs_human_review,
            "avg_context_conflict_score": self.avg_context_conflict_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UniversalContextAuditReport":
        data = dict(data or {})
        return cls(
            job_id=str(data.get("job_id", "")),
            engine=str(data.get("engine", ENGINE)),
            segments=[
                UniversalSegmentContextAudit.from_dict(segment)
                for segment in data.get("segments", [])
                if isinstance(segment, dict)
            ],
            total_segments=int(data.get("total_segments", 0) or 0),
            keep_as_setup=int(data.get("keep_as_setup", 0) or 0),
            keep_as_payoff=int(data.get("keep_as_payoff", 0) or 0),
            keep_context_chain=int(data.get("keep_context_chain", 0) or 0),
            private_menu_block_candidate=int(data.get("private_menu_block_candidate", 0) or 0),
            boring_bridge_candidate=int(data.get("boring_bridge_candidate", 0) or 0),
            boundary_protect=int(data.get("boundary_protect", 0) or 0),
            edge_trim_candidate=int(data.get("edge_trim_candidate", 0) or 0),
            needs_human_review=int(data.get("needs_human_review", 0) or 0),
            avg_context_conflict_score=data.get("avg_context_conflict_score", 0.0),
        )


_SCORE_FIELDS = (
    "previous_context_strength",
    "next_context_strength",
    "setup_score",
    "payoff_score",
    "neighbor_keep_score",
    "neighbor_remove_score",
    "context_conflict_score",
    "edge_trim_safety_score",
)
