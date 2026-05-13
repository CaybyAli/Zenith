from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.cut_list import (
    CUT_LIST_ACTION_CENSOR_KEEP,
    CUT_LIST_ACTION_KEEP,
    CUT_LIST_ACTION_PROTECT,
    CUT_LIST_ACTION_REVIEW_KEEP,
    CUT_LIST_ACTION_REVIEW_REMOVE,
    CUT_LIST_ACTION_REVIEW_TRIM,
    CUT_LIST_ACTION_TECHNICAL_REVIEW,
    CUT_LIST_ACTION_UNKNOWN_REVIEW,
)


CUT_LIST_SIGNAL_SOURCE = "cut_list_generator"


ACTION_TO_SIGNAL = {
    CUT_LIST_ACTION_KEEP: {
        "signal_type": "cut_list_keep_candidate",
        "action_hint": "review_keep_candidate",
        "priority": "high",
    },
    CUT_LIST_ACTION_REVIEW_KEEP: {
        "signal_type": "cut_list_review_keep",
        "action_hint": "review_keep_candidate",
        "priority": "medium",
    },
    CUT_LIST_ACTION_REVIEW_TRIM: {
        "signal_type": "cut_list_review_trim",
        "action_hint": "review_trim_candidate",
        "priority": "medium",
    },
    CUT_LIST_ACTION_REVIEW_REMOVE: {
        "signal_type": "cut_list_review_remove",
        "action_hint": "review_remove_candidate",
        "priority": "medium",
    },
    CUT_LIST_ACTION_PROTECT: {
        "signal_type": "cut_list_protect_segment",
        "action_hint": "protect_segment_from_cut",
        "priority": "high",
    },
    CUT_LIST_ACTION_CENSOR_KEEP: {
        "signal_type": "cut_list_censor_keep",
        "action_hint": "preserve_segment_for_censor_sfx",
        "priority": "high",
    },
    CUT_LIST_ACTION_TECHNICAL_REVIEW: {
        "signal_type": "cut_list_technical_review",
        "action_hint": "review_technical_cut_risk",
        "priority": "high",
    },
    CUT_LIST_ACTION_UNKNOWN_REVIEW: {
        "signal_type": "cut_list_unknown_review",
        "action_hint": "review_unknown_cut_decision",
        "priority": "low",
    },
}


@dataclass
class CutListSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    keep_signal_count: int = 0
    review_keep_signal_count: int = 0
    review_trim_signal_count: int = 0
    review_remove_signal_count: int = 0
    protect_signal_count: int = 0
    censor_keep_signal_count: int = 0
    technical_review_signal_count: int = 0
    unknown_review_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_cut_list_signals"

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)
        self.keep_signal_count = _count_type(self.signals, "cut_list_keep_candidate")
        self.review_keep_signal_count = _count_type(self.signals, "cut_list_review_keep")
        self.review_trim_signal_count = _count_type(self.signals, "cut_list_review_trim")
        self.review_remove_signal_count = _count_type(self.signals, "cut_list_review_remove")
        self.protect_signal_count = _count_type(self.signals, "cut_list_protect_segment")
        self.censor_keep_signal_count = _count_type(self.signals, "cut_list_censor_keep")
        self.technical_review_signal_count = _count_type(self.signals, "cut_list_technical_review")
        self.unknown_review_signal_count = _count_type(self.signals, "cut_list_unknown_review")

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()
        return {
            "status": self.status,
            "signals": list(self.signals),
            "signal_count": self.signal_count,
            "keep_signal_count": self.keep_signal_count,
            "review_keep_signal_count": self.review_keep_signal_count,
            "review_trim_signal_count": self.review_trim_signal_count,
            "review_remove_signal_count": self.review_remove_signal_count,
            "protect_signal_count": self.protect_signal_count,
            "censor_keep_signal_count": self.censor_keep_signal_count,
            "technical_review_signal_count": self.technical_review_signal_count,
            "unknown_review_signal_count": self.unknown_review_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CutListSignalAdapterResult":
        if not isinstance(data, dict):
            data = {}

        result = cls(
            status=str(data.get("status") or "ok"),
            signals=list(data.get("signals") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(data.get("recommendation") or "review_cut_list_signals"),
        )
        result.refresh_counts()
        return result


def _count_type(signals: list[dict[str, Any]], signal_type: str) -> int:
    return sum(1 for signal in signals if signal.get("signal_type") == signal_type)


def _read_value(source: Any, key: str, default: Any = None) -> Any:
    if source is None:
        return default

    if isinstance(source, dict):
        return source.get(key, default)

    return getattr(source, key, default)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
        if isinstance(report_or_items.get("items"), list):
            return list(report_or_items.get("items") or [])

        plan = report_or_items.get("cut_list_plan")
        if isinstance(plan, dict) and isinstance(plan.get("items"), list):
            return list(plan.get("items") or [])

    if hasattr(report_or_items, "items"):
        items = getattr(report_or_items, "items")
        if isinstance(items, list):
            return list(items)

    if hasattr(report_or_items, "cut_list_plan"):
        plan = getattr(report_or_items, "cut_list_plan")
        if hasattr(plan, "items"):
            items = getattr(plan, "items")
            if isinstance(items, list):
                return list(items)

    return []


def adapt_cut_list_item_to_signal(item: Any, index: int = 0) -> dict[str, Any] | None:
    item_data = _item_to_dict(item)
    action = str(item_data.get("proposed_action") or "").strip().upper()

    mapping = ACTION_TO_SIGNAL.get(action)
    if not mapping:
        return None

    item_id = str(item_data.get("item_id") or f"cutlist_item_{index}")
    segment_id = item_data.get("segment_id") or item_data.get("source_segment_id")

    signal = {
        "signal_id": f"cut_list_signal_{item_id}",
        "signal_type": mapping["signal_type"],
        "source": CUT_LIST_SIGNAL_SOURCE,
        "source_item_id": item_id,
        "segment_id": segment_id,
        "start_seconds": item_data.get("start_seconds"),
        "end_seconds": item_data.get("end_seconds"),
        "center_seconds": item_data.get("center_seconds"),
        "duration_seconds": item_data.get("duration_seconds"),
        "confidence": _safe_float(item_data.get("action_confidence"), 0.0),
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": str(item_data.get("reason") or ""),
        "metadata": {
            "cut_list_action": action,
            "segment_type": item_data.get("segment_type"),
            "murch_score": item_data.get("murch_score"),
            "content_value_score": item_data.get("content_value_score"),
            "risk_score": item_data.get("risk_score"),
            "protection_score": item_data.get("protection_score"),
            "censor_required": bool(item_data.get("censor_required", False)),
            "is_protected": bool(item_data.get("is_protected", False)),
            "is_review_required": bool(item_data.get("is_review_required", True)),
            "decision_basis": dict(item_data.get("decision_basis") or {}),
        },
    }

    return signal


def adapt_cut_list_report_to_signals(report_or_items: Any) -> CutListSignalAdapterResult:
    items = _extract_items(report_or_items)

    if not items:
        return CutListSignalAdapterResult(
            status="empty",
            signals=[],
            signal_count=0,
            recommendation="cut_list_signal_adapter_empty",
        )

    signals = []
    warnings = []

    for index, item in enumerate(items):
        signal = adapt_cut_list_item_to_signal(item, index=index)
        if signal is None:
            item_data = _item_to_dict(item)
            warnings.append(
                f"unsupported_cut_list_action:{item_data.get('proposed_action')}"
            )
            continue

        signals.append(signal)

    result = CutListSignalAdapterResult(
        status="ok" if signals else "empty",
        signals=signals,
        warnings=warnings,
        recommendation=(
            "cut_list_signals_generated"
            if signals
            else "cut_list_signal_adapter_empty"
        ),
    )
    result.refresh_counts()
    return result
