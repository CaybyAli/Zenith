from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.final_cut_list import (
    FINAL_ACTION_BLOCKED_BY_CONTINUITY,
    FINAL_ACTION_CENSOR_KEEP,
    FINAL_ACTION_KEEP_HIGH_VALUE,
    FINAL_ACTION_KEEP_REVIEW,
    FINAL_ACTION_PROTECT,
    FINAL_ACTION_REMOVE_REVIEW,
    FINAL_ACTION_TECHNICAL_REVIEW,
    FINAL_ACTION_TRIM_REVIEW,
    FINAL_ACTION_UNKNOWN_REVIEW,
)


FINAL_CUT_LIST_SIGNAL_SOURCE = "cut_list_finalizer"

FINAL_ACTION_TO_SIGNAL = {
    FINAL_ACTION_KEEP_REVIEW: {
        "signal_type": "final_cut_list_keep_review",
        "action_hint": "review_final_keep_candidate",
        "priority": "medium",
    },
    FINAL_ACTION_KEEP_HIGH_VALUE: {
        "signal_type": "final_cut_list_keep_high_value",
        "action_hint": "review_final_high_value_keep",
        "priority": "high",
    },
    FINAL_ACTION_TRIM_REVIEW: {
        "signal_type": "final_cut_list_trim_review",
        "action_hint": "review_final_trim_candidate",
        "priority": "medium",
    },
    FINAL_ACTION_REMOVE_REVIEW: {
        "signal_type": "final_cut_list_remove_review",
        "action_hint": "review_final_remove_candidate",
        "priority": "medium",
    },
    FINAL_ACTION_PROTECT: {
        "signal_type": "final_cut_list_protect",
        "action_hint": "protect_final_cutlist_segment",
        "priority": "high",
    },
    FINAL_ACTION_CENSOR_KEEP: {
        "signal_type": "final_cut_list_censor_keep",
        "action_hint": "preserve_final_segment_for_censor_sfx",
        "priority": "high",
    },
    FINAL_ACTION_TECHNICAL_REVIEW: {
        "signal_type": "final_cut_list_technical_review",
        "action_hint": "review_final_technical_risk",
        "priority": "high",
    },
    FINAL_ACTION_BLOCKED_BY_CONTINUITY: {
        "signal_type": "final_cut_list_blocked_by_continuity",
        "action_hint": "block_final_cutlist_until_review",
        "priority": "high",
    },
    FINAL_ACTION_UNKNOWN_REVIEW: {
        "signal_type": "final_cut_list_unknown_review",
        "action_hint": "review_final_unknown_decision",
        "priority": "low",
    },
}


@dataclass
class FinalCutListSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    keep_review_signal_count: int = 0
    keep_high_value_signal_count: int = 0
    trim_review_signal_count: int = 0
    remove_review_signal_count: int = 0
    protect_signal_count: int = 0
    censor_keep_signal_count: int = 0
    technical_review_signal_count: int = 0
    blocked_by_continuity_signal_count: int = 0
    unknown_review_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_final_cut_list_signals"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)
        self.keep_review_signal_count = _count_type(
            self.signals,
            "final_cut_list_keep_review",
        )
        self.keep_high_value_signal_count = _count_type(
            self.signals,
            "final_cut_list_keep_high_value",
        )
        self.trim_review_signal_count = _count_type(
            self.signals,
            "final_cut_list_trim_review",
        )
        self.remove_review_signal_count = _count_type(
            self.signals,
            "final_cut_list_remove_review",
        )
        self.protect_signal_count = _count_type(
            self.signals,
            "final_cut_list_protect",
        )
        self.censor_keep_signal_count = _count_type(
            self.signals,
            "final_cut_list_censor_keep",
        )
        self.technical_review_signal_count = _count_type(
            self.signals,
            "final_cut_list_technical_review",
        )
        self.blocked_by_continuity_signal_count = _count_type(
            self.signals,
            "final_cut_list_blocked_by_continuity",
        )
        self.unknown_review_signal_count = _count_type(
            self.signals,
            "final_cut_list_unknown_review",
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()

        return {
            "status": self.status,
            "signals": list(self.signals),
            "signal_count": self.signal_count,
            "keep_review_signal_count": self.keep_review_signal_count,
            "keep_high_value_signal_count": self.keep_high_value_signal_count,
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

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "FinalCutListSignalAdapterResult":
        if not isinstance(data, dict):
            data = {}

        result = cls(
            status=str(data.get("status") or "ok"),
            signals=list(data.get("signals") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(
                data.get("recommendation") or "review_final_cut_list_signals"
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


def _extract_items(report_or_items: Any) -> list[Any]:
    if report_or_items is None:
        return []

    if isinstance(report_or_items, list):
        return report_or_items

    if isinstance(report_or_items, tuple):
        return list(report_or_items)

    if isinstance(report_or_items, dict):
        for key in ("final_items", "final_cut_list_items", "items"):
            value = report_or_items.get(key)
            if isinstance(value, list):
                return list(value)

        plan = report_or_items.get("final_cut_list_plan")
        if isinstance(plan, dict):
            value = plan.get("final_items")
            if isinstance(value, list):
                return list(value)

    if hasattr(report_or_items, "final_items"):
        value = getattr(report_or_items, "final_items")
        if isinstance(value, list):
            return list(value)

    if hasattr(report_or_items, "final_cut_list_plan"):
        plan = getattr(report_or_items, "final_cut_list_plan")
        if hasattr(plan, "final_items"):
            value = getattr(plan, "final_items")
            if isinstance(value, list):
                return list(value)

    return []


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def adapt_final_cut_list_item_to_signal(
    item: Any,
    index: int = 0,
) -> dict[str, Any] | None:
    item_data = _item_to_dict(item)
    final_action = str(item_data.get("final_action") or "").strip().upper()

    mapping = FINAL_ACTION_TO_SIGNAL.get(final_action)
    if not mapping:
        mapping = FINAL_ACTION_TO_SIGNAL[FINAL_ACTION_UNKNOWN_REVIEW]
        final_action = FINAL_ACTION_UNKNOWN_REVIEW

    final_item_id = str(
        item_data.get("final_item_id") or f"final_cut_list_item_{index}"
    )
    confidence = _safe_float(item_data.get("final_confidence"), 0.0)

    return {
        "signal_id": f"cut_list_finalizer_signal_{final_item_id}",
        "signal_type": mapping["signal_type"],
        "source": FINAL_CUT_LIST_SIGNAL_SOURCE,
        "source_item_id": item_data.get("source_item_id") or final_item_id,
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
            "final_action": final_action,
            "priority": item_data.get("priority"),
            "segment_type": item_data.get("segment_type"),
            "cut_list_action": item_data.get("cut_list_action"),
            "duration_status": item_data.get("duration_status"),
            "transition_type": item_data.get("transition_type"),
            "murch_score": _safe_float(item_data.get("murch_score"), 0.0),
            "continuity_blocked": bool(
                item_data.get("continuity_blocked", False)
            ),
            "is_protected": bool(item_data.get("is_protected", False)),
            "is_censor_keep": bool(item_data.get("is_censor_keep", False)),
            "is_technical_review": bool(
                item_data.get("is_technical_review", False)
            ),
            "is_review_required": bool(
                item_data.get("is_review_required", True)
            ),
            "is_keep_candidate": bool(item_data.get("is_keep_candidate", False)),
            "is_trim_candidate": bool(item_data.get("is_trim_candidate", False)),
            "is_remove_candidate": bool(
                item_data.get("is_remove_candidate", False)
            ),
            "is_invalid_timing": bool(item_data.get("is_invalid_timing", False)),
            "recommended_start_seconds": item_data.get(
                "recommended_start_seconds"
            ),
            "recommended_end_seconds": item_data.get("recommended_end_seconds"),
            "recommended_duration_seconds": item_data.get(
                "recommended_duration_seconds"
            ),
            "decision_basis": dict(item_data.get("decision_basis") or {}),
            "source_signal_ids": list(item_data.get("source_signal_ids") or []),
            "review_only": True,
        },
    }


def adapt_final_cut_list_report_to_signals(
    report_or_items: Any,
) -> FinalCutListSignalAdapterResult:
    items = _extract_items(report_or_items)

    if not items:
        return FinalCutListSignalAdapterResult(
            status="empty",
            signals=[],
            signal_count=0,
            recommendation="final_cut_list_signal_adapter_empty",
            metadata={
                "source": FINAL_CUT_LIST_SIGNAL_SOURCE,
                "review_only": True,
            },
        )

    signals: list[dict[str, Any]] = []
    warnings: list[str] = []

    for index, item in enumerate(items):
        signal = adapt_final_cut_list_item_to_signal(item, index=index)
        if signal is None:
            warnings.append(f"unsupported_final_cut_list_item:{index}")
            continue

        signals.append(signal)

    result = FinalCutListSignalAdapterResult(
        status="ok" if signals else "empty",
        signals=signals,
        warnings=warnings,
        recommendation=(
            "final_cut_list_signals_generated"
            if signals
            else "final_cut_list_signal_adapter_empty"
        ),
        metadata={
            "source": FINAL_CUT_LIST_SIGNAL_SOURCE,
            "review_only": True,
        },
    )
    result.refresh_counts()
    return result
