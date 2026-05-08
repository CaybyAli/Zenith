from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ENGINE = "phase-2b-stabilization-v1"

STATUSES = {
    "passed",
    "passed_with_known_warnings",
    "failed",
}


def _safe_int(value: object, fallback: int = 0) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        numeric = fallback
    return max(0, numeric)


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
class Phase2BStabilizationResult:
    job_id: str = ""
    engine: str = ENGINE

    phase: str = "2.B"
    status: str = "failed"

    timeline_exists: bool = False
    render_exists: bool = False
    export_exists: bool = False
    final_review_exists: bool = False
    universal_moment_debug_exists: bool = False
    universal_soft_decision_exists: bool = False
    universal_role_audit_exists: bool = False
    universal_context_audit_exists: bool = False
    universal_boundary_evidence_exists: bool = False
    review_markdown_exists: bool = False
    validator_failed_only_thumbnail: bool = False

    timeline_segments: int = 0
    final_review_segments: int = 0
    boundary_count: int = 0
    high_priority_reviews: int = 0
    medium_priority_reviews: int = 0

    missing_thumbnail_known_warning: bool = False
    high_boundary_review_warning: bool = False
    transcript_boundary_precision_warning: bool = False

    phase_2b_ready_to_close: bool = False
    next_phase_recommendation: str = ""
    known_open_items: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.job_id = str(self.job_id or "")
        self.engine = str(self.engine or ENGINE)
        self.phase = str(self.phase or "2.B")
        self.status = str(self.status or "failed")
        if self.status not in STATUSES:
            self.status = "failed"

        for name in _BOOL_FIELDS:
            setattr(self, name, bool(getattr(self, name, False)))
        for name in _INT_FIELDS:
            setattr(self, name, _safe_int(getattr(self, name, 0)))

        self.next_phase_recommendation = str(self.next_phase_recommendation or "")
        self.known_open_items = _clean_string_list(self.known_open_items)
        self.notes = _clean_string_list(self.notes)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "job_id": self.job_id,
            "engine": self.engine,
            "phase": self.phase,
            "status": self.status,
            "next_phase_recommendation": self.next_phase_recommendation,
            "known_open_items": list(self.known_open_items),
            "notes": list(self.notes),
        }
        for name in _BOOL_FIELDS:
            payload[name] = getattr(self, name)
        for name in _INT_FIELDS:
            payload[name] = getattr(self, name)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Phase2BStabilizationResult":
        data = dict(data or {})
        kwargs: dict[str, Any] = {name: bool(data.get(name, False)) for name in _BOOL_FIELDS}
        kwargs.update({name: data.get(name, 0) for name in _INT_FIELDS})
        return cls(
            job_id=str(data.get("job_id", "")),
            engine=str(data.get("engine", ENGINE)),
            phase=str(data.get("phase", "2.B")),
            status=str(data.get("status", "failed")),
            next_phase_recommendation=str(data.get("next_phase_recommendation", "")),
            known_open_items=list(data.get("known_open_items") or []),
            notes=list(data.get("notes") or []),
            **kwargs,
        )


_BOOL_FIELDS = (
    "timeline_exists",
    "render_exists",
    "export_exists",
    "final_review_exists",
    "universal_moment_debug_exists",
    "universal_soft_decision_exists",
    "universal_role_audit_exists",
    "universal_context_audit_exists",
    "universal_boundary_evidence_exists",
    "review_markdown_exists",
    "validator_failed_only_thumbnail",
    "missing_thumbnail_known_warning",
    "high_boundary_review_warning",
    "transcript_boundary_precision_warning",
    "phase_2b_ready_to_close",
)

_INT_FIELDS = (
    "timeline_segments",
    "final_review_segments",
    "boundary_count",
    "high_priority_reviews",
    "medium_priority_reviews",
)
