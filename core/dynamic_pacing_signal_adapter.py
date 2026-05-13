from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.dynamic_pacing import (
    DYNAMIC_PACING_STATUS_BLOCKED,
    DYNAMIC_PACING_STATUS_FAILED,
    DYNAMIC_PACING_STATUS_NO_TIMELINE_ITEMS,
    DYNAMIC_PACING_STATUS_READY,
    DYNAMIC_PACING_STATUS_READY_WITH_WARNINGS,
    PACING_STATUS_GOOD,
    DynamicPacingReport,
)


DYNAMIC_PACING_SIGNAL_SOURCE = "dynamic_pacing"

STATUS_TO_SIGNAL = {
    DYNAMIC_PACING_STATUS_READY: "dynamic_pacing_analysis_ready",
    DYNAMIC_PACING_STATUS_READY_WITH_WARNINGS: "dynamic_pacing_ready_with_warnings",
    DYNAMIC_PACING_STATUS_BLOCKED: "dynamic_pacing_blocked",
    DYNAMIC_PACING_STATUS_NO_TIMELINE_ITEMS: "dynamic_pacing_blocked",
    DYNAMIC_PACING_STATUS_FAILED: "dynamic_pacing_failed",
}

SUGGESTION_TO_SIGNAL = {
    "pacing_too_slow_for_energy": "dynamic_pacing_too_slow_for_energy",
    "pacing_too_fast_for_energy": "dynamic_pacing_too_fast_for_energy",
    "missing_breathing_room": "dynamic_pacing_missing_breathing_room",
    "monotone_pacing_risk": "dynamic_pacing_monotone_risk",
    "clip_too_long_review": "dynamic_pacing_clip_too_long_review",
    "clip_too_short_review": "dynamic_pacing_clip_too_short_review",
    "censor_pacing_review_required": "dynamic_pacing_censor_review_required",
    "continuity_pacing_blocked": "dynamic_pacing_continuity_blocked",
}


@dataclass
class DynamicPacingSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0

    ready_signal_count: int = 0
    ready_with_warnings_signal_count: int = 0
    blocked_signal_count: int = 0
    failed_signal_count: int = 0
    good_match_signal_count: int = 0
    too_slow_signal_count: int = 0
    too_fast_signal_count: int = 0
    missing_breathing_room_signal_count: int = 0
    monotone_risk_signal_count: int = 0
    clip_too_long_signal_count: int = 0
    clip_too_short_signal_count: int = 0
    censor_review_required_signal_count: int = 0
    continuity_blocked_signal_count: int = 0

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "dynamic_pacing_signals_pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)
        self.ready_signal_count = _count_type(
            self.signals,
            "dynamic_pacing_analysis_ready",
        )
        self.ready_with_warnings_signal_count = _count_type(
            self.signals,
            "dynamic_pacing_ready_with_warnings",
        )
        self.blocked_signal_count = _count_type(
            self.signals,
            "dynamic_pacing_blocked",
        )
        self.failed_signal_count = _count_type(
            self.signals,
            "dynamic_pacing_failed",
        )
        self.good_match_signal_count = _count_type(
            self.signals,
            "dynamic_pacing_good_match",
        )
        self.too_slow_signal_count = _count_type(
            self.signals,
            "dynamic_pacing_too_slow_for_energy",
        )
        self.too_fast_signal_count = _count_type(
            self.signals,
            "dynamic_pacing_too_fast_for_energy",
        )
        self.missing_breathing_room_signal_count = _count_type(
            self.signals,
            "dynamic_pacing_missing_breathing_room",
        )
        self.monotone_risk_signal_count = _count_type(
            self.signals,
            "dynamic_pacing_monotone_risk",
        )
        self.clip_too_long_signal_count = _count_type(
            self.signals,
            "dynamic_pacing_clip_too_long_review",
        )
        self.clip_too_short_signal_count = _count_type(
            self.signals,
            "dynamic_pacing_clip_too_short_review",
        )
        self.censor_review_required_signal_count = _count_type(
            self.signals,
            "dynamic_pacing_censor_review_required",
        )
        self.continuity_blocked_signal_count = _count_type(
            self.signals,
            "dynamic_pacing_continuity_blocked",
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
            "good_match_signal_count": self.good_match_signal_count,
            "too_slow_signal_count": self.too_slow_signal_count,
            "too_fast_signal_count": self.too_fast_signal_count,
            "missing_breathing_room_signal_count": (
                self.missing_breathing_room_signal_count
            ),
            "monotone_risk_signal_count": self.monotone_risk_signal_count,
            "clip_too_long_signal_count": self.clip_too_long_signal_count,
            "clip_too_short_signal_count": self.clip_too_short_signal_count,
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
    ) -> "DynamicPacingSignalAdapterResult":
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
                data.get("recommendation") or "dynamic_pacing_signals_pending"
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
    if not data and hasattr(report_or_job, "dynamic_pacing_report"):
        data = _safe_dict(getattr(report_or_job, "dynamic_pacing_report"))

    if "dynamic_pacing_report" in data:
        nested = _safe_dict(data.get("dynamic_pacing_report"))
        if nested:
            return nested

    if "dynamic_pacing" in data:
        nested = _safe_dict(data.get("dynamic_pacing"))
        if nested:
            return nested

    if "pacing_segments" in data or "suggestions" in data:
        return data

    return {}


def _base_metadata(report_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_id": report_data.get("report_id"),
        "review_only": True,
        "media_unchanged": True,
        "no_execution_in_2b_39": True,
        "no_render_in_2b_39": True,
        "no_timeline_reorder_in_2b_39": True,
        "no_pacing_apply_in_2b_39": True,
        "no_split_merge_trim_extend_in_2b_39": True,
        "can_apply_pacing": False,
        "can_split_clips": False,
        "can_merge_clips": False,
        "can_trim": False,
        "can_extend": False,
        "can_reorder_timeline": False,
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
    score = (
        0.95
        if status in {DYNAMIC_PACING_STATUS_BLOCKED, DYNAMIC_PACING_STATUS_FAILED}
        else 0.85
    )
    priority = (
        "high"
        if status in {DYNAMIC_PACING_STATUS_BLOCKED, DYNAMIC_PACING_STATUS_FAILED}
        else "medium"
    )
    return {
        "signal_id": (
            f"dynamic_pacing_status_{report_data.get('report_id') or 'unknown'}_"
            f"{signal_type}"
        ),
        "signal_type": signal_type,
        "source": DYNAMIC_PACING_SIGNAL_SOURCE,
        "source_item_id": report_data.get("report_id"),
        "segment_id": None,
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": None,
        "duration_seconds": None,
        "signal_score": score,
        "confidence": score,
        "priority": priority,
        "action_hint": "review_dynamic_pacing",
        "reason": status or signal_type,
        "metadata": {
            **_base_metadata(report_data),
            "status": status,
            "review_required": True,
            "average_cut_rate": _safe_float(
                report_data.get("average_cut_rate"),
                0.0,
            ),
            "target_cut_rate_range": dict(
                report_data.get("target_cut_rate_range") or {}
            ),
            "pacing_match_score": _safe_float(
                report_data.get("pacing_match_score"),
                0.0,
            ),
            "monotony_score": _safe_float(report_data.get("monotony_score"), 0.0),
            "breathing_room_score": _safe_float(
                report_data.get("breathing_room_score"),
                0.0,
            ),
            "fast_run_count": int(report_data.get("fast_run_count", 0) or 0),
            "slow_run_count": int(report_data.get("slow_run_count", 0) or 0),
            "blocking_reasons": list(report_data.get("blocking_reasons") or []),
            "warnings": list(report_data.get("warnings") or []),
        },
    }


def _segment_signal(
    report_data: dict[str, Any],
    segment: dict[str, Any],
) -> dict[str, Any]:
    score = _safe_float(segment.get("energy_score"), 0.0)
    return {
        "signal_id": (
            f"dynamic_pacing_segment_"
            f"{segment.get('segment_id') or segment.get('source_item_id')}"
        ),
        "signal_type": "dynamic_pacing_good_match",
        "source": DYNAMIC_PACING_SIGNAL_SOURCE,
        "source_item_id": segment.get("source_item_id"),
        "segment_id": segment.get("source_segment_id"),
        "start_seconds": segment.get("start_seconds"),
        "end_seconds": segment.get("end_seconds"),
        "center_seconds": _center_seconds(
            segment.get("start_seconds"),
            segment.get("end_seconds"),
        ),
        "duration_seconds": segment.get("duration_seconds"),
        "signal_score": max(0.5, score),
        "confidence": max(0.5, score),
        "priority": "medium",
        "action_hint": "review_dynamic_pacing",
        "reason": "good_pacing_match",
        "metadata": {
            **_base_metadata(report_data),
            "segment_id": segment.get("segment_id"),
            "pacing_status": segment.get("pacing_status"),
            "energy_score": score,
            "actual_cut_rate": _safe_float(segment.get("actual_cut_rate"), 0.0),
            "target_cut_rate_min": _safe_float(
                segment.get("target_cut_rate_min"),
                0.0,
            ),
            "target_cut_rate_max": _safe_float(
                segment.get("target_cut_rate_max"),
                0.0,
            ),
            "arc_phase": segment.get("arc_phase"),
            "review_required": True,
        },
    }


def _suggestion_signal(
    report_data: dict[str, Any],
    suggestion: dict[str, Any],
    signal_type: str,
) -> dict[str, Any]:
    severity = str(suggestion.get("severity") or "medium")
    metadata = dict(suggestion.get("metadata") or {})
    score = 0.95 if severity == "blocking" else 0.82
    return {
        "signal_id": (
            f"dynamic_pacing_suggestion_"
            f"{suggestion.get('suggestion_id') or signal_type}"
        ),
        "signal_type": signal_type,
        "source": DYNAMIC_PACING_SIGNAL_SOURCE,
        "source_item_id": suggestion.get("source_item_id"),
        "segment_id": suggestion.get("source_segment_id"),
        "start_seconds": metadata.get("start_seconds"),
        "end_seconds": metadata.get("end_seconds"),
        "center_seconds": _center_seconds(
            metadata.get("start_seconds"),
            metadata.get("end_seconds"),
        ),
        "duration_seconds": metadata.get("duration_seconds"),
        "signal_score": score,
        "confidence": score,
        "priority": _priority_for_severity(severity),
        "action_hint": "review_dynamic_pacing",
        "reason": str(suggestion.get("reason") or signal_type),
        "metadata": {
            **_base_metadata(report_data),
            "suggestion_id": suggestion.get("suggestion_id"),
            "suggestion_type": suggestion.get("suggestion_type"),
            "severity": severity,
            "review_required": True,
            "can_auto_apply": False,
            "suggestion_metadata": metadata,
        },
    }


def _center_seconds(start_seconds: Any, end_seconds: Any) -> float | None:
    try:
        if start_seconds is None or end_seconds is None:
            return None
        return round((float(start_seconds) + float(end_seconds)) / 2.0, 3)
    except (TypeError, ValueError):
        return None


def adapt_dynamic_pacing_report_to_signals(
    report_or_job: Any,
) -> DynamicPacingSignalAdapterResult:
    try:
        report_data = _extract_report(report_or_job)
        if not report_data:
            return DynamicPacingSignalAdapterResult(
                status="empty",
                signals=[],
                signal_count=0,
                recommendation="dynamic_pacing_signal_adapter_empty",
                metadata={
                    "source": DYNAMIC_PACING_SIGNAL_SOURCE,
                    "review_only": True,
                    "media_unchanged": True,
                    "no_execution_in_2b_39": True,
                    "no_render_in_2b_39": True,
                },
            )

        report = DynamicPacingReport.from_dict(report_data)
        report_data = report.to_dict()
        status = str(report_data.get("status") or "")
        signals: list[dict[str, Any]] = []

        status_signal_type = STATUS_TO_SIGNAL.get(
            status,
            "dynamic_pacing_ready_with_warnings",
        )
        signals.append(_status_signal(report_data, status_signal_type))

        for segment in report_data.get("pacing_segments", []) or []:
            if not isinstance(segment, dict):
                continue
            if str(segment.get("pacing_status") or "") == PACING_STATUS_GOOD:
                signals.append(_segment_signal(report_data, segment))

        for suggestion in report_data.get("suggestions", []) or []:
            if not isinstance(suggestion, dict):
                continue
            suggestion_type = str(suggestion.get("suggestion_type") or "")
            signal_type = SUGGESTION_TO_SIGNAL.get(suggestion_type)
            if not signal_type:
                continue
            signals.append(_suggestion_signal(report_data, suggestion, signal_type))

        result = DynamicPacingSignalAdapterResult(
            status="ok" if signals else "empty",
            signals=signals,
            warnings=list(report_data.get("warnings") or []),
            errors=[],
            recommendation=(
                "dynamic_pacing_signals_generated"
                if signals
                else "dynamic_pacing_signal_adapter_empty"
            ),
            metadata={
                "source": DYNAMIC_PACING_SIGNAL_SOURCE,
                "review_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_39": True,
                "no_render_in_2b_39": True,
                "no_timeline_reorder_in_2b_39": True,
                "no_pacing_apply_in_2b_39": True,
                "no_split_merge_trim_extend_in_2b_39": True,
            },
        )
        result.refresh_counts()
        return result

    except Exception as exc:
        return DynamicPacingSignalAdapterResult(
            status="failed",
            signals=[],
            warnings=[],
            errors=[f"dynamic_pacing_signal_adapter_failed:{exc}"],
            recommendation="review_dynamic_pacing_signal_adapter_error",
            metadata={
                "source": DYNAMIC_PACING_SIGNAL_SOURCE,
                "review_only": True,
                "media_unchanged": True,
            },
        )
