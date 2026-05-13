from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CLIP_DURATION_SIGNAL_SOURCE = "clip_duration_optimizer"


DURATION_STATUS_TO_SIGNAL = {
    "duration_ok": {
        "signal_type": "clip_duration_ok",
        "action_hint": "review_duration_ok",
        "priority": "low",
    },
    "too_short_review": {
        "signal_type": "clip_duration_too_short_review",
        "action_hint": "review_extend_duration_candidate",
        "priority": "medium",
    },
    "extend_review": {
        "signal_type": "clip_duration_too_short_review",
        "action_hint": "review_extend_duration_candidate",
        "priority": "medium",
    },
    "too_long_review": {
        "signal_type": "clip_duration_too_long_review",
        "action_hint": "review_trim_duration_candidate",
        "priority": "medium",
    },
    "trim_review": {
        "signal_type": "clip_duration_too_long_review",
        "action_hint": "review_trim_duration_candidate",
        "priority": "medium",
    },
    "protect_duration": {
        "signal_type": "clip_duration_protected",
        "action_hint": "protect_duration_from_blind_trim",
        "priority": "high",
    },
    "censor_keep_duration": {
        "signal_type": "clip_duration_censor_keep",
        "action_hint": "preserve_duration_for_censor_sfx",
        "priority": "high",
    },
    "technical_review": {
        "signal_type": "clip_duration_technical_review",
        "action_hint": "review_duration_technical_risk",
        "priority": "high",
    },
    "invalid_timing_review": {
        "signal_type": "clip_duration_invalid_timing",
        "action_hint": "review_invalid_clip_timing",
        "priority": "high",
    },
    "unknown_review": {
        "signal_type": "clip_duration_unknown_review",
        "action_hint": "review_unknown_duration_decision",
        "priority": "low",
    },
}


@dataclass
class ClipDurationSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    duration_ok_signal_count: int = 0
    too_short_signal_count: int = 0
    too_long_signal_count: int = 0
    protected_signal_count: int = 0
    censor_keep_signal_count: int = 0
    technical_review_signal_count: int = 0
    invalid_timing_signal_count: int = 0
    unknown_review_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_clip_duration_signals"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)
        self.duration_ok_signal_count = _count_type(self.signals, "clip_duration_ok")
        self.too_short_signal_count = _count_type(
            self.signals,
            "clip_duration_too_short_review",
        )
        self.too_long_signal_count = _count_type(
            self.signals,
            "clip_duration_too_long_review",
        )
        self.protected_signal_count = _count_type(
            self.signals,
            "clip_duration_protected",
        )
        self.censor_keep_signal_count = _count_type(
            self.signals,
            "clip_duration_censor_keep",
        )
        self.technical_review_signal_count = _count_type(
            self.signals,
            "clip_duration_technical_review",
        )
        self.invalid_timing_signal_count = _count_type(
            self.signals,
            "clip_duration_invalid_timing",
        )
        self.unknown_review_signal_count = _count_type(
            self.signals,
            "clip_duration_unknown_review",
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()
        return {
            "status": self.status,
            "signals": list(self.signals),
            "signal_count": self.signal_count,
            "duration_ok_signal_count": self.duration_ok_signal_count,
            "too_short_signal_count": self.too_short_signal_count,
            "too_long_signal_count": self.too_long_signal_count,
            "protected_signal_count": self.protected_signal_count,
            "censor_keep_signal_count": self.censor_keep_signal_count,
            "technical_review_signal_count": self.technical_review_signal_count,
            "invalid_timing_signal_count": self.invalid_timing_signal_count,
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
    ) -> "ClipDurationSignalAdapterResult":
        if not isinstance(data, dict):
            data = {}

        result = cls(
            status=str(data.get("status") or "ok"),
            signals=list(data.get("signals") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(
                data.get("recommendation") or "review_clip_duration_signals"
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


def _extract_recommendations(report_or_recommendations: Any) -> list[Any]:
    if report_or_recommendations is None:
        return []

    if isinstance(report_or_recommendations, list):
        return report_or_recommendations

    if isinstance(report_or_recommendations, tuple):
        return list(report_or_recommendations)

    if isinstance(report_or_recommendations, dict):
        for key in ("recommendations", "clip_duration_recommendations"):
            value = report_or_recommendations.get(key)
            if isinstance(value, list):
                return list(value)

        plan = report_or_recommendations.get("clip_duration_plan")
        if isinstance(plan, dict):
            value = plan.get("recommendations")
            if isinstance(value, list):
                return list(value)

    if hasattr(report_or_recommendations, "recommendations"):
        value = getattr(report_or_recommendations, "recommendations")
        if isinstance(value, list):
            return list(value)

    if hasattr(report_or_recommendations, "clip_duration_plan"):
        plan = getattr(report_or_recommendations, "clip_duration_plan")
        if hasattr(plan, "recommendations"):
            value = getattr(plan, "recommendations")
            if isinstance(value, list):
                return list(value)

    return []


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def adapt_clip_duration_recommendation_to_signal(
    recommendation: Any,
    index: int = 0,
) -> dict[str, Any] | None:
    item_data = _item_to_dict(recommendation)
    duration_status = str(item_data.get("duration_status") or "").strip().lower()

    mapping = DURATION_STATUS_TO_SIGNAL.get(duration_status)
    if not mapping:
        mapping = DURATION_STATUS_TO_SIGNAL["unknown_review"]
        duration_status = "unknown_review"

    recommendation_id = str(
        item_data.get("recommendation_id") or f"clip_duration_rec_{index}"
    )

    return {
        "signal_id": f"clip_duration_signal_{recommendation_id}",
        "signal_type": mapping["signal_type"],
        "source": CLIP_DURATION_SIGNAL_SOURCE,
        "source_item_id": item_data.get("source_item_id") or recommendation_id,
        "segment_id": item_data.get("segment_id"),
        "start_seconds": item_data.get("start_seconds"),
        "end_seconds": item_data.get("end_seconds"),
        "center_seconds": item_data.get("center_seconds"),
        "duration_seconds": item_data.get("duration_seconds"),
        "confidence": _safe_float(item_data.get("confidence"), 0.0),
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": str(item_data.get("reason") or ""),
        "metadata": {
            "duration_status": duration_status,
            "proposed_action": item_data.get("proposed_action"),
            "recommended_min_duration_seconds": item_data.get(
                "recommended_min_duration_seconds"
            ),
            "recommended_max_duration_seconds": item_data.get(
                "recommended_max_duration_seconds"
            ),
            "recommended_target_duration_seconds": item_data.get(
                "recommended_target_duration_seconds"
            ),
            "suggested_start_seconds": item_data.get("suggested_start_seconds"),
            "suggested_end_seconds": item_data.get("suggested_end_seconds"),
            "suggested_duration_seconds": item_data.get("suggested_duration_seconds"),
            "adjustment_seconds": item_data.get("adjustment_seconds"),
            "is_review_required": bool(item_data.get("is_review_required", True)),
            "is_protected": bool(item_data.get("is_protected", False)),
            "is_censor_keep": bool(item_data.get("is_censor_keep", False)),
            "is_invalid_timing": bool(item_data.get("is_invalid_timing", False)),
            "decision_basis": dict(item_data.get("decision_basis") or {}),
            "review_only": True,
        },
    }


def adapt_clip_duration_report_to_signals(
    report_or_recommendations: Any,
) -> ClipDurationSignalAdapterResult:
    recommendations = _extract_recommendations(report_or_recommendations)

    if not recommendations:
        return ClipDurationSignalAdapterResult(
            status="empty",
            signals=[],
            signal_count=0,
            recommendation="clip_duration_signal_adapter_empty",
            metadata={
                "source": CLIP_DURATION_SIGNAL_SOURCE,
                "review_only": True,
            },
        )

    signals: list[dict[str, Any]] = []
    warnings: list[str] = []

    for index, recommendation in enumerate(recommendations):
        signal = adapt_clip_duration_recommendation_to_signal(
            recommendation,
            index=index,
        )
        if signal is None:
            warnings.append(f"unsupported_clip_duration_recommendation:{index}")
            continue

        signals.append(signal)

    result = ClipDurationSignalAdapterResult(
        status="ok" if signals else "empty",
        signals=signals,
        warnings=warnings,
        recommendation=(
            "clip_duration_signals_generated"
            if signals
            else "clip_duration_signal_adapter_empty"
        ),
        metadata={
            "source": CLIP_DURATION_SIGNAL_SOURCE,
            "review_only": True,
        },
    )
    result.refresh_counts()
    return result
