from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


HOOK_IDENTIFICATION_STATUS_CANDIDATE_FOUND = "hook_candidate_found"
HOOK_IDENTIFICATION_STATUS_NO_SAFE_CANDIDATE = "no_safe_hook_candidate"
HOOK_IDENTIFICATION_STATUS_BLOCKED = "blocked"
HOOK_IDENTIFICATION_STATUS_FAILED = "failed"

HOOK_IDENTIFICATION_RECOMMENDATION_REVIEW = "review_hook_candidate"
HOOK_IDENTIFICATION_RECOMMENDATION_NO_CANDIDATE = "no_safe_hook_candidate"
HOOK_IDENTIFICATION_RECOMMENDATION_BLOCKED = "review_hook_identification_blockers"
HOOK_IDENTIFICATION_RECOMMENDATION_FAILED = "review_hook_identification_failure"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_hook_candidate_id() -> str:
    return f"hook_candidate_{uuid.uuid4().hex[:12]}"


def new_hook_identification_report_id() -> str:
    return f"hook_identification_report_{uuid.uuid4().hex[:12]}"


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
class HookCandidate:
    candidate_id: str = field(default_factory=new_hook_candidate_id)
    source_item_id: str | None = None
    source_segment_id: str | None = None

    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float = 0.0

    hook_score: float = 0.0
    energy_peak_score: float = 0.0
    surprise_factor_score: float = 0.0
    emotional_value_score: float = 0.0
    content_value_score: float = 0.0
    confidence: float = 0.0

    reason: str = ""
    review_required: bool = True
    review_only: bool = True

    safety_flags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.review_only = True
        self.metadata.update(
            {
                "review_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_37": True,
                "no_render_in_2b_37": True,
                "no_timeline_reorder_in_2b_37": True,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        return {
            "candidate_id": self.candidate_id,
            "source_item_id": self.source_item_id,
            "source_segment_id": self.source_segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "hook_score": self.hook_score,
            "energy_peak_score": self.energy_peak_score,
            "surprise_factor_score": self.surprise_factor_score,
            "emotional_value_score": self.emotional_value_score,
            "content_value_score": self.content_value_score,
            "confidence": self.confidence,
            "reason": self.reason,
            "review_required": self.review_required,
            "review_only": self.review_only,
            "safety_flags": list(self.safety_flags or []),
            "warnings": list(self.warnings or []),
            "blocking_reasons": list(self.blocking_reasons or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "HookCandidate":
        data = data or {}
        candidate = cls(
            candidate_id=str(data.get("candidate_id") or new_hook_candidate_id()),
            source_item_id=data.get("source_item_id"),
            source_segment_id=data.get("source_segment_id"),
            start_seconds=_safe_optional_float(data.get("start_seconds")),
            end_seconds=_safe_optional_float(data.get("end_seconds")),
            duration_seconds=_safe_float(data.get("duration_seconds"), 0.0),
            hook_score=_safe_float(data.get("hook_score"), 0.0),
            energy_peak_score=_safe_float(data.get("energy_peak_score"), 0.0),
            surprise_factor_score=_safe_float(
                data.get("surprise_factor_score"),
                0.0,
            ),
            emotional_value_score=_safe_float(
                data.get("emotional_value_score"),
                0.0,
            ),
            content_value_score=_safe_float(data.get("content_value_score"), 0.0),
            confidence=_safe_float(data.get("confidence"), 0.0),
            reason=str(data.get("reason") or ""),
            review_required=True,
            review_only=True,
            safety_flags=[str(item) for item in _safe_list(data.get("safety_flags"))],
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            blocking_reasons=[
                str(item) for item in _safe_list(data.get("blocking_reasons"))
            ],
            metadata=_safe_dict(data.get("metadata")),
        )
        candidate.enforce_review_only()
        return candidate


@dataclass
class HookIdentificationReport:
    report_id: str = field(default_factory=new_hook_identification_report_id)
    job_id: str | None = None
    status: str = HOOK_IDENTIFICATION_STATUS_NO_SAFE_CANDIDATE

    selected_candidate: HookCandidate | None = None
    candidates: list[HookCandidate] = field(default_factory=list)

    total_candidates: int = 0
    best_hook_score: float = 0.0

    review_required: bool = True
    can_apply_hook: bool = False
    can_reorder_timeline: bool = False
    can_render: bool = False

    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str = HOOK_IDENTIFICATION_RECOMMENDATION_NO_CANDIDATE

    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.can_apply_hook = False
        self.can_reorder_timeline = False
        self.can_render = False

        if self.selected_candidate is not None:
            self.selected_candidate.enforce_review_only()
        for candidate in self.candidates:
            candidate.enforce_review_only()

        self.metadata.update(
            {
                "phase": "2B-37",
                "block": "block7_story_pacing",
                "review_only": True,
                "hook_identification_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_37": True,
                "no_render_in_2b_37": True,
                "no_timeline_reorder_in_2b_37": True,
            }
        )

    def refresh_counts(self) -> None:
        self.total_candidates = len(self.candidates)
        scores = [float(candidate.hook_score or 0.0) for candidate in self.candidates]
        self.best_hook_score = round(max(scores), 6) if scores else 0.0

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        self.refresh_counts()
        return {
            "report_id": self.report_id,
            "job_id": self.job_id,
            "status": self.status,
            "selected_candidate": (
                self.selected_candidate.to_dict()
                if self.selected_candidate is not None
                else None
            ),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "total_candidates": self.total_candidates,
            "best_hook_score": self.best_hook_score,
            "review_required": self.review_required,
            "can_apply_hook": self.can_apply_hook,
            "can_reorder_timeline": self.can_reorder_timeline,
            "can_render": self.can_render,
            "warnings": list(self.warnings or []),
            "blocking_reasons": list(self.blocking_reasons or []),
            "recommendation": self.recommendation,
            "created_at": self.created_at,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "HookIdentificationReport":
        data = data or {}
        raw_selected = data.get("selected_candidate")
        selected_candidate = (
            HookCandidate.from_dict(raw_selected)
            if isinstance(raw_selected, dict)
            else None
        )
        candidates = [
            HookCandidate.from_dict(item)
            for item in data.get("candidates", []) or []
            if isinstance(item, dict)
        ]

        report = cls(
            report_id=str(
                data.get("report_id") or new_hook_identification_report_id()
            ),
            job_id=data.get("job_id"),
            status=str(
                data.get("status")
                or HOOK_IDENTIFICATION_STATUS_NO_SAFE_CANDIDATE
            ),
            selected_candidate=selected_candidate,
            candidates=candidates,
            total_candidates=int(data.get("total_candidates", len(candidates)) or 0),
            best_hook_score=_safe_float(data.get("best_hook_score"), 0.0),
            review_required=True,
            can_apply_hook=False,
            can_reorder_timeline=False,
            can_render=False,
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            blocking_reasons=[
                str(item) for item in _safe_list(data.get("blocking_reasons"))
            ],
            recommendation=str(
                data.get("recommendation")
                or HOOK_IDENTIFICATION_RECOMMENDATION_NO_CANDIDATE
            ),
            created_at=str(data.get("created_at") or utc_now_iso()),
            metadata=_safe_dict(data.get("metadata")),
        )
        report.enforce_review_only()
        report.refresh_counts()
        return report
