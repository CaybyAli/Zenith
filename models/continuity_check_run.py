from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.continuity_check import ContinuityCheckResult, ContinuityIssue


@dataclass
class ContinuityCheckRunReport:
    status: str = "skipped_no_transition_decisions"
    source: str = "continuity_check"
    continuity_check_result: ContinuityCheckResult | None = None
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "continuity_check_result": (
                self.continuity_check_result.to_dict()
                if self.continuity_check_result is not None
                else None
            ),
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
    def from_dict(cls, data: dict[str, Any] | None) -> "ContinuityCheckRunReport":
        data = data or {}

        result_data = data.get("continuity_check_result")
        continuity_check_result = (
            ContinuityCheckResult.from_dict(result_data)
            if isinstance(result_data, dict)
            else None
        )

        issues = [
            ContinuityIssue.from_dict(item)
            for item in data.get("issues", []) or []
            if isinstance(item, dict)
        ]

        return cls(
            status=str(data.get("status") or "skipped_no_transition_decisions"),
            source=str(data.get("source") or "continuity_check"),
            continuity_check_result=continuity_check_result,
            issues=issues,
            issue_count=int(data.get("issue_count", len(issues)) or 0),
            blocking_issue_count=int(data.get("blocking_issue_count", 0) or 0),
            sentence_break_risk_count=int(
                data.get("sentence_break_risk_count", 0) or 0
            ),
            context_jump_risk_count=int(data.get("context_jump_risk_count", 0) or 0),
            censor_context_risk_count=int(
                data.get("censor_context_risk_count", 0) or 0
            ),
            timing_issue_count=int(data.get("timing_issue_count", 0) or 0),
            transition_conflict_count=int(
                data.get("transition_conflict_count", 0) or 0
            ),
            technical_issue_count=int(data.get("technical_issue_count", 0) or 0),
            protected_context_count=int(data.get("protected_context_count", 0) or 0),
            recommendation=str(
                data.get("recommendation") or "continuity_check_skipped_no_inputs"
            ),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
