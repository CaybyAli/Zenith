from __future__ import annotations

from typing import Any

from models.final_cut_list import (
    FINAL_ACTION_BLOCKED_BY_CONTINUITY,
    FINAL_ACTION_CENSOR_KEEP,
    FINAL_ACTION_KEEP_HIGH_VALUE,
    FINAL_ACTION_KEEP_REVIEW,
    FINAL_ACTION_PROTECT,
    FINAL_ACTION_REMOVE_REVIEW,
    FINAL_ACTION_TECHNICAL_REVIEW,
    FINAL_ACTION_TRIM_REVIEW,
    FINAL_ACTION_UNKNOWN_REVIEW,
    FINAL_CUT_LIST_STATUS_COMPLETED_WITH_WARNINGS,
    FINAL_CUT_LIST_STATUS_FAILED,
    FINAL_CUT_LIST_STATUS_OK,
    FINAL_CUT_LIST_STATUS_SKIPPED_NO_CUT_LIST_ITEMS,
    FINAL_CUT_LIST_STATUS_SKIPPED_NO_INPUTS,
    FINAL_PRIORITY_HIGH,
    FINAL_PRIORITY_LOW,
    FINAL_PRIORITY_MEDIUM,
    FinalCutListItem,
    FinalCutListPlan,
)


HIGH_VALUE_SIGNAL_TYPES = {
    "cut_list_keep_candidate",
    "murch_high_score",
    "murch_high_value",
    "segment_highlight",
    "segment_hook_candidate",
    "content_value_high",
    "keyword_emotion_hype",
    "face_reaction_high",
    "visual_energy_high",
}

PROTECT_SIGNAL_TYPES = {
    "cut_list_protect_segment",
    "clip_duration_protected",
    "transition_no_cut_protect",
    "continuity_protected_context_violation",
    "sentence_boundary_protection",
    "sentence_protection_zone",
    "segment_protected_context",
}

CENSOR_SIGNAL_TYPES = {
    "cut_list_censor_keep",
    "clip_duration_censor_keep",
    "transition_censor_safe_keep",
    "continuity_censor_context_risk",
    "profanity_censor_sfx_required",
    "murch_censor_required_context",
}

TECHNICAL_SIGNAL_TYPES = {
    "cut_list_technical_review",
    "clip_duration_technical_review",
    "clip_duration_invalid_timing",
    "transition_technical_review",
    "continuity_technical_risk",
    "stutter_segment_candidate",
    "freeze_segment_candidate",
    "technical_warning",
}

REMOVE_SIGNAL_TYPES = {
    "cut_list_review_remove",
    "segment_dead_candidate",
    "dead_content_candidate",
    "dead_content_low_value_candidate",
}

TRIM_SIGNAL_TYPES = {
    "cut_list_review_trim",
    "clip_duration_too_long_review",
}

BLOCKING_CONTINUITY_TYPES = {
    "invalid_timing",
}

CRITICAL_CONTINUITY_TYPES = {
    "sentence_break_risk",
    "context_jump_risk",
}


def clamp_score(value: Any) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return 0.0

    return min(max(numeric_value, 0.0), 1.0)


def _object_to_dict(value: Any) -> dict[str, Any]:
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


def _safe_upper(value: Any) -> str:
    return str(value or "").strip().upper()


def _safe_lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _list_of_strings(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item) for item in value if item is not None]

    if isinstance(value, tuple):
        return [str(item) for item in value if item is not None]

    return [str(value)]


def _dict_or_wrapped(value: Any, key: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    if value is None:
        return {}

    return {key: value}


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


def _normalize_time_fields(value: Any) -> dict[str, float | None]:
    start_seconds = _float_or_none(
        _first_value(value, ["start_seconds", "start", "start_time"])
    )
    end_seconds = _float_or_none(
        _first_value(value, ["end_seconds", "end", "end_time"])
    )
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
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
    }


def _has_text_flag(values: list[Any], needles: set[str]) -> bool:
    haystack = " ".join(str(value or "").lower() for value in values)
    return any(needle in haystack for needle in needles)


def _source_ids(*items: dict[str, Any], signals: list[dict[str, Any]] | None = None) -> list[str]:
    ids: list[str] = []
    for item in items:
        ids.extend(_list_of_strings(item.get("source_signal_ids")))

    for signal in signals or []:
        signal_id = signal.get("signal_id")
        if signal_id:
            ids.append(str(signal_id))

    return sorted(set(ids))


def normalize_cut_list_item(value: Any) -> dict[str, Any]:
    data = _object_to_dict(value)
    time_fields = _normalize_time_fields(data)
    action = _safe_upper(
        _first_value(data, ["proposed_action", "cut_list_action", "action"])
    )
    warnings = _list_of_strings(data.get("warnings"))
    errors = _list_of_strings(data.get("errors"))
    decision_basis = _dict_or_wrapped(data.get("decision_basis"), "raw_decision_basis")
    metadata = _dict_or_wrapped(data.get("metadata"), "raw_metadata")
    segment_type = _string_or_none(data.get("segment_type"))

    return {
        "kind": "cut_list_item",
        "id": _string_or_none(_first_value(data, ["item_id", "id"])),
        "source_item_id": _string_or_none(
            _first_value(data, ["source_item_id", "item_id", "id"])
        ),
        "segment_id": _string_or_none(
            _first_value(data, ["segment_id", "source_segment_id"])
        ),
        **time_fields,
        "cut_list_action": action or "UNKNOWN_REVIEW",
        "action_confidence": clamp_score(data.get("action_confidence")),
        "priority": _safe_lower(data.get("priority")),
        "segment_type": segment_type,
        "murch_score": clamp_score(data.get("murch_score")),
        "is_protected": bool(data.get("is_protected", False))
        or action == "PROTECT"
        or segment_type == "protected_context",
        "is_censor_keep": bool(data.get("censor_required", False))
        or bool(data.get("is_censor_keep", False))
        or action == "CENSOR_KEEP",
        "is_review_required": bool(data.get("is_review_required", True)),
        "is_keep_candidate": bool(data.get("is_keep_candidate", False))
        or action in {"KEEP", "REVIEW_KEEP"},
        "is_trim_candidate": bool(data.get("is_trim_candidate", False))
        or action == "REVIEW_TRIM",
        "is_remove_candidate": bool(data.get("is_remove_candidate", False))
        or action == "REVIEW_REMOVE",
        "is_technical_review": bool(data.get("is_technical_review", False))
        or action == "TECHNICAL_REVIEW"
        or _has_text_flag(warnings + errors, {"technical", "stutter", "freeze"}),
        "reason": str(data.get("reason") or ""),
        "decision_basis": decision_basis,
        "source_signal_ids": _list_of_strings(data.get("source_signal_ids")),
        "warnings": warnings,
        "errors": errors,
        "metadata": metadata,
    }


def normalize_clip_duration_recommendation(value: Any) -> dict[str, Any]:
    data = _object_to_dict(value)
    time_fields = _normalize_time_fields(data)
    duration_status = _safe_lower(data.get("duration_status")) or "unknown_review"
    warnings = _list_of_strings(data.get("warnings"))
    errors = _list_of_strings(data.get("errors"))

    recommended_start = _float_or_none(
        _first_value(data, ["recommended_start_seconds", "suggested_start_seconds"])
    )
    recommended_end = _float_or_none(
        _first_value(data, ["recommended_end_seconds", "suggested_end_seconds"])
    )
    recommended_duration = _float_or_none(
        _first_value(
            data,
            ["recommended_duration_seconds", "suggested_duration_seconds"],
        )
    )
    recommended_duration = _derive_duration(
        recommended_start,
        recommended_end,
        recommended_duration,
    )

    return {
        "kind": "clip_duration_recommendation",
        "id": _string_or_none(
            _first_value(data, ["recommendation_id", "id", "item_id"])
        ),
        "source_item_id": _string_or_none(
            _first_value(data, ["source_item_id", "item_id", "cut_list_item_id", "id"])
        ),
        "segment_id": _string_or_none(data.get("segment_id")),
        **time_fields,
        "duration_status": duration_status,
        "confidence": clamp_score(data.get("confidence")),
        "recommended_start_seconds": recommended_start,
        "recommended_end_seconds": recommended_end,
        "recommended_duration_seconds": recommended_duration,
        "is_protected": bool(data.get("is_protected", False))
        or duration_status == "protect_duration",
        "is_censor_keep": bool(data.get("is_censor_keep", False))
        or duration_status == "censor_keep_duration",
        "is_invalid_timing": bool(data.get("is_invalid_timing", False))
        or duration_status == "invalid_timing_review",
        "is_too_long": bool(data.get("is_too_long", False))
        or duration_status in {"too_long_review", "trim_review"},
        "is_technical_review": bool(data.get("is_technical_review", False))
        or duration_status in {"technical_review", "invalid_timing_review"},
        "decision_basis": _dict_or_wrapped(
            data.get("decision_basis"),
            "raw_decision_basis",
        ),
        "source_signal_ids": _list_of_strings(data.get("source_signal_ids")),
        "warnings": warnings,
        "errors": errors,
        "metadata": _dict_or_wrapped(data.get("metadata"), "raw_metadata"),
    }


def normalize_transition_decision(value: Any) -> dict[str, Any]:
    data = _object_to_dict(value)
    time_fields = _normalize_time_fields(data)
    transition_type = _safe_lower(
        _first_value(data, ["transition_type", "signal_type", "type"])
    )
    warnings = _list_of_strings(data.get("warnings"))
    errors = _list_of_strings(data.get("errors"))
    decision_basis = _dict_or_wrapped(data.get("decision_basis"), "raw_decision_basis")

    return {
        "kind": "transition_decision",
        "id": _string_or_none(_first_value(data, ["decision_id", "id"])),
        "source_item_id": _string_or_none(
            _first_value(data, ["source_item_id", "item_id", "cut_list_item_id"])
        ),
        "segment_id": _string_or_none(data.get("segment_id")),
        **time_fields,
        "transition_type": transition_type,
        "transition_confidence": clamp_score(
            _first_value(data, ["transition_confidence", "confidence"])
        ),
        "cut_list_action": _safe_upper(data.get("cut_list_action")),
        "duration_status": _safe_lower(data.get("duration_status")),
        "is_protected": bool(data.get("is_protected", False))
        or transition_type == "no_cut_protect",
        "is_censor_keep": bool(data.get("is_censor_keep", False))
        or transition_type == "censor_safe_keep",
        "is_technical_review": bool(data.get("is_technical_review", False))
        or transition_type == "technical_transition_review"
        or _has_text_flag(warnings + errors, {"technical", "stutter", "freeze"}),
        "decision_basis": decision_basis,
        "source_signal_ids": _list_of_strings(data.get("source_signal_ids")),
        "warnings": warnings,
        "errors": errors,
        "metadata": _dict_or_wrapped(data.get("metadata"), "raw_metadata"),
    }


def normalize_continuity_issue(value: Any) -> dict[str, Any]:
    data = _object_to_dict(value)
    time_fields = _normalize_time_fields(data)
    issue_type = _safe_lower(data.get("issue_type")) or "unknown_continuity_review"
    severity = _safe_lower(data.get("severity")) or "low"
    warnings = _list_of_strings(data.get("warnings"))
    errors = _list_of_strings(data.get("errors"))

    is_blocking = bool(data.get("is_blocking", False))
    if issue_type in BLOCKING_CONTINUITY_TYPES:
        is_blocking = True
    if issue_type in CRITICAL_CONTINUITY_TYPES and severity == "critical":
        is_blocking = True
    if issue_type == "transition_conflict" and severity in {"high", "critical"}:
        is_blocking = True

    return {
        "kind": "continuity_issue",
        "id": _string_or_none(_first_value(data, ["issue_id", "id"])),
        "source_item_id": _string_or_none(
            _first_value(data, ["source_item_id", "item_id", "cut_list_item_id"])
        ),
        "segment_id": _string_or_none(data.get("segment_id")),
        **time_fields,
        "issue_type": issue_type,
        "severity": severity,
        "confidence": clamp_score(data.get("confidence")),
        "is_blocking": is_blocking,
        "is_protected_context": bool(data.get("is_protected_context", False))
        or issue_type == "protected_context_violation",
        "is_censor_context": bool(data.get("is_censor_context", False))
        or issue_type == "censor_context_risk",
        "is_technical_issue": bool(data.get("is_technical_issue", False))
        or issue_type in {"invalid_timing", "technical_continuity_risk"},
        "requires_review": bool(data.get("requires_review", True)),
        "reason": str(data.get("reason") or ""),
        "evidence": _dict_or_wrapped(data.get("evidence"), "raw_evidence"),
        "source_signal_ids": _list_of_strings(data.get("source_signal_ids")),
        "warnings": warnings,
        "errors": errors,
        "metadata": _dict_or_wrapped(data.get("metadata"), "raw_metadata"),
    }


def normalize_murch_score(value: Any) -> dict[str, Any]:
    data = _object_to_dict(value)
    time_fields = _normalize_time_fields(data)
    murch_score = clamp_score(
        _first_value(data, ["murch_score", "weighted_score", "score"])
    )
    murch_tier = _safe_lower(data.get("murch_tier"))
    warnings = _list_of_strings(data.get("warnings"))
    errors = _list_of_strings(data.get("errors"))

    return {
        "kind": "murch_score",
        "id": _string_or_none(_first_value(data, ["score_id", "id"])),
        "source_item_id": _string_or_none(data.get("source_item_id")),
        "segment_id": _string_or_none(
            _first_value(data, ["segment_id", "source_segment_id"])
        ),
        **time_fields,
        "segment_type": _string_or_none(data.get("segment_type")),
        "murch_score": murch_score,
        "murch_tier": murch_tier,
        "is_high_murch_score": bool(data.get("is_high_murch_score", False))
        or murch_tier == "high"
        or murch_score >= 0.8,
        "is_low_murch_score": bool(data.get("is_low_murch_score", False))
        or murch_tier == "low"
        or (0.0 < murch_score <= 0.25),
        "is_protected_context": bool(data.get("is_protected_context", False))
        or murch_tier == "protected",
        "is_censor_required": bool(data.get("is_censor_required", False))
        or bool(data.get("censor_required", False)),
        "is_technical_warning": bool(data.get("is_technical_warning", False))
        or murch_tier == "technical_warning"
        or _has_text_flag(warnings + errors, {"technical", "stutter", "freeze"}),
        "source_signal_ids": _list_of_strings(data.get("source_signal_ids")),
        "warnings": warnings,
        "errors": errors,
        "metadata": _dict_or_wrapped(data.get("metadata"), "raw_metadata"),
    }


def normalize_segment_classification(value: Any) -> dict[str, Any]:
    data = _object_to_dict(value)
    time_fields = _normalize_time_fields(data)
    segment_type = _safe_lower(data.get("segment_type")) or "unknown"
    warnings = _list_of_strings(data.get("warnings"))
    errors = _list_of_strings(data.get("errors"))

    return {
        "kind": "segment_classification",
        "id": _string_or_none(_first_value(data, ["classification_id", "id"])),
        "source_item_id": _string_or_none(data.get("source_item_id")),
        "segment_id": _string_or_none(data.get("segment_id")),
        **time_fields,
        "segment_type": segment_type,
        "confidence": clamp_score(data.get("confidence")),
        "segment_score": clamp_score(data.get("segment_score")),
        "is_highlight_candidate": bool(data.get("is_highlight_candidate", False))
        or segment_type in {"highlight", "strong_moment"},
        "is_hook_candidate": bool(data.get("is_hook_candidate", False))
        or segment_type == "hook_candidate",
        "is_protected_context": bool(data.get("is_protected_context", False))
        or segment_type == "protected_context",
        "is_dead_candidate": bool(data.get("is_dead_candidate", False))
        or segment_type == "dead_candidate",
        "censor_required": bool(data.get("censor_required", False))
        or segment_type == "censor_required_segment",
        "is_technical_warning": bool(data.get("is_technical_warning", False))
        or segment_type == "technical_warning"
        or _has_text_flag(warnings + errors, {"technical", "stutter", "freeze"}),
        "source_signal_ids": _list_of_strings(data.get("source_signal_ids")),
        "warnings": warnings,
        "errors": errors,
        "metadata": _dict_or_wrapped(data.get("metadata"), "raw_metadata"),
    }


def normalize_signal(value: Any) -> dict[str, Any]:
    data = _object_to_dict(value)
    time_fields = _normalize_time_fields(data)

    return {
        "kind": "unified_signal",
        "signal_id": _string_or_none(
            _first_value(data, ["signal_id", "id", "source_signal_id"])
        ),
        "source_item_id": _string_or_none(data.get("source_item_id")),
        "segment_id": _string_or_none(data.get("segment_id")),
        **time_fields,
        "signal_type": _safe_lower(_first_value(data, ["signal_type", "type"])),
        "source": _string_or_none(data.get("source")),
        "confidence": clamp_score(_first_value(data, ["confidence", "signal_score"])),
        "priority": _safe_lower(data.get("priority")),
        "action_hint": _safe_lower(data.get("action_hint")),
        "reason": str(data.get("reason") or ""),
        "metadata": _dict_or_wrapped(data.get("metadata"), "raw_metadata"),
    }


def _matches_by_identity(source: dict[str, Any], candidate: dict[str, Any]) -> bool:
    source_ids = {
        source.get("id"),
        source.get("source_item_id"),
        source.get("segment_id"),
    }
    candidate_ids = {
        candidate.get("id"),
        candidate.get("source_item_id"),
        candidate.get("segment_id"),
    }
    source_ids.discard(None)
    candidate_ids.discard(None)

    return bool(source_ids & candidate_ids)


def _matches_by_time(
    source: dict[str, Any],
    candidate: dict[str, Any],
    tolerance_seconds: float,
) -> bool:
    source_start = source.get("start_seconds")
    source_end = source.get("end_seconds")
    candidate_start = candidate.get("start_seconds")
    candidate_end = candidate.get("end_seconds")
    candidate_center = candidate.get("center_seconds")

    if source_start is None and source_end is None:
        return False

    if source_start is None:
        source_start = source_end
    if source_end is None:
        source_end = source_start

    if candidate_center is not None:
        return (
            float(source_start) - tolerance_seconds
            <= float(candidate_center)
            <= float(source_end) + tolerance_seconds
        )

    if candidate_start is None and candidate_end is None:
        return False

    if candidate_start is None:
        candidate_start = candidate_end
    if candidate_end is None:
        candidate_end = candidate_start

    return (
        float(candidate_end) >= float(source_start) - tolerance_seconds
        and float(candidate_start) <= float(source_end) + tolerance_seconds
    )


def find_related_by_time(
    source: Any,
    candidates: list[Any] | None = None,
    tolerance_seconds: float = 0.35,
) -> list[dict[str, Any]]:
    normalized_source = (
        source if isinstance(source, dict) else normalize_cut_list_item(source)
    )
    related: list[dict[str, Any]] = []

    for candidate in candidates or []:
        candidate_data = candidate if isinstance(candidate, dict) else _object_to_dict(candidate)
        if not candidate_data:
            continue

        if _matches_by_identity(normalized_source, candidate_data) or _matches_by_time(
            normalized_source,
            candidate_data,
            tolerance_seconds,
        ):
            related.append(candidate_data)

    return related


def _related_items(
    source: dict[str, Any],
    candidates: list[dict[str, Any]],
    tolerance_seconds: float = 0.35,
) -> list[dict[str, Any]]:
    related: list[dict[str, Any]] = []
    for candidate in candidates:
        if _matches_by_identity(source, candidate) or _matches_by_time(
            source,
            candidate,
            tolerance_seconds,
        ):
            related.append(candidate)

    return related


def _signal_types(signals: list[dict[str, Any]]) -> set[str]:
    return {str(signal.get("signal_type") or "") for signal in signals}


def collect_finalization_evidence(
    cut_list_item: Any = None,
    duration_recommendation: Any = None,
    transition_decision: Any = None,
    continuity_issues: list[Any] | None = None,
    murch_score: Any = None,
    segment_classification: Any = None,
    related_signals: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cut_item = (
        cut_list_item
        if isinstance(cut_list_item, dict)
        else normalize_cut_list_item(cut_list_item)
    )
    duration_item = (
        duration_recommendation
        if isinstance(duration_recommendation, dict)
        else normalize_clip_duration_recommendation(duration_recommendation)
        if duration_recommendation is not None
        else {}
    )
    transition_item = (
        transition_decision
        if isinstance(transition_decision, dict)
        else normalize_transition_decision(transition_decision)
        if transition_decision is not None
        else {}
    )
    issue_items = [
        item if isinstance(item, dict) else normalize_continuity_issue(item)
        for item in continuity_issues or []
    ]
    murch_item = (
        murch_score
        if isinstance(murch_score, dict)
        else normalize_murch_score(murch_score)
        if murch_score is not None
        else {}
    )
    segment_item = (
        segment_classification
        if isinstance(segment_classification, dict)
        else normalize_segment_classification(segment_classification)
        if segment_classification is not None
        else {}
    )
    signal_items = [
        item if isinstance(item, dict) else normalize_signal(item)
        for item in related_signals or []
    ]

    signal_types = _signal_types(signal_items)
    cut_action = _safe_upper(cut_item.get("cut_list_action"))
    duration_status = _safe_lower(duration_item.get("duration_status"))
    transition_type = _safe_lower(transition_item.get("transition_type"))
    segment_type = _safe_lower(
        segment_item.get("segment_type") or cut_item.get("segment_type")
    )
    murch_value = clamp_score(
        murch_item.get("murch_score")
        if murch_item
        else cut_item.get("murch_score")
    )
    warnings = (
        list(cut_item.get("warnings") or [])
        + list(duration_item.get("warnings") or [])
        + list(transition_item.get("warnings") or [])
        + list(murch_item.get("warnings") or [])
        + list(segment_item.get("warnings") or [])
    )
    errors = (
        list(cut_item.get("errors") or [])
        + list(duration_item.get("errors") or [])
        + list(transition_item.get("errors") or [])
        + list(murch_item.get("errors") or [])
        + list(segment_item.get("errors") or [])
    )
    for issue in issue_items:
        warnings.extend(issue.get("warnings") or [])
        errors.extend(issue.get("errors") or [])

    start = cut_item.get("start_seconds")
    end = cut_item.get("end_seconds")
    duration_seconds = cut_item.get("duration_seconds")
    invalid_timing = bool(duration_item.get("is_invalid_timing", False))
    invalid_timing = invalid_timing or any(
        issue.get("issue_type") == "invalid_timing" for issue in issue_items
    )
    invalid_timing = invalid_timing or (
        start is not None and end is not None and float(end) < float(start)
    )
    invalid_timing = invalid_timing or (
        duration_seconds is not None and float(duration_seconds) < 0.0
    )

    continuity_blocked = bool(invalid_timing) or any(
        bool(issue.get("is_blocking", False)) for issue in issue_items
    )
    continuity_blocked = continuity_blocked or any(
        issue.get("issue_type") in CRITICAL_CONTINUITY_TYPES
        and issue.get("severity") == "critical"
        for issue in issue_items
    )
    continuity_blocked = continuity_blocked or any(
        issue.get("issue_type") == "transition_conflict"
        and issue.get("severity") in {"high", "critical"}
        for issue in issue_items
    )

    is_protected = (
        cut_action == "PROTECT"
        or bool(cut_item.get("is_protected", False))
        or bool(duration_item.get("is_protected", False))
        or bool(transition_item.get("is_protected", False))
        or bool(murch_item.get("is_protected_context", False))
        or bool(segment_item.get("is_protected_context", False))
        or any(issue.get("is_protected_context") for issue in issue_items)
        or bool(signal_types & PROTECT_SIGNAL_TYPES)
        or segment_type == "protected_context"
    )

    is_censor_keep = (
        cut_action == "CENSOR_KEEP"
        or bool(cut_item.get("is_censor_keep", False))
        or bool(duration_item.get("is_censor_keep", False))
        or bool(transition_item.get("is_censor_keep", False))
        or bool(murch_item.get("is_censor_required", False))
        or bool(segment_item.get("censor_required", False))
        or any(issue.get("is_censor_context") for issue in issue_items)
        or bool(signal_types & CENSOR_SIGNAL_TYPES)
        or segment_type == "censor_required_segment"
    )

    is_technical_review = (
        cut_action == "TECHNICAL_REVIEW"
        or bool(cut_item.get("is_technical_review", False))
        or bool(duration_item.get("is_technical_review", False))
        or bool(transition_item.get("is_technical_review", False))
        or bool(murch_item.get("is_technical_warning", False))
        or bool(segment_item.get("is_technical_warning", False))
        or any(issue.get("is_technical_issue") for issue in issue_items)
        or bool(signal_types & TECHNICAL_SIGNAL_TYPES)
        or _has_text_flag(warnings + errors, {"technical", "stutter", "freeze"})
    )

    is_high_value = (
        cut_action == "KEEP"
        or bool(murch_item.get("is_high_murch_score", False))
        or murch_value >= 0.8
        or bool(segment_item.get("is_highlight_candidate", False))
        or bool(segment_item.get("is_hook_candidate", False))
        or bool(signal_types & HIGH_VALUE_SIGNAL_TYPES)
    )
    is_keep_review = cut_action == "REVIEW_KEEP"
    is_trim_candidate = (
        cut_action == "REVIEW_TRIM"
        or bool(cut_item.get("is_trim_candidate", False))
        or bool(duration_item.get("is_too_long", False))
        or duration_status in {"too_long_review", "trim_review"}
        or transition_type
        in {
            "hard_cut_review",
            "j_cut_review",
            "l_cut_review",
            "quick_fade_review",
        }
        or bool(signal_types & TRIM_SIGNAL_TYPES)
    )
    is_remove_candidate = (
        cut_action == "REVIEW_REMOVE"
        or bool(cut_item.get("is_remove_candidate", False))
        or bool(segment_item.get("is_dead_candidate", False))
        or segment_type == "dead_candidate"
        or bool(murch_item.get("is_low_murch_score", False))
        or bool(signal_types & REMOVE_SIGNAL_TYPES)
    )

    confidence_values = [
        cut_item.get("action_confidence"),
        duration_item.get("confidence"),
        transition_item.get("transition_confidence"),
        murch_value,
        segment_item.get("confidence"),
    ] + [signal.get("confidence") for signal in signal_items]

    final_confidence = max(clamp_score(value) for value in confidence_values)

    return {
        "cut_item": cut_item,
        "duration_item": duration_item,
        "transition_item": transition_item,
        "continuity_issues": issue_items,
        "murch_item": murch_item,
        "segment_item": segment_item,
        "related_signals": signal_items,
        "cut_list_action": cut_action or "UNKNOWN_REVIEW",
        "duration_status": duration_status or None,
        "transition_type": transition_type or None,
        "segment_type": segment_type or cut_item.get("segment_type"),
        "murch_score": murch_value,
        "continuity_blocked": continuity_blocked,
        "is_protected": is_protected,
        "is_censor_keep": is_censor_keep,
        "is_technical_review": is_technical_review,
        "is_high_value": is_high_value,
        "is_keep_review": is_keep_review,
        "is_trim_candidate": is_trim_candidate,
        "is_remove_candidate": is_remove_candidate,
        "is_invalid_timing": invalid_timing,
        "final_confidence": final_confidence,
        "warnings": warnings,
        "errors": errors,
        "source_signal_ids": _source_ids(
            cut_item,
            duration_item,
            transition_item,
            murch_item,
            segment_item,
            *issue_items,
            signals=signal_items,
        ),
        "metadata": {
            **dict(metadata or {}),
            "review_only": True,
            "related_signal_count": len(signal_items),
            "continuity_issue_count": len(issue_items),
        },
    }


def infer_final_action(evidence: dict[str, Any]) -> str:
    if evidence.get("continuity_blocked"):
        return FINAL_ACTION_BLOCKED_BY_CONTINUITY

    if evidence.get("is_protected"):
        return FINAL_ACTION_PROTECT

    if evidence.get("is_censor_keep"):
        return FINAL_ACTION_CENSOR_KEEP

    if evidence.get("is_technical_review") or evidence.get("is_invalid_timing"):
        return FINAL_ACTION_TECHNICAL_REVIEW

    if evidence.get("is_high_value"):
        return FINAL_ACTION_KEEP_HIGH_VALUE

    if evidence.get("is_trim_candidate"):
        return FINAL_ACTION_TRIM_REVIEW

    if evidence.get("is_remove_candidate"):
        return FINAL_ACTION_REMOVE_REVIEW

    if evidence.get("is_keep_review"):
        return FINAL_ACTION_KEEP_REVIEW

    return FINAL_ACTION_UNKNOWN_REVIEW


def _priority_for_action(action: str) -> str:
    if action in {
        FINAL_ACTION_BLOCKED_BY_CONTINUITY,
        FINAL_ACTION_PROTECT,
        FINAL_ACTION_CENSOR_KEEP,
        FINAL_ACTION_TECHNICAL_REVIEW,
        FINAL_ACTION_KEEP_HIGH_VALUE,
    }:
        return FINAL_PRIORITY_HIGH

    if action in {
        FINAL_ACTION_KEEP_REVIEW,
        FINAL_ACTION_TRIM_REVIEW,
        FINAL_ACTION_REMOVE_REVIEW,
    }:
        return FINAL_PRIORITY_MEDIUM

    return FINAL_PRIORITY_LOW


def _reason_for_action(action: str, evidence: dict[str, Any]) -> str:
    if action == FINAL_ACTION_BLOCKED_BY_CONTINUITY:
        return "continuity_blocking_issue_requires_review"
    if action == FINAL_ACTION_PROTECT:
        return "protected_context_preserved_for_review"
    if action == FINAL_ACTION_CENSOR_KEEP:
        return "censor_context_preserved_for_review"
    if action == FINAL_ACTION_TECHNICAL_REVIEW:
        return "technical_risk_requires_review"
    if action == FINAL_ACTION_KEEP_HIGH_VALUE:
        return "high_value_candidate_kept_for_review"
    if action == FINAL_ACTION_KEEP_REVIEW:
        return "keep_candidate_requires_review"
    if action == FINAL_ACTION_TRIM_REVIEW:
        return "trim_candidate_requires_review"
    if action == FINAL_ACTION_REMOVE_REVIEW:
        return "remove_candidate_requires_review_only"

    cut_item = evidence.get("cut_item") or {}
    return str(cut_item.get("reason") or "unknown_final_decision_requires_review")


def build_final_cut_list_item(
    cut_list_item: Any = None,
    duration_recommendation: Any = None,
    transition_decision: Any = None,
    continuity_issues: list[Any] | None = None,
    murch_score: Any = None,
    segment_classification: Any = None,
    related_signals: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> FinalCutListItem:
    evidence = collect_finalization_evidence(
        cut_list_item=cut_list_item,
        duration_recommendation=duration_recommendation,
        transition_decision=transition_decision,
        continuity_issues=continuity_issues,
        murch_score=murch_score,
        segment_classification=segment_classification,
        related_signals=related_signals,
        metadata=metadata,
    )
    cut_item = evidence["cut_item"]
    duration_item = evidence["duration_item"]
    transition_item = evidence["transition_item"]
    action = infer_final_action(evidence)
    source_item_id = cut_item.get("source_item_id") or cut_item.get("id")

    decision_basis = {
        "cut_list_action": evidence.get("cut_list_action"),
        "duration_status": evidence.get("duration_status"),
        "transition_type": evidence.get("transition_type"),
        "murch_score": evidence.get("murch_score"),
        "continuity_issue_count": len(evidence.get("continuity_issues") or []),
        "related_signal_count": len(evidence.get("related_signals") or []),
        "review_only": True,
    }

    return FinalCutListItem(
        final_item_id=f"final_cut_list_item_{source_item_id or 'unknown'}",
        source_item_id=source_item_id,
        segment_id=cut_item.get("segment_id"),
        start_seconds=cut_item.get("start_seconds"),
        end_seconds=cut_item.get("end_seconds"),
        center_seconds=cut_item.get("center_seconds"),
        duration_seconds=cut_item.get("duration_seconds"),
        final_action=action,
        final_confidence=evidence["final_confidence"],
        priority=_priority_for_action(action),
        segment_type=evidence.get("segment_type"),
        cut_list_action=evidence.get("cut_list_action"),
        duration_status=evidence.get("duration_status"),
        transition_type=evidence.get("transition_type"),
        murch_score=evidence.get("murch_score", 0.0),
        continuity_blocked=bool(evidence.get("continuity_blocked", False)),
        is_protected=bool(evidence.get("is_protected", False)),
        is_censor_keep=bool(evidence.get("is_censor_keep", False)),
        is_technical_review=bool(evidence.get("is_technical_review", False)),
        is_review_required=True,
        is_keep_candidate=action
        in {
            FINAL_ACTION_KEEP_REVIEW,
            FINAL_ACTION_KEEP_HIGH_VALUE,
            FINAL_ACTION_PROTECT,
            FINAL_ACTION_CENSOR_KEEP,
        },
        is_trim_candidate=action == FINAL_ACTION_TRIM_REVIEW,
        is_remove_candidate=action == FINAL_ACTION_REMOVE_REVIEW,
        is_invalid_timing=bool(evidence.get("is_invalid_timing", False)),
        recommended_start_seconds=duration_item.get("recommended_start_seconds"),
        recommended_end_seconds=duration_item.get("recommended_end_seconds"),
        recommended_duration_seconds=duration_item.get(
            "recommended_duration_seconds"
        ),
        reason=_reason_for_action(action, evidence),
        decision_basis=decision_basis,
        source_signal_ids=list(evidence.get("source_signal_ids") or []),
        warnings=list(evidence.get("warnings") or []),
        errors=list(evidence.get("errors") or []),
        metadata={
            **dict(evidence.get("metadata") or {}),
            "duration_recommendation_id": duration_item.get("id"),
            "transition_decision_id": transition_item.get("id"),
            "source": "cut_list_finalizer",
        },
    )


def _recommendation_for_plan(plan: FinalCutListPlan) -> str:
    if plan.status in {
        FINAL_CUT_LIST_STATUS_SKIPPED_NO_INPUTS,
        FINAL_CUT_LIST_STATUS_SKIPPED_NO_CUT_LIST_ITEMS,
    }:
        return "final_cut_list_skipped_no_inputs"

    if plan.blocking_issue_count:
        return "final_cut_list_blocked_by_continuity"

    if plan.final_technical_review_count or plan.final_unknown_review_count:
        return "final_cut_list_requires_manual_review"

    return "final_cut_list_ready_for_review"


def finalize_cut_list(
    cut_list_items: list[Any] | None = None,
    clip_duration_recommendations: list[Any] | None = None,
    transition_decisions: list[Any] | None = None,
    continuity_issues: list[Any] | None = None,
    murch_scores: list[Any] | None = None,
    segment_classifications: list[Any] | None = None,
    unified_signals: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> FinalCutListPlan:
    run_metadata = {
        **dict(metadata or {}),
        "source": "cut_list_finalizer",
        "review_only": True,
    }

    cut_list_items = cut_list_items or []
    clip_duration_recommendations = clip_duration_recommendations or []
    transition_decisions = transition_decisions or []
    continuity_issues = continuity_issues or []
    murch_scores = murch_scores or []
    segment_classifications = segment_classifications or []
    unified_signals = unified_signals or []

    if not any(
        [
            cut_list_items,
            clip_duration_recommendations,
            transition_decisions,
            continuity_issues,
            murch_scores,
            segment_classifications,
            unified_signals,
        ]
    ):
        return FinalCutListPlan(
            status=FINAL_CUT_LIST_STATUS_SKIPPED_NO_INPUTS,
            final_items=[],
            recommendation="final_cut_list_skipped_no_inputs",
            metadata=run_metadata,
        )

    if not cut_list_items:
        return FinalCutListPlan(
            status=FINAL_CUT_LIST_STATUS_SKIPPED_NO_CUT_LIST_ITEMS,
            final_items=[],
            recommendation="final_cut_list_skipped_no_inputs",
            metadata=run_metadata,
        )

    try:
        normalized_cut_items = [
            normalize_cut_list_item(item) for item in cut_list_items
        ]
        normalized_duration_items = [
            normalize_clip_duration_recommendation(item)
            for item in clip_duration_recommendations
        ]
        normalized_transition_items = [
            normalize_transition_decision(item) for item in transition_decisions
        ]
        normalized_issues = [
            normalize_continuity_issue(item) for item in continuity_issues
        ]
        normalized_murch_items = [
            normalize_murch_score(item) for item in murch_scores
        ]
        normalized_segment_items = [
            normalize_segment_classification(item)
            for item in segment_classifications
        ]
        normalized_signals = [normalize_signal(item) for item in unified_signals]

        final_items: list[FinalCutListItem] = []
        for index, cut_item in enumerate(normalized_cut_items, start=1):
            related_duration = _related_items(cut_item, normalized_duration_items)
            related_transition = _related_items(cut_item, normalized_transition_items)
            related_issues = _related_items(cut_item, normalized_issues)
            related_murch = _related_items(cut_item, normalized_murch_items)
            related_segments = _related_items(cut_item, normalized_segment_items)
            related_signals = _related_items(cut_item, normalized_signals)

            final_item = build_final_cut_list_item(
                cut_list_item=cut_item,
                duration_recommendation=related_duration[0]
                if related_duration
                else None,
                transition_decision=related_transition[0]
                if related_transition
                else None,
                continuity_issues=related_issues,
                murch_score=related_murch[0] if related_murch else None,
                segment_classification=related_segments[0]
                if related_segments
                else None,
                related_signals=related_signals,
                metadata={
                    **run_metadata,
                    "source_index": index,
                },
            )
            final_items.append(final_item)

        plan = FinalCutListPlan(
            status=FINAL_CUT_LIST_STATUS_OK,
            final_items=final_items,
            warnings=[],
            errors=[],
            metadata={
                **run_metadata,
                "cut_list_item_count": len(cut_list_items),
                "clip_duration_recommendation_count": len(
                    clip_duration_recommendations
                ),
                "transition_decision_count": len(transition_decisions),
                "continuity_issue_count": len(continuity_issues),
                "murch_score_count": len(murch_scores),
                "segment_classification_count": len(segment_classifications),
                "unified_signal_count": len(unified_signals),
            },
        )
        plan.refresh_counts()
        plan.status = (
            FINAL_CUT_LIST_STATUS_COMPLETED_WITH_WARNINGS
            if plan.blocking_issue_count
            or plan.final_technical_review_count
            or plan.final_unknown_review_count
            else FINAL_CUT_LIST_STATUS_OK
        )
        plan.recommendation = _recommendation_for_plan(plan)
        return plan
    except Exception as exc:
        return FinalCutListPlan(
            status=FINAL_CUT_LIST_STATUS_FAILED,
            final_items=[],
            recommendation="cut_list_finalization_failed",
            warnings=[],
            errors=[str(exc)],
            metadata=run_metadata,
        )
