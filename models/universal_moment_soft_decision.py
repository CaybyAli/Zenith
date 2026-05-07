from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ENGINE = "universal-moment-soft-decision-v1"

SOFT_DECISIONS = {
    "keep_dominant",
    "remove_dominant",
    "trim_edges_candidate",
    "needs_human_review",
    "safe_keep",
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
class UniversalMomentSegmentDecision:
    segment_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.001
    duration_seconds: float = 0.001
    segment_role: str = "unknown"

    keep_confidence: float = 0.0
    remove_confidence: float = 0.0
    trim_confidence: float = 0.0
    review_confidence: float = 0.0
    conflict_score: float = 0.0
    private_confidence: float = 0.0
    boring_confidence: float = 0.0
    action_confidence: float = 0.0
    speech_confidence: float = 0.0
    context_confidence: float = 0.0

    soft_decision: str = "unknown"

    is_mixed_conflict: bool = False
    should_not_auto_remove: bool = True
    can_trim_edges_later: bool = False
    needs_human_review: bool = False
    protect_pre_context: bool = False
    protect_post_context: bool = False

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source_verdict: str = "unknown"
    source_diagnosis: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.segment_id = str(self.segment_id or "")
        self.segment_role = str(self.segment_role or "unknown")
        self.start_time = _safe_seconds(self.start_time)
        self.end_time = _safe_seconds(self.end_time, self.start_time + 0.001)
        if self.end_time <= self.start_time:
            self.end_time = round(self.start_time + 0.001, 3)
        self.duration_seconds = round(max(0.001, self.end_time - self.start_time), 3)

        for name in _SCORE_FIELDS:
            setattr(self, name, _clamp_score(getattr(self, name, 0.0)))

        self.soft_decision = str(self.soft_decision or "unknown")
        if self.soft_decision not in SOFT_DECISIONS:
            self.soft_decision = "unknown"

        self.is_mixed_conflict = bool(self.is_mixed_conflict)
        self.should_not_auto_remove = bool(self.should_not_auto_remove)
        self.can_trim_edges_later = bool(self.can_trim_edges_later)
        self.needs_human_review = bool(self.needs_human_review)
        self.protect_pre_context = bool(self.protect_pre_context)
        self.protect_post_context = bool(self.protect_post_context)
        self.reasons = _clean_string_list(self.reasons)
        self.warnings = _clean_string_list(self.warnings)
        self.source_verdict = str(self.source_verdict or "unknown")
        self.source_diagnosis = _clean_string_list(self.source_diagnosis)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "segment_id": self.segment_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "segment_role": self.segment_role,
            "soft_decision": self.soft_decision,
            "is_mixed_conflict": self.is_mixed_conflict,
            "should_not_auto_remove": self.should_not_auto_remove,
            "can_trim_edges_later": self.can_trim_edges_later,
            "needs_human_review": self.needs_human_review,
            "protect_pre_context": self.protect_pre_context,
            "protect_post_context": self.protect_post_context,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "source_verdict": self.source_verdict,
            "source_diagnosis": list(self.source_diagnosis),
        }
        for name in _SCORE_FIELDS:
            payload[name] = getattr(self, name)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UniversalMomentSegmentDecision":
        data = dict(data or {})
        kwargs = {name: data.get(name, 0.0) for name in _SCORE_FIELDS}
        return cls(
            segment_id=str(data.get("segment_id", "")),
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", data.get("start_time", 0.0)),
            duration_seconds=data.get("duration_seconds", 0.0),
            segment_role=str(data.get("segment_role", "unknown")),
            soft_decision=str(data.get("soft_decision", "unknown")),
            is_mixed_conflict=bool(data.get("is_mixed_conflict", False)),
            should_not_auto_remove=bool(data.get("should_not_auto_remove", True)),
            can_trim_edges_later=bool(data.get("can_trim_edges_later", False)),
            needs_human_review=bool(data.get("needs_human_review", False)),
            protect_pre_context=bool(data.get("protect_pre_context", False)),
            protect_post_context=bool(data.get("protect_post_context", False)),
            reasons=list(data.get("reasons") or []),
            warnings=list(data.get("warnings") or []),
            source_verdict=str(data.get("source_verdict", "unknown")),
            source_diagnosis=list(data.get("source_diagnosis") or []),
            **kwargs,
        )


@dataclass
class UniversalMomentSoftDecisionReport:
    job_id: str = ""
    engine: str = ENGINE
    decisions: list[UniversalMomentSegmentDecision] = field(default_factory=list)
    total_segments: int = 0
    keep_dominant: int = 0
    remove_dominant: int = 0
    trim_edges_candidate: int = 0
    needs_human_review: int = 0
    safe_keep: int = 0
    avg_keep_confidence: float = 0.0
    avg_remove_confidence: float = 0.0
    avg_conflict_score: float = 0.0

    def __post_init__(self) -> None:
        self.job_id = str(self.job_id or "")
        self.engine = str(self.engine or ENGINE)
        self.decisions = sorted(
            [
                decision
                if isinstance(decision, UniversalMomentSegmentDecision)
                else UniversalMomentSegmentDecision.from_dict(decision)
                for decision in (self.decisions or [])
                if isinstance(decision, (UniversalMomentSegmentDecision, dict))
            ],
            key=lambda item: (item.start_time, item.end_time, item.segment_id),
        )
        self.total_segments = len(self.decisions)
        self.keep_dominant = self._count("keep_dominant")
        self.remove_dominant = self._count("remove_dominant")
        self.trim_edges_candidate = self._count("trim_edges_candidate")
        self.needs_human_review = self._count("needs_human_review")
        self.safe_keep = self._count("safe_keep")
        self.avg_keep_confidence = _clamp_score(
            sum(item.keep_confidence for item in self.decisions) / len(self.decisions)
            if self.decisions
            else 0.0
        )
        self.avg_remove_confidence = _clamp_score(
            sum(item.remove_confidence for item in self.decisions) / len(self.decisions)
            if self.decisions
            else 0.0
        )
        self.avg_conflict_score = _clamp_score(
            sum(item.conflict_score for item in self.decisions) / len(self.decisions)
            if self.decisions
            else 0.0
        )

    def _count(self, soft_decision: str) -> int:
        return sum(item.soft_decision == soft_decision for item in self.decisions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "engine": self.engine,
            "decisions": [decision.to_dict() for decision in self.decisions],
            "total_segments": self.total_segments,
            "keep_dominant": self.keep_dominant,
            "remove_dominant": self.remove_dominant,
            "trim_edges_candidate": self.trim_edges_candidate,
            "needs_human_review": self.needs_human_review,
            "safe_keep": self.safe_keep,
            "avg_keep_confidence": self.avg_keep_confidence,
            "avg_remove_confidence": self.avg_remove_confidence,
            "avg_conflict_score": self.avg_conflict_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UniversalMomentSoftDecisionReport":
        data = dict(data or {})
        return cls(
            job_id=str(data.get("job_id", "")),
            engine=str(data.get("engine", ENGINE)),
            decisions=[
                UniversalMomentSegmentDecision.from_dict(decision)
                for decision in data.get("decisions", [])
                if isinstance(decision, dict)
            ],
            total_segments=int(data.get("total_segments", 0) or 0),
            keep_dominant=int(data.get("keep_dominant", 0) or 0),
            remove_dominant=int(data.get("remove_dominant", 0) or 0),
            trim_edges_candidate=int(data.get("trim_edges_candidate", 0) or 0),
            needs_human_review=int(data.get("needs_human_review", 0) or 0),
            safe_keep=int(data.get("safe_keep", 0) or 0),
            avg_keep_confidence=data.get("avg_keep_confidence", 0.0),
            avg_remove_confidence=data.get("avg_remove_confidence", 0.0),
            avg_conflict_score=data.get("avg_conflict_score", 0.0),
        )


_SCORE_FIELDS = (
    "keep_confidence",
    "remove_confidence",
    "trim_confidence",
    "review_confidence",
    "conflict_score",
    "private_confidence",
    "boring_confidence",
    "action_confidence",
    "speech_confidence",
    "context_confidence",
)
