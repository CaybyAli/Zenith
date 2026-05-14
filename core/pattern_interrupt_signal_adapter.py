from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.pattern_interrupt import (
    PATTERN_INTERRUPT_STATUS_BLOCKED,
    PATTERN_INTERRUPT_STATUS_FAILED,
    PATTERN_INTERRUPT_STATUS_NO_TIMELINE_ITEMS,
    PATTERN_INTERRUPT_STATUS_READY,
    PATTERN_INTERRUPT_STATUS_READY_WITH_WARNINGS,
    PatternInterruptReport,
)


PATTERN_INTERRUPT_SIGNAL_SOURCE = "pattern_interrupt"

STATUS_TO_SIGNAL = {
    PATTERN_INTERRUPT_STATUS_READY: "pattern_interrupt_analysis_ready",
    PATTERN_INTERRUPT_STATUS_READY_WITH_WARNINGS: (
        "pattern_interrupt_ready_with_warnings"
    ),
    PATTERN_INTERRUPT_STATUS_BLOCKED: "pattern_interrupt_blocked",
    PATTERN_INTERRUPT_STATUS_NO_TIMELINE_ITEMS: "pattern_interrupt_blocked",
    PATTERN_INTERRUPT_STATUS_FAILED: "pattern_interrupt_failed",
}

SUGGESTION_TO_SIGNAL = {
    "pattern_interrupt_needed": "pattern_interrupt_needed",
    "monotony_risk": "pattern_interrupt_monotony_risk",
    "zoom_reaction_candidate": "pattern_interrupt_zoom_reaction_candidate",
    "text_overlay_candidate": "pattern_interrupt_text_overlay_candidate",
    "sfx_candidate": "pattern_interrupt_sfx_candidate",
    "energy_shift_needed": "pattern_interrupt_energy_shift_needed",
    "pacing_shift_needed": "pattern_interrupt_pacing_shift_needed",
    "breathing_break_candidate": "pattern_interrupt_breathing_break_candidate",
    "censor_interrupt_review_required": (
        "pattern_interrupt_censor_review_required"
    ),
    "continuity_interrupt_blocked": "pattern_interrupt_continuity_blocked",
}


@dataclass
class PatternInterruptSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0

    ready_signal_count: int = 0
    ready_with_warnings_signal_count: int = 0
    blocked_signal_count: int = 0
    failed_signal_count: int = 0
    interrupt_needed_signal_count: int = 0
    monotony_risk_signal_count: int = 0
    zoom_reaction_candidate_signal_count: int = 0
    text_overlay_candidate_signal_count: int = 0
    sfx_candidate_signal_count: int = 0
    energy_shift_needed_signal_count: int = 0
    pacing_shift_needed_signal_count: int = 0
    breathing_break_candidate_signal_count: int = 0
    censor_review_required_signal_count: int = 0
    continuity_blocked_signal_count: int = 0

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "pattern_interrupt_signals_pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)
        self.ready_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_analysis_ready",
        )
        self.ready_with_warnings_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_ready_with_warnings",
        )
        self.blocked_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_blocked",
        )
        self.failed_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_failed",
        )
        self.interrupt_needed_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_needed",
        )
        self.monotony_risk_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_monotony_risk",
        )
        self.zoom_reaction_candidate_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_zoom_reaction_candidate",
        )
        self.text_overlay_candidate_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_text_overlay_candidate",
        )
        self.sfx_candidate_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_sfx_candidate",
        )
        self.energy_shift_needed_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_energy_shift_needed",
        )
        self.pacing_shift_needed_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_pacing_shift_needed",
        )
        self.breathing_break_candidate_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_breathing_break_candidate",
        )
        self.censor_review_required_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_censor_review_required",
        )
        self.continuity_blocked_signal_count = _count_type(
            self.signals,
            "pattern_interrupt_continuity_blocked",
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
            "interrupt_needed_signal_count": self.interrupt_needed_signal_count,
            "monotony_risk_signal_count": self.monotony_risk_signal_count,
            "zoom_reaction_candidate_signal_count": (
                self.zoom_reaction_candidate_signal_count
            ),
            "text_overlay_candidate_signal_count": (
                self.text_overlay_candidate_signal_count
            ),
            "sfx_candidate_signal_count": self.sfx_candidate_signal_count,
            "energy_shift_needed_signal_count": (
                self.energy_shift_needed_signal_count
            ),
            "pacing_shift_needed_signal_count": (
                self.pacing_shift_needed_signal_count
            ),
            "breathing_break_candidate_signal_count": (
                self.breathing_break_candidate_signal_count
            ),
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
    ) -> "PatternInterruptSignalAdapterResult":
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
                data.get("recommendation") or "pattern_interrupt_signals_pending"
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
    if not data and hasattr(report_or_job, "pattern_interrupt_report"):
        data = _safe_dict(getattr(report_or_job, "pattern_interrupt_report"))

    if "pattern_interrupt_report" in data:
        nested = _safe_dict(data.get("pattern_interrupt_report"))
        if nested:
            return nested

    if "pattern_interrupt" in data:
        nested = _safe_dict(data.get("pattern_interrupt"))
        if nested:
            return nested

    if "windows" in data or "suggestions" in data:
        return data

    return {}


def _base_metadata(report_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_id": report_data.get("report_id"),
        "review_only": True,
        "media_unchanged": True,
        "no_execution_in_2b_40": True,
        "no_render_in_2b_40": True,
        "no_timeline_reorder_in_2b_40": True,
        "no_pattern_apply_in_2b_40": True,
        "no_zoom_insert_in_2b_40": True,
        "no_text_overlay_insert_in_2b_40": True,
        "no_sfx_insert_in_2b_40": True,
        "can_apply_interrupts": False,
        "can_insert_zoom": False,
        "can_insert_text_overlay": False,
        "can_insert_sfx": False,
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


def _center_seconds(start_seconds: Any, end_seconds: Any) -> float | None:
    try:
        if start_seconds is None or end_seconds is None:
            return None
        return round((float(start_seconds) + float(end_seconds)) / 2.0, 3)
    except (TypeError, ValueError):
        return None


def _status_signal(report_data: dict[str, Any], signal_type: str) -> dict[str, Any]:
    status = str(report_data.get("status") or "")
    score = (
        0.95
        if status in {PATTERN_INTERRUPT_STATUS_BLOCKED, PATTERN_INTERRUPT_STATUS_FAILED}
        else 0.85
    )
    priority = (
        "high"
        if status in {PATTERN_INTERRUPT_STATUS_BLOCKED, PATTERN_INTERRUPT_STATUS_FAILED}
        else "medium"
    )
    return {
        "signal_id": (
            f"pattern_interrupt_status_{report_data.get('report_id') or 'unknown'}_"
            f"{signal_type}"
        ),
        "signal_type": signal_type,
        "source": PATTERN_INTERRUPT_SIGNAL_SOURCE,
        "source_item_id": report_data.get("report_id"),
        "segment_id": None,
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": None,
        "duration_seconds": None,
        "signal_score": score,
        "confidence": score,
        "priority": priority,
        "action_hint": "review_pattern_interrupt",
        "reason": status or signal_type,
        "metadata": {
            **_base_metadata(report_data),
            "status": status,
            "review_required": True,
            "total_windows": int(report_data.get("total_windows", 0) or 0),
            "interrupt_needed_count": int(
                report_data.get("interrupt_needed_count", 0) or 0
            ),
            "monotony_score": _safe_float(report_data.get("monotony_score"), 0.0),
            "average_window_duration_seconds": _safe_float(
                report_data.get("average_window_duration_seconds"),
                0.0,
            ),
            "recommended_interrupt_count": int(
                report_data.get("recommended_interrupt_count", 0) or 0
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
    score = 0.95 if severity == "blocking" else 0.82
    start = suggestion.get("start_seconds")
    end = suggestion.get("end_seconds")
    return {
        "signal_id": (
            f"pattern_interrupt_suggestion_"
            f"{suggestion.get('suggestion_id') or signal_type}"
        ),
        "signal_type": signal_type,
        "source": PATTERN_INTERRUPT_SIGNAL_SOURCE,
        "source_item_id": suggestion.get("source_item_id"),
        "segment_id": suggestion.get("source_window_id"),
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": _center_seconds(start, end),
        "duration_seconds": _safe_float(end, 0.0) - _safe_float(start, 0.0)
        if start is not None and end is not None
        else None,
        "signal_score": score,
        "confidence": score,
        "priority": _priority_for_severity(severity),
        "action_hint": "review_pattern_interrupt",
        "reason": str(suggestion.get("reason") or signal_type),
        "metadata": {
            **_base_metadata(report_data),
            "suggestion_id": suggestion.get("suggestion_id"),
            "suggestion_type": suggestion.get("suggestion_type"),
            "source_window_id": suggestion.get("source_window_id"),
            "severity": severity,
            "review_required": True,
            "can_auto_apply": False,
            "can_insert_zoom": False,
            "can_insert_text_overlay": False,
            "can_insert_sfx": False,
            "can_reorder_timeline": False,
            "can_render": False,
            "suggestion_metadata": dict(suggestion.get("metadata") or {}),
        },
    }


def adapt_pattern_interrupt_report_to_signals(
    report_or_job: Any,
) -> PatternInterruptSignalAdapterResult:
    try:
        report_data = _extract_report(report_or_job)
        if not report_data:
            return PatternInterruptSignalAdapterResult(
                status="empty",
                signals=[],
                signal_count=0,
                recommendation="pattern_interrupt_signal_adapter_empty",
                metadata={
                    "source": PATTERN_INTERRUPT_SIGNAL_SOURCE,
                    "review_only": True,
                    "media_unchanged": True,
                    "no_execution_in_2b_40": True,
                    "no_render_in_2b_40": True,
                },
            )

        report = PatternInterruptReport.from_dict(report_data)
        report_data = report.to_dict()
        status = str(report_data.get("status") or "")
        signals: list[dict[str, Any]] = []

        status_signal_type = STATUS_TO_SIGNAL.get(
            status,
            "pattern_interrupt_ready_with_warnings",
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

        result = PatternInterruptSignalAdapterResult(
            status="ok" if signals else "empty",
            signals=signals,
            warnings=list(report_data.get("warnings") or []),
            errors=[],
            recommendation=(
                "pattern_interrupt_signals_generated"
                if signals
                else "pattern_interrupt_signal_adapter_empty"
            ),
            metadata={
                "source": PATTERN_INTERRUPT_SIGNAL_SOURCE,
                "review_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_40": True,
                "no_render_in_2b_40": True,
                "no_timeline_reorder_in_2b_40": True,
                "no_pattern_apply_in_2b_40": True,
                "no_zoom_insert_in_2b_40": True,
                "no_text_overlay_insert_in_2b_40": True,
                "no_sfx_insert_in_2b_40": True,
            },
        )
        result.refresh_counts()
        return result

    except Exception as exc:
        return PatternInterruptSignalAdapterResult(
            status="failed",
            signals=[],
            warnings=[],
            errors=[f"pattern_interrupt_signal_adapter_failed:{exc}"],
            recommendation="review_pattern_interrupt_signal_adapter_error",
            metadata={
                "source": PATTERN_INTERRUPT_SIGNAL_SOURCE,
                "review_only": True,
                "media_unchanged": True,
            },
        )
