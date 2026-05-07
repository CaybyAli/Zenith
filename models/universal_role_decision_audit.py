from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ENGINE = "universal-role-decision-audit-v1"

ROLE_DECISION_ALIGNMENTS = {
    "aligned",
    "protected_trim_conflict",
    "review_maybe_trim",
    "remove_blocked_by_role",
    "safe_keep_correct",
    "unclear",
}

SUGGESTED_SOFT_DECISIONS = {
    "keep_current",
    "consider_trim_edges",
    "keep_protected",
    "needs_human_review",
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
class UniversalRoleDecisionSegmentAudit:
    segment_id: str = ""
    segment_role: str = "unknown"
    start_time: float = 0.0
    end_time: float = 0.001
    duration_seconds: float = 0.001

    soft_decision: str = "unknown"
    professional_verdict: str = "unknown"
    is_protected_role: bool = False
    is_first_30s: bool = False

    keep_confidence: float = 0.0
    remove_confidence: float = 0.0
    trim_confidence: float = 0.0
    review_confidence: float = 0.0
    conflict_score: float = 0.0
    avg_peak_score: float = 0.0
    avg_tension_score: float = 0.0
    avg_private_talk_score: float = 0.0
    avg_boring_score: float = 0.0
    avg_cut_risk_score: float = 0.0
    avg_zoom_risk_score: float = 0.0

    role_decision_alignment: str = "unclear"
    suggested_soft_decision: str = "unknown"
    suggested_reason: str = ""
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

        self.soft_decision = str(self.soft_decision or "unknown")
        self.professional_verdict = str(self.professional_verdict or "unknown")
        self.is_protected_role = bool(self.is_protected_role)
        self.is_first_30s = bool(self.is_first_30s)

        for name in _SCORE_FIELDS:
            setattr(self, name, _clamp_score(getattr(self, name, 0.0)))

        self.role_decision_alignment = str(self.role_decision_alignment or "unclear")
        if self.role_decision_alignment not in ROLE_DECISION_ALIGNMENTS:
            self.role_decision_alignment = "unclear"

        self.suggested_soft_decision = str(self.suggested_soft_decision or "unknown")
        if self.suggested_soft_decision not in SUGGESTED_SOFT_DECISIONS:
            self.suggested_soft_decision = "unknown"

        self.suggested_reason = str(self.suggested_reason or "")
        self.warnings = _clean_string_list(self.warnings)
        self.notes = _clean_string_list(self.notes)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "segment_id": self.segment_id,
            "segment_role": self.segment_role,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "soft_decision": self.soft_decision,
            "professional_verdict": self.professional_verdict,
            "is_protected_role": self.is_protected_role,
            "is_first_30s": self.is_first_30s,
            "role_decision_alignment": self.role_decision_alignment,
            "suggested_soft_decision": self.suggested_soft_decision,
            "suggested_reason": self.suggested_reason,
            "warnings": list(self.warnings),
            "notes": list(self.notes),
        }
        for name in _SCORE_FIELDS:
            payload[name] = getattr(self, name)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UniversalRoleDecisionSegmentAudit":
        data = dict(data or {})
        kwargs = {name: data.get(name, 0.0) for name in _SCORE_FIELDS}
        return cls(
            segment_id=str(data.get("segment_id", "")),
            segment_role=str(data.get("segment_role", "unknown")),
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", data.get("start_time", 0.0)),
            duration_seconds=data.get("duration_seconds", 0.0),
            soft_decision=str(data.get("soft_decision", "unknown")),
            professional_verdict=str(data.get("professional_verdict", "unknown")),
            is_protected_role=bool(data.get("is_protected_role", False)),
            is_first_30s=bool(data.get("is_first_30s", False)),
            role_decision_alignment=str(data.get("role_decision_alignment", "unclear")),
            suggested_soft_decision=str(data.get("suggested_soft_decision", "unknown")),
            suggested_reason=str(data.get("suggested_reason", "")),
            warnings=list(data.get("warnings") or []),
            notes=list(data.get("notes") or []),
            **kwargs,
        )


@dataclass
class UniversalRoleDecisionAuditReport:
    job_id: str = ""
    engine: str = ENGINE
    segments: list[UniversalRoleDecisionSegmentAudit] = field(default_factory=list)
    total_segments: int = 0
    protected_trim_conflicts: int = 0
    review_maybe_trim: int = 0
    safe_keep_correct: int = 0
    aligned: int = 0
    unclear: int = 0

    def __post_init__(self) -> None:
        self.job_id = str(self.job_id or "")
        self.engine = str(self.engine or ENGINE)
        self.segments = sorted(
            [
                segment
                if isinstance(segment, UniversalRoleDecisionSegmentAudit)
                else UniversalRoleDecisionSegmentAudit.from_dict(segment)
                for segment in (self.segments or [])
                if isinstance(segment, (UniversalRoleDecisionSegmentAudit, dict))
            ],
            key=lambda item: (item.start_time, item.end_time, item.segment_id),
        )
        self.total_segments = len(self.segments)
        self.protected_trim_conflicts = self._count("protected_trim_conflict")
        self.review_maybe_trim = self._count("review_maybe_trim")
        self.safe_keep_correct = self._count("safe_keep_correct")
        self.aligned = self._count("aligned")
        self.unclear = self._count("unclear")

    def _count(self, alignment: str) -> int:
        return sum(segment.role_decision_alignment == alignment for segment in self.segments)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "engine": self.engine,
            "segments": [segment.to_dict() for segment in self.segments],
            "total_segments": self.total_segments,
            "protected_trim_conflicts": self.protected_trim_conflicts,
            "review_maybe_trim": self.review_maybe_trim,
            "safe_keep_correct": self.safe_keep_correct,
            "aligned": self.aligned,
            "unclear": self.unclear,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UniversalRoleDecisionAuditReport":
        data = dict(data or {})
        return cls(
            job_id=str(data.get("job_id", "")),
            engine=str(data.get("engine", ENGINE)),
            segments=[
                UniversalRoleDecisionSegmentAudit.from_dict(segment)
                for segment in data.get("segments", [])
                if isinstance(segment, dict)
            ],
            total_segments=int(data.get("total_segments", 0) or 0),
            protected_trim_conflicts=int(data.get("protected_trim_conflicts", 0) or 0),
            review_maybe_trim=int(data.get("review_maybe_trim", 0) or 0),
            safe_keep_correct=int(data.get("safe_keep_correct", 0) or 0),
            aligned=int(data.get("aligned", 0) or 0),
            unclear=int(data.get("unclear", 0) or 0),
        )


_SCORE_FIELDS = (
    "keep_confidence",
    "remove_confidence",
    "trim_confidence",
    "review_confidence",
    "conflict_score",
    "avg_peak_score",
    "avg_tension_score",
    "avg_private_talk_score",
    "avg_boring_score",
    "avg_cut_risk_score",
    "avg_zoom_risk_score",
)
