from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.review_timeline_dashboard_package import (
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY_WITH_WARNINGS,
)


REVIEW_TIMELINE_DASHBOARD_PACKAGE_SIGNAL_SOURCE = (
    "review_timeline_dashboard_package"
)

DASHBOARD_PACKAGE_STATUS_TO_SIGNAL = {
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY: {
        "signal_type": "review_timeline_dashboard_package_ready",
        "action_hint": "show_review_timeline_dashboard_package",
        "priority": "medium",
        "score": 0.9,
    },
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY_WITH_WARNINGS: {
        "signal_type": "review_timeline_dashboard_package_ready_with_warnings",
        "action_hint": "show_review_timeline_dashboard_package_with_warnings",
        "priority": "medium",
        "score": 0.85,
    },
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED: {
        "signal_type": "review_timeline_dashboard_package_blocked",
        "action_hint": "show_dashboard_blocking_errors",
        "priority": "high",
        "score": 0.95,
    },
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED: {
        "signal_type": "review_timeline_dashboard_package_failed",
        "action_hint": "review_dashboard_package_builder_failure",
        "priority": "high",
        "score": 0.95,
    },
}


@dataclass
class ReviewTimelineDashboardPackageSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0

    ready_signal_count: int = 0
    ready_with_warnings_signal_count: int = 0
    blocked_signal_count: int = 0
    failed_signal_count: int = 0

    item_card_signal_count: int = 0
    warning_signal_count: int = 0
    blocking_error_signal_count: int = 0

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_timeline_dashboard_package_signals_pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)

        self.ready_signal_count = _count_type(
            self.signals,
            "review_timeline_dashboard_package_ready",
        )
        self.ready_with_warnings_signal_count = _count_type(
            self.signals,
            "review_timeline_dashboard_package_ready_with_warnings",
        )
        self.blocked_signal_count = _count_type(
            self.signals,
            "review_timeline_dashboard_package_blocked",
        )
        self.failed_signal_count = _count_type(
            self.signals,
            "review_timeline_dashboard_package_failed",
        )
        self.item_card_signal_count = _count_type(
            self.signals,
            "review_timeline_dashboard_item_card",
        )
        self.warning_signal_count = _count_type(
            self.signals,
            "review_timeline_dashboard_warning",
        )
        self.blocking_error_signal_count = _count_type(
            self.signals,
            "review_timeline_dashboard_blocking_error",
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()

        return {
            "status": self.status,
            "signals": list(self.signals),
            "signal_count": self.signal_count,
            "ready_signal_count": self.ready_signal_count,
            "ready_with_warnings_signal_count": (
                self.ready_with_warnings_signal_count
            ),
            "blocked_signal_count": self.blocked_signal_count,
            "failed_signal_count": self.failed_signal_count,
            "item_card_signal_count": self.item_card_signal_count,
            "warning_signal_count": self.warning_signal_count,
            "blocking_error_signal_count": self.blocking_error_signal_count,
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


def _extract_dashboard_package(report_or_package: Any) -> dict[str, Any]:
    if report_or_package is None:
        return {}

    data = _to_dict(report_or_package)

    if "dashboard_package" in data:
        nested = _to_dict(data.get("dashboard_package"))
        if nested:
            return nested

    if data:
        return data

    if hasattr(report_or_package, "dashboard_package"):
        nested = _to_dict(getattr(report_or_package, "dashboard_package"))
        if nested:
            return nested

    return {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_status_signal(
    package_data: dict[str, Any],
    package_id: str,
) -> dict[str, Any]:
    package_status = str(
        package_data.get("package_status")
        or REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED
    )

    mapping = DASHBOARD_PACKAGE_STATUS_TO_SIGNAL.get(package_status)
    if not mapping:
        package_status = REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED
        mapping = DASHBOARD_PACKAGE_STATUS_TO_SIGNAL[
            REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED
        ]

    score = _safe_float(mapping.get("score"), 0.85)

    return {
        "signal_id": f"review_timeline_dashboard_package_status_{package_id}",
        "signal_type": mapping["signal_type"],
        "source": REVIEW_TIMELINE_DASHBOARD_PACKAGE_SIGNAL_SOURCE,
        "source_item_id": package_id,
        "segment_id": None,
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": None,
        "duration_seconds": None,
        "signal_score": score,
        "confidence": score,
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": package_status,
        "metadata": {
            "dashboard_package_id": package_id,
            "package_status": package_status,
            "review_status": package_data.get("review_status"),
            "approval_status": package_data.get("approval_status"),
            "safety_status": package_data.get("safety_status"),
            "can_proceed_to_execution": bool(
                package_data.get("can_proceed_to_execution", False)
            ),
            "can_render": False,
            "is_safe_for_future_execution": bool(
                package_data.get("is_safe_for_future_execution", False)
            ),
            "is_safe_for_render": False,
            "requires_manual_review": bool(
                package_data.get("requires_manual_review", True)
            ),
            "source_review_timeline_plan_id": package_data.get(
                "source_review_timeline_plan_id"
            ),
            "source_timeline_approval_gate_id": package_data.get(
                "source_timeline_approval_gate_id"
            ),
            "source_timeline_safety_validation_id": package_data.get(
                "source_timeline_safety_validation_id"
            ),
            "dashboard_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_35": True,
            "no_render_in_2b_35": True,
            "source_metadata": dict(package_data.get("metadata") or {}),
        },
    }


def _build_item_card_signals(
    package_data: dict[str, Any],
    package_id: str,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []

    item_cards = [
        item
        for item in list(package_data.get("item_cards") or [])
        if isinstance(item, dict)
    ]

    for index, item_card in enumerate(item_cards):
        item_id = str(item_card.get("item_id") or f"item_{index}")
        start_seconds = item_card.get("start_seconds")
        end_seconds = item_card.get("end_seconds")
        duration_seconds = item_card.get("duration_seconds")

        priority = "medium"
        if item_card.get("severity") in {"high", "blocking"}:
            priority = "high"

        signals.append(
            {
                "signal_id": (
                    f"review_timeline_dashboard_item_card_{package_id}_{index}"
                ),
                "signal_type": "review_timeline_dashboard_item_card",
                "source": REVIEW_TIMELINE_DASHBOARD_PACKAGE_SIGNAL_SOURCE,
                "source_item_id": package_id,
                "segment_id": item_id,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "center_seconds": _center_seconds(start_seconds, end_seconds),
                "duration_seconds": duration_seconds,
                "signal_score": 0.8,
                "confidence": 0.85,
                "priority": priority,
                "action_hint": "show_review_timeline_item_card",
                "reason": str(item_card.get("badge") or ""),
                "metadata": {
                    "dashboard_package_id": package_id,
                    "item_id": item_id,
                    "action": item_card.get("action"),
                    "label": item_card.get("label"),
                    "badge": item_card.get("badge"),
                    "severity": item_card.get("severity"),
                    "review_required": bool(
                        item_card.get("review_required", True)
                    ),
                    "protected": bool(item_card.get("protected", False)),
                    "censor_sfx_required": bool(
                        item_card.get("censor_sfx_required", False)
                    ),
                    "continuity_blocked": bool(
                        item_card.get("continuity_blocked", False)
                    ),
                    "safety_status": item_card.get("safety_status"),
                    "warnings": list(item_card.get("warnings") or []),
                    "blocking_errors": list(
                        item_card.get("blocking_errors") or []
                    ),
                    "dashboard_only": True,
                    "media_unchanged": True,
                    "no_execution_in_2b_35": True,
                    "no_render_in_2b_35": True,
                },
            }
        )

    return signals


def _build_warning_signals(
    package_data: dict[str, Any],
    package_id: str,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []

    for index, warning in enumerate(list(package_data.get("warnings") or [])):
        warning_text = str(warning)

        signals.append(
            {
                "signal_id": (
                    f"review_timeline_dashboard_warning_{package_id}_{index}"
                ),
                "signal_type": "review_timeline_dashboard_warning",
                "source": REVIEW_TIMELINE_DASHBOARD_PACKAGE_SIGNAL_SOURCE,
                "source_item_id": package_id,
                "segment_id": None,
                "start_seconds": None,
                "end_seconds": None,
                "center_seconds": None,
                "duration_seconds": None,
                "signal_score": 0.75,
                "confidence": 0.85,
                "priority": "medium",
                "action_hint": "show_review_timeline_dashboard_warning",
                "reason": warning_text,
                "metadata": {
                    "dashboard_package_id": package_id,
                    "warning": warning_text,
                    "dashboard_only": True,
                    "media_unchanged": True,
                    "no_execution_in_2b_35": True,
                    "no_render_in_2b_35": True,
                },
            }
        )

    return signals


def _build_blocking_error_signals(
    package_data: dict[str, Any],
    package_id: str,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []

    for index, error in enumerate(
        list(package_data.get("blocking_errors") or [])
    ):
        error_text = str(error)

        signals.append(
            {
                "signal_id": (
                    f"review_timeline_dashboard_blocking_error_"
                    f"{package_id}_{index}"
                ),
                "signal_type": "review_timeline_dashboard_blocking_error",
                "source": REVIEW_TIMELINE_DASHBOARD_PACKAGE_SIGNAL_SOURCE,
                "source_item_id": package_id,
                "segment_id": None,
                "start_seconds": None,
                "end_seconds": None,
                "center_seconds": None,
                "duration_seconds": None,
                "signal_score": 0.95,
                "confidence": 0.95,
                "priority": "high",
                "action_hint": "show_review_timeline_dashboard_blocker",
                "reason": error_text,
                "metadata": {
                    "dashboard_package_id": package_id,
                    "blocking_error": error_text,
                    "dashboard_only": True,
                    "media_unchanged": True,
                    "no_execution_in_2b_35": True,
                    "no_render_in_2b_35": True,
                },
            }
        )

    return signals


def _center_seconds(
    start_seconds: Any,
    end_seconds: Any,
) -> float | None:
    if start_seconds is None or end_seconds is None:
        return None

    try:
        return round((float(start_seconds) + float(end_seconds)) / 2.0, 3)
    except (TypeError, ValueError):
        return None


def adapt_review_timeline_dashboard_package_to_signals(
    dashboard_package: Any,
) -> ReviewTimelineDashboardPackageSignalAdapterResult:
    package_data = _extract_dashboard_package(dashboard_package)

    if not package_data:
        return ReviewTimelineDashboardPackageSignalAdapterResult(
            status="empty",
            signals=[],
            signal_count=0,
            recommendation=(
                "review_timeline_dashboard_package_signal_adapter_empty"
            ),
            metadata={
                "source": REVIEW_TIMELINE_DASHBOARD_PACKAGE_SIGNAL_SOURCE,
                "dashboard_only": True,
                "media_unchanged": True,
            },
        )

    package_id = str(
        package_data.get("dashboard_package_id")
        or "review_timeline_dashboard_package_unknown"
    )

    signals = [_build_status_signal(package_data, package_id)]
    signals.extend(_build_item_card_signals(package_data, package_id))
    signals.extend(_build_warning_signals(package_data, package_id))
    signals.extend(_build_blocking_error_signals(package_data, package_id))

    result = ReviewTimelineDashboardPackageSignalAdapterResult(
        status="ok",
        signals=signals,
        recommendation=(
            "review_timeline_dashboard_package_signals_generated"
        ),
        warnings=list(package_data.get("warnings") or []),
        errors=[],
        metadata={
            "source": REVIEW_TIMELINE_DASHBOARD_PACKAGE_SIGNAL_SOURCE,
            "dashboard_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_35": True,
            "no_render_in_2b_35": True,
        },
    )
    result.refresh_counts()
    return result


def adapt_review_timeline_dashboard_package_report_to_signals(
    report_or_package: Any,
) -> ReviewTimelineDashboardPackageSignalAdapterResult:
    return adapt_review_timeline_dashboard_package_to_signals(
        report_or_package
    )
