from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


TRANSITION_DECISION_SIGNAL_SOURCE = "transition_decision"

TRANSITION_TYPE_TO_SIGNAL = {
    "hard_cut_review": {
        "signal_type": "transition_hard_cut_review",
        "action_hint": "review_hard_cut_transition",
        "priority": "medium",
    },
    "j_cut_review": {
        "signal_type": "transition_j_cut_review",
        "action_hint": "review_j_cut_transition",
        "priority": "medium",
    },
    "l_cut_review": {
        "signal_type": "transition_l_cut_review",
        "action_hint": "review_l_cut_transition",
        "priority": "medium",
    },
    "quick_fade_review": {
        "signal_type": "transition_quick_fade_review",
        "action_hint": "review_quick_fade_transition",
        "priority": "medium",
    },
    "no_cut_protect": {
        "signal_type": "transition_no_cut_protect",
        "action_hint": "protect_from_blind_transition",
        "priority": "high",
    },
    "censor_safe_keep": {
        "signal_type": "transition_censor_safe_keep",
        "action_hint": "preserve_transition_for_censor_sfx",
        "priority": "high",
    },
    "technical_transition_review": {
        "signal_type": "transition_technical_review",
        "action_hint": "review_transition_technical_risk",
        "priority": "high",
    },
    "transition_unknown_review": {
        "signal_type": "transition_unknown_review",
        "action_hint": "review_unknown_transition_decision",
        "priority": "low",
    },
}


@dataclass
class TransitionDecisionSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    hard_cut_review_signal_count: int = 0
    j_cut_review_signal_count: int = 0
    l_cut_review_signal_count: int = 0
    quick_fade_review_signal_count: int = 0
    no_cut_protect_signal_count: int = 0
    censor_safe_keep_signal_count: int = 0
    technical_review_signal_count: int = 0
    unknown_review_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_transition_decision_signals"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)
        self.hard_cut_review_signal_count = _count_type(
            self.signals,
            "transition_hard_cut_review",
        )
        self.j_cut_review_signal_count = _count_type(
            self.signals,
            "transition_j_cut_review",
        )
        self.l_cut_review_signal_count = _count_type(
            self.signals,
            "transition_l_cut_review",
        )
        self.quick_fade_review_signal_count = _count_type(
            self.signals,
            "transition_quick_fade_review",
        )
        self.no_cut_protect_signal_count = _count_type(
            self.signals,
            "transition_no_cut_protect",
        )
        self.censor_safe_keep_signal_count = _count_type(
            self.signals,
            "transition_censor_safe_keep",
        )
        self.technical_review_signal_count = _count_type(
            self.signals,
            "transition_technical_review",
        )
        self.unknown_review_signal_count = _count_type(
            self.signals,
            "transition_unknown_review",
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()
        return {
            "status": self.status,
            "signals": list(self.signals),
            "signal_count": self.signal_count,
            "hard_cut_review_signal_count": self.hard_cut_review_signal_count,
            "j_cut_review_signal_count": self.j_cut_review_signal_count,
            "l_cut_review_signal_count": self.l_cut_review_signal_count,
            "quick_fade_review_signal_count": self.quick_fade_review_signal_count,
            "no_cut_protect_signal_count": self.no_cut_protect_signal_count,
            "censor_safe_keep_signal_count": self.censor_safe_keep_signal_count,
            "technical_review_signal_count": self.technical_review_signal_count,
            "unknown_review_signal_count": self.unknown_review_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "TransitionDecisionSignalAdapterResult":
        if not isinstance(data, dict):
            data = {}

        result = cls(
            status=str(data.get("status") or "ok"),
            signals=list(data.get("signals") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(
                data.get("recommendation")
                or "review_transition_decision_signals"
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


def _extract_decisions(report_or_decisions: Any) -> list[Any]:
    if report_or_decisions is None:
        return []

    if isinstance(report_or_decisions, list):
        return report_or_decisions

    if isinstance(report_or_decisions, tuple):
        return list(report_or_decisions)

    if isinstance(report_or_decisions, dict):
        for key in ("decisions", "transition_decision_decisions"):
            value = report_or_decisions.get(key)
            if isinstance(value, list):
                return list(value)

        plan = report_or_decisions.get("transition_decision_plan")
        if isinstance(plan, dict):
            value = plan.get("decisions")
            if isinstance(value, list):
                return list(value)

    if hasattr(report_or_decisions, "decisions"):
        value = getattr(report_or_decisions, "decisions")
        if isinstance(value, list):
            return list(value)

    if hasattr(report_or_decisions, "transition_decision_plan"):
        plan = getattr(report_or_decisions, "transition_decision_plan")
        if hasattr(plan, "decisions"):
            value = getattr(plan, "decisions")
            if isinstance(value, list):
                return list(value)

    return []


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def adapt_transition_decision_to_signal(
    decision: Any,
    index: int = 0,
) -> dict[str, Any] | None:
    item_data = _item_to_dict(decision)
    transition_type = str(item_data.get("transition_type") or "").strip().lower()

    mapping = TRANSITION_TYPE_TO_SIGNAL.get(transition_type)
    if not mapping:
        mapping = TRANSITION_TYPE_TO_SIGNAL["transition_unknown_review"]
        transition_type = "transition_unknown_review"

    decision_id = str(
        item_data.get("decision_id") or f"transition_decision_{index}"
    )

    return {
        "signal_id": f"transition_decision_signal_{decision_id}",
        "signal_type": mapping["signal_type"],
        "source": TRANSITION_DECISION_SIGNAL_SOURCE,
        "source_item_id": item_data.get("source_item_id") or decision_id,
        "segment_id": item_data.get("segment_id"),
        "start_seconds": item_data.get("start_seconds"),
        "end_seconds": item_data.get("end_seconds"),
        "center_seconds": item_data.get("center_seconds"),
        "duration_seconds": item_data.get("duration_seconds"),
        "confidence": _safe_float(item_data.get("transition_confidence"), 0.0),
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": str(item_data.get("reason") or ""),
        "metadata": {
            "transition_type": transition_type,
            "proposed_action": item_data.get("proposed_action"),
            "cut_list_action": item_data.get("cut_list_action"),
            "duration_status": item_data.get("duration_status"),
            "murch_score": _safe_float(item_data.get("murch_score"), 0.0),
            "is_protected": bool(item_data.get("is_protected", False)),
            "is_censor_keep": bool(item_data.get("is_censor_keep", False)),
            "is_technical_review": bool(item_data.get("is_technical_review", False)),
            "is_scene_change_aligned": bool(
                item_data.get("is_scene_change_aligned", False)
            ),
            "is_beat_aligned": bool(item_data.get("is_beat_aligned", False)),
            "is_sentence_safe": bool(item_data.get("is_sentence_safe", False)),
            "is_dialogue_context": bool(item_data.get("is_dialogue_context", False)),
            "decision_basis": dict(item_data.get("decision_basis") or {}),
            "source_signal_ids": list(item_data.get("source_signal_ids") or []),
            "review_only": True,
        },
    }


def adapt_transition_decision_report_to_signals(
    report_or_decisions: Any,
) -> TransitionDecisionSignalAdapterResult:
    decisions = _extract_decisions(report_or_decisions)

    if not decisions:
        return TransitionDecisionSignalAdapterResult(
            status="empty",
            signals=[],
            signal_count=0,
            recommendation="transition_decision_signal_adapter_empty",
            metadata={
                "source": TRANSITION_DECISION_SIGNAL_SOURCE,
                "review_only": True,
            },
        )

    signals: list[dict[str, Any]] = []
    warnings: list[str] = []

    for index, decision in enumerate(decisions):
        signal = adapt_transition_decision_to_signal(
            decision,
            index=index,
        )
        if signal is None:
            warnings.append(f"unsupported_transition_decision:{index}")
            continue

        signals.append(signal)

    result = TransitionDecisionSignalAdapterResult(
        status="ok" if signals else "empty",
        signals=signals,
        warnings=warnings,
        recommendation=(
            "transition_decision_signals_generated"
            if signals
            else "transition_decision_signal_adapter_empty"
        ),
        metadata={
            "source": TRANSITION_DECISION_SIGNAL_SOURCE,
            "review_only": True,
        },
    )
    result.refresh_counts()
    return result
