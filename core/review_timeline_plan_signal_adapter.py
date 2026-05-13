from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.review_timeline_plan import (
    REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY,
    REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
    REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
    REVIEW_TIMELINE_ACTION_PROTECT,
    REVIEW_TIMELINE_ACTION_REMOVE_REVIEW,
    REVIEW_TIMELINE_ACTION_TECHNICAL_REVIEW,
    REVIEW_TIMELINE_ACTION_TRIM_REVIEW,
    REVIEW_TIMELINE_ACTION_UNKNOWN_REVIEW,
)


REVIEW_TIMELINE_PLAN_SIGNAL_SOURCE = "review_timeline_plan"

ACTION_TO_SIGNAL = {
    REVIEW_TIMELINE_ACTION_KEEP_REVIEW: {
        "signal_type": "review_timeline_keep_review",
        "action_hint": "review_keep_candidate",
        "priority": "medium",
    },
    REVIEW_TIMELINE_ACTION_TRIM_REVIEW: {
        "signal_type": "review_timeline_trim_review",
        "action_hint": "human_review_trim_candidate",
        "priority": "medium",
    },
    REVIEW_TIMELINE_ACTION_REMOVE_REVIEW: {
        "signal_type": "review_timeline_remove_review",
        "action_hint": "human_review_remove_candidate",
        "priority": "medium",
    },
    REVIEW_TIMELINE_ACTION_PROTECT: {
        "signal_type": "review_timeline_protect",
        "action_hint": "preserve_protected_item",
        "priority": "high",
    },
    REVIEW_TIMELINE_ACTION_CENSOR_KEEP: {
        "signal_type": "review_timeline_censor_keep",
        "action_hint": "preserve_censor_item_for_later_approval",
        "priority": "high",
    },
    REVIEW_TIMELINE_ACTION_TECHNICAL_REVIEW: {
        "signal_type": "review_timeline_technical_review",
        "action_hint": "human_review_technical_item",
        "priority": "high",
    },
    REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY: {
        "signal_type": "review_timeline_blocked_by_continuity",
        "action_hint": "keep_blocked_until_human_review",
        "priority": "high",
    },
    REVIEW_TIMELINE_ACTION_UNKNOWN_REVIEW: {
        "signal_type": "review_timeline_unknown_review",
        "action_hint": "human_review_unknown_item",
        "priority": "low",
    },
}


@dataclass
class ReviewTimelinePlanSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0

    keep_review_signal_count: int = 0
    trim_review_signal_count: int = 0
    remove_review_signal_count: int = 0
    protect_signal_count: int = 0
    censor_keep_signal_count: int = 0
    technical_review_signal_count: int = 0
    blocked_by_continuity_signal_count: int = 0
    unknown_review_signal_count: int = 0

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_timeline_plan_signals_pending_review"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)
        self.keep_review_signal_count = _count_type(
            self.signals,
            "review_timeline_keep_review",
        )
        self.trim_review_signal_count = _count_type(
            self.signals,
            "review_timeline_trim_review",
        )
        self.remove_review_signal_count = _count_type(
            self.signals,
            "review_timeline_remove_review",
        )
        self.protect_signal_count = _count_type(
            self.signals,
            "review_timeline_protect",
        )
        self.censor_keep_signal_count = _count_type(
            self.signals,
            "review_timeline_censor_keep",
        )
        self.technical_review_signal_count = _count_type(
            self.signals,
            "review_timeline_technical_review",
        )
        self.blocked_by_continuity_signal_count = _count_type(
            self.signals,
            "review_timeline_blocked_by_continuity",
        )
        self.unknown_review_signal_count = _count_type(
            self.signals,
            "review_timeline_unknown_review",
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()

        return {
            "status": self.status,
            "signals": list(self.signals),
            "signal_count": self.signal_count,
            "keep_review_signal_count": self.keep_review_signal_count,
            "trim_review_signal_count": self.trim_review_signal_count,
            "remove_review_signal_count": self.remove_review_signal_count,
            "protect_signal_count": self.protect_signal_count,
            "censor_keep_signal_count": self.censor_keep_signal_count,
            "technical_review_signal_count": self.technical_review_signal_count,
            "blocked_by_continuity_signal_count": (
                self.blocked_by_continuity_signal_count
            ),
            "unknown_review_signal_count": self.unknown_review_signal_count,
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata or {}),
        }


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


def _extract_items(report_or_items: Any) -> list[Any]:
    if report_or_items is None:
        return []

    if isinstance(report_or_items, list):
        return report_or_items

    if isinstance(report_or_items, tuple):
        return list(report_or_items)

    if isinstance(report_or_items, dict):
        for key in ("items", "review_timeline_plan_items"):
            value = report_or_items.get(key)
            if isinstance(value, list):
                return list(value)

        plan = report_or_items.get("review_timeline_plan")
        if isinstance(plan, dict):
            value = plan.get("items")
            if isinstance(value, list):
                return list(value)

    if hasattr(report_or_items, "items"):
        value = getattr(report_or_items, "items")
        if isinstance(value, list):
            return list(value)

    if hasattr(report_or_items, "review_timeline_plan"):
        plan = getattr(report_or_items, "review_timeline_plan")
        if hasattr(plan, "items"):
            value = getattr(plan, "items")
            if isinstance(value, list):
                return list(value)

    return []


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def adapt_review_timeline_plan_item_to_signal(
    item: Any,
    index: int = 0,
) -> dict[str, Any] | None:
    item_data = _item_to_dict(item)
    action = str(item_data.get("action") or REVIEW_TIMELINE_ACTION_UNKNOWN_REVIEW)

    mapping = ACTION_TO_SIGNAL.get(action)
    if not mapping:
        mapping = ACTION_TO_SIGNAL[REVIEW_TIMELINE_ACTION_UNKNOWN_REVIEW]
        action = REVIEW_TIMELINE_ACTION_UNKNOWN_REVIEW

    item_id = str(item_data.get("timeline_item_id") or f"review_timeline_item_{index}")

    review_required = bool(item_data.get("review_required", True))
    censor_sfx_required = bool(item_data.get("censor_sfx_required", False))
    continuity_blocked = bool(item_data.get("continuity_blocked", False))

    score = 0.65
    if item_data.get("protection_status") in {"protected", "censor_protected"}:
        score = 0.95
    if censor_sfx_required or continuity_blocked:
        score = 0.95
    if review_required:
        score = max(score, 0.75)

    return {
        "signal_id": f"review_timeline_plan_signal_{item_id}",
        "signal_type": mapping["signal_type"],
        "source": REVIEW_TIMELINE_PLAN_SIGNAL_SOURCE,
        "source_item_id": item_id,
        "segment_id": item_data.get("source_segment_id"),
        "start_seconds": item_data.get("source_start_seconds"),
        "end_seconds": item_data.get("source_end_seconds"),
        "center_seconds": None,
        "duration_seconds": item_data.get("duration_seconds"),
        "signal_score": _safe_float(score, 0.75),
        "confidence": _safe_float(score, 0.75),
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": str(item_data.get("review_reason") or ""),
        "metadata": {
            "review_timeline_action": action,
            "final_decision": item_data.get("final_decision"),
            "timeline_start_seconds": item_data.get("start_seconds"),
            "timeline_end_seconds": item_data.get("end_seconds"),
            "protection_status": item_data.get("protection_status"),
            "censor_sfx_required": censor_sfx_required,
            "continuity_blocked": continuity_blocked,
            "review_required": review_required,
            "safety_flags": list(item_data.get("safety_flags") or []),
            "notes": list(item_data.get("notes") or []),
            "review_only": True,
            "approval_required": True,
            "source_metadata": dict(item_data.get("metadata") or {}),
        },
    }


def adapt_review_timeline_plan_report_to_signals(
    report_or_items: Any,
) -> ReviewTimelinePlanSignalAdapterResult:
    items = _extract_items(report_or_items)

    if not items:
        return ReviewTimelinePlanSignalAdapterResult(
            status="empty",
            signals=[],
            signal_count=0,
            recommendation="review_timeline_plan_signal_adapter_empty",
            metadata={
                "source": REVIEW_TIMELINE_PLAN_SIGNAL_SOURCE,
                "review_only": True,
            },
        )

    signals: list[dict[str, Any]] = []
    warnings: list[str] = []

    for index, item in enumerate(items):
        signal = adapt_review_timeline_plan_item_to_signal(item, index=index)
        if signal is None:
            warnings.append(f"unsupported_review_timeline_plan_item:{index}")
            continue

        signals.append(signal)

    result = ReviewTimelinePlanSignalAdapterResult(
        status="ok" if signals else "empty",
        signals=signals,
        warnings=warnings,
        recommendation=(
            "review_timeline_plan_signals_generated"
            if signals
            else "review_timeline_plan_signal_adapter_empty"
        ),
        metadata={
            "source": REVIEW_TIMELINE_PLAN_SIGNAL_SOURCE,
            "review_only": True,
            "approval_required": True,
        },
    )
    result.refresh_counts()
    return result
