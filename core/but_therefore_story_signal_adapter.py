from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.but_therefore_story import (
    ButThereforeStoryReport,
    STORY_ROLE_AND,
    STORY_ROLE_BUT,
    STORY_ROLE_CENSOR_REVIEW,
    STORY_ROLE_CONTINUITY_BLOCKED,
    STORY_ROLE_PAYOFF,
    STORY_ROLE_PROTECTED,
    STORY_ROLE_REACTION,
    STORY_ROLE_THEREFORE,
    STORY_STATUS_BLOCKED,
    STORY_STATUS_FAILED,
    STORY_STATUS_NO_TIMELINE_ITEMS,
    STORY_STATUS_READY,
    STORY_STATUS_READY_WITH_WARNINGS,
)


BUT_THEREFORE_STORY_SIGNAL_SOURCE = "but_therefore_story"

STATUS_TO_SIGNAL = {
    STORY_STATUS_READY: "but_therefore_story_ready",
    STORY_STATUS_READY_WITH_WARNINGS: "but_therefore_story_ready_with_warnings",
    STORY_STATUS_BLOCKED: "but_therefore_story_blocked",
    STORY_STATUS_NO_TIMELINE_ITEMS: "but_therefore_story_blocked",
    STORY_STATUS_FAILED: "but_therefore_story_failed",
}

ROLE_TO_SIGNAL = {
    STORY_ROLE_BUT: "story_but_moment",
    STORY_ROLE_THEREFORE: "story_therefore_moment",
    STORY_ROLE_AND: "story_and_moment",
    STORY_ROLE_REACTION: "story_reaction_moment",
    STORY_ROLE_PAYOFF: "story_payoff_moment",
    STORY_ROLE_CENSOR_REVIEW: "story_censor_review_required",
    STORY_ROLE_CONTINUITY_BLOCKED: "story_continuity_blocked",
    STORY_ROLE_PROTECTED: "story_protected_preserved",
}

SUGGESTION_TO_SIGNAL = {
    "too_many_and_moments": "story_too_many_and_moments",
    "weak_but_therefore_ratio": "story_weak_but_therefore_ratio",
    "orphan_reaction": "story_orphan_reaction",
    "missing_payoff": "story_missing_payoff",
    "story_flow_break": "story_flow_break",
    "censor_story_review_required": "story_censor_review_required",
    "continuity_story_blocked": "story_continuity_blocked",
    "protected_story_preserved": "story_protected_preserved",
}


@dataclass
class ButThereforeStorySignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0

    ready_signal_count: int = 0
    ready_with_warnings_signal_count: int = 0
    blocked_signal_count: int = 0
    failed_signal_count: int = 0

    but_moment_signal_count: int = 0
    therefore_moment_signal_count: int = 0
    and_moment_signal_count: int = 0
    reaction_moment_signal_count: int = 0
    payoff_moment_signal_count: int = 0

    too_many_and_signal_count: int = 0
    weak_ratio_signal_count: int = 0
    orphan_reaction_signal_count: int = 0
    missing_payoff_signal_count: int = 0
    flow_break_signal_count: int = 0
    censor_review_required_signal_count: int = 0
    continuity_blocked_signal_count: int = 0
    protected_preserved_signal_count: int = 0

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "but_therefore_story_signals_pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)
        self.ready_signal_count = _count_type(self.signals, "but_therefore_story_ready")
        self.ready_with_warnings_signal_count = _count_type(
            self.signals,
            "but_therefore_story_ready_with_warnings",
        )
        self.blocked_signal_count = _count_type(self.signals, "but_therefore_story_blocked")
        self.failed_signal_count = _count_type(self.signals, "but_therefore_story_failed")

        self.but_moment_signal_count = _count_type(self.signals, "story_but_moment")
        self.therefore_moment_signal_count = _count_type(
            self.signals,
            "story_therefore_moment",
        )
        self.and_moment_signal_count = _count_type(self.signals, "story_and_moment")
        self.reaction_moment_signal_count = _count_type(
            self.signals,
            "story_reaction_moment",
        )
        self.payoff_moment_signal_count = _count_type(self.signals, "story_payoff_moment")

        self.too_many_and_signal_count = _count_type(
            self.signals,
            "story_too_many_and_moments",
        )
        self.weak_ratio_signal_count = _count_type(
            self.signals,
            "story_weak_but_therefore_ratio",
        )
        self.orphan_reaction_signal_count = _count_type(
            self.signals,
            "story_orphan_reaction",
        )
        self.missing_payoff_signal_count = _count_type(
            self.signals,
            "story_missing_payoff",
        )
        self.flow_break_signal_count = _count_type(self.signals, "story_flow_break")
        self.censor_review_required_signal_count = _count_type(
            self.signals,
            "story_censor_review_required",
        )
        self.continuity_blocked_signal_count = _count_type(
            self.signals,
            "story_continuity_blocked",
        )
        self.protected_preserved_signal_count = _count_type(
            self.signals,
            "story_protected_preserved",
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_counts()
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "ready_signal_count": self.ready_signal_count,
            "ready_with_warnings_signal_count": self.ready_with_warnings_signal_count,
            "blocked_signal_count": self.blocked_signal_count,
            "failed_signal_count": self.failed_signal_count,
            "but_moment_signal_count": self.but_moment_signal_count,
            "therefore_moment_signal_count": self.therefore_moment_signal_count,
            "and_moment_signal_count": self.and_moment_signal_count,
            "reaction_moment_signal_count": self.reaction_moment_signal_count,
            "payoff_moment_signal_count": self.payoff_moment_signal_count,
            "too_many_and_signal_count": self.too_many_and_signal_count,
            "weak_ratio_signal_count": self.weak_ratio_signal_count,
            "orphan_reaction_signal_count": self.orphan_reaction_signal_count,
            "missing_payoff_signal_count": self.missing_payoff_signal_count,
            "flow_break_signal_count": self.flow_break_signal_count,
            "censor_review_required_signal_count": self.censor_review_required_signal_count,
            "continuity_blocked_signal_count": self.continuity_blocked_signal_count,
            "protected_preserved_signal_count": self.protected_preserved_signal_count,
            "warnings": list(self.warnings or []),
            "errors": list(self.errors or []),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ButThereforeStorySignalAdapterResult":
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
                data.get("recommendation") or "but_therefore_story_signals_pending"
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

    if not data and hasattr(report_or_job, "but_therefore_story_report"):
        data = _safe_dict(getattr(report_or_job, "but_therefore_story_report"))

    if "but_therefore_story_report" in data:
        nested = _safe_dict(data.get("but_therefore_story_report"))
        if nested:
            return nested

    if "but_therefore_story" in data:
        nested = _safe_dict(data.get("but_therefore_story"))
        if nested:
            return nested

    if "moments" in data or "transitions" in data:
        return data

    return {}


def _base_metadata(report_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_id": report_data.get("report_id"),
        "review_only": True,
        "media_unchanged": True,
        "no_execution_in_2b_42": True,
        "no_render_in_2b_42": True,
        "no_timeline_reorder_in_2b_42": True,
        "no_story_apply_in_2b_42": True,
        "no_and_moment_remove_in_2b_42": True,
        "can_apply_story_changes": False,
        "can_remove_and_moments": False,
        "can_reorder_timeline": False,
        "can_trim": False,
        "can_extend": False,
        "can_render": False,
        "source_metadata": dict(report_data.get("metadata") or {}),
    }


def _center_seconds(start_seconds: Any, end_seconds: Any) -> float | None:
    try:
        if start_seconds is None or end_seconds is None:
            return None
        return round((float(start_seconds) + float(end_seconds)) / 2.0, 3)
    except (TypeError, ValueError):
        return None


def _status_signal(report_data: dict[str, Any], signal_type: str) -> dict[str, Any]:
    status = str(report_data.get("status") or "")
    score = 0.95 if status in {STORY_STATUS_BLOCKED, STORY_STATUS_FAILED} else 0.85
    priority = "high" if status in {STORY_STATUS_BLOCKED, STORY_STATUS_FAILED} else "medium"

    return {
        "signal_id": (
            f"but_therefore_story_status_"
            f"{report_data.get('report_id') or 'unknown'}_{signal_type}"
        ),
        "signal_type": signal_type,
        "source": BUT_THEREFORE_STORY_SIGNAL_SOURCE,
        "source_item_id": report_data.get("report_id"),
        "segment_id": None,
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": None,
        "duration_seconds": None,
        "signal_score": score,
        "confidence": score,
        "priority": priority,
        "action_hint": "review_but_therefore_story",
        "reason": status or signal_type,
        "metadata": {
            **_base_metadata(report_data),
            "status": status,
            "review_required": True,
            "total_moments": int(report_data.get("total_moments", 0) or 0),
            "but_therefore_ratio": _safe_float(
                report_data.get("but_therefore_ratio"),
                0.0,
            ),
            "story_flow_score": _safe_float(report_data.get("story_flow_score"), 0.0),
            "and_streak_max": int(report_data.get("and_streak_max", 0) or 0),
            "orphan_reaction_count": int(
                report_data.get("orphan_reaction_count", 0) or 0
            ),
            "missing_payoff_count": int(
                report_data.get("missing_payoff_count", 0) or 0
            ),
            "blocking_reasons": list(report_data.get("blocking_reasons") or []),
            "warnings": list(report_data.get("warnings") or []),
        },
    }


def _moment_signal(
    report_data: dict[str, Any],
    moment: dict[str, Any],
    signal_type: str,
) -> dict[str, Any]:
    start = moment.get("start_seconds")
    end = moment.get("end_seconds")
    score = _safe_float(moment.get("story_score"), 0.0)
    priority = "high" if moment.get("story_role") in {
        STORY_ROLE_BUT,
        STORY_ROLE_PAYOFF,
        STORY_ROLE_REACTION,
        STORY_ROLE_CENSOR_REVIEW,
        STORY_ROLE_CONTINUITY_BLOCKED,
    } else "medium"

    return {
        "signal_id": f"but_therefore_story_moment_{moment.get('moment_id') or signal_type}",
        "signal_type": signal_type,
        "source": BUT_THEREFORE_STORY_SIGNAL_SOURCE,
        "source_item_id": moment.get("source_item_id"),
        "segment_id": moment.get("source_segment_id"),
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": _center_seconds(start, end),
        "duration_seconds": moment.get("duration_seconds"),
        "signal_score": score,
        "confidence": score,
        "priority": priority,
        "action_hint": "review_but_therefore_story",
        "reason": str(moment.get("story_role") or signal_type),
        "metadata": {
            **_base_metadata(report_data),
            "moment_id": moment.get("moment_id"),
            "story_role": moment.get("story_role"),
            "conflict_score": _safe_float(moment.get("conflict_score"), 0.0),
            "consequence_score": _safe_float(moment.get("consequence_score"), 0.0),
            "reaction_score": _safe_float(moment.get("reaction_score"), 0.0),
            "neutral_score": _safe_float(moment.get("neutral_score"), 0.0),
            "evidence": list(moment.get("evidence") or []),
            "review_required": True,
            "warnings": list(moment.get("warnings") or []),
            "blocking_reasons": list(moment.get("blocking_reasons") or []),
            "moment_metadata": dict(moment.get("metadata") or {}),
        },
    }


def _suggestion_signal(
    report_data: dict[str, Any],
    suggestion: dict[str, Any],
    signal_type: str,
) -> dict[str, Any]:
    severity = str(suggestion.get("severity") or "medium")
    score = 0.90 if severity == "high" else 0.76 if severity == "medium" else 0.55

    return {
        "signal_id": (
            f"but_therefore_story_suggestion_"
            f"{suggestion.get('suggestion_type') or signal_type}_"
            f"{suggestion.get('moment_id') or suggestion.get('transition_id') or 'global'}"
        ),
        "signal_type": signal_type,
        "source": BUT_THEREFORE_STORY_SIGNAL_SOURCE,
        "source_item_id": suggestion.get("moment_id") or suggestion.get("transition_id"),
        "segment_id": None,
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": None,
        "duration_seconds": None,
        "signal_score": score,
        "confidence": score,
        "priority": "high" if severity == "high" else "medium",
        "action_hint": "review_but_therefore_story",
        "reason": str(suggestion.get("reason") or signal_type),
        "metadata": {
            **_base_metadata(report_data),
            "suggestion_type": suggestion.get("suggestion_type"),
            "severity": severity,
            "moment_id": suggestion.get("moment_id"),
            "transition_id": suggestion.get("transition_id"),
            "review_required": True,
            "can_apply_story_changes": False,
            "suggestion_metadata": dict(suggestion.get("metadata") or {}),
        },
    }


def adapt_but_therefore_story_report_to_signals(
    report_or_job: Any,
) -> ButThereforeStorySignalAdapterResult:
    try:
        report_data = _extract_report(report_or_job)
        if not report_data:
            return ButThereforeStorySignalAdapterResult(
                status="empty",
                signals=[],
                recommendation="but_therefore_story_signal_adapter_empty",
                metadata={
                    "source": BUT_THEREFORE_STORY_SIGNAL_SOURCE,
                    "review_only": True,
                    "media_unchanged": True,
                    "no_execution_in_2b_42": True,
                    "no_render_in_2b_42": True,
                },
            )

        report = ButThereforeStoryReport.from_dict(report_data)
        report_data = report.to_dict()
        status = str(report_data.get("status") or "")
        signals: list[dict[str, Any]] = []

        status_signal_type = STATUS_TO_SIGNAL.get(
            status,
            "but_therefore_story_ready_with_warnings",
        )
        signals.append(_status_signal(report_data, status_signal_type))

        for moment in report_data.get("moments", []) or []:
            if not isinstance(moment, dict):
                continue
            story_role = str(moment.get("story_role") or "")
            signal_type = ROLE_TO_SIGNAL.get(story_role)
            if signal_type:
                signals.append(_moment_signal(report_data, moment, signal_type))

        for suggestion in report_data.get("suggestions", []) or []:
            if not isinstance(suggestion, dict):
                continue
            suggestion_type = str(suggestion.get("suggestion_type") or "")
            signal_type = SUGGESTION_TO_SIGNAL.get(suggestion_type)
            if signal_type:
                signals.append(_suggestion_signal(report_data, suggestion, signal_type))

        result = ButThereforeStorySignalAdapterResult(
            status="ok" if signals else "empty",
            signals=signals,
            warnings=list(report_data.get("warnings") or []),
            errors=[],
            recommendation=(
                "but_therefore_story_signals_generated"
                if signals
                else "but_therefore_story_signal_adapter_empty"
            ),
            metadata={
                "source": BUT_THEREFORE_STORY_SIGNAL_SOURCE,
                "review_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_42": True,
                "no_render_in_2b_42": True,
                "no_timeline_reorder_in_2b_42": True,
                "no_story_apply_in_2b_42": True,
                "no_and_moment_remove_in_2b_42": True,
            },
        )
        result.refresh_counts()
        return result

    except Exception as exc:
        return ButThereforeStorySignalAdapterResult(
            status="failed",
            signals=[],
            warnings=[],
            errors=[f"but_therefore_story_signal_adapter_failed:{exc}"],
            recommendation="review_but_therefore_story_signal_adapter_error",
            metadata={
                "source": BUT_THEREFORE_STORY_SIGNAL_SOURCE,
                "review_only": True,
                "media_unchanged": True,
            },
        )
