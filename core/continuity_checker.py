from __future__ import annotations

from typing import Any

from models.continuity_check import (
    CONTINUITY_CHECK_STATUS_COMPLETED_WITH_WARNINGS,
    CONTINUITY_CHECK_STATUS_FAILED,
    CONTINUITY_CHECK_STATUS_OK,
    CONTINUITY_CHECK_STATUS_SKIPPED_NO_TRANSITION_DECISIONS,
    CONTINUITY_ISSUE_CENSOR_CONTEXT_RISK,
    CONTINUITY_ISSUE_CONTEXT_JUMP_RISK,
    CONTINUITY_ISSUE_GAP_RISK,
    CONTINUITY_ISSUE_INVALID_TIMING,
    CONTINUITY_ISSUE_OVERLAP_RISK,
    CONTINUITY_ISSUE_PROTECTED_CONTEXT_VIOLATION,
    CONTINUITY_ISSUE_SENTENCE_BREAK_RISK,
    CONTINUITY_ISSUE_TECHNICAL_CONTINUITY_RISK,
    CONTINUITY_ISSUE_TRANSITION_CONFLICT,
    CONTINUITY_PRIORITY_HIGH,
    CONTINUITY_PRIORITY_LOW,
    CONTINUITY_PRIORITY_MEDIUM,
    CONTINUITY_SEVERITY_CRITICAL,
    CONTINUITY_SEVERITY_HIGH,
    CONTINUITY_SEVERITY_MEDIUM,
    ContinuityCheckResult,
    ContinuityIssue,
)


SENTENCE_PROTECTION_TYPES = {
    "sentence_boundary_protection",
    "sentence_protection_zone",
    "sentence_question_context_protection",
}

CONTEXT_TYPES = {
    "interaction_question_answer_segment",
    "interaction_context_needed_segment",
    "interaction_dialogue_segment",
    "segment_protected_context",
    "cut_list_protect_segment",
    "clip_duration_protected",
}

CENSOR_TYPES = {
    "cut_list_censor_keep",
    "clip_duration_censor_keep",
    "profanity_censor_sfx_required",
    "murch_censor_required_context",
}

TECHNICAL_TYPES = {
    "stutter_segment_candidate",
    "freeze_segment_candidate",
    "technical_warning",
    "clip_duration_invalid_timing",
    "cut_list_technical_review",
    "murch_technical_warning",
    "transition_technical_review",
}

HARD_TRANSITION_TYPES = {
    "hard_cut_review",
    "transition_hard_cut_review",
}

UNSAFE_TRANSITION_TYPES = {
    "hard_cut_review",
    "transition_hard_cut_review",
    "quick_fade_review",
    "transition_quick_fade_review",
    "technical_transition_review",
    "transition_technical_review",
}

TRIM_OR_REMOVE_ACTIONS = {
    "REVIEW_TRIM",
    "REVIEW_REMOVE",
}

KEEP_OR_PROTECT_ACTIONS = {
    "KEEP",
    "REVIEW_KEEP",
    "PROTECT",
    "CENSOR_KEEP",
}

RISK_DURATION_STATUSES = {
    "too_long_review",
    "trim_review",
    "invalid_timing_review",
    "technical_review",
}

PROTECT_DURATION_STATUSES = {
    "protect_duration",
    "censor_keep_duration",
}


def clamp_score(value: Any) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return 0.0

    return min(max(numeric_value, 0.0), 1.0)


def _get_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)

    return getattr(item, key, default)


def _first_value(item: Any, keys: list[str], default: Any = None) -> Any:
    for key in keys:
        value = _get_value(item, key, None)
        if value is not None:
            return value

    return default


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    return text


def _list_of_strings(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item) for item in value if item is not None]

    if isinstance(value, tuple):
        return [str(item) for item in value if item is not None]

    return [str(value)]


def _safe_metadata(value: Any) -> dict[str, Any]:
    metadata = _get_value(value, "metadata", {}) or {}
    if isinstance(metadata, dict):
        return dict(metadata)

    return {"raw_metadata": metadata}


def _safe_upper(value: Any) -> str:
    return str(value or "").strip().upper()


def _safe_lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _has_text_flag(values: list[Any], needles: set[str]) -> bool:
    haystack = " ".join(str(value or "").lower() for value in values)
    return any(needle in haystack for needle in needles)


def _derive_duration(
    start_seconds: float | None,
    end_seconds: float | None,
    duration_seconds: float | None,
) -> float | None:
    if duration_seconds is not None:
        return duration_seconds

    if start_seconds is not None and end_seconds is not None:
        return end_seconds - start_seconds

    return None


def _derive_center(
    start_seconds: float | None,
    end_seconds: float | None,
    center_seconds: float | None,
) -> float | None:
    if center_seconds is not None:
        return center_seconds

    if start_seconds is not None and end_seconds is not None:
        return (start_seconds + end_seconds) / 2.0

    if start_seconds is not None:
        return start_seconds

    if end_seconds is not None:
        return end_seconds

    return None


def normalize_transition_decision(value: Any) -> dict[str, Any]:
    value = value or {}

    start_seconds = _float_or_none(
        _first_value(value, ["start_seconds", "start", "start_time"])
    )
    end_seconds = _float_or_none(_first_value(value, ["end_seconds", "end", "end_time"]))
    duration_seconds = _float_or_none(
        _first_value(value, ["duration_seconds", "duration"])
    )
    duration_seconds = _derive_duration(start_seconds, end_seconds, duration_seconds)
    center_seconds = _derive_center(
        start_seconds,
        end_seconds,
        _float_or_none(_first_value(value, ["center_seconds", "center"])),
    )

    decision_basis = _get_value(value, "decision_basis", {}) or {}
    if not isinstance(decision_basis, dict):
        decision_basis = {"raw_decision_basis": decision_basis}

    transition_type = _safe_lower(
        _first_value(value, ["transition_type", "signal_type", "type"])
    )
    cut_list_action = _first_value(value, ["cut_list_action", "proposed_action"])
    duration_status = _first_value(value, ["duration_status", "status"])
    warnings = _list_of_strings(_get_value(value, "warnings", []))
    errors = _list_of_strings(_get_value(value, "errors", []))

    is_protected = (
        bool(_get_value(value, "is_protected", False))
        or bool(decision_basis.get("is_protected", False))
        or _safe_lower(duration_status) in PROTECT_DURATION_STATUSES
        or _safe_upper(cut_list_action) == "PROTECT"
        or transition_type == "no_cut_protect"
    )
    is_censor_keep = (
        bool(_get_value(value, "is_censor_keep", False))
        or bool(decision_basis.get("is_censor_keep", False))
        or _safe_upper(cut_list_action) == "CENSOR_KEEP"
        or _safe_lower(duration_status) == "censor_keep_duration"
        or transition_type == "censor_safe_keep"
    )
    is_technical_review = (
        bool(_get_value(value, "is_technical_review", False))
        or bool(decision_basis.get("is_technical_review", False))
        or _safe_lower(duration_status) in {"technical_review", "invalid_timing_review"}
        or transition_type == "technical_transition_review"
        or _has_text_flag(warnings + errors, {"technical", "stutter", "freeze"})
    )

    return {
        "kind": "transition_decision",
        "id": _string_or_none(_first_value(value, ["decision_id", "id"])),
        "source_item_id": _string_or_none(
            _first_value(value, ["source_item_id", "item_id", "cut_list_item_id"])
        ),
        "segment_id": _string_or_none(_get_value(value, "segment_id")),
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "transition_type": transition_type,
        "transition_confidence": clamp_score(
            _first_value(value, ["transition_confidence", "confidence"], 0.0)
        ),
        "priority": _safe_lower(_get_value(value, "priority", CONTINUITY_PRIORITY_LOW)),
        "proposed_action": str(_get_value(value, "proposed_action", "review_transition")),
        "cut_list_action": cut_list_action,
        "duration_status": duration_status,
        "is_protected": is_protected,
        "is_censor_keep": is_censor_keep,
        "is_technical_review": is_technical_review,
        "is_sentence_safe": bool(_get_value(value, "is_sentence_safe", False)),
        "is_dialogue_context": bool(_get_value(value, "is_dialogue_context", False)),
        "reason": str(_get_value(value, "reason", "") or ""),
        "decision_basis": decision_basis,
        "source_signal_ids": _list_of_strings(_get_value(value, "source_signal_ids", [])),
        "warnings": warnings,
        "errors": errors,
        "metadata": _safe_metadata(value),
    }


def normalize_cut_list_item(value: Any) -> dict[str, Any]:
    value = value or {}

    start_seconds = _float_or_none(
        _first_value(value, ["start_seconds", "start", "start_time"])
    )
    end_seconds = _float_or_none(_first_value(value, ["end_seconds", "end", "end_time"]))
    duration_seconds = _float_or_none(
        _first_value(value, ["duration_seconds", "duration"])
    )
    duration_seconds = _derive_duration(start_seconds, end_seconds, duration_seconds)
    center_seconds = _derive_center(
        start_seconds,
        end_seconds,
        _float_or_none(_first_value(value, ["center_seconds", "center"])),
    )
    proposed_action = str(_get_value(value, "proposed_action", "UNKNOWN_REVIEW"))
    warnings = _list_of_strings(_get_value(value, "warnings", []))
    errors = _list_of_strings(_get_value(value, "errors", []))

    return {
        "kind": "cut_list_item",
        "id": _string_or_none(_first_value(value, ["item_id", "id"])),
        "source_item_id": _string_or_none(_first_value(value, ["item_id", "id"])),
        "segment_id": _string_or_none(_get_value(value, "segment_id")),
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "proposed_action": proposed_action,
        "cut_list_action": proposed_action,
        "action_confidence": clamp_score(_get_value(value, "action_confidence", 0.0)),
        "priority": _safe_lower(_get_value(value, "priority", CONTINUITY_PRIORITY_LOW)),
        "segment_type": str(_get_value(value, "segment_type", "unknown")),
        "censor_required": bool(_get_value(value, "censor_required", False)),
        "is_protected": bool(_get_value(value, "is_protected", False))
        or _safe_upper(proposed_action) == "PROTECT",
        "is_censor_keep": bool(_get_value(value, "censor_required", False))
        or _safe_upper(proposed_action) == "CENSOR_KEEP",
        "is_technical_review": bool(_get_value(value, "is_technical_review", False))
        or _safe_upper(proposed_action) == "TECHNICAL_REVIEW"
        or _has_text_flag(warnings + errors, {"technical", "stutter", "freeze"}),
        "reason": str(_get_value(value, "reason", "") or ""),
        "decision_basis": dict(_get_value(value, "decision_basis", {}) or {}),
        "source_signal_ids": _list_of_strings(_get_value(value, "source_signal_ids", [])),
        "warnings": warnings,
        "errors": errors,
        "metadata": _safe_metadata(value),
    }


def normalize_clip_duration_recommendation(value: Any) -> dict[str, Any]:
    value = value or {}

    start_seconds = _float_or_none(
        _first_value(value, ["start_seconds", "start", "start_time"])
    )
    end_seconds = _float_or_none(_first_value(value, ["end_seconds", "end", "end_time"]))
    duration_seconds = _float_or_none(
        _first_value(value, ["duration_seconds", "duration"])
    )
    duration_seconds = _derive_duration(start_seconds, end_seconds, duration_seconds)
    center_seconds = _derive_center(
        start_seconds,
        end_seconds,
        _float_or_none(_first_value(value, ["center_seconds", "center"])),
    )
    duration_status = _safe_lower(_get_value(value, "duration_status", "unknown_review"))
    warnings = _list_of_strings(_get_value(value, "warnings", []))
    errors = _list_of_strings(_get_value(value, "errors", []))

    return {
        "kind": "clip_duration_recommendation",
        "id": _string_or_none(
            _first_value(value, ["recommendation_id", "id", "item_id"])
        ),
        "source_item_id": _string_or_none(
            _first_value(value, ["source_item_id", "item_id", "cut_list_item_id", "id"])
        ),
        "segment_id": _string_or_none(_get_value(value, "segment_id")),
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "proposed_action": str(_get_value(value, "proposed_action", "review")),
        "duration_status": duration_status,
        "confidence": clamp_score(_get_value(value, "confidence", 0.0)),
        "priority": _safe_lower(_get_value(value, "priority", CONTINUITY_PRIORITY_LOW)),
        "is_protected": bool(_get_value(value, "is_protected", False))
        or duration_status == "protect_duration",
        "is_censor_keep": bool(_get_value(value, "is_censor_keep", False))
        or duration_status == "censor_keep_duration",
        "is_invalid_timing": bool(_get_value(value, "is_invalid_timing", False))
        or duration_status == "invalid_timing_review",
        "is_too_long": bool(_get_value(value, "is_too_long", False))
        or duration_status in {"too_long_review", "trim_review"},
        "source_signal_ids": _list_of_strings(_get_value(value, "source_signal_ids", [])),
        "warnings": warnings,
        "errors": errors,
        "metadata": _safe_metadata(value),
    }


def normalize_signal(value: Any) -> dict[str, Any]:
    value = value or {}

    start_seconds = _float_or_none(
        _first_value(value, ["start_seconds", "start", "start_time"])
    )
    end_seconds = _float_or_none(_first_value(value, ["end_seconds", "end", "end_time"]))
    duration_seconds = _float_or_none(
        _first_value(value, ["duration_seconds", "duration"])
    )
    duration_seconds = _derive_duration(start_seconds, end_seconds, duration_seconds)
    center_seconds = _derive_center(
        start_seconds,
        end_seconds,
        _float_or_none(_first_value(value, ["center_seconds", "center"])),
    )

    return {
        "signal_id": _string_or_none(
            _first_value(value, ["signal_id", "id", "source_signal_id"])
        ),
        "signal_type": _safe_lower(_first_value(value, ["signal_type", "type"], "")),
        "source": _string_or_none(_get_value(value, "source")),
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "confidence": clamp_score(_get_value(value, "confidence", 0.0)),
        "priority": _safe_lower(_get_value(value, "priority", CONTINUITY_PRIORITY_LOW)),
        "metadata": _safe_metadata(value),
    }


def find_related_signals(
    start_seconds: float | None,
    end_seconds: float | None,
    unified_signals: list[Any] | None = None,
    tolerance_seconds: float = 0.35,
) -> list[dict[str, Any]]:
    signals = [normalize_signal(item) for item in (unified_signals or [])]
    if start_seconds is None or end_seconds is None:
        return signals

    related: list[dict[str, Any]] = []
    window_start = float(start_seconds) - tolerance_seconds
    window_end = float(end_seconds) + tolerance_seconds

    for signal in signals:
        signal_start = signal.get("start_seconds")
        signal_end = signal.get("end_seconds")
        signal_center = signal.get("center_seconds")

        if signal_center is not None and window_start <= signal_center <= window_end:
            related.append(signal)
            continue

        if signal_start is None and signal_end is None:
            continue

        if signal_start is None:
            signal_start = signal_end

        if signal_end is None:
            signal_end = signal_start

        if signal_start is None or signal_end is None:
            continue

        if signal_end >= window_start and signal_start <= window_end:
            related.append(signal)

    return related


def _issue_id(prefix: str, issue_type: str, source_id: Any, index: int) -> str:
    source_part = str(source_id or index).replace(" ", "_")
    return f"{prefix}_{issue_type}_{source_part}_{index}"


def _source_signal_ids(signals: list[dict[str, Any]], *items: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in items:
        ids.extend(item.get("source_signal_ids", []) or [])

    ids.extend(str(signal["signal_id"]) for signal in signals if signal.get("signal_id"))
    return sorted(set(ids))


def _signal_types(signals: list[dict[str, Any]]) -> set[str]:
    return {str(signal.get("signal_type") or "") for signal in signals}


def _item_matches(source: dict[str, Any], candidate: dict[str, Any]) -> bool:
    source_item_id = source.get("source_item_id") or source.get("id")
    candidate_item_id = candidate.get("source_item_id") or candidate.get("id")
    if source_item_id and candidate_item_id and source_item_id == candidate_item_id:
        return True

    source_segment_id = source.get("segment_id")
    candidate_segment_id = candidate.get("segment_id")
    if source_segment_id and candidate_segment_id and source_segment_id == candidate_segment_id:
        return True

    source_start = source.get("start_seconds")
    source_end = source.get("end_seconds")
    candidate_start = candidate.get("start_seconds")
    candidate_end = candidate.get("end_seconds")
    if None in {source_start, source_end, candidate_start, candidate_end}:
        return False

    return float(candidate_end) >= float(source_start) and float(candidate_start) <= float(source_end)


def _related_items_for_decision(
    decision: dict[str, Any],
    cut_items: list[dict[str, Any]],
    duration_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    related: list[dict[str, Any]] = []

    for item in cut_items + duration_items:
        if _item_matches(decision, item):
            related.append(item)

    return related


def _combined_context(
    decision: dict[str, Any],
    related_items: list[dict[str, Any]],
    related_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    signal_types = _signal_types(related_signals)
    cut_actions = {
        _safe_upper(item.get("cut_list_action") or item.get("proposed_action"))
        for item in related_items
    }
    duration_statuses = {
        _safe_lower(item.get("duration_status"))
        for item in related_items
        if item.get("duration_status") is not None
    }

    if decision.get("cut_list_action") is not None:
        cut_actions.add(_safe_upper(decision.get("cut_list_action")))

    if decision.get("duration_status") is not None:
        duration_statuses.add(_safe_lower(decision.get("duration_status")))

    transition_type = _safe_lower(decision.get("transition_type"))
    is_hard_transition = transition_type in HARD_TRANSITION_TYPES or bool(
        signal_types & {"transition_hard_cut_review"}
    )
    is_no_cut_protect = transition_type == "no_cut_protect" or bool(
        signal_types & {"transition_no_cut_protect"}
    )
    has_sentence_protection = bool(signal_types & SENTENCE_PROTECTION_TYPES) or bool(
        decision.get("is_sentence_safe")
    )
    has_context = (
        bool(signal_types & CONTEXT_TYPES)
        or bool(decision.get("is_dialogue_context"))
        or any(bool(item.get("is_protected")) for item in related_items)
    )
    has_protected_context = (
        bool(signal_types & CONTEXT_TYPES)
        or bool(decision.get("is_protected"))
        or any(bool(item.get("is_protected")) for item in related_items)
        or "PROTECT" in cut_actions
        or bool(duration_statuses & PROTECT_DURATION_STATUSES)
        or is_no_cut_protect
    )
    has_censor_context = (
        bool(signal_types & CENSOR_TYPES)
        or bool(decision.get("is_censor_keep"))
        or any(bool(item.get("is_censor_keep")) for item in related_items)
        or "CENSOR_KEEP" in cut_actions
        or "censor_keep_duration" in duration_statuses
    )
    has_technical_context = (
        bool(signal_types & TECHNICAL_TYPES)
        or bool(decision.get("is_technical_review"))
        or any(
            bool(item.get("is_technical_review")) or bool(item.get("is_invalid_timing"))
            for item in related_items
        )
        or _has_text_flag(
            list(decision.get("warnings") or [])
            + list(decision.get("errors") or [])
            + [
                warning
                for item in related_items
                for warning in list(item.get("warnings") or [])
            ]
            + [
                error
                for item in related_items
                for error in list(item.get("errors") or [])
            ],
            {"technical", "stutter", "freeze", "invalid timing"},
        )
    )
    has_trim_or_remove = bool(cut_actions & TRIM_OR_REMOVE_ACTIONS) or bool(
        duration_statuses & RISK_DURATION_STATUSES
    )
    has_too_long_protected = (
        has_protected_context or has_censor_context
    ) and bool(duration_statuses & {"too_long_review", "trim_review"})

    return {
        "signal_types": sorted(item for item in signal_types if item),
        "cut_actions": sorted(item for item in cut_actions if item),
        "duration_statuses": sorted(item for item in duration_statuses if item),
        "transition_type": transition_type,
        "is_hard_transition": is_hard_transition,
        "is_no_cut_protect": is_no_cut_protect,
        "has_sentence_protection": has_sentence_protection,
        "has_context": has_context,
        "has_protected_context": has_protected_context,
        "has_censor_context": has_censor_context,
        "has_technical_context": has_technical_context,
        "has_trim_or_remove": has_trim_or_remove,
        "has_too_long_protected": has_too_long_protected,
    }


def _make_issue(
    issue_type: str,
    source: dict[str, Any],
    context: dict[str, Any],
    related_items: list[dict[str, Any]],
    related_signals: list[dict[str, Any]],
    index: int,
    severity: str,
    priority: str,
    confidence: float,
    recommendation: str,
    reason: str,
    is_blocking: bool = False,
    is_protected_context: bool = False,
    is_censor_context: bool = False,
    is_technical_issue: bool = False,
    errors: list[str] | None = None,
) -> ContinuityIssue:
    source_id = source.get("source_item_id") or source.get("id")
    return ContinuityIssue(
        issue_id=_issue_id("continuity_issue", issue_type, source_id, index),
        source_item_id=source.get("source_item_id") or source.get("id"),
        segment_id=source.get("segment_id"),
        start_seconds=source.get("start_seconds"),
        end_seconds=source.get("end_seconds"),
        center_seconds=source.get("center_seconds"),
        duration_seconds=source.get("duration_seconds"),
        issue_type=issue_type,
        severity=severity,
        confidence=clamp_score(confidence),
        priority=priority,
        is_blocking=is_blocking,
        is_protected_context=is_protected_context,
        is_censor_context=is_censor_context,
        is_technical_issue=is_technical_issue,
        requires_review=True,
        recommendation=recommendation,
        reason=reason,
        evidence={
            **context,
            "source": dict(source),
            "related_items": [dict(item) for item in related_items],
            "related_signal_count": len(related_signals),
            "review_only": True,
        },
        source_signal_ids=_source_signal_ids(related_signals, source, *related_items),
        warnings=list(source.get("warnings") or []),
        errors=list(errors or []) + list(source.get("errors") or []),
        metadata={
            "engine": "continuity_checker",
            "review_only": True,
        },
    )


def check_transition_continuity(
    decision: Any,
    related_items: list[Any] | None = None,
    related_signals: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[ContinuityIssue]:
    del metadata

    normalized_decision = normalize_transition_decision(decision)
    normalized_items: list[dict[str, Any]] = []
    for item in related_items or []:
        if isinstance(item, dict) and item.get("kind") == "clip_duration_recommendation":
            normalized_items.append(item)
        elif isinstance(item, dict) and item.get("kind") == "cut_list_item":
            normalized_items.append(item)
        elif _get_value(item, "duration_status") is not None:
            normalized_items.append(normalize_clip_duration_recommendation(item))
        else:
            normalized_items.append(normalize_cut_list_item(item))

    normalized_signals = [normalize_signal(item) for item in (related_signals or [])]
    context = _combined_context(
        normalized_decision,
        normalized_items,
        normalized_signals,
    )
    issues: list[ContinuityIssue] = []
    index = 1

    if context["is_hard_transition"] and context["has_sentence_protection"]:
        blocking = bool(context["is_no_cut_protect"])
        issues.append(
            _make_issue(
                CONTINUITY_ISSUE_SENTENCE_BREAK_RISK,
                normalized_decision,
                context,
                normalized_items,
                normalized_signals,
                index,
                CONTINUITY_SEVERITY_CRITICAL if blocking else CONTINUITY_SEVERITY_HIGH,
                CONTINUITY_PRIORITY_HIGH,
                0.9,
                "review_sentence_boundary_continuity",
                "hard_transition_conflicts_with_sentence_protection",
                is_blocking=blocking,
                is_protected_context=context["has_protected_context"],
            )
        )
        index += 1

    if context["has_context"] and (
        context["has_trim_or_remove"] or context["is_hard_transition"]
    ):
        issues.append(
            _make_issue(
                CONTINUITY_ISSUE_CONTEXT_JUMP_RISK,
                normalized_decision,
                context,
                normalized_items,
                normalized_signals,
                index,
                CONTINUITY_SEVERITY_HIGH,
                CONTINUITY_PRIORITY_HIGH,
                0.86,
                "review_context_jump_continuity",
                "context_segment_is_at_risk_from_review_action_or_transition",
                is_blocking=context["has_protected_context"],
                is_protected_context=context["has_protected_context"],
            )
        )
        index += 1

    if context["has_censor_context"] and (
        context["has_trim_or_remove"] or context["is_hard_transition"]
    ):
        issues.append(
            _make_issue(
                CONTINUITY_ISSUE_CENSOR_CONTEXT_RISK,
                normalized_decision,
                context,
                normalized_items,
                normalized_signals,
                index,
                CONTINUITY_SEVERITY_HIGH,
                CONTINUITY_PRIORITY_HIGH,
                0.9,
                "protect_censor_context_continuity",
                "censor_context_must_be_preserved_for_review",
                is_blocking=True,
                is_protected_context=True,
                is_censor_context=True,
            )
        )
        index += 1

    if (
        context["is_no_cut_protect"] and context["is_hard_transition"]
    ) or (
        context["has_protected_context"] and context["is_hard_transition"]
    ) or (
        context["has_technical_context"]
        and context["transition_type"] in {"quick_fade_review", "transition_quick_fade_review"}
    ):
        issues.append(
            _make_issue(
                CONTINUITY_ISSUE_TRANSITION_CONFLICT,
                normalized_decision,
                context,
                normalized_items,
                normalized_signals,
                index,
                CONTINUITY_SEVERITY_HIGH,
                CONTINUITY_PRIORITY_HIGH,
                0.88,
                "review_transition_conflict",
                "transition_review_conflicts_with_protection_or_technical_context",
                is_blocking=context["has_protected_context"],
                is_protected_context=context["has_protected_context"],
                is_technical_issue=context["has_technical_context"],
            )
        )
        index += 1

    if context["has_too_long_protected"]:
        issues.append(
            _make_issue(
                CONTINUITY_ISSUE_PROTECTED_CONTEXT_VIOLATION,
                normalized_decision,
                context,
                normalized_items,
                normalized_signals,
                index,
                CONTINUITY_SEVERITY_HIGH,
                CONTINUITY_PRIORITY_HIGH,
                0.86,
                "review_context_jump_continuity",
                "protected_or_censor_context_has_duration_review_risk",
                is_blocking=True,
                is_protected_context=True,
                is_censor_context=context["has_censor_context"],
            )
        )
        index += 1

    if context["has_technical_context"]:
        issues.append(
            _make_issue(
                CONTINUITY_ISSUE_TECHNICAL_CONTINUITY_RISK,
                normalized_decision,
                context,
                normalized_items,
                normalized_signals,
                index,
                CONTINUITY_SEVERITY_HIGH,
                CONTINUITY_PRIORITY_HIGH,
                0.84,
                "review_technical_continuity",
                "technical_warning_requires_continuity_review",
                is_technical_issue=True,
            )
        )

    return issues


def _timing_source_id(item: dict[str, Any], index: int) -> str:
    return str(
        item.get("source_item_id")
        or item.get("id")
        or item.get("segment_id")
        or f"timing_item_{index}"
    )


def _is_keep_or_protect_timing_item(item: dict[str, Any]) -> bool:
    action = _safe_upper(item.get("cut_list_action") or item.get("proposed_action"))
    duration_status = _safe_lower(item.get("duration_status"))

    if action in KEEP_OR_PROTECT_ACTIONS:
        return True

    if duration_status in {"duration_ok", "protect_duration", "censor_keep_duration"}:
        return True

    if item.get("is_protected") or item.get("is_censor_keep"):
        return True

    return not action and not duration_status


def _normalize_timing_item(value: Any) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("kind") in {
        "transition_decision",
        "cut_list_item",
        "clip_duration_recommendation",
    }:
        return value

    if _get_value(value, "transition_type") is not None:
        return normalize_transition_decision(value)

    if _get_value(value, "duration_status") is not None:
        return normalize_clip_duration_recommendation(value)

    return normalize_cut_list_item(value)


def check_timing_continuity(
    items: list[Any],
    metadata: dict[str, Any] | None = None,
) -> list[ContinuityIssue]:
    del metadata

    normalized_items = [_normalize_timing_item(item) for item in (items or [])]
    issues: list[ContinuityIssue] = []

    for index, item in enumerate(normalized_items, start=1):
        start_seconds = item.get("start_seconds")
        end_seconds = item.get("end_seconds")
        duration_seconds = item.get("duration_seconds")

        errors: list[str] = []
        if start_seconds is None or end_seconds is None:
            errors.append("missing_start_or_end_seconds")
        if start_seconds is not None and end_seconds is not None and end_seconds < start_seconds:
            errors.append("end_before_start")
        if duration_seconds is not None and duration_seconds < 0:
            errors.append("negative_duration")
        if item.get("is_invalid_timing"):
            errors.append("item_marked_invalid_timing")

        if errors:
            issues.append(
                _make_issue(
                    CONTINUITY_ISSUE_INVALID_TIMING,
                    item,
                    {
                        "timing_errors": list(errors),
                        "signal_types": [],
                        "cut_actions": [],
                        "duration_statuses": [],
                    },
                    [],
                    [],
                    index,
                    CONTINUITY_SEVERITY_HIGH,
                    CONTINUITY_PRIORITY_HIGH,
                    0.95,
                    "review_invalid_timing",
                    "invalid_timing_detected",
                    is_blocking=True,
                    is_technical_issue=True,
                    errors=errors,
                )
            )

    valid_items = [
        item
        for item in normalized_items
        if item.get("start_seconds") is not None
        and item.get("end_seconds") is not None
        and item.get("end_seconds") >= item.get("start_seconds")
    ]
    valid_items.sort(key=lambda item: float(item.get("start_seconds") or 0.0))

    for index, (previous, current) in enumerate(
        zip(valid_items, valid_items[1:]),
        start=1,
    ):
        previous_end = float(previous.get("end_seconds") or 0.0)
        current_start = float(current.get("start_seconds") or 0.0)
        overlap_seconds = previous_end - current_start

        if overlap_seconds > 0.35:
            source = {
                **current,
                "start_seconds": current_start,
                "end_seconds": previous_end,
                "center_seconds": (current_start + previous_end) / 2.0,
                "duration_seconds": overlap_seconds,
                "source_item_id": _timing_source_id(previous, index)
                + "_"
                + _timing_source_id(current, index + 1),
            }
            issues.append(
                _make_issue(
                    CONTINUITY_ISSUE_OVERLAP_RISK,
                    source,
                    {
                        "previous_item": previous,
                        "current_item": current,
                        "overlap_seconds": overlap_seconds,
                        "signal_types": [],
                        "cut_actions": [],
                        "duration_statuses": [],
                    },
                    [],
                    [],
                    index,
                    CONTINUITY_SEVERITY_MEDIUM,
                    CONTINUITY_PRIORITY_MEDIUM,
                    0.8,
                    "review_overlap_continuity",
                    "timeline_items_overlap",
                    is_technical_issue=True,
                )
            )

        gap_seconds = current_start - previous_end
        if (
            gap_seconds > 1.5
            and _is_keep_or_protect_timing_item(previous)
            and _is_keep_or_protect_timing_item(current)
        ):
            source = {
                **current,
                "start_seconds": previous_end,
                "end_seconds": current_start,
                "center_seconds": (previous_end + current_start) / 2.0,
                "duration_seconds": gap_seconds,
                "source_item_id": _timing_source_id(previous, index)
                + "_"
                + _timing_source_id(current, index + 1),
            }
            issues.append(
                _make_issue(
                    CONTINUITY_ISSUE_GAP_RISK,
                    source,
                    {
                        "previous_item": previous,
                        "current_item": current,
                        "gap_seconds": gap_seconds,
                        "signal_types": [],
                        "cut_actions": [],
                        "duration_statuses": [],
                    },
                    [],
                    [],
                    index,
                    CONTINUITY_SEVERITY_MEDIUM,
                    CONTINUITY_PRIORITY_MEDIUM,
                    0.72,
                    "review_gap_continuity",
                    "large_gap_between_keep_or_protect_items",
                    is_technical_issue=True,
                )
            )

    return issues


def _status_for_issues(issues: list[ContinuityIssue]) -> str:
    if issues:
        return CONTINUITY_CHECK_STATUS_COMPLETED_WITH_WARNINGS

    return CONTINUITY_CHECK_STATUS_OK


def _recommendation_for_issues(issues: list[ContinuityIssue]) -> str:
    if not issues:
        return "continuity_ok"

    priority_order = [
        CONTINUITY_ISSUE_CENSOR_CONTEXT_RISK,
        CONTINUITY_ISSUE_SENTENCE_BREAK_RISK,
        CONTINUITY_ISSUE_CONTEXT_JUMP_RISK,
        CONTINUITY_ISSUE_INVALID_TIMING,
        CONTINUITY_ISSUE_OVERLAP_RISK,
        CONTINUITY_ISSUE_GAP_RISK,
        CONTINUITY_ISSUE_TRANSITION_CONFLICT,
        CONTINUITY_ISSUE_PROTECTED_CONTEXT_VIOLATION,
        CONTINUITY_ISSUE_TECHNICAL_CONTINUITY_RISK,
    ]
    recommendation_by_type = {
        CONTINUITY_ISSUE_CENSOR_CONTEXT_RISK: "protect_censor_context_continuity",
        CONTINUITY_ISSUE_SENTENCE_BREAK_RISK: "review_sentence_boundary_continuity",
        CONTINUITY_ISSUE_CONTEXT_JUMP_RISK: "review_context_jump_continuity",
        CONTINUITY_ISSUE_INVALID_TIMING: "review_invalid_timing",
        CONTINUITY_ISSUE_OVERLAP_RISK: "review_overlap_continuity",
        CONTINUITY_ISSUE_GAP_RISK: "review_gap_continuity",
        CONTINUITY_ISSUE_TRANSITION_CONFLICT: "review_transition_conflict",
        CONTINUITY_ISSUE_PROTECTED_CONTEXT_VIOLATION: "review_context_jump_continuity",
        CONTINUITY_ISSUE_TECHNICAL_CONTINUITY_RISK: "review_technical_continuity",
    }
    issue_types = {issue.issue_type for issue in issues}

    for issue_type in priority_order:
        if issue_type in issue_types:
            return recommendation_by_type[issue_type]

    return "review_unknown_continuity"


def run_continuity_check(
    transition_decisions: list[Any] | None = None,
    cut_list_items: list[Any] | None = None,
    clip_duration_recommendations: list[Any] | None = None,
    unified_signals: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ContinuityCheckResult:
    run_metadata = {
        **dict(metadata or {}),
        "engine": "continuity_checker",
        "review_only": True,
    }

    transition_decisions = transition_decisions or []
    cut_list_items = cut_list_items or []
    clip_duration_recommendations = clip_duration_recommendations or []
    unified_signals = unified_signals or []

    if not transition_decisions and not cut_list_items:
        return ContinuityCheckResult(
            status=CONTINUITY_CHECK_STATUS_SKIPPED_NO_TRANSITION_DECISIONS,
            issues=[],
            issue_count=0,
            recommendation="continuity_check_skipped_no_inputs",
            metadata=run_metadata,
        )

    try:
        normalized_decisions = [
            normalize_transition_decision(item) for item in transition_decisions
        ]
        normalized_cut_items = [
            normalize_cut_list_item(item) for item in cut_list_items
        ]
        normalized_duration_items = [
            normalize_clip_duration_recommendation(item)
            for item in clip_duration_recommendations
        ]
        normalized_signals = [normalize_signal(item) for item in unified_signals]

        if not normalized_decisions:
            normalized_decisions = [
                {
                    **item,
                    "kind": "transition_decision",
                    "id": f"continuity_cut_list_fallback_{index}",
                    "transition_type": "",
                    "transition_confidence": item.get("action_confidence", 0.0),
                    "cut_list_action": item.get("cut_list_action")
                    or item.get("proposed_action"),
                    "duration_status": None,
                    "is_sentence_safe": False,
                    "is_dialogue_context": False,
                }
                for index, item in enumerate(normalized_cut_items, start=1)
            ]

        issues: list[ContinuityIssue] = []

        for decision in normalized_decisions:
            related_items = _related_items_for_decision(
                decision,
                normalized_cut_items,
                normalized_duration_items,
            )
            related_signals = find_related_signals(
                decision.get("start_seconds"),
                decision.get("end_seconds"),
                unified_signals=normalized_signals,
            )
            issues.extend(
                check_transition_continuity(
                    decision,
                    related_items=related_items,
                    related_signals=related_signals,
                    metadata=run_metadata,
                )
            )

        if normalized_cut_items:
            timing_items = normalized_cut_items
        elif normalized_decisions:
            timing_items = normalized_decisions
        else:
            timing_items = normalized_duration_items

        issues.extend(
            check_timing_continuity(
                timing_items,
                metadata=run_metadata,
            )
        )

        result = ContinuityCheckResult(
            status=_status_for_issues(issues),
            issues=issues,
            recommendation=_recommendation_for_issues(issues),
            warnings=[],
            errors=[],
            metadata={
                **run_metadata,
                "transition_decision_count": len(transition_decisions),
                "cut_list_item_count": len(cut_list_items),
                "clip_duration_recommendation_count": len(
                    clip_duration_recommendations
                ),
                "unified_signal_count": len(unified_signals),
            },
        )
        result.refresh_counts()
        return result
    except Exception as exc:
        return ContinuityCheckResult(
            status=CONTINUITY_CHECK_STATUS_FAILED,
            issues=[],
            issue_count=0,
            recommendation="continuity_check_failed",
            warnings=[],
            errors=[str(exc)],
            metadata=run_metadata,
        )
