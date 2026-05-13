from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.hook_identification import (
    HOOK_IDENTIFICATION_STATUS_BLOCKED,
    HOOK_IDENTIFICATION_STATUS_CANDIDATE_FOUND,
    HOOK_IDENTIFICATION_STATUS_FAILED,
    HOOK_IDENTIFICATION_STATUS_NO_SAFE_CANDIDATE,
    HookIdentificationReport,
)


HOOK_IDENTIFICATION_SIGNAL_SOURCE = "hook_identification"


@dataclass
class HookIdentificationSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0

    candidate_found_signal_count: int = 0
    review_required_signal_count: int = 0
    high_score_signal_count: int = 0
    blocked_signal_count: int = 0
    missing_safe_candidate_signal_count: int = 0
    failed_signal_count: int = 0

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "hook_identification_signals_pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)
        self.candidate_found_signal_count = _count_type(
            self.signals,
            "hook_candidate_found",
        )
        self.review_required_signal_count = _count_type(
            self.signals,
            "hook_candidate_review_required",
        )
        self.high_score_signal_count = _count_type(
            self.signals,
            "hook_candidate_high_score",
        )
        self.blocked_signal_count = _count_type(
            self.signals,
            "hook_candidate_blocked",
        )
        self.missing_safe_candidate_signal_count = _count_type(
            self.signals,
            "hook_candidate_missing_safe_candidate",
        )
        self.failed_signal_count = _count_type(
            self.signals,
            "hook_identification_failed",
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "candidate_found_signal_count": self.candidate_found_signal_count,
            "review_required_signal_count": self.review_required_signal_count,
            "high_score_signal_count": self.high_score_signal_count,
            "blocked_signal_count": self.blocked_signal_count,
            "missing_safe_candidate_signal_count": (
                self.missing_safe_candidate_signal_count
            ),
            "failed_signal_count": self.failed_signal_count,
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata or {}),
        }


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
    if not data and hasattr(report_or_job, "hook_identification_report"):
        data = _safe_dict(getattr(report_or_job, "hook_identification_report"))

    if "hook_identification_report" in data:
        nested = _safe_dict(data.get("hook_identification_report"))
        if nested:
            return nested

    if "hook_identification" in data:
        nested = _safe_dict(data.get("hook_identification"))
        if nested:
            return nested

    if "selected_candidate" in data or "candidates" in data:
        return data

    return {}


def _base_metadata(report_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_id": report_data.get("report_id"),
        "review_only": True,
        "media_unchanged": True,
        "no_execution_in_2b_37": True,
        "no_render_in_2b_37": True,
        "no_timeline_reorder_in_2b_37": True,
        "can_apply_hook": False,
        "can_reorder_timeline": False,
        "can_render": False,
        "source_metadata": dict(report_data.get("metadata") or {}),
    }


def _candidate_signal(
    report_data: dict[str, Any],
    candidate: dict[str, Any],
    signal_type: str,
    suffix: str,
    priority: str = "high",
) -> dict[str, Any]:
    hook_score = _safe_float(candidate.get("hook_score"), 0.0)
    return {
        "signal_id": (
            f"hook_identification_{suffix}_"
            f"{candidate.get('candidate_id') or 'candidate'}"
        ),
        "signal_type": signal_type,
        "source": HOOK_IDENTIFICATION_SIGNAL_SOURCE,
        "source_item_id": candidate.get("source_item_id"),
        "segment_id": candidate.get("source_segment_id"),
        "start_seconds": candidate.get("start_seconds"),
        "end_seconds": candidate.get("end_seconds"),
        "center_seconds": _center_seconds(
            candidate.get("start_seconds"),
            candidate.get("end_seconds"),
        ),
        "duration_seconds": candidate.get("duration_seconds"),
        "signal_score": hook_score,
        "confidence": _safe_float(candidate.get("confidence"), hook_score),
        "priority": priority,
        "action_hint": "review_hook_candidate",
        "reason": str(candidate.get("reason") or signal_type),
        "metadata": {
            **_base_metadata(report_data),
            "candidate_id": candidate.get("candidate_id"),
            "hook_score": hook_score,
            "energy_peak_score": _safe_float(
                candidate.get("energy_peak_score"),
                0.0,
            ),
            "surprise_factor_score": _safe_float(
                candidate.get("surprise_factor_score"),
                0.0,
            ),
            "emotional_value_score": _safe_float(
                candidate.get("emotional_value_score"),
                0.0,
            ),
            "content_value_score": _safe_float(
                candidate.get("content_value_score"),
                0.0,
            ),
            "review_required": True,
            "safety_flags": list(candidate.get("safety_flags") or []),
            "warnings": list(candidate.get("warnings") or []),
            "blocking_reasons": list(candidate.get("blocking_reasons") or []),
        },
    }


def _status_signal(
    report_data: dict[str, Any],
    signal_type: str,
    action_hint: str,
    reason: str,
    score: float,
    priority: str,
) -> dict[str, Any]:
    return {
        "signal_id": (
            f"hook_identification_status_"
            f"{report_data.get('report_id') or 'unknown'}_{signal_type}"
        ),
        "signal_type": signal_type,
        "source": HOOK_IDENTIFICATION_SIGNAL_SOURCE,
        "source_item_id": report_data.get("report_id"),
        "segment_id": None,
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": None,
        "duration_seconds": None,
        "signal_score": score,
        "confidence": score,
        "priority": priority,
        "action_hint": action_hint,
        "reason": reason,
        "metadata": {
            **_base_metadata(report_data),
            "status": report_data.get("status"),
            "review_required": True,
            "blocking_reasons": list(report_data.get("blocking_reasons") or []),
            "warnings": list(report_data.get("warnings") or []),
        },
    }


def _center_seconds(start_seconds: Any, end_seconds: Any) -> float | None:
    try:
        if start_seconds is None or end_seconds is None:
            return None
        return round((float(start_seconds) + float(end_seconds)) / 2.0, 3)
    except (TypeError, ValueError):
        return None


def adapt_hook_identification_report_to_signals(
    report_or_job: Any,
) -> HookIdentificationSignalAdapterResult:
    try:
        report_data = _extract_report(report_or_job)
        if not report_data:
            return HookIdentificationSignalAdapterResult(
                status="empty",
                signals=[],
                signal_count=0,
                recommendation="hook_identification_signal_adapter_empty",
                metadata={
                    "source": HOOK_IDENTIFICATION_SIGNAL_SOURCE,
                    "review_only": True,
                    "media_unchanged": True,
                },
            )

        report = HookIdentificationReport.from_dict(report_data)
        report_data = report.to_dict()
        selected_candidate = _safe_dict(report_data.get("selected_candidate"))
        status = str(report_data.get("status") or "")
        signals: list[dict[str, Any]] = []

        if status == HOOK_IDENTIFICATION_STATUS_CANDIDATE_FOUND and selected_candidate:
            signals.append(
                _candidate_signal(
                    report_data,
                    selected_candidate,
                    "hook_candidate_found",
                    "found",
                )
            )
            signals.append(
                _candidate_signal(
                    report_data,
                    selected_candidate,
                    "hook_candidate_review_required",
                    "review_required",
                    priority="medium",
                )
            )
            if _safe_float(selected_candidate.get("hook_score"), 0.0) >= 0.75:
                signals.append(
                    _candidate_signal(
                        report_data,
                        selected_candidate,
                        "hook_candidate_high_score",
                        "high_score",
                    )
                )
        elif status == HOOK_IDENTIFICATION_STATUS_BLOCKED:
            signals.append(
                _status_signal(
                    report_data,
                    "hook_candidate_blocked",
                    "review_hook_candidate",
                    "hook_identification_blocked",
                    0.95,
                    "high",
                )
            )
        elif status == HOOK_IDENTIFICATION_STATUS_NO_SAFE_CANDIDATE:
            signals.append(
                _status_signal(
                    report_data,
                    "hook_candidate_missing_safe_candidate",
                    "review_hook_candidate",
                    "no_safe_hook_candidate",
                    0.7,
                    "medium",
                )
            )
        elif status == HOOK_IDENTIFICATION_STATUS_FAILED:
            signals.append(
                _status_signal(
                    report_data,
                    "hook_identification_failed",
                    "review_hook_candidate",
                    "hook_identification_failed",
                    0.95,
                    "high",
                )
            )

        for candidate in report_data.get("candidates", []) or []:
            if not isinstance(candidate, dict) or not candidate.get("blocking_reasons"):
                continue
            signals.append(
                _candidate_signal(
                    report_data,
                    candidate,
                    "hook_candidate_blocked",
                    "candidate_blocked",
                    priority="high",
                )
            )

        result = HookIdentificationSignalAdapterResult(
            status="ok" if signals else "empty",
            signals=signals,
            warnings=list(report_data.get("warnings") or []),
            errors=[],
            recommendation=(
                "hook_identification_signals_generated"
                if signals
                else "hook_identification_signal_adapter_empty"
            ),
            metadata={
                "source": HOOK_IDENTIFICATION_SIGNAL_SOURCE,
                "review_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_37": True,
                "no_render_in_2b_37": True,
                "no_timeline_reorder_in_2b_37": True,
            },
        )
        result.refresh_counts()
        return result

    except Exception as exc:
        return HookIdentificationSignalAdapterResult(
            status="failed",
            signals=[],
            warnings=[],
            errors=[f"hook_identification_signal_adapter_failed:{exc}"],
            recommendation="review_hook_identification_signal_adapter_error",
            metadata={
                "source": HOOK_IDENTIFICATION_SIGNAL_SOURCE,
                "review_only": True,
                "media_unchanged": True,
            },
        )
