from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.timeline_approval_gate import (
    TIMELINE_APPROVAL_GATE_STATUS_APPROVED,
    TIMELINE_APPROVAL_GATE_STATUS_BLOCKED,
    TIMELINE_APPROVAL_GATE_STATUS_FAILED,
    TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
    TIMELINE_APPROVAL_STATUS_APPROVED,
    TIMELINE_APPROVAL_STATUS_BLOCKED,
    TIMELINE_APPROVAL_STATUS_FAILED,
    TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES,
    TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
    TIMELINE_APPROVAL_STATUS_REJECTED,
)


TIMELINE_APPROVAL_GATE_SIGNAL_SOURCE = "timeline_approval_gate"

APPROVAL_STATUS_TO_SIGNAL = {
    TIMELINE_APPROVAL_STATUS_PENDING_REVIEW: {
        "signal_type": "timeline_approval_pending_review",
        "action_hint": "wait_for_human_review",
        "priority": "high",
    },
    TIMELINE_APPROVAL_STATUS_APPROVED: {
        "signal_type": "timeline_approval_approved",
        "action_hint": "future_execution_allowed_after_approval",
        "priority": "medium",
    },
    TIMELINE_APPROVAL_STATUS_REJECTED: {
        "signal_type": "timeline_approval_rejected",
        "action_hint": "do_not_process_timeline",
        "priority": "high",
    },
    TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES: {
        "signal_type": "timeline_approval_needs_manual_changes",
        "action_hint": "manual_changes_required_before_processing",
        "priority": "high",
    },
    TIMELINE_APPROVAL_STATUS_BLOCKED: {
        "signal_type": "timeline_approval_blocked",
        "action_hint": "blocked_until_issue_resolved",
        "priority": "high",
    },
    TIMELINE_APPROVAL_STATUS_FAILED: {
        "signal_type": "timeline_approval_failed",
        "action_hint": "approval_gate_failed",
        "priority": "high",
    },
}


@dataclass
class TimelineApprovalGateSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0

    pending_review_signal_count: int = 0
    approved_signal_count: int = 0
    rejected_signal_count: int = 0
    needs_manual_changes_signal_count: int = 0
    blocked_signal_count: int = 0
    failed_signal_count: int = 0

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "timeline_approval_gate_signals_pending_review"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)
        self.pending_review_signal_count = _count_type(
            self.signals,
            "timeline_approval_pending_review",
        )
        self.approved_signal_count = _count_type(
            self.signals,
            "timeline_approval_approved",
        )
        self.rejected_signal_count = _count_type(
            self.signals,
            "timeline_approval_rejected",
        )
        self.needs_manual_changes_signal_count = _count_type(
            self.signals,
            "timeline_approval_needs_manual_changes",
        )
        self.blocked_signal_count = _count_type(
            self.signals,
            "timeline_approval_blocked",
        )
        self.failed_signal_count = _count_type(
            self.signals,
            "timeline_approval_failed",
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()

        return {
            "status": self.status,
            "signals": list(self.signals),
            "signal_count": self.signal_count,
            "pending_review_signal_count": self.pending_review_signal_count,
            "approved_signal_count": self.approved_signal_count,
            "rejected_signal_count": self.rejected_signal_count,
            "needs_manual_changes_signal_count": (
                self.needs_manual_changes_signal_count
            ),
            "blocked_signal_count": self.blocked_signal_count,
            "failed_signal_count": self.failed_signal_count,
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata or {}),
        }


def _count_type(signals: list[dict[str, Any]], signal_type: str) -> int:
    return sum(1 for signal in signals if signal.get("signal_type") == signal_type)


def _gate_to_dict(gate: Any) -> dict[str, Any]:
    if isinstance(gate, dict):
        return dict(gate)

    if hasattr(gate, "to_dict"):
        try:
            converted = gate.to_dict()
            if isinstance(converted, dict):
                return dict(converted)
        except Exception:
            return {}

    return {}


def _extract_gate(report_or_gate: Any) -> dict[str, Any]:
    if report_or_gate is None:
        return {}

    data = _gate_to_dict(report_or_gate)

    if "timeline_approval_gate" in data:
        nested = _gate_to_dict(data.get("timeline_approval_gate"))
        if nested:
            return nested

    if data:
        return data

    if hasattr(report_or_gate, "timeline_approval_gate"):
        nested = _gate_to_dict(getattr(report_or_gate, "timeline_approval_gate"))
        if nested:
            return nested

    return {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _status_score(
    approval_status: str,
    gate_status: str,
    can_proceed_to_execution: bool,
) -> float:
    if approval_status == TIMELINE_APPROVAL_STATUS_APPROVED and can_proceed_to_execution:
        return 0.95

    if gate_status in {
        TIMELINE_APPROVAL_GATE_STATUS_BLOCKED,
        TIMELINE_APPROVAL_GATE_STATUS_FAILED,
    }:
        return 0.95

    if approval_status in {
        TIMELINE_APPROVAL_STATUS_REJECTED,
        TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES,
        TIMELINE_APPROVAL_STATUS_BLOCKED,
        TIMELINE_APPROVAL_STATUS_FAILED,
    }:
        return 0.95

    return 0.85


def adapt_timeline_approval_gate_to_signal(
    gate: Any,
    index: int = 0,
) -> dict[str, Any] | None:
    gate_data = _extract_gate(gate)

    if not gate_data:
        return None

    approval_status = str(
        gate_data.get("approval_status") or TIMELINE_APPROVAL_STATUS_PENDING_REVIEW
    )

    gate_status = str(
        gate_data.get("gate_status") or TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW
    )

    mapping = APPROVAL_STATUS_TO_SIGNAL.get(approval_status)
    if not mapping:
        approval_status = TIMELINE_APPROVAL_STATUS_PENDING_REVIEW
        mapping = APPROVAL_STATUS_TO_SIGNAL[TIMELINE_APPROVAL_STATUS_PENDING_REVIEW]

    approval_gate_id = str(
        gate_data.get("approval_gate_id") or f"timeline_approval_gate_{index}"
    )

    can_proceed_to_execution = bool(
        gate_data.get("can_proceed_to_execution", False)
    )
    can_render = bool(gate_data.get("can_render", False))
    requires_human_approval = bool(
        gate_data.get("requires_human_approval", True)
    )

    score = _status_score(
        approval_status=approval_status,
        gate_status=gate_status,
        can_proceed_to_execution=can_proceed_to_execution,
    )

    return {
        "signal_id": f"timeline_approval_gate_signal_{approval_gate_id}",
        "signal_type": mapping["signal_type"],
        "source": TIMELINE_APPROVAL_GATE_SIGNAL_SOURCE,
        "source_item_id": approval_gate_id,
        "segment_id": None,
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": None,
        "duration_seconds": None,
        "signal_score": _safe_float(score, 0.85),
        "confidence": _safe_float(score, 0.85),
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": ",".join(list(gate_data.get("blocking_reasons") or [])),
        "metadata": {
            "approval_status": approval_status,
            "gate_status": gate_status,
            "can_proceed_to_execution": can_proceed_to_execution,
            "can_render": can_render,
            "requires_human_approval": requires_human_approval,
            "source_review_timeline_plan_id": gate_data.get(
                "source_review_timeline_plan_id"
            ),
            "source_review_timeline_plan_status": gate_data.get(
                "source_review_timeline_plan_status"
            ),
            "total_items": gate_data.get("total_items"),
            "review_required_count": gate_data.get("review_required_count"),
            "protected_count": gate_data.get("protected_count"),
            "censor_required_count": gate_data.get("censor_required_count"),
            "continuity_blocked_count": gate_data.get("continuity_blocked_count"),
            "blocking_reasons": list(gate_data.get("blocking_reasons") or []),
            "warnings": list(gate_data.get("warnings") or []),
            "safety_flags": list(gate_data.get("safety_flags") or []),
            "review_only": True,
            "approval_gate_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_33": True,
            "source_metadata": dict(gate_data.get("metadata") or {}),
        },
    }


def adapt_timeline_approval_gate_report_to_signals(
    report_or_gate: Any,
) -> TimelineApprovalGateSignalAdapterResult:
    signal = adapt_timeline_approval_gate_to_signal(report_or_gate)

    if signal is None:
        return TimelineApprovalGateSignalAdapterResult(
            status="empty",
            signals=[],
            signal_count=0,
            recommendation="timeline_approval_gate_signal_adapter_empty",
            metadata={
                "source": TIMELINE_APPROVAL_GATE_SIGNAL_SOURCE,
                "review_only": True,
                "approval_gate_only": True,
            },
        )

    result = TimelineApprovalGateSignalAdapterResult(
        status="ok",
        signals=[signal],
        recommendation="timeline_approval_gate_signals_generated",
        metadata={
            "source": TIMELINE_APPROVAL_GATE_SIGNAL_SOURCE,
            "review_only": True,
            "approval_gate_only": True,
            "media_unchanged": True,
        },
    )
    result.refresh_counts()
    return result
