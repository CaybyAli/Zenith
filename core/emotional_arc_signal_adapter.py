from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.emotional_arc import (
    EMOTIONAL_ARC_STATUS_BLOCKED,
    EMOTIONAL_ARC_STATUS_FAILED,
    EMOTIONAL_ARC_STATUS_NO_TIMELINE_ITEMS,
    EMOTIONAL_ARC_STATUS_READY,
    EMOTIONAL_ARC_STATUS_READY_WITH_WARNINGS,
    EmotionalArcReport,
)


EMOTIONAL_ARC_SIGNAL_SOURCE = "emotional_arc"

STATUS_TO_SIGNAL = {
    EMOTIONAL_ARC_STATUS_READY: "emotional_arc_analysis_ready",
    EMOTIONAL_ARC_STATUS_READY_WITH_WARNINGS: "emotional_arc_ready_with_warnings",
    EMOTIONAL_ARC_STATUS_BLOCKED: "emotional_arc_blocked",
    EMOTIONAL_ARC_STATUS_NO_TIMELINE_ITEMS: "emotional_arc_blocked",
    EMOTIONAL_ARC_STATUS_FAILED: "emotional_arc_failed",
}

SUGGESTION_TO_SIGNAL = {
    "weak_hook": "emotional_arc_weak_hook",
    "missing_climax": "emotional_arc_missing_climax",
    "flat_energy_curve": "emotional_arc_flat_energy_curve",
    "missing_breathing_room": "emotional_arc_missing_breathing_room",
    "abrupt_emotional_drop": "emotional_arc_abrupt_drop",
    "censor_arc_review_required": "emotional_arc_censor_review_required",
    "continuity_arc_blocked": "emotional_arc_continuity_blocked",
}


@dataclass
class EmotionalArcSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0

    ready_signal_count: int = 0
    ready_with_warnings_signal_count: int = 0
    blocked_signal_count: int = 0
    failed_signal_count: int = 0
    weak_hook_signal_count: int = 0
    missing_climax_signal_count: int = 0
    flat_energy_curve_signal_count: int = 0
    missing_breathing_room_signal_count: int = 0
    abrupt_drop_signal_count: int = 0
    censor_review_required_signal_count: int = 0
    continuity_blocked_signal_count: int = 0

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "emotional_arc_signals_pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)
        self.ready_signal_count = _count_type(
            self.signals,
            "emotional_arc_analysis_ready",
        )
        self.ready_with_warnings_signal_count = _count_type(
            self.signals,
            "emotional_arc_ready_with_warnings",
        )
        self.blocked_signal_count = _count_type(
            self.signals,
            "emotional_arc_blocked",
        )
        self.failed_signal_count = _count_type(
            self.signals,
            "emotional_arc_failed",
        )
        self.weak_hook_signal_count = _count_type(
            self.signals,
            "emotional_arc_weak_hook",
        )
        self.missing_climax_signal_count = _count_type(
            self.signals,
            "emotional_arc_missing_climax",
        )
        self.flat_energy_curve_signal_count = _count_type(
            self.signals,
            "emotional_arc_flat_energy_curve",
        )
        self.missing_breathing_room_signal_count = _count_type(
            self.signals,
            "emotional_arc_missing_breathing_room",
        )
        self.abrupt_drop_signal_count = _count_type(
            self.signals,
            "emotional_arc_abrupt_drop",
        )
        self.censor_review_required_signal_count = _count_type(
            self.signals,
            "emotional_arc_censor_review_required",
        )
        self.continuity_blocked_signal_count = _count_type(
            self.signals,
            "emotional_arc_continuity_blocked",
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "ready_signal_count": self.ready_signal_count,
            "ready_with_warnings_signal_count": (
                self.ready_with_warnings_signal_count
            ),
            "blocked_signal_count": self.blocked_signal_count,
            "failed_signal_count": self.failed_signal_count,
            "weak_hook_signal_count": self.weak_hook_signal_count,
            "missing_climax_signal_count": self.missing_climax_signal_count,
            "flat_energy_curve_signal_count": (
                self.flat_energy_curve_signal_count
            ),
            "missing_breathing_room_signal_count": (
                self.missing_breathing_room_signal_count
            ),
            "abrupt_drop_signal_count": self.abrupt_drop_signal_count,
            "censor_review_required_signal_count": (
                self.censor_review_required_signal_count
            ),
            "continuity_blocked_signal_count": (
                self.continuity_blocked_signal_count
            ),
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "EmotionalArcSignalAdapterResult":
        data = data or {}
        result = cls(
            status=str(data.get("status") or "ok"),
            signals=[
                dict(signal)
                for signal in data.get("signals", []) or []
                if isinstance(signal, dict)
            ],
            warnings=[str(item) for item in data.get("warnings", []) or []],
            errors=[str(item) for item in data.get("errors", []) or []],
            recommendation=str(
                data.get("recommendation") or "emotional_arc_signals_pending"
            ),
            metadata=dict(data.get("metadata") or {}),
        )
        result.refresh_counts()
        return result


def _count_type(signals: list[dict[str, Any]], signal_type: str) -> int:
    return sum(1 for signal in signals if signal.get("signal_type") == signal_type)


def _safe_dict(value: Any) -> dict[str, Any]:
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_report(report_or_job: Any) -> dict[str, Any]:
    data = _safe_dict(report_or_job)
    if not data and hasattr(report_or_job, "emotional_arc_report"):
        data = _safe_dict(getattr(report_or_job, "emotional_arc_report"))

    if "emotional_arc_report" in data:
        nested = _safe_dict(data.get("emotional_arc_report"))
        if nested:
            return nested

    if "emotional_arc" in data:
        nested = _safe_dict(data.get("emotional_arc"))
        if nested:
            return nested

    if "arc_points" in data or "suggestions" in data:
        return data

    return {}


def _base_metadata(report_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_id": report_data.get("report_id"),
        "review_only": True,
        "media_unchanged": True,
        "no_execution_in_2b_38": True,
        "no_render_in_2b_38": True,
        "no_timeline_reorder_in_2b_38": True,
        "no_arc_apply_in_2b_38": True,
        "can_apply_arc": False,
        "can_reorder_timeline": False,
        "can_trim": False,
        "can_extend": False,
        "can_render": False,
        "source_metadata": dict(report_data.get("metadata") or {}),
    }


def _priority_for_severity(severity: str) -> str:
    if severity == "blocking":
        return "high"
    if severity in {"high", "medium", "low"}:
        return severity
    return "medium"


def _status_signal(report_data: dict[str, Any], signal_type: str) -> dict[str, Any]:
    status = str(report_data.get("status") or "")
    score = 0.95 if status in {EMOTIONAL_ARC_STATUS_BLOCKED, EMOTIONAL_ARC_STATUS_FAILED} else 0.85
    priority = "high" if status in {EMOTIONAL_ARC_STATUS_BLOCKED, EMOTIONAL_ARC_STATUS_FAILED} else "medium"
    return {
        "signal_id": (
            f"emotional_arc_status_{report_data.get('report_id') or 'unknown'}_"
            f"{signal_type}"
        ),
        "signal_type": signal_type,
        "source": EMOTIONAL_ARC_SIGNAL_SOURCE,
        "source_item_id": report_data.get("report_id"),
        "segment_id": None,
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": None,
        "duration_seconds": None,
        "signal_score": score,
        "confidence": score,
        "priority": priority,
        "action_hint": "review_emotional_arc",
        "reason": status or signal_type,
        "metadata": {
            **_base_metadata(report_data),
            "status": status,
            "review_required": True,
            "average_deviation": _safe_float(
                report_data.get("average_deviation"),
                0.0,
            ),
            "max_deviation": _safe_float(report_data.get("max_deviation"), 0.0),
            "flatness_score": _safe_float(report_data.get("flatness_score"), 0.0),
            "hook_strength_score": _safe_float(
                report_data.get("hook_strength_score"),
                0.0,
            ),
            "climax_strength_score": _safe_float(
                report_data.get("climax_strength_score"),
                0.0,
            ),
            "breathing_room_score": _safe_float(
                report_data.get("breathing_room_score"),
                0.0,
            ),
            "blocking_reasons": list(report_data.get("blocking_reasons") or []),
            "warnings": list(report_data.get("warnings") or []),
        },
    }


def _suggestion_signal(
    report_data: dict[str, Any],
    suggestion: dict[str, Any],
    signal_type: str,
) -> dict[str, Any]:
    severity = str(suggestion.get("severity") or "medium")
    score = 0.95 if severity == "blocking" else 0.80
    return {
        "signal_id": (
            f"emotional_arc_suggestion_"
            f"{suggestion.get('suggestion_id') or signal_type}"
        ),
        "signal_type": signal_type,
        "source": EMOTIONAL_ARC_SIGNAL_SOURCE,
        "source_item_id": suggestion.get("source_item_id"),
        "segment_id": suggestion.get("source_segment_id"),
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": None,
        "duration_seconds": None,
        "signal_score": score,
        "confidence": score,
        "priority": _priority_for_severity(severity),
        "action_hint": "review_emotional_arc",
        "reason": str(suggestion.get("reason") or signal_type),
        "metadata": {
            **_base_metadata(report_data),
            "suggestion_id": suggestion.get("suggestion_id"),
            "suggestion_type": suggestion.get("suggestion_type"),
            "arc_phase": suggestion.get("arc_phase"),
            "severity": severity,
            "review_required": True,
            "can_auto_apply": False,
            "suggestion_metadata": dict(suggestion.get("metadata") or {}),
        },
    }


def adapt_emotional_arc_report_to_signals(
    report_or_job: Any,
) -> EmotionalArcSignalAdapterResult:
    try:
        report_data = _extract_report(report_or_job)
        if not report_data:
            return EmotionalArcSignalAdapterResult(
                status="empty",
                signals=[],
                signal_count=0,
                recommendation="emotional_arc_signal_adapter_empty",
                metadata={
                    "source": EMOTIONAL_ARC_SIGNAL_SOURCE,
                    "review_only": True,
                    "media_unchanged": True,
                    "no_execution_in_2b_38": True,
                    "no_render_in_2b_38": True,
                },
            )

        report = EmotionalArcReport.from_dict(report_data)
        report_data = report.to_dict()
        status = str(report_data.get("status") or "")
        signals: list[dict[str, Any]] = []

        status_signal_type = STATUS_TO_SIGNAL.get(
            status,
            "emotional_arc_ready_with_warnings",
        )
        signals.append(_status_signal(report_data, status_signal_type))

        for suggestion in report_data.get("suggestions", []) or []:
            if not isinstance(suggestion, dict):
                continue
            suggestion_type = str(suggestion.get("suggestion_type") or "")
            signal_type = SUGGESTION_TO_SIGNAL.get(suggestion_type)
            if not signal_type:
                continue
            signals.append(_suggestion_signal(report_data, suggestion, signal_type))

        result = EmotionalArcSignalAdapterResult(
            status="ok" if signals else "empty",
            signals=signals,
            warnings=list(report_data.get("warnings") or []),
            errors=[],
            recommendation=(
                "emotional_arc_signals_generated"
                if signals
                else "emotional_arc_signal_adapter_empty"
            ),
            metadata={
                "source": EMOTIONAL_ARC_SIGNAL_SOURCE,
                "review_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_38": True,
                "no_render_in_2b_38": True,
                "no_timeline_reorder_in_2b_38": True,
                "no_arc_apply_in_2b_38": True,
            },
        )
        result.refresh_counts()
        return result

    except Exception as exc:
        return EmotionalArcSignalAdapterResult(
            status="failed",
            signals=[],
            warnings=[],
            errors=[f"emotional_arc_signal_adapter_failed:{exc}"],
            recommendation="review_emotional_arc_signal_adapter_error",
            metadata={
                "source": EMOTIONAL_ARC_SIGNAL_SOURCE,
                "review_only": True,
                "media_unchanged": True,
            },
        )
