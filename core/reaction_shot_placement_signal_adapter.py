from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.reaction_shot_placement import (
    PLACEMENT_TYPE_AFTER_CLIMAX,
    PLACEMENT_TYPE_AFTER_HIGHLIGHT,
    PLACEMENT_TYPE_AFTER_HOOK,
    PLACEMENT_TYPE_AFTER_PATTERN_INTERRUPT,
    PLACEMENT_TYPE_BLOCKED_BY_CONTINUITY,
    PLACEMENT_TYPE_CENSOR_REVIEW,
    PLACEMENT_TYPE_MANUAL_PLACEHOLDER,
    PLACEMENT_TYPE_PROTECTED_PRESERVED,
    REACTION_SHOT_STATUS_BLOCKED,
    REACTION_SHOT_STATUS_FAILED,
    REACTION_SHOT_STATUS_NO_CANDIDATES,
    REACTION_SHOT_STATUS_NO_TIMELINE_ITEMS,
    REACTION_SHOT_STATUS_READY,
    REACTION_SHOT_STATUS_READY_WITH_WARNINGS,
    ReactionShotPlacementReport,
)


REACTION_SHOT_PLACEMENT_SIGNAL_SOURCE = "reaction_shot_placement"

STATUS_TO_SIGNAL = {
    REACTION_SHOT_STATUS_READY: "reaction_shot_placement_ready",
    REACTION_SHOT_STATUS_READY_WITH_WARNINGS: (
        "reaction_shot_placement_ready_with_warnings"
    ),
    REACTION_SHOT_STATUS_BLOCKED: "reaction_shot_placement_blocked",
    REACTION_SHOT_STATUS_NO_CANDIDATES: "reaction_shot_placement_blocked",
    REACTION_SHOT_STATUS_NO_TIMELINE_ITEMS: "reaction_shot_placement_blocked",
    REACTION_SHOT_STATUS_FAILED: "reaction_shot_placement_failed",
}

PLACEMENT_TO_SIGNAL = {
    PLACEMENT_TYPE_AFTER_HIGHLIGHT: "reaction_shot_after_highlight_candidate",
    PLACEMENT_TYPE_AFTER_HOOK: "reaction_shot_after_hook_candidate",
    PLACEMENT_TYPE_AFTER_CLIMAX: "reaction_shot_after_climax_candidate",
    PLACEMENT_TYPE_AFTER_PATTERN_INTERRUPT: (
        "reaction_shot_after_pattern_interrupt_candidate"
    ),
    PLACEMENT_TYPE_MANUAL_PLACEHOLDER: "reaction_shot_missing_placeholder",
    PLACEMENT_TYPE_BLOCKED_BY_CONTINUITY: "reaction_shot_continuity_blocked",
    PLACEMENT_TYPE_CENSOR_REVIEW: "reaction_shot_censor_review_required",
    PLACEMENT_TYPE_PROTECTED_PRESERVED: "reaction_shot_protected_preserved",
}

WARNING_TO_SIGNAL = {
    "too_short_reaction": "reaction_shot_too_short_review",
    "short_reaction_review": "reaction_shot_too_short_review",
    "too_long_reaction": "reaction_shot_too_long_review",
    "consecutive_reaction_risk": "reaction_shot_consecutive_risk",
    "reaction_shot_censor_review_required": (
        "reaction_shot_censor_review_required"
    ),
    "reaction_shot_continuity_blocked": "reaction_shot_continuity_blocked",
    "reaction_shot_protected_preserved": "reaction_shot_protected_preserved",
    "missing_reaction_placeholder": "reaction_shot_missing_placeholder",
}


@dataclass
class ReactionShotPlacementSignalAdapterResult:
    status: str = "ok"
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0

    ready_signal_count: int = 0
    ready_with_warnings_signal_count: int = 0
    blocked_signal_count: int = 0
    failed_signal_count: int = 0
    candidate_found_signal_count: int = 0
    after_highlight_candidate_signal_count: int = 0
    after_hook_candidate_signal_count: int = 0
    after_climax_candidate_signal_count: int = 0
    after_pattern_interrupt_candidate_signal_count: int = 0
    missing_placeholder_signal_count: int = 0
    too_short_review_signal_count: int = 0
    too_long_review_signal_count: int = 0
    consecutive_risk_signal_count: int = 0
    censor_review_required_signal_count: int = 0
    continuity_blocked_signal_count: int = 0
    protected_preserved_signal_count: int = 0

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "reaction_shot_placement_signals_pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def refresh_counts(self) -> None:
        self.signal_count = len(self.signals)
        self.ready_signal_count = _count_type(
            self.signals,
            "reaction_shot_placement_ready",
        )
        self.ready_with_warnings_signal_count = _count_type(
            self.signals,
            "reaction_shot_placement_ready_with_warnings",
        )
        self.blocked_signal_count = _count_type(
            self.signals,
            "reaction_shot_placement_blocked",
        )
        self.failed_signal_count = _count_type(
            self.signals,
            "reaction_shot_placement_failed",
        )
        self.candidate_found_signal_count = _count_type(
            self.signals,
            "reaction_shot_candidate_found",
        )
        self.after_highlight_candidate_signal_count = _count_type(
            self.signals,
            "reaction_shot_after_highlight_candidate",
        )
        self.after_hook_candidate_signal_count = _count_type(
            self.signals,
            "reaction_shot_after_hook_candidate",
        )
        self.after_climax_candidate_signal_count = _count_type(
            self.signals,
            "reaction_shot_after_climax_candidate",
        )
        self.after_pattern_interrupt_candidate_signal_count = _count_type(
            self.signals,
            "reaction_shot_after_pattern_interrupt_candidate",
        )
        self.missing_placeholder_signal_count = _count_type(
            self.signals,
            "reaction_shot_missing_placeholder",
        )
        self.too_short_review_signal_count = _count_type(
            self.signals,
            "reaction_shot_too_short_review",
        )
        self.too_long_review_signal_count = _count_type(
            self.signals,
            "reaction_shot_too_long_review",
        )
        self.consecutive_risk_signal_count = _count_type(
            self.signals,
            "reaction_shot_consecutive_risk",
        )
        self.censor_review_required_signal_count = _count_type(
            self.signals,
            "reaction_shot_censor_review_required",
        )
        self.continuity_blocked_signal_count = _count_type(
            self.signals,
            "reaction_shot_continuity_blocked",
        )
        self.protected_preserved_signal_count = _count_type(
            self.signals,
            "reaction_shot_protected_preserved",
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
            "candidate_found_signal_count": self.candidate_found_signal_count,
            "after_highlight_candidate_signal_count": (
                self.after_highlight_candidate_signal_count
            ),
            "after_hook_candidate_signal_count": (
                self.after_hook_candidate_signal_count
            ),
            "after_climax_candidate_signal_count": (
                self.after_climax_candidate_signal_count
            ),
            "after_pattern_interrupt_candidate_signal_count": (
                self.after_pattern_interrupt_candidate_signal_count
            ),
            "missing_placeholder_signal_count": (
                self.missing_placeholder_signal_count
            ),
            "too_short_review_signal_count": self.too_short_review_signal_count,
            "too_long_review_signal_count": self.too_long_review_signal_count,
            "consecutive_risk_signal_count": self.consecutive_risk_signal_count,
            "censor_review_required_signal_count": (
                self.censor_review_required_signal_count
            ),
            "continuity_blocked_signal_count": (
                self.continuity_blocked_signal_count
            ),
            "protected_preserved_signal_count": (
                self.protected_preserved_signal_count
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
    ) -> "ReactionShotPlacementSignalAdapterResult":
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
                data.get("recommendation")
                or "reaction_shot_placement_signals_pending"
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

    if not data and hasattr(report_or_job, "reaction_shot_placement_report"):
        data = _safe_dict(getattr(report_or_job, "reaction_shot_placement_report"))

    if "reaction_shot_placement_report" in data:
        nested = _safe_dict(data.get("reaction_shot_placement_report"))
        if nested:
            return nested

    if "reaction_shot_placement" in data:
        nested = _safe_dict(data.get("reaction_shot_placement"))
        if nested:
            return nested

    if "candidates" in data or "placements" in data:
        return data

    return {}


def _base_metadata(report_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_id": report_data.get("report_id"),
        "review_only": True,
        "media_unchanged": True,
        "no_execution_in_2b_41": True,
        "no_render_in_2b_41": True,
        "no_timeline_reorder_in_2b_41": True,
        "no_reaction_apply_in_2b_41": True,
        "no_reaction_insert_in_2b_41": True,
        "no_facecam_move_in_2b_41": True,
        "no_zoom_insert_in_2b_41": True,
        "can_apply_reaction_shots": False,
        "can_move_clip": False,
        "can_insert_clip": False,
        "can_trim": False,
        "can_extend": False,
        "can_reorder_timeline": False,
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
    score = (
        0.95
        if status in {REACTION_SHOT_STATUS_BLOCKED, REACTION_SHOT_STATUS_FAILED}
        else 0.85
    )
    priority = (
        "high"
        if status in {REACTION_SHOT_STATUS_BLOCKED, REACTION_SHOT_STATUS_FAILED}
        else "medium"
    )

    return {
        "signal_id": (
            f"reaction_shot_placement_status_"
            f"{report_data.get('report_id') or 'unknown'}_{signal_type}"
        ),
        "signal_type": signal_type,
        "source": REACTION_SHOT_PLACEMENT_SIGNAL_SOURCE,
        "source_item_id": report_data.get("report_id"),
        "segment_id": None,
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": None,
        "duration_seconds": None,
        "signal_score": score,
        "confidence": score,
        "priority": priority,
        "action_hint": "review_reaction_shot_placement",
        "reason": status or signal_type,
        "metadata": {
            **_base_metadata(report_data),
            "status": status,
            "review_required": True,
            "total_candidates": int(report_data.get("total_candidates", 0) or 0),
            "total_placements": int(report_data.get("total_placements", 0) or 0),
            "best_placement_score": _safe_float(
                report_data.get("best_placement_score"),
                0.0,
            ),
            "missing_reaction_placeholder_count": int(
                report_data.get("missing_reaction_placeholder_count", 0) or 0
            ),
            "blocking_reasons": list(report_data.get("blocking_reasons") or []),
            "warnings": list(report_data.get("warnings") or []),
        },
    }


def _candidate_signal(
    report_data: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    start = candidate.get("start_seconds")
    end = candidate.get("end_seconds")
    score = _safe_float(candidate.get("confidence"), 0.0)
    return {
        "signal_id": (
            f"reaction_shot_candidate_"
            f"{candidate.get('candidate_id') or 'unknown'}"
        ),
        "signal_type": "reaction_shot_candidate_found",
        "source": REACTION_SHOT_PLACEMENT_SIGNAL_SOURCE,
        "source_item_id": candidate.get("source_item_id"),
        "segment_id": candidate.get("source_segment_id"),
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": _center_seconds(start, end),
        "duration_seconds": candidate.get("duration_seconds"),
        "signal_score": score,
        "confidence": score,
        "priority": "medium" if score < 0.80 else "high",
        "action_hint": "review_reaction_shot_placement",
        "reason": str(candidate.get("reaction_type") or "reaction_candidate"),
        "metadata": {
            **_base_metadata(report_data),
            "candidate_id": candidate.get("candidate_id"),
            "reaction_type": candidate.get("reaction_type"),
            "reaction_score": _safe_float(candidate.get("reaction_score"), 0.0),
            "expressiveness_score": _safe_float(
                candidate.get("expressiveness_score"),
                0.0,
            ),
            "audio_reaction_score": _safe_float(
                candidate.get("audio_reaction_score"),
                0.0,
            ),
            "face_reaction_score": _safe_float(
                candidate.get("face_reaction_score"),
                0.0,
            ),
            "keyword_reaction_score": _safe_float(
                candidate.get("keyword_reaction_score"),
                0.0,
            ),
            "review_required": True,
            "warnings": list(candidate.get("warnings") or []),
            "blocking_reasons": list(candidate.get("blocking_reasons") or []),
            "candidate_metadata": dict(candidate.get("metadata") or {}),
        },
    }


def _placement_signal(
    report_data: dict[str, Any],
    placement: dict[str, Any],
    signal_type: str,
) -> dict[str, Any]:
    start = placement.get("trigger_start_seconds")
    end = placement.get("reaction_end_seconds") or placement.get("trigger_end_seconds")
    score = _safe_float(placement.get("placement_score"), 0.0)
    priority = "high" if score >= 0.80 else "medium"

    if signal_type in {
        "reaction_shot_missing_placeholder",
        "reaction_shot_continuity_blocked",
        "reaction_shot_censor_review_required",
    }:
        priority = "high"

    return {
        "signal_id": (
            f"reaction_shot_placement_"
            f"{placement.get('placement_id') or signal_type}"
        ),
        "signal_type": signal_type,
        "source": REACTION_SHOT_PLACEMENT_SIGNAL_SOURCE,
        "source_item_id": placement.get("trigger_item_id"),
        "segment_id": placement.get("trigger_segment_id"),
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": _center_seconds(start, end),
        "duration_seconds": (
            _safe_float(end, 0.0) - _safe_float(start, 0.0)
            if start is not None and end is not None
            else None
        ),
        "signal_score": score,
        "confidence": score,
        "priority": priority,
        "action_hint": "review_reaction_shot_placement",
        "reason": str(placement.get("placement_type") or signal_type),
        "metadata": {
            **_base_metadata(report_data),
            "placement_id": placement.get("placement_id"),
            "placement_type": placement.get("placement_type"),
            "suggested_position": placement.get("suggested_position"),
            "reaction_candidate_id": placement.get("reaction_candidate_id"),
            "suggested_duration_seconds": _safe_float(
                placement.get("suggested_duration_seconds"),
                0.0,
            ),
            "review_required": True,
            "can_auto_place": False,
            "can_move_clip": False,
            "can_insert_clip": False,
            "can_trim": False,
            "can_extend": False,
            "can_render": False,
            "warnings": list(placement.get("warnings") or []),
            "blocking_reasons": list(placement.get("blocking_reasons") or []),
            "placement_metadata": dict(placement.get("metadata") or {}),
        },
    }


def _warning_signal_from_timed_payload(
    report_data: dict[str, Any],
    payload: dict[str, Any],
    signal_type: str,
    payload_kind: str,
) -> dict[str, Any]:
    start = payload.get("start_seconds")
    end = payload.get("end_seconds")
    if start is None:
        start = payload.get("trigger_start_seconds")
    if end is None:
        end = payload.get("reaction_end_seconds") or payload.get(
            "trigger_end_seconds"
        )

    score = _safe_float(
        payload.get("placement_score", payload.get("confidence")),
        0.0,
    )

    return {
        "signal_id": (
            f"reaction_shot_warning_"
            f"{payload.get('placement_id') or payload.get('candidate_id') or signal_type}"
            f"_{signal_type}"
        ),
        "signal_type": signal_type,
        "source": REACTION_SHOT_PLACEMENT_SIGNAL_SOURCE,
        "source_item_id": payload.get("trigger_item_id")
        or payload.get("source_item_id"),
        "segment_id": payload.get("trigger_segment_id")
        or payload.get("source_segment_id"),
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": _center_seconds(start, end),
        "duration_seconds": (
            _safe_float(end, 0.0) - _safe_float(start, 0.0)
            if start is not None and end is not None
            else payload.get("duration_seconds")
        ),
        "signal_score": max(score, 0.75),
        "confidence": max(score, 0.75),
        "priority": "high",
        "action_hint": "review_reaction_shot_placement",
        "reason": signal_type,
        "metadata": {
            **_base_metadata(report_data),
            "payload_kind": payload_kind,
            "candidate_id": payload.get("candidate_id"),
            "placement_id": payload.get("placement_id"),
            "review_required": True,
            "warnings": list(payload.get("warnings") or []),
            "blocking_reasons": list(payload.get("blocking_reasons") or []),
            "payload_metadata": dict(payload.get("metadata") or {}),
        },
    }


def _warning_signals(
    report_data: dict[str, Any],
    payload: dict[str, Any],
    payload_kind: str = "placement",
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    seen: set[str] = set()

    for warning in list(payload.get("warnings") or []):
        signal_type = WARNING_TO_SIGNAL.get(str(warning))
        if not signal_type or signal_type in seen:
            continue
        seen.add(signal_type)
        signals.append(
            _warning_signal_from_timed_payload(
                report_data,
                payload,
                signal_type,
                payload_kind,
            )
        )

    for reason in list(payload.get("blocking_reasons") or []):
        signal_type = WARNING_TO_SIGNAL.get(str(reason))
        if not signal_type or signal_type in seen:
            continue
        seen.add(signal_type)
        signals.append(
            _warning_signal_from_timed_payload(
                report_data,
                payload,
                signal_type,
                payload_kind,
            )
        )

    return signals


def adapt_reaction_shot_placement_report_to_signals(
    report_or_job: Any,
) -> ReactionShotPlacementSignalAdapterResult:
    try:
        report_data = _extract_report(report_or_job)
        if not report_data:
            return ReactionShotPlacementSignalAdapterResult(
                status="empty",
                signals=[],
                recommendation="reaction_shot_placement_signal_adapter_empty",
                metadata={
                    "source": REACTION_SHOT_PLACEMENT_SIGNAL_SOURCE,
                    "review_only": True,
                    "media_unchanged": True,
                    "no_execution_in_2b_41": True,
                    "no_render_in_2b_41": True,
                },
            )

        report = ReactionShotPlacementReport.from_dict(report_data)
        report_data = report.to_dict()
        status = str(report_data.get("status") or "")
        signals: list[dict[str, Any]] = []

        status_signal_type = STATUS_TO_SIGNAL.get(
            status,
            "reaction_shot_placement_ready_with_warnings",
        )
        signals.append(_status_signal(report_data, status_signal_type))

        for candidate in report_data.get("candidates", []) or []:
            if isinstance(candidate, dict):
                signals.append(_candidate_signal(report_data, candidate))
                signals.extend(
                    _warning_signals(
                        report_data,
                        candidate,
                        payload_kind="candidate",
                    )
                )

        for placement in report_data.get("placements", []) or []:
            if not isinstance(placement, dict):
                continue

            placement_type = str(placement.get("placement_type") or "")
            signal_type = PLACEMENT_TO_SIGNAL.get(placement_type)
            if signal_type:
                signals.append(_placement_signal(report_data, placement, signal_type))

            signals.extend(_warning_signals(report_data, placement))

        result = ReactionShotPlacementSignalAdapterResult(
            status="ok" if signals else "empty",
            signals=signals,
            warnings=list(report_data.get("warnings") or []),
            errors=[],
            recommendation=(
                "reaction_shot_placement_signals_generated"
                if signals
                else "reaction_shot_placement_signal_adapter_empty"
            ),
            metadata={
                "source": REACTION_SHOT_PLACEMENT_SIGNAL_SOURCE,
                "review_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_41": True,
                "no_render_in_2b_41": True,
                "no_timeline_reorder_in_2b_41": True,
                "no_reaction_apply_in_2b_41": True,
                "no_reaction_insert_in_2b_41": True,
                "no_facecam_move_in_2b_41": True,
                "no_zoom_insert_in_2b_41": True,
            },
        )
        result.refresh_counts()
        return result

    except Exception as exc:
        return ReactionShotPlacementSignalAdapterResult(
            status="failed",
            signals=[],
            warnings=[],
            errors=[f"reaction_shot_placement_signal_adapter_failed:{exc}"],
            recommendation="review_reaction_shot_placement_signal_adapter_error",
            metadata={
                "source": REACTION_SHOT_PLACEMENT_SIGNAL_SOURCE,
                "review_only": True,
                "media_unchanged": True,
            },
        )
