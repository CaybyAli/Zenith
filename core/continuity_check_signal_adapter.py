from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CONTINUITY_CHECK_SIGNAL_SOURCE = "continuity_check"


ISSUE_TYPE_TO_SIGNAL = {
    "sentence_break_risk": {
        "signal_type": "continuity_sentence_break_risk",
        "action_hint": "review_sentence_boundary_continuity",
        "priority": "high",
    },
    "context_jump_risk": {
        "signal_type": "continuity_context_jump_risk",
        "action_hint": "review_context_jump_continuity",
        "priority": "high",
    },
    "censor_context_risk": {
        "signal_type": "continuity_censor_context_risk",
        "action_hint": "protect_censor_context_continuity",
        "priority": "high",
    },
    "invalid_timing": {
        "signal_type": "continuity_timing_issue",
        "action_hint": "review_timing_continuity",
        "priority": "high",
    },
    "overlap_risk": {
        "signal_type": "continuity_timing_issue",
        "action_hint": "review_timing_continuity",
        "priority": "high",
    },
    "gap_risk": {
        "signal_type": "continuity_timing_issue",
        "action_hint": "review_timing_continuity",
        "priority": "medium",
    },
    "transition_conflict": {
        "signal_type": "continuity_transition_conflict",
        "action_hint": "review_transition_conflict",
        "priority": "high",
    },
    "protected_context_violation": {
        "signal_type": "continuity_protected_context_violation",
        "action_hint": "protect_context_from_cut",
        "priority": "high",
    },
    "technical_continuity_risk": {
        "signal_type": "continuity_technical_risk",
        "action_hint": "review_technical_continuity",
        "priority": "high",
    },
    "unknown_continuity_review": {
        "signal_type": "continuity_unknown_review",
        "action_hint": "review_unknown_continuity",
        "priority": "low",
    },
}


@dataclass
class ContinuityCheckSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    sentence_break_signal_count: int = 0
    context_jump_signal_count: int = 0
    censor_context_signal_count: int = 0
    timing_issue_signal_count: int = 0
    transition_conflict_signal_count: int = 0
    protected_context_signal_count: int = 0
    technical_risk_signal_count: int = 0
    unknown_review_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_continuity_check_signals"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)
        self.sentence_break_signal_count = _count_type(
            self.signals,
            "continuity_sentence_break_risk",
        )
        self.context_jump_signal_count = _count_type(
            self.signals,
            "continuity_context_jump_risk",
        )
        self.censor_context_signal_count = _count_type(
            self.signals,
            "continuity_censor_context_risk",
        )
        self.timing_issue_signal_count = _count_type(
            self.signals,
            "continuity_timing_issue",
        )
        self.transition_conflict_signal_count = _count_type(
            self.signals,
            "continuity_transition_conflict",
        )
        self.protected_context_signal_count = _count_type(
            self.signals,
            "continuity_protected_context_violation",
        )
        self.technical_risk_signal_count = _count_type(
            self.signals,
            "continuity_technical_risk",
        )
        self.unknown_review_signal_count = _count_type(
            self.signals,
            "continuity_unknown_review",
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()
        return {
            "status": self.status,
            "signals": list(self.signals),
            "signal_count": self.signal_count,
            "sentence_break_signal_count": self.sentence_break_signal_count,
            "context_jump_signal_count": self.context_jump_signal_count,
            "censor_context_signal_count": self.censor_context_signal_count,
            "timing_issue_signal_count": self.timing_issue_signal_count,
            "transition_conflict_signal_count": self.transition_conflict_signal_count,
            "protected_context_signal_count": self.protected_context_signal_count,
            "technical_risk_signal_count": self.technical_risk_signal_count,
            "unknown_review_signal_count": self.unknown_review_signal_count,
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ContinuityCheckSignalAdapterResult":
        if not isinstance(data, dict):
            data = {}

        result = cls(
            status=str(data.get("status") or "ok"),
            signals=list(data.get("signals") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(
                data.get("recommendation") or "review_continuity_check_signals"
            ),
            metadata=dict(data.get("metadata") or {}),
        )
        result.refresh_counts()
        return result


def _count_type(signals: list[dict[str, Any]], signal_type: str) -> int:
    return sum(1 for signal in signals if signal.get("signal_type") == signal_type)


def _item_to_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return dict(item)

    if hasattr(item, "to_dict"):
        try:
            converted = item.to_dict()
            if isinstance(converted, dict):
                return dict(converted)
        except Exception:
            return {}

    return {}


def _extract_issues(report_or_issues: Any) -> list[Any]:
    if report_or_issues is None:
        return []

    if isinstance(report_or_issues, list):
        return report_or_issues

    if isinstance(report_or_issues, tuple):
        return list(report_or_issues)

    if isinstance(report_or_issues, dict):
        for key in ("issues", "continuity_check_issues"):
            value = report_or_issues.get(key)
            if isinstance(value, list):
                return list(value)

        result = report_or_issues.get("continuity_check_result")
        if isinstance(result, dict):
            value = result.get("issues")
            if isinstance(value, list):
                return list(value)

    if hasattr(report_or_issues, "issues"):
        value = getattr(report_or_issues, "issues")
        if isinstance(value, list):
            return list(value)

    if hasattr(report_or_issues, "continuity_check_result"):
        result = getattr(report_or_issues, "continuity_check_result")
        if hasattr(result, "issues"):
            value = getattr(result, "issues")
            if isinstance(value, list):
                return list(value)

    return []


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _mapping_for_issue(issue_type: str) -> dict[str, str]:
    return ISSUE_TYPE_TO_SIGNAL.get(
        issue_type,
        ISSUE_TYPE_TO_SIGNAL["unknown_continuity_review"],
    )


def adapt_continuity_issue_to_signal(
    issue: Any,
    index: int = 0,
) -> dict[str, Any] | None:
    item_data = _item_to_dict(issue)
    issue_type = str(item_data.get("issue_type") or "").strip().lower()

    mapping = _mapping_for_issue(issue_type)
    if issue_type not in ISSUE_TYPE_TO_SIGNAL:
        issue_type = "unknown_continuity_review"

    issue_id = str(item_data.get("issue_id") or f"continuity_issue_{index}")
    confidence = _safe_float(item_data.get("confidence"), 0.0)

    return {
        "signal_id": f"continuity_check_signal_{issue_id}",
        "signal_type": mapping["signal_type"],
        "source": CONTINUITY_CHECK_SIGNAL_SOURCE,
        "source_item_id": item_data.get("source_item_id") or issue_id,
        "segment_id": item_data.get("segment_id"),
        "start_seconds": item_data.get("start_seconds"),
        "end_seconds": item_data.get("end_seconds"),
        "center_seconds": item_data.get("center_seconds"),
        "duration_seconds": item_data.get("duration_seconds"),
        "signal_score": confidence,
        "confidence": confidence,
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": str(item_data.get("reason") or ""),
        "metadata": {
            "issue_type": issue_type,
            "severity": item_data.get("severity"),
            "is_blocking": bool(item_data.get("is_blocking", False)),
            "is_protected_context": bool(
                item_data.get("is_protected_context", False)
            ),
            "is_censor_context": bool(item_data.get("is_censor_context", False)),
            "is_technical_issue": bool(item_data.get("is_technical_issue", False)),
            "requires_review": bool(item_data.get("requires_review", True)),
            "recommendation": item_data.get("recommendation"),
            "evidence": dict(item_data.get("evidence") or {}),
            "source_signal_ids": list(item_data.get("source_signal_ids") or []),
            "review_only": True,
        },
    }


def adapt_continuity_check_report_to_signals(
    report_or_issues: Any,
) -> ContinuityCheckSignalAdapterResult:
    issues = _extract_issues(report_or_issues)

    if not issues:
        return ContinuityCheckSignalAdapterResult(
            status="empty",
            signals=[],
            signal_count=0,
            recommendation="continuity_check_signal_adapter_empty",
            metadata={
                "source": CONTINUITY_CHECK_SIGNAL_SOURCE,
                "review_only": True,
            },
        )

    signals: list[dict[str, Any]] = []
    warnings: list[str] = []

    for index, issue in enumerate(issues):
        signal = adapt_continuity_issue_to_signal(
            issue,
            index=index,
        )
        if signal is None:
            warnings.append(f"unsupported_continuity_issue:{index}")
            continue

        signals.append(signal)

    result = ContinuityCheckSignalAdapterResult(
        status="ok" if signals else "empty",
        signals=signals,
        warnings=warnings,
        recommendation=(
            "continuity_check_signals_generated"
            if signals
            else "continuity_check_signal_adapter_empty"
        ),
        metadata={
            "source": CONTINUITY_CHECK_SIGNAL_SOURCE,
            "review_only": True,
        },
    )
    result.refresh_counts()
    return result
