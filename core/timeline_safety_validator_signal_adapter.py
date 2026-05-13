from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.timeline_safety_validator import (
    TIMELINE_SAFETY_REASON_APPROVAL_OVERRIDDEN_BY_SAFETY_VALIDATOR,
    TIMELINE_SAFETY_REASON_CENSOR_ITEM_NOT_PROTECTED,
    TIMELINE_SAFETY_REASON_CONTINUITY_BLOCK_NOT_PRESERVED,
    TIMELINE_SAFETY_REASON_END_BEFORE_START,
    TIMELINE_SAFETY_REASON_EXECUTION_NOT_SAFE,
    TIMELINE_SAFETY_REASON_INVALID_SOURCE_TIMING,
    TIMELINE_SAFETY_REASON_NEGATIVE_END_TIME,
    TIMELINE_SAFETY_REASON_NEGATIVE_START_TIME,
    TIMELINE_SAFETY_REASON_PROTECTED_ITEM_HAS_UNSAFE_ACTION,
    TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34,
    TIMELINE_SAFETY_REASON_TIMELINE_GAP,
    TIMELINE_SAFETY_REASON_TIMELINE_OVERLAP,
    TIMELINE_SAFETY_REASON_ZERO_OR_NEGATIVE_DURATION,
    TIMELINE_SAFETY_STATUS_BLOCKED,
    TIMELINE_SAFETY_STATUS_FAILED,
    TIMELINE_SAFETY_STATUS_PASSED,
    TIMELINE_SAFETY_STATUS_PASSED_WITH_WARNINGS,
)


TIMELINE_SAFETY_VALIDATOR_SIGNAL_SOURCE = "timeline_safety_validator"

SAFETY_STATUS_TO_SIGNAL = {
    TIMELINE_SAFETY_STATUS_PASSED: {
        "signal_type": "timeline_safety_passed",
        "action_hint": "timeline_safety_validated_for_future_review_flow",
        "priority": "medium",
    },
    TIMELINE_SAFETY_STATUS_PASSED_WITH_WARNINGS: {
        "signal_type": "timeline_safety_passed_with_warnings",
        "action_hint": "timeline_safety_validated_with_warnings",
        "priority": "medium",
    },
    TIMELINE_SAFETY_STATUS_BLOCKED: {
        "signal_type": "timeline_safety_blocked",
        "action_hint": "timeline_must_not_execute_until_fixed",
        "priority": "high",
    },
    TIMELINE_SAFETY_STATUS_FAILED: {
        "signal_type": "timeline_safety_failed",
        "action_hint": "timeline_safety_validator_failed",
        "priority": "high",
    },
}

SAFETY_REASON_TO_SIGNAL_TYPE = {
    TIMELINE_SAFETY_REASON_INVALID_SOURCE_TIMING: (
        "timeline_safety_invalid_timing"
    ),
    TIMELINE_SAFETY_REASON_NEGATIVE_START_TIME: (
        "timeline_safety_invalid_timing"
    ),
    TIMELINE_SAFETY_REASON_NEGATIVE_END_TIME: (
        "timeline_safety_invalid_timing"
    ),
    TIMELINE_SAFETY_REASON_END_BEFORE_START: (
        "timeline_safety_invalid_timing"
    ),
    TIMELINE_SAFETY_REASON_ZERO_OR_NEGATIVE_DURATION: (
        "timeline_safety_invalid_timing"
    ),
    TIMELINE_SAFETY_REASON_TIMELINE_OVERLAP: "timeline_safety_overlap",
    TIMELINE_SAFETY_REASON_TIMELINE_GAP: "timeline_safety_gap",
    TIMELINE_SAFETY_REASON_PROTECTED_ITEM_HAS_UNSAFE_ACTION: (
        "timeline_safety_protected_violation"
    ),
    TIMELINE_SAFETY_REASON_CENSOR_ITEM_NOT_PROTECTED: (
        "timeline_safety_censor_violation"
    ),
    TIMELINE_SAFETY_REASON_CONTINUITY_BLOCK_NOT_PRESERVED: (
        "timeline_safety_continuity_violation"
    ),
    TIMELINE_SAFETY_REASON_APPROVAL_OVERRIDDEN_BY_SAFETY_VALIDATOR: (
        "timeline_safety_approval_violation"
    ),
    TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34: (
        "timeline_safety_approval_violation"
    ),
    TIMELINE_SAFETY_REASON_EXECUTION_NOT_SAFE: (
        "timeline_safety_approval_violation"
    ),
}


@dataclass
class TimelineSafetyValidatorSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0

    passed_signal_count: int = 0
    passed_with_warnings_signal_count: int = 0
    blocked_signal_count: int = 0
    failed_signal_count: int = 0

    invalid_timing_signal_count: int = 0
    overlap_signal_count: int = 0
    gap_signal_count: int = 0
    protected_violation_signal_count: int = 0
    censor_violation_signal_count: int = 0
    continuity_violation_signal_count: int = 0
    approval_violation_signal_count: int = 0

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "timeline_safety_validator_signals_pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)

        self.passed_signal_count = _count_type(
            self.signals,
            "timeline_safety_passed",
        )
        self.passed_with_warnings_signal_count = _count_type(
            self.signals,
            "timeline_safety_passed_with_warnings",
        )
        self.blocked_signal_count = _count_type(
            self.signals,
            "timeline_safety_blocked",
        )
        self.failed_signal_count = _count_type(
            self.signals,
            "timeline_safety_failed",
        )
        self.invalid_timing_signal_count = _count_type(
            self.signals,
            "timeline_safety_invalid_timing",
        )
        self.overlap_signal_count = _count_type(
            self.signals,
            "timeline_safety_overlap",
        )
        self.gap_signal_count = _count_type(
            self.signals,
            "timeline_safety_gap",
        )
        self.protected_violation_signal_count = _count_type(
            self.signals,
            "timeline_safety_protected_violation",
        )
        self.censor_violation_signal_count = _count_type(
            self.signals,
            "timeline_safety_censor_violation",
        )
        self.continuity_violation_signal_count = _count_type(
            self.signals,
            "timeline_safety_continuity_violation",
        )
        self.approval_violation_signal_count = _count_type(
            self.signals,
            "timeline_safety_approval_violation",
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()

        return {
            "status": self.status,
            "signals": list(self.signals),
            "signal_count": self.signal_count,
            "passed_signal_count": self.passed_signal_count,
            "passed_with_warnings_signal_count": (
                self.passed_with_warnings_signal_count
            ),
            "blocked_signal_count": self.blocked_signal_count,
            "failed_signal_count": self.failed_signal_count,
            "invalid_timing_signal_count": self.invalid_timing_signal_count,
            "overlap_signal_count": self.overlap_signal_count,
            "gap_signal_count": self.gap_signal_count,
            "protected_violation_signal_count": (
                self.protected_violation_signal_count
            ),
            "censor_violation_signal_count": (
                self.censor_violation_signal_count
            ),
            "continuity_violation_signal_count": (
                self.continuity_violation_signal_count
            ),
            "approval_violation_signal_count": (
                self.approval_violation_signal_count
            ),
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata or {}),
        }


def _count_type(signals: list[dict[str, Any]], signal_type: str) -> int:
    return sum(1 for signal in signals if signal.get("signal_type") == signal_type)


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    if hasattr(value, "to_dict"):
        try:
            converted = value.to_dict()
            if isinstance(converted, dict):
                return dict(converted)
        except Exception:
            return {}

    return {}


def _extract_validation(report_or_validation: Any) -> dict[str, Any]:
    if report_or_validation is None:
        return {}

    data = _to_dict(report_or_validation)

    if "timeline_safety_validation" in data:
        nested = _to_dict(data.get("timeline_safety_validation"))
        if nested:
            return nested

    if data:
        return data

    if hasattr(report_or_validation, "timeline_safety_validation"):
        nested = _to_dict(
            getattr(report_or_validation, "timeline_safety_validation")
        )
        if nested:
            return nested

    return {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _status_score(validation_status: str) -> float:
    if validation_status in {
        TIMELINE_SAFETY_STATUS_BLOCKED,
        TIMELINE_SAFETY_STATUS_FAILED,
    }:
        return 0.95

    if validation_status == TIMELINE_SAFETY_STATUS_PASSED:
        return 0.9

    if validation_status == TIMELINE_SAFETY_STATUS_PASSED_WITH_WARNINGS:
        return 0.85

    return 0.75


def _build_status_signal(
    validation_data: dict[str, Any],
    validation_id: str,
) -> dict[str, Any]:
    validation_status = str(
        validation_data.get("validation_status")
        or TIMELINE_SAFETY_STATUS_BLOCKED
    )

    mapping = SAFETY_STATUS_TO_SIGNAL.get(validation_status)
    if not mapping:
        validation_status = TIMELINE_SAFETY_STATUS_BLOCKED
        mapping = SAFETY_STATUS_TO_SIGNAL[TIMELINE_SAFETY_STATUS_BLOCKED]

    score = _status_score(validation_status)

    return {
        "signal_id": f"timeline_safety_status_signal_{validation_id}",
        "signal_type": mapping["signal_type"],
        "source": TIMELINE_SAFETY_VALIDATOR_SIGNAL_SOURCE,
        "source_item_id": validation_id,
        "segment_id": None,
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": None,
        "duration_seconds": None,
        "signal_score": _safe_float(score, 0.85),
        "confidence": _safe_float(score, 0.85),
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": ",".join(list(validation_data.get("blocking_errors") or [])),
        "metadata": {
            "validation_status": validation_status,
            "is_safe_for_future_execution": bool(
                validation_data.get("is_safe_for_future_execution", False)
            ),
            "is_safe_for_render": False,
            "requires_manual_review": bool(
                validation_data.get("requires_manual_review", True)
            ),
            "source_review_timeline_plan_id": validation_data.get(
                "source_review_timeline_plan_id"
            ),
            "source_timeline_approval_gate_id": validation_data.get(
                "source_timeline_approval_gate_id"
            ),
            "blocking_errors": list(
                validation_data.get("blocking_errors") or []
            ),
            "warnings": list(validation_data.get("warnings") or []),
            "review_only": True,
            "safety_validator_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_34": True,
            "no_render_in_2b_34": True,
            "source_metadata": dict(validation_data.get("metadata") or {}),
        },
    }


def _build_reason_signals(
    validation_data: dict[str, Any],
    validation_id: str,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []

    reasons = list(validation_data.get("blocking_errors") or [])
    reasons.extend(list(validation_data.get("warnings") or []))

    seen: set[str] = set()

    for index, reason in enumerate(reasons):
        reason = str(reason)
        if reason in seen:
            continue

        seen.add(reason)

        signal_type = SAFETY_REASON_TO_SIGNAL_TYPE.get(reason)
        if not signal_type:
            continue

        signals.append(
            {
                "signal_id": (
                    f"timeline_safety_reason_signal_{validation_id}_{index}"
                ),
                "signal_type": signal_type,
                "source": TIMELINE_SAFETY_VALIDATOR_SIGNAL_SOURCE,
                "source_item_id": validation_id,
                "segment_id": None,
                "start_seconds": None,
                "end_seconds": None,
                "center_seconds": None,
                "duration_seconds": None,
                "signal_score": 0.9,
                "confidence": 0.9,
                "priority": "high",
                "action_hint": "timeline_safety_issue_requires_review",
                "reason": reason,
                "metadata": {
                    "validation_id": validation_id,
                    "reason": reason,
                    "review_only": True,
                    "safety_validator_only": True,
                    "media_unchanged": True,
                    "no_execution_in_2b_34": True,
                    "no_render_in_2b_34": True,
                },
            }
        )

    return signals


def adapt_timeline_safety_validation_to_signals(
    validation: Any,
) -> TimelineSafetyValidatorSignalAdapterResult:
    validation_data = _extract_validation(validation)

    if not validation_data:
        return TimelineSafetyValidatorSignalAdapterResult(
            status="empty",
            signals=[],
            signal_count=0,
            recommendation="timeline_safety_validator_signal_adapter_empty",
            metadata={
                "source": TIMELINE_SAFETY_VALIDATOR_SIGNAL_SOURCE,
                "review_only": True,
                "safety_validator_only": True,
            },
        )

    validation_id = str(
        validation_data.get("safety_validation_id")
        or "timeline_safety_validation_unknown"
    )

    signals = [_build_status_signal(validation_data, validation_id)]
    signals.extend(_build_reason_signals(validation_data, validation_id))

    result = TimelineSafetyValidatorSignalAdapterResult(
        status="ok",
        signals=signals,
        recommendation="timeline_safety_validator_signals_generated",
        metadata={
            "source": TIMELINE_SAFETY_VALIDATOR_SIGNAL_SOURCE,
            "review_only": True,
            "safety_validator_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_34": True,
            "no_render_in_2b_34": True,
        },
    )
    result.refresh_counts()
    return result


def adapt_timeline_safety_validator_report_to_signals(
    report_or_validation: Any,
) -> TimelineSafetyValidatorSignalAdapterResult:
    return adapt_timeline_safety_validation_to_signals(report_or_validation)
