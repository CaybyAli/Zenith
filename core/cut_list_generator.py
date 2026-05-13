from __future__ import annotations

from typing import Any

from models.cut_list import (
    CUT_LIST_ACTION_CENSOR_KEEP,
    CUT_LIST_ACTION_KEEP,
    CUT_LIST_ACTION_PROTECT,
    CUT_LIST_ACTION_REVIEW_KEEP,
    CUT_LIST_ACTION_REVIEW_REMOVE,
    CUT_LIST_ACTION_REVIEW_TRIM,
    CUT_LIST_ACTION_TECHNICAL_REVIEW,
    CUT_LIST_ACTION_UNKNOWN_REVIEW,
    CUT_LIST_PRIORITY_HIGH,
    CUT_LIST_PRIORITY_LOW,
    CUT_LIST_PRIORITY_MEDIUM,
    CUT_LIST_STATUS_COMPLETED_WITH_WARNINGS,
    CUT_LIST_STATUS_OK,
    CUT_LIST_STATUS_SKIPPED_NO_SEGMENTS,
    CutListItem,
    CutListPlan,
)


def _read_value(source: Any, names: list[str], default: Any = None) -> Any:
    if source is None:
        return default

    if isinstance(source, dict):
        for name in names:
            if name in source:
                return source.get(name)
        return default

    for name in names:
        if hasattr(source, name):
            return getattr(source, name)

    return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "ja"}

    return bool(value)


def _as_float_or_none(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp_score(value: Any) -> float:
    number = _as_float_or_none(value)

    if number is None:
        return 0.0

    if number < 0.0:
        return 0.0

    if number > 1.0:
        return 1.0

    return number


def _normal_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def normalize_segment(segment: Any) -> dict[str, Any]:
    segment_id = _read_value(segment, ["segment_id", "id", "source_segment_id"])
    start_seconds = _as_float_or_none(_read_value(segment, ["start_seconds", "start", "start_time"]))
    end_seconds = _as_float_or_none(_read_value(segment, ["end_seconds", "end", "end_time"]))
    duration_seconds = _as_float_or_none(_read_value(segment, ["duration_seconds", "duration"]))

    if duration_seconds is None and start_seconds is not None and end_seconds is not None:
        duration_seconds = max(0.0, end_seconds - start_seconds)

    center_seconds = _as_float_or_none(_read_value(segment, ["center_seconds", "center", "midpoint_seconds"]))

    if center_seconds is None and start_seconds is not None and end_seconds is not None:
        center_seconds = (start_seconds + end_seconds) / 2.0

    segment_type = _normal_text(
        _read_value(segment, ["segment_type", "type", "label", "classification", "category"], "unknown")
    )

    text_blob = " ".join(
        [
            segment_type,
            _normal_text(_read_value(segment, ["reason", "description", "decision_reason"])),
        ]
    )

    censor_required = _as_bool(
        _read_value(segment, ["censor_required", "needs_censor", "profanity_required"], False)
    ) or _contains_any(text_blob, ["censor", "profanity"])

    is_protected = _as_bool(
        _read_value(segment, ["is_protected", "protected", "protect"], False)
    ) or _contains_any(text_blob, ["protected_context", "context_protection"])

    technical_warning = _as_bool(
        _read_value(segment, ["technical_warning", "is_technical_warning"], False)
    ) or _contains_any(text_blob, ["technical", "stutter", "freezing", "freeze"])

    hook_candidate = _as_bool(
        _read_value(segment, ["hook_candidate", "is_hook_candidate"], False)
    ) or _contains_any(text_blob, ["hook"])

    return {
        "segment_id": str(segment_id) if segment_id is not None else None,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "segment_type": segment_type or "unknown",
        "content_value_score": clamp_score(
            _read_value(segment, ["content_value_score", "content_score", "value_score"], 0.0)
        ),
        "risk_score": clamp_score(_read_value(segment, ["risk_score"], 0.0)),
        "protection_score": clamp_score(_read_value(segment, ["protection_score"], 1.0 if is_protected else 0.0)),
        "censor_required": censor_required,
        "is_protected": is_protected,
        "technical_warning": technical_warning,
        "hook_candidate": hook_candidate,
        "source_signal_ids": list(_read_value(segment, ["source_signal_ids", "signal_ids"], []) or []),
        "metadata": dict(_read_value(segment, ["metadata"], {}) or {}),
    }


def normalize_murch_score(score: Any) -> dict[str, Any]:
    tier = _normal_text(_read_value(score, ["tier", "murch_tier", "quality_tier"], ""))
    recommendation = _normal_text(_read_value(score, ["recommendation", "action", "decision"], ""))

    return {
        "segment_id": _read_value(score, ["segment_id", "source_segment_id", "id"]),
        "murch_score": clamp_score(_read_value(score, ["murch_score", "final_score", "score", "value"], 0.0)),
        "tier": tier,
        "recommendation": recommendation,
        "is_protected": _as_bool(_read_value(score, ["is_protected", "protected"], False))
        or tier == "protected",
        "censor_required": _as_bool(_read_value(score, ["censor_required", "needs_censor"], False)),
    }


def _signal_id(signal: Any) -> str | None:
    value = _read_value(signal, ["signal_id", "id"])
    return str(value) if value is not None else None


def _signal_text(signal: Any) -> str:
    parts = [
        _read_value(signal, ["signal_type", "type"], ""),
        _read_value(signal, ["source", "source_name"], ""),
        _read_value(signal, ["action_hint", "hint"], ""),
        _read_value(signal, ["reason", "description"], ""),
    ]
    return " ".join(_normal_text(part) for part in parts)


def _related_signals_for_segment(segment: dict[str, Any], unified_signals: list[Any]) -> list[Any]:
    segment_id = segment.get("segment_id")
    if not segment_id:
        return []

    related = []

    for signal in unified_signals:
        signal_segment_id = _read_value(signal, ["segment_id", "source_segment_id", "related_segment_id"])
        if signal_segment_id is not None and str(signal_segment_id) == str(segment_id):
            related.append(signal)

    return related


def infer_cut_list_action(
    segment: Any,
    murch_score: Any = None,
    related_signals: list[Any] | None = None,
) -> str:
    normalized_segment = normalize_segment(segment)
    normalized_murch = normalize_murch_score(murch_score)
    related_signals = related_signals or []

    segment_type = normalized_segment["segment_type"]
    signal_text = " ".join(_signal_text(signal) for signal in related_signals)
    murch_tier = normalized_murch["tier"]
    murch_value = normalized_murch["murch_score"]
    content_value = normalized_segment["content_value_score"]

    protected_by_signal = _contains_any(signal_text, ["sentence_boundary", "protect", "protected"])
    censor_by_signal = _contains_any(signal_text, ["profanity", "censor"])
    technical_by_signal = _contains_any(signal_text, ["technical", "stutter", "freezing", "freeze"])

    if normalized_segment["is_protected"] or normalized_murch["is_protected"] or protected_by_signal:
        return CUT_LIST_ACTION_PROTECT

    if normalized_segment["censor_required"] or normalized_murch["censor_required"] or censor_by_signal:
        return CUT_LIST_ACTION_CENSOR_KEEP

    if normalized_segment["technical_warning"] or technical_by_signal:
        return CUT_LIST_ACTION_TECHNICAL_REVIEW

    if _contains_any(segment_type, ["dead_candidate", "dead_content", "dead"]):
        if murch_value <= 0.25 and content_value <= 0.25:
            return CUT_LIST_ACTION_REVIEW_REMOVE
        return CUT_LIST_ACTION_REVIEW_TRIM

    if _contains_any(segment_type, ["filler", "idle", "low_value"]):
        return CUT_LIST_ACTION_REVIEW_TRIM

    if _contains_any(segment_type, ["transition"]):
        if murch_value >= 0.65 or content_value >= 0.65:
            return CUT_LIST_ACTION_REVIEW_KEEP
        return CUT_LIST_ACTION_REVIEW_TRIM

    high_value_by_type = _contains_any(segment_type, ["highlight", "high_value", "strong_moment"])
    hook_candidate = normalized_segment["hook_candidate"] or _contains_any(signal_text, ["hook"])

    if murch_value >= 0.82 and high_value_by_type:
        return CUT_LIST_ACTION_KEEP

    if murch_value >= 0.70 or high_value_by_type or hook_candidate or murch_tier == "high":
        return CUT_LIST_ACTION_REVIEW_KEEP

    if content_value >= 0.65:
        return CUT_LIST_ACTION_REVIEW_KEEP

    return CUT_LIST_ACTION_UNKNOWN_REVIEW


def classify_cut_priority(item_or_evidence: Any) -> str:
    action = _read_value(item_or_evidence, ["proposed_action", "action"], None)

    if isinstance(item_or_evidence, dict):
        action = item_or_evidence.get("proposed_action") or item_or_evidence.get("action") or action

    if action in {
        CUT_LIST_ACTION_KEEP,
        CUT_LIST_ACTION_PROTECT,
        CUT_LIST_ACTION_CENSOR_KEEP,
        CUT_LIST_ACTION_TECHNICAL_REVIEW,
    }:
        return CUT_LIST_PRIORITY_HIGH

    if action in {
        CUT_LIST_ACTION_REVIEW_KEEP,
        CUT_LIST_ACTION_REVIEW_TRIM,
        CUT_LIST_ACTION_REVIEW_REMOVE,
    }:
        return CUT_LIST_PRIORITY_MEDIUM

    return CUT_LIST_PRIORITY_LOW


def _confidence_for_action(
    action: str,
    segment: dict[str, Any],
    murch_score: dict[str, Any],
    related_signals: list[Any],
) -> float:
    base = 0.60

    if action in {
        CUT_LIST_ACTION_PROTECT,
        CUT_LIST_ACTION_CENSOR_KEEP,
        CUT_LIST_ACTION_TECHNICAL_REVIEW,
    }:
        base = 0.90
    elif action == CUT_LIST_ACTION_KEEP:
        base = 0.86
    elif action in {CUT_LIST_ACTION_REVIEW_TRIM, CUT_LIST_ACTION_REVIEW_REMOVE}:
        base = 0.78
    elif action == CUT_LIST_ACTION_REVIEW_KEEP:
        base = 0.74

    if related_signals:
        base += 0.04

    if murch_score["murch_score"] >= 0.85:
        base += 0.04

    if segment["content_value_score"] >= 0.75:
        base += 0.03

    return clamp_score(base)


def _reason_for_action(action: str) -> str:
    reasons = {
        CUT_LIST_ACTION_KEEP: "Strong keep candidate based on segment value and Murch score.",
        CUT_LIST_ACTION_REVIEW_KEEP: "Review keep candidate based on positive evidence.",
        CUT_LIST_ACTION_REVIEW_TRIM: "Review trim candidate based on low or transitional value.",
        CUT_LIST_ACTION_REVIEW_REMOVE: "Review remove candidate based on weak evidence.",
        CUT_LIST_ACTION_PROTECT: "Protected context must be preserved.",
        CUT_LIST_ACTION_CENSOR_KEEP: "Censor-related segment must be preserved for later safety handling.",
        CUT_LIST_ACTION_TECHNICAL_REVIEW: "Technical issue needs human review.",
        CUT_LIST_ACTION_UNKNOWN_REVIEW: "Unknown evidence needs human review.",
    }
    return reasons.get(action, reasons[CUT_LIST_ACTION_UNKNOWN_REVIEW])


def build_cut_list_item(
    segment: Any = None,
    murch_score: Any = None,
    related_signals: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> CutListItem:
    normalized_segment = normalize_segment(segment)
    normalized_murch = normalize_murch_score(murch_score)
    related_signals = related_signals or []

    action = infer_cut_list_action(normalized_segment, normalized_murch, related_signals)
    priority = classify_cut_priority({"proposed_action": action})
    confidence = _confidence_for_action(action, normalized_segment, normalized_murch, related_signals)

    segment_id = normalized_segment["segment_id"]
    item_id = f"cutlist_{segment_id}" if segment_id else "cutlist_unknown"

    source_signal_ids = list(normalized_segment.get("source_signal_ids") or [])
    for signal in related_signals:
        signal_id = _signal_id(signal)
        if signal_id and signal_id not in source_signal_ids:
            source_signal_ids.append(signal_id)

    return CutListItem(
        item_id=item_id,
        segment_id=segment_id,
        start_seconds=normalized_segment["start_seconds"],
        end_seconds=normalized_segment["end_seconds"],
        center_seconds=normalized_segment["center_seconds"],
        duration_seconds=normalized_segment["duration_seconds"],
        proposed_action=action,
        action_confidence=confidence,
        priority=priority,
        segment_type=normalized_segment["segment_type"],
        murch_score=normalized_murch["murch_score"],
        content_value_score=normalized_segment["content_value_score"],
        risk_score=normalized_segment["risk_score"],
        protection_score=normalized_segment["protection_score"],
        censor_required=normalized_segment["censor_required"] or normalized_murch["censor_required"],
        is_protected=normalized_segment["is_protected"] or normalized_murch["is_protected"],
        is_review_required=action != CUT_LIST_ACTION_KEEP,
        is_keep_candidate=action in {
            CUT_LIST_ACTION_KEEP,
            CUT_LIST_ACTION_REVIEW_KEEP,
            CUT_LIST_ACTION_PROTECT,
            CUT_LIST_ACTION_CENSOR_KEEP,
        },
        is_trim_candidate=action == CUT_LIST_ACTION_REVIEW_TRIM,
        is_remove_candidate=action == CUT_LIST_ACTION_REVIEW_REMOVE,
        is_technical_review=action == CUT_LIST_ACTION_TECHNICAL_REVIEW,
        reason=_reason_for_action(action),
        decision_basis={
            "segment_type": normalized_segment["segment_type"],
            "murch_score": normalized_murch["murch_score"],
            "murch_tier": normalized_murch["tier"],
            "content_value_score": normalized_segment["content_value_score"],
            "related_signal_count": len(related_signals),
        },
        source_segment_id=segment_id,
        source_signal_ids=source_signal_ids,
        metadata=dict(metadata or {}),
    )


def _murch_scores_by_segment_id(murch_scores: list[Any]) -> dict[str, Any]:
    mapped = {}

    for score in murch_scores:
        normalized = normalize_murch_score(score)
        segment_id = normalized.get("segment_id")
        if segment_id is not None:
            mapped[str(segment_id)] = score

    return mapped


def generate_cut_list_plan(
    segment_classifications: list[Any] | None = None,
    murch_scores: list[Any] | None = None,
    unified_signals: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> CutListPlan:
    segment_classifications = list(segment_classifications or [])
    murch_scores = list(murch_scores or [])
    unified_signals = list(unified_signals or [])

    if not segment_classifications:
        return CutListPlan(
            status=CUT_LIST_STATUS_SKIPPED_NO_SEGMENTS,
            items=[],
            recommendation="cut_list_skipped_no_segments",
            metadata=dict(metadata or {}),
        )

    warnings = []
    status = CUT_LIST_STATUS_OK

    if not murch_scores:
        status = CUT_LIST_STATUS_COMPLETED_WITH_WARNINGS
        warnings.append("missing_murch_scores_using_safe_fallback")

    murch_by_segment_id = _murch_scores_by_segment_id(murch_scores)
    items = []

    for index, segment in enumerate(segment_classifications):
        normalized_segment = normalize_segment(segment)
        segment_id = normalized_segment.get("segment_id")

        murch_score = None
        if segment_id is not None:
            murch_score = murch_by_segment_id.get(str(segment_id))

        if murch_score is None and index < len(murch_scores):
            murch_score = murch_scores[index]

        related_signals = _related_signals_for_segment(normalized_segment, unified_signals)

        item = build_cut_list_item(
            segment=normalized_segment,
            murch_score=murch_score,
            related_signals=related_signals,
            metadata=metadata,
        )
        items.append(item)

    plan = CutListPlan(
        status=status,
        items=items,
        recommendation="cut_list_candidates_generated",
        warnings=warnings,
        metadata=dict(metadata or {}),
    )
    plan.refresh_counts()
    return plan
