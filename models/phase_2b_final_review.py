from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ENGINE = "phase-2b-final-review-v1"

FINAL_REVIEW_STATUSES = {
    "strong_keep",
    "keep_with_boundary_warning",
    "review_needed",
    "possible_edge_trim_later",
    "safe",
    "unknown",
}

HUMAN_REVIEW_PRIORITIES = {"high", "medium", "low", "none"}


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
        text = str(value)
        return [text] if text else []
    try:
        return [str(item) for item in value if str(item)]
    except TypeError:
        text = str(value)
        return [text] if text else []


@dataclass
class Phase2BSegmentReview:
    segment_id: str = ""
    index: int = 0
    segment_role: str = "unknown"
    start_time: float = 0.0
    end_time: float = 0.001
    duration_seconds: float = 0.001

    soft_decision: str = "unknown"
    context_decision: str = "unknown"
    professional_verdict: str = "unknown"
    final_review_status: str = "unknown"

    keep_confidence: float = 0.0
    remove_confidence: float = 0.0
    conflict_score: float = 0.0
    context_conflict_score: float = 0.0

    previous_boundary_type: str = "clean"
    next_boundary_type: str = "clean"
    protect_previous_boundary: bool = False
    protect_next_boundary: bool = False

    human_review_priority: str = "none"
    human_review_reason: str = ""

    key_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.segment_id = str(self.segment_id or "")
        try:
            self.index = max(0, int(self.index or 0))
        except (TypeError, ValueError):
            self.index = 0
        self.segment_role = str(self.segment_role or "unknown")
        self.start_time = _safe_seconds(self.start_time)
        self.end_time = _safe_seconds(self.end_time, self.start_time + 0.001)
        if self.end_time <= self.start_time:
            self.end_time = round(self.start_time + 0.001, 3)
        self.duration_seconds = round(max(0.001, self.end_time - self.start_time), 3)

        self.soft_decision = str(self.soft_decision or "unknown")
        self.context_decision = str(self.context_decision or "unknown")
        self.professional_verdict = str(self.professional_verdict or "unknown")
        self.final_review_status = str(self.final_review_status or "unknown")
        if self.final_review_status not in FINAL_REVIEW_STATUSES:
            self.final_review_status = "unknown"

        for name in _SCORE_FIELDS:
            setattr(self, name, _clamp_score(getattr(self, name, 0.0)))

        self.previous_boundary_type = str(self.previous_boundary_type or "clean")
        self.next_boundary_type = str(self.next_boundary_type or "clean")
        self.protect_previous_boundary = bool(self.protect_previous_boundary)
        self.protect_next_boundary = bool(self.protect_next_boundary)

        self.human_review_priority = str(self.human_review_priority or "none")
        if self.human_review_priority not in HUMAN_REVIEW_PRIORITIES:
            self.human_review_priority = "none"
        self.human_review_reason = str(self.human_review_reason or "")
        self.key_reasons = _clean_string_list(self.key_reasons)
        self.warnings = _clean_string_list(self.warnings)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "segment_id": self.segment_id,
            "index": self.index,
            "segment_role": self.segment_role,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "soft_decision": self.soft_decision,
            "context_decision": self.context_decision,
            "professional_verdict": self.professional_verdict,
            "final_review_status": self.final_review_status,
            "previous_boundary_type": self.previous_boundary_type,
            "next_boundary_type": self.next_boundary_type,
            "protect_previous_boundary": self.protect_previous_boundary,
            "protect_next_boundary": self.protect_next_boundary,
            "human_review_priority": self.human_review_priority,
            "human_review_reason": self.human_review_reason,
            "key_reasons": list(self.key_reasons),
            "warnings": list(self.warnings),
        }
        for name in _SCORE_FIELDS:
            payload[name] = getattr(self, name)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Phase2BSegmentReview":
        data = dict(data or {})
        kwargs = {name: data.get(name, 0.0) for name in _SCORE_FIELDS}
        return cls(
            segment_id=str(data.get("segment_id", "")),
            index=int(data.get("index", 0) or 0),
            segment_role=str(data.get("segment_role", "unknown")),
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", data.get("start_time", 0.0)),
            duration_seconds=data.get("duration_seconds", 0.0),
            soft_decision=str(data.get("soft_decision", "unknown")),
            context_decision=str(data.get("context_decision", "unknown")),
            professional_verdict=str(data.get("professional_verdict", "unknown")),
            final_review_status=str(data.get("final_review_status", "unknown")),
            previous_boundary_type=str(data.get("previous_boundary_type", "clean")),
            next_boundary_type=str(data.get("next_boundary_type", "clean")),
            protect_previous_boundary=bool(data.get("protect_previous_boundary", False)),
            protect_next_boundary=bool(data.get("protect_next_boundary", False)),
            human_review_priority=str(data.get("human_review_priority", "none")),
            human_review_reason=str(data.get("human_review_reason", "")),
            key_reasons=list(data.get("key_reasons") or []),
            warnings=list(data.get("warnings") or []),
            **kwargs,
        )


@dataclass
class Phase2BFinalReviewReport:
    job_id: str = ""
    engine: str = ENGINE
    segments: list[Phase2BSegmentReview] = field(default_factory=list)
    total_segments: int = 0
    strong_keep: int = 0
    keep_with_boundary_warning: int = 0
    review_needed: int = 0
    possible_edge_trim_later: int = 0
    safe: int = 0
    high_priority_reviews: int = 0
    medium_priority_reviews: int = 0

    def __post_init__(self) -> None:
        self.job_id = str(self.job_id or "")
        self.engine = str(self.engine or ENGINE)
        self.segments = sorted(
            [
                segment
                if isinstance(segment, Phase2BSegmentReview)
                else Phase2BSegmentReview.from_dict(segment)
                for segment in (self.segments or [])
                if isinstance(segment, (Phase2BSegmentReview, dict))
            ],
            key=lambda item: (item.start_time, item.end_time, item.segment_id),
        )
        self.total_segments = len(self.segments)
        self.strong_keep = self._count_status("strong_keep")
        self.keep_with_boundary_warning = self._count_status("keep_with_boundary_warning")
        self.review_needed = self._count_status("review_needed")
        self.possible_edge_trim_later = self._count_status("possible_edge_trim_later")
        self.safe = self._count_status("safe")
        self.high_priority_reviews = self._count_priority("high")
        self.medium_priority_reviews = self._count_priority("medium")

    def _count_status(self, status: str) -> int:
        return sum(segment.final_review_status == status for segment in self.segments)

    def _count_priority(self, priority: str) -> int:
        return sum(segment.human_review_priority == priority for segment in self.segments)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "engine": self.engine,
            "segments": [segment.to_dict() for segment in self.segments],
            "total_segments": self.total_segments,
            "strong_keep": self.strong_keep,
            "keep_with_boundary_warning": self.keep_with_boundary_warning,
            "review_needed": self.review_needed,
            "possible_edge_trim_later": self.possible_edge_trim_later,
            "safe": self.safe,
            "high_priority_reviews": self.high_priority_reviews,
            "medium_priority_reviews": self.medium_priority_reviews,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Phase2BFinalReviewReport":
        data = dict(data or {})
        return cls(
            job_id=str(data.get("job_id", "")),
            engine=str(data.get("engine", ENGINE)),
            segments=[
                Phase2BSegmentReview.from_dict(segment)
                for segment in data.get("segments", [])
                if isinstance(segment, dict)
            ],
            total_segments=int(data.get("total_segments", 0) or 0),
            strong_keep=int(data.get("strong_keep", 0) or 0),
            keep_with_boundary_warning=int(data.get("keep_with_boundary_warning", 0) or 0),
            review_needed=int(data.get("review_needed", 0) or 0),
            possible_edge_trim_later=int(data.get("possible_edge_trim_later", 0) or 0),
            safe=int(data.get("safe", 0) or 0),
            high_priority_reviews=int(data.get("high_priority_reviews", 0) or 0),
            medium_priority_reviews=int(data.get("medium_priority_reviews", 0) or 0),
        )


_SCORE_FIELDS = (
    "keep_confidence",
    "remove_confidence",
    "conflict_score",
    "context_conflict_score",
)
