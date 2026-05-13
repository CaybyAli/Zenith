from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CONTINUITY_CHECK_STATUS_OK = "ok"
CONTINUITY_CHECK_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
CONTINUITY_CHECK_STATUS_SKIPPED_NO_TRANSITION_DECISIONS = (
    "skipped_no_transition_decisions"
)
CONTINUITY_CHECK_STATUS_SKIPPED_NO_CUT_LIST_ITEMS = "skipped_no_cut_list_items"
CONTINUITY_CHECK_STATUS_FAILED = "failed"

CONTINUITY_ISSUE_SENTENCE_BREAK_RISK = "sentence_break_risk"
CONTINUITY_ISSUE_CONTEXT_JUMP_RISK = "context_jump_risk"
CONTINUITY_ISSUE_CENSOR_CONTEXT_RISK = "censor_context_risk"
CONTINUITY_ISSUE_INVALID_TIMING = "invalid_timing"
CONTINUITY_ISSUE_OVERLAP_RISK = "overlap_risk"
CONTINUITY_ISSUE_GAP_RISK = "gap_risk"
CONTINUITY_ISSUE_TRANSITION_CONFLICT = "transition_conflict"
CONTINUITY_ISSUE_PROTECTED_CONTEXT_VIOLATION = "protected_context_violation"
CONTINUITY_ISSUE_TECHNICAL_CONTINUITY_RISK = "technical_continuity_risk"
CONTINUITY_ISSUE_UNKNOWN_REVIEW = "unknown_continuity_review"

CONTINUITY_SEVERITY_LOW = "low"
CONTINUITY_SEVERITY_MEDIUM = "medium"
CONTINUITY_SEVERITY_HIGH = "high"
CONTINUITY_SEVERITY_CRITICAL = "critical"

CONTINUITY_PRIORITY_LOW = "low"
CONTINUITY_PRIORITY_MEDIUM = "medium"
CONTINUITY_PRIORITY_HIGH = "high"


@dataclass
class ContinuityIssue:
    issue_id: str
    source_item_id: str | None = None
    segment_id: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    center_seconds: float | None = None
    duration_seconds: float | None = None
    issue_type: str = CONTINUITY_ISSUE_UNKNOWN_REVIEW
    severity: str = CONTINUITY_SEVERITY_LOW
    confidence: float = 0.0
    priority: str = CONTINUITY_PRIORITY_LOW
    is_blocking: bool = False
    is_protected_context: bool = False
    is_censor_context: bool = False
    is_technical_issue: bool = False
    requires_review: bool = True
    recommendation: str = "continuity_ok"
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    source_signal_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "source_item_id": self.source_item_id,
            "segment_id": self.segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "center_seconds": self.center_seconds,
            "duration_seconds": self.duration_seconds,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "confidence": self.confidence,
            "priority": self.priority,
            "is_blocking": self.is_blocking,
            "is_protected_context": self.is_protected_context,
            "is_censor_context": self.is_censor_context,
            "is_technical_issue": self.is_technical_issue,
            "requires_review": self.requires_review,
            "recommendation": self.recommendation,
            "reason": self.reason,
            "evidence": dict(self.evidence or {}),
            "source_signal_ids": list(self.source_signal_ids or []),
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ContinuityIssue":
        data = data or {}

        return cls(
            issue_id=str(data.get("issue_id") or ""),
            source_item_id=data.get("source_item_id"),
            segment_id=data.get("segment_id"),
            start_seconds=data.get("start_seconds"),
            end_seconds=data.get("end_seconds"),
            center_seconds=data.get("center_seconds"),
            duration_seconds=data.get("duration_seconds"),
            issue_type=str(
                data.get("issue_type") or CONTINUITY_ISSUE_UNKNOWN_REVIEW
            ),
            severity=str(data.get("severity") or CONTINUITY_SEVERITY_LOW),
            confidence=float(data.get("confidence") or 0.0),
            priority=str(data.get("priority") or CONTINUITY_PRIORITY_LOW),
            is_blocking=bool(data.get("is_blocking", False)),
            is_protected_context=bool(data.get("is_protected_context", False)),
            is_censor_context=bool(data.get("is_censor_context", False)),
            is_technical_issue=bool(data.get("is_technical_issue", False)),
            requires_review=bool(data.get("requires_review", True)),
            recommendation=str(data.get("recommendation") or "continuity_ok"),
            reason=str(data.get("reason") or ""),
            evidence=dict(data.get("evidence") or {}),
            source_signal_ids=list(data.get("source_signal_ids") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class ContinuityCheckResult:
    status: str = CONTINUITY_CHECK_STATUS_SKIPPED_NO_TRANSITION_DECISIONS
    issues: list[ContinuityIssue] = field(default_factory=list)
    issue_count: int = 0
    blocking_issue_count: int = 0
    sentence_break_risk_count: int = 0
    context_jump_risk_count: int = 0
    censor_context_risk_count: int = 0
    timing_issue_count: int = 0
    transition_conflict_count: int = 0
    technical_issue_count: int = 0
    protected_context_count: int = 0
    recommendation: str = "continuity_check_skipped_no_inputs"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.issue_count = len(self.issues)
        self.blocking_issue_count = sum(
            1 for issue in self.issues if issue.is_blocking
        )
        self.sentence_break_risk_count = sum(
            1
            for issue in self.issues
            if issue.issue_type == CONTINUITY_ISSUE_SENTENCE_BREAK_RISK
        )
        self.context_jump_risk_count = sum(
            1
            for issue in self.issues
            if issue.issue_type == CONTINUITY_ISSUE_CONTEXT_JUMP_RISK
        )
        self.censor_context_risk_count = sum(
            1
            for issue in self.issues
            if issue.issue_type == CONTINUITY_ISSUE_CENSOR_CONTEXT_RISK
        )
        self.timing_issue_count = sum(
            1
            for issue in self.issues
            if issue.issue_type
            in {
                CONTINUITY_ISSUE_INVALID_TIMING,
                CONTINUITY_ISSUE_OVERLAP_RISK,
                CONTINUITY_ISSUE_GAP_RISK,
            }
        )
        self.transition_conflict_count = sum(
            1
            for issue in self.issues
            if issue.issue_type == CONTINUITY_ISSUE_TRANSITION_CONFLICT
        )
        self.technical_issue_count = sum(
            1 for issue in self.issues if issue.is_technical_issue
        )
        self.protected_context_count = sum(
            1 for issue in self.issues if issue.is_protected_context
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()

        return {
            "status": self.status,
            "issues": [issue.to_dict() for issue in self.issues],
            "issue_count": self.issue_count,
            "blocking_issue_count": self.blocking_issue_count,
            "sentence_break_risk_count": self.sentence_break_risk_count,
            "context_jump_risk_count": self.context_jump_risk_count,
            "censor_context_risk_count": self.censor_context_risk_count,
            "timing_issue_count": self.timing_issue_count,
            "transition_conflict_count": self.transition_conflict_count,
            "technical_issue_count": self.technical_issue_count,
            "protected_context_count": self.protected_context_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ContinuityCheckResult":
        data = data or {}
        issues = [
            ContinuityIssue.from_dict(item)
            for item in data.get("issues", []) or []
            if isinstance(item, dict)
        ]

        result = cls(
            status=str(
                data.get("status")
                or CONTINUITY_CHECK_STATUS_SKIPPED_NO_TRANSITION_DECISIONS
            ),
            issues=issues,
            recommendation=str(
                data.get("recommendation") or "continuity_check_skipped_no_inputs"
            ),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
        result.refresh_counts()
        return result
