from __future__ import annotations

from typing import Any

from models.transition_decision import (
    TRANSITION_DECISION_STATUS_COMPLETED_WITH_WARNINGS,
    TRANSITION_DECISION_STATUS_OK,
    TRANSITION_DECISION_STATUS_SKIPPED_NO_CLIP_DURATION_RECOMMENDATIONS,
    TRANSITION_PRIORITY_HIGH,
    TRANSITION_PRIORITY_LOW,
    TRANSITION_PRIORITY_MEDIUM,
    TRANSITION_TYPE_CENSOR_SAFE_KEEP,
    TRANSITION_TYPE_HARD_CUT_REVIEW,
    TRANSITION_TYPE_J_CUT_REVIEW,
    TRANSITION_TYPE_L_CUT_REVIEW,
    TRANSITION_TYPE_NO_CUT_PROTECT,
    TRANSITION_TYPE_QUICK_FADE_REVIEW,
    TRANSITION_TYPE_TECHNICAL_TRANSITION_REVIEW,
    TRANSITION_TYPE_UNKNOWN_REVIEW,
    TransitionDecision,
    TransitionDecisionPlan,
)


SCENE_HARD_TYPES = {
    "scene_hard_cut_point",
}

SCENE_SOFT_TYPES = {
    "scene_soft_transition",
}

PROTECTED_TYPES = {
    "sentence_boundary_protection",
    "sentence_question_context_protection",
    "sentence_protection_zone",
    "segment_protected_context",
    "cut_list_protect_segment",
    "clip_duration_protected",
}

DIALOGUE_TYPES = {
    "interaction_dialogue_segment",
    "interaction_question_answer_segment",
    "interaction_context_needed_segment",
}

BEAT_TYPES = {
    "beat_sync_point",
    "beat_strong_sync_point",
    "beat_downbeat_candidate",
}

CENSOR_TYPES = {
    "profanity_censor_sfx_required",
    "cut_list_censor_keep",
    "clip_duration_censor_keep",
    "murch_censor_required_context",
}

TECHNICAL_TYPES = {
    "stutter_segment_candidate",
    "freeze_segment_candidate",
    "clip_duration_invalid_timing",
    "cut_list_technical_review",
    "murch_technical_warning",
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

    return [str(value)]


def normalize_clip_duration_recommendation(value: Any) -> dict[str, Any]:
    value = value or {}

    start_seconds = _float_or_none(
        _first_value(value, ["start_seconds", "start", "start_time"])
    )
    end_seconds = _float_or_none(_first_value(value, ["end_seconds", "end", "end_time"]))
    duration_seconds = _float_or_none(
        _first_value(value, ["duration_seconds", "duration"])
    )

    if duration_seconds is None and start_seconds is not None and end_seconds is not None:
        duration_seconds = end_seconds - start_seconds

    center_seconds = _float_or_none(_first_value(value, ["center_seconds", "center"]))
    if center_seconds is None and start_seconds is not None and end_seconds is not None:
        center_seconds = (start_seconds + end_seconds) / 2.0

    metadata = _get_value(value, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {"raw_metadata": metadata}

    return {
        "recommendation_id": _string_or_none(
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
        "duration_status": _string_or_none(_get_value(value, "duration_status")),
        "confidence": clamp_score(_get_value(value, "confidence", 0.0)),
        "priority": str(_get_value(value, "priority", TRANSITION_PRIORITY_LOW)),
        "is_protected": bool(_get_value(value, "is_protected", False)),
        "is_censor_keep": bool(_get_value(value, "is_censor_keep", False)),
        "is_invalid_timing": bool(_get_value(value, "is_invalid_timing", False)),
        "murch_score": float(_get_value(value, "murch_score", 0.0) or 0.0),
        "source_signal_ids": _list_of_strings(_get_value(value, "source_signal_ids", [])),
        "warnings": _list_of_strings(_get_value(value, "warnings", [])),
        "errors": _list_of_strings(_get_value(value, "errors", [])),
        "metadata": metadata,
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

    if duration_seconds is None and start_seconds is not None and end_seconds is not None:
        duration_seconds = end_seconds - start_seconds

    center_seconds = _float_or_none(_first_value(value, ["center_seconds", "center"]))
    if center_seconds is None and start_seconds is not None and end_seconds is not None:
        center_seconds = (start_seconds + end_seconds) / 2.0

    metadata = _get_value(value, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {"raw_metadata": metadata}

    return {
        "item_id": _string_or_none(_first_value(value, ["item_id", "id"])),
        "segment_id": _string_or_none(_get_value(value, "segment_id")),
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "proposed_action": str(_get_value(value, "proposed_action", "UNKNOWN_REVIEW")),
        "action_confidence": clamp_score(_get_value(value, "action_confidence", 0.0)),
        "priority": str(_get_value(value, "priority", TRANSITION_PRIORITY_LOW)),
        "segment_type": str(_get_value(value, "segment_type", "unknown")),
        "murch_score": float(_get_value(value, "murch_score", 0.0) or 0.0),
        "censor_required": bool(_get_value(value, "censor_required", False)),
        "is_protected": bool(_get_value(value, "is_protected", False)),
        "is_technical_review": bool(_get_value(value, "is_technical_review", False)),
        "source_signal_ids": _list_of_strings(_get_value(value, "source_signal_ids", [])),
        "warnings": _list_of_strings(_get_value(value, "warnings", [])),
        "errors": _list_of_strings(_get_value(value, "errors", [])),
        "metadata": metadata,
    }


def _normalize_signal(value: Any) -> dict[str, Any]:
    value = value or {}

    metadata = _get_value(value, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {"raw_metadata": metadata}

    return {
        "signal_id": _string_or_none(
            _first_value(value, ["signal_id", "id", "source_signal_id"])
        ),
        "signal_type": str(_first_value(value, ["signal_type", "type"], "")),
        "source": _string_or_none(_get_value(value, "source")),
        "start_seconds": _float_or_none(
            _first_value(value, ["start_seconds", "start", "start_time"])
        ),
        "end_seconds": _float_or_none(
            _first_value(value, ["end_seconds", "end", "end_time"])
        ),
        "center_seconds": _float_or_none(_first_value(value, ["center_seconds", "center"])),
        "confidence": clamp_score(_get_value(value, "confidence", 0.0)),
        "priority": str(_get_value(value, "priority", TRANSITION_PRIORITY_LOW)),
        "metadata": metadata,
    }


def find_related_signals(
    start_seconds: float | None,
    end_seconds: float | None,
    unified_signals: list[Any] | None = None,
    tolerance_seconds: float = 0.35,
) -> list[dict[str, Any]]:
    signals = [_normalize_signal(item) for item in (unified_signals or [])]
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


def collect_transition_evidence(
    recommendation: Any = None,
    cut_list_item: Any = None,
    related_signals: list[Any] | None = None,
) -> dict[str, Any]:
    rec = normalize_clip_duration_recommendation(recommendation)
    cut_item = normalize_cut_list_item(cut_list_item)

    signal_items = [_normalize_signal(item) for item in (related_signals or [])]
    signal_types = {str(item.get("signal_type") or "") for item in signal_items}

    proposed_action = rec.get("proposed_action") or cut_item.get("proposed_action")
    duration_status = rec.get("duration_status")
    cut_list_action = cut_item.get("proposed_action")

    source_signal_ids = []
    source_signal_ids.extend(rec.get("source_signal_ids", []))
    source_signal_ids.extend(cut_item.get("source_signal_ids", []))
    source_signal_ids.extend(
        [str(item["signal_id"]) for item in signal_items if item.get("signal_id")]
    )

    start_seconds = rec.get("start_seconds")
    if start_seconds is None:
        start_seconds = cut_item.get("start_seconds")

    end_seconds = rec.get("end_seconds")
    if end_seconds is None:
        end_seconds = cut_item.get("end_seconds")

    center_seconds = rec.get("center_seconds")
    if center_seconds is None:
        center_seconds = cut_item.get("center_seconds")

    duration_seconds = rec.get("duration_seconds")
    if duration_seconds is None:
        duration_seconds = cut_item.get("duration_seconds")

    is_protected = (
        bool(rec.get("is_protected"))
        or bool(cut_item.get("is_protected"))
        or str(cut_list_action).upper() == "PROTECT"
        or str(duration_status) == "protect_duration"
        or bool(signal_types & PROTECTED_TYPES)
    )
    is_censor_keep = (
        bool(rec.get("is_censor_keep"))
        or bool(cut_item.get("censor_required"))
        or str(cut_list_action).upper() == "CENSOR_KEEP"
        or str(duration_status) == "censor_keep_duration"
        or bool(signal_types & CENSOR_TYPES)
    )
    is_technical_review = (
        bool(rec.get("is_invalid_timing"))
        or bool(cut_item.get("is_technical_review"))
        or str(cut_list_action).upper() == "TECHNICAL_REVIEW"
        or str(duration_status) in {"technical_review", "invalid_timing_review"}
        or bool(signal_types & TECHNICAL_TYPES)
    )

    return {
        "source_item_id": rec.get("source_item_id") or cut_item.get("item_id"),
        "segment_id": rec.get("segment_id") or cut_item.get("segment_id"),
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "proposed_action": proposed_action,
        "cut_list_action": cut_list_action,
        "duration_status": duration_status,
        "murch_score": float(cut_item.get("murch_score") or rec.get("murch_score") or 0.0),
        "recommendation_confidence": clamp_score(rec.get("confidence")),
        "cut_list_confidence": clamp_score(cut_item.get("action_confidence")),
        "is_protected": is_protected,
        "is_censor_keep": is_censor_keep,
        "is_technical_review": is_technical_review,
        "is_scene_hard": bool(signal_types & SCENE_HARD_TYPES),
        "is_scene_soft": bool(signal_types & SCENE_SOFT_TYPES),
        "is_beat_aligned": bool(signal_types & BEAT_TYPES),
        "is_sentence_safe": bool(signal_types & PROTECTED_TYPES),
        "is_dialogue_context": bool(signal_types & DIALOGUE_TYPES),
        "signal_types": sorted(item for item in signal_types if item),
        "source_signal_ids": sorted(set(source_signal_ids)),
        "warnings": list(rec.get("warnings", [])) + list(cut_item.get("warnings", [])),
        "errors": list(rec.get("errors", [])) + list(cut_item.get("errors", [])),
        "metadata": {
            "recommendation": rec,
            "cut_list_item": cut_item,
            "related_signal_count": len(signal_items),
            "review_only": True,
        },
    }


def infer_transition_type(evidence: dict[str, Any]) -> str:
    if evidence.get("is_censor_keep"):
        return TRANSITION_TYPE_CENSOR_SAFE_KEEP

    if evidence.get("is_protected"):
        return TRANSITION_TYPE_NO_CUT_PROTECT

    if evidence.get("is_technical_review"):
        return TRANSITION_TYPE_TECHNICAL_TRANSITION_REVIEW

    if evidence.get("is_scene_hard"):
        return TRANSITION_TYPE_HARD_CUT_REVIEW

    if evidence.get("is_scene_soft"):
        return TRANSITION_TYPE_QUICK_FADE_REVIEW

    if evidence.get("is_dialogue_context"):
        if str(evidence.get("cut_list_action") or "").upper() == "REVIEW_KEEP":
            return TRANSITION_TYPE_L_CUT_REVIEW
        return TRANSITION_TYPE_J_CUT_REVIEW

    if evidence.get("is_beat_aligned"):
        if float(evidence.get("murch_score") or 0.0) >= 0.75:
            return TRANSITION_TYPE_HARD_CUT_REVIEW
        return TRANSITION_TYPE_QUICK_FADE_REVIEW

    duration_status = str(evidence.get("duration_status") or "")
    cut_list_action = str(evidence.get("cut_list_action") or "").upper()

    if duration_status in {"trim_review", "too_long_review", "extend_review"}:
        return TRANSITION_TYPE_QUICK_FADE_REVIEW

    if cut_list_action in {"KEEP", "REVIEW_KEEP", "REVIEW_TRIM", "REVIEW_REMOVE"}:
        return TRANSITION_TYPE_HARD_CUT_REVIEW

    return TRANSITION_TYPE_UNKNOWN_REVIEW


def _priority_for_transition_type(transition_type: str) -> str:
    if transition_type in {
        TRANSITION_TYPE_NO_CUT_PROTECT,
        TRANSITION_TYPE_CENSOR_SAFE_KEEP,
        TRANSITION_TYPE_TECHNICAL_TRANSITION_REVIEW,
    }:
        return TRANSITION_PRIORITY_HIGH

    if transition_type == TRANSITION_TYPE_UNKNOWN_REVIEW:
        return TRANSITION_PRIORITY_LOW

    return TRANSITION_PRIORITY_MEDIUM


def _reason_for_transition_type(transition_type: str) -> str:
    reasons = {
        TRANSITION_TYPE_HARD_CUT_REVIEW: "scene_or_candidate_supports_hard_cut_review",
        TRANSITION_TYPE_J_CUT_REVIEW: "dialogue_context_supports_j_cut_review",
        TRANSITION_TYPE_L_CUT_REVIEW: "dialogue_context_supports_l_cut_review",
        TRANSITION_TYPE_QUICK_FADE_REVIEW: "soft_or_duration_context_supports_quick_fade_review",
        TRANSITION_TYPE_NO_CUT_PROTECT: "protected_context_prevents_blind_transition_review",
        TRANSITION_TYPE_CENSOR_SAFE_KEEP: "censor_context_must_be_preserved_for_review",
        TRANSITION_TYPE_TECHNICAL_TRANSITION_REVIEW: "technical_risk_needs_transition_review",
        TRANSITION_TYPE_UNKNOWN_REVIEW: "transition_decision_needs_manual_review",
    }
    return reasons.get(transition_type, "transition_decision_needs_manual_review")


def _confidence_for_evidence(evidence: dict[str, Any], transition_type: str) -> float:
    base = max(
        clamp_score(evidence.get("recommendation_confidence")),
        clamp_score(evidence.get("cut_list_confidence")),
    )

    if base == 0.0:
        base = 0.55

    if transition_type in {
        TRANSITION_TYPE_NO_CUT_PROTECT,
        TRANSITION_TYPE_CENSOR_SAFE_KEEP,
        TRANSITION_TYPE_TECHNICAL_TRANSITION_REVIEW,
    }:
        base = max(base, 0.85)

    if evidence.get("is_scene_hard") or evidence.get("is_scene_soft"):
        base = max(base, 0.8)

    if evidence.get("is_beat_aligned") or evidence.get("is_dialogue_context"):
        base = max(base, 0.7)

    if transition_type == TRANSITION_TYPE_UNKNOWN_REVIEW:
        base = min(base, 0.45)

    return clamp_score(base)


def build_transition_decision(
    recommendation: Any = None,
    cut_list_item: Any = None,
    related_signals: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> TransitionDecision:
    evidence = collect_transition_evidence(
        recommendation=recommendation,
        cut_list_item=cut_list_item,
        related_signals=related_signals,
    )
    transition_type = infer_transition_type(evidence)
    metadata = metadata or {}

    source_item_id = evidence.get("source_item_id")
    decision_id = str(
        metadata.get("decision_id")
        or f"transition_decision_{source_item_id or metadata.get('index', 1)}"
    )

    return TransitionDecision(
        decision_id=decision_id,
        source_item_id=source_item_id,
        segment_id=evidence.get("segment_id"),
        start_seconds=evidence.get("start_seconds"),
        end_seconds=evidence.get("end_seconds"),
        center_seconds=evidence.get("center_seconds"),
        duration_seconds=evidence.get("duration_seconds"),
        transition_type=transition_type,
        transition_confidence=_confidence_for_evidence(evidence, transition_type),
        priority=_priority_for_transition_type(transition_type),
        proposed_action="review_transition",
        cut_list_action=evidence.get("cut_list_action"),
        duration_status=evidence.get("duration_status"),
        murch_score=float(evidence.get("murch_score") or 0.0),
        is_protected=bool(evidence.get("is_protected")),
        is_censor_keep=bool(evidence.get("is_censor_keep")),
        is_technical_review=bool(evidence.get("is_technical_review")),
        is_scene_change_aligned=bool(
            evidence.get("is_scene_hard") or evidence.get("is_scene_soft")
        ),
        is_beat_aligned=bool(evidence.get("is_beat_aligned")),
        is_sentence_safe=bool(evidence.get("is_sentence_safe")),
        is_dialogue_context=bool(evidence.get("is_dialogue_context")),
        reason=_reason_for_transition_type(transition_type),
        decision_basis=evidence,
        source_signal_ids=list(evidence.get("source_signal_ids", [])),
        warnings=list(evidence.get("warnings", [])),
        errors=list(evidence.get("errors", [])),
        metadata={
            **dict(metadata),
            "engine": "transition_decision_engine",
            "review_only": True,
        },
    )


def _match_cut_list_item(
    recommendation: dict[str, Any],
    cut_list_items: list[Any] | None,
) -> Any | None:
    if not cut_list_items:
        return None

    source_item_id = recommendation.get("source_item_id")
    segment_id = recommendation.get("segment_id")

    for item in cut_list_items:
        normalized = normalize_cut_list_item(item)
        if source_item_id and source_item_id == normalized.get("item_id"):
            return item

        if segment_id and segment_id == normalized.get("segment_id"):
            return item

    return None


def _count_transition_types(decisions: list[TransitionDecision]) -> dict[str, int]:
    return {
        "hard_cut_review_count": sum(
            item.transition_type == TRANSITION_TYPE_HARD_CUT_REVIEW for item in decisions
        ),
        "j_cut_review_count": sum(
            item.transition_type == TRANSITION_TYPE_J_CUT_REVIEW for item in decisions
        ),
        "l_cut_review_count": sum(
            item.transition_type == TRANSITION_TYPE_L_CUT_REVIEW for item in decisions
        ),
        "quick_fade_review_count": sum(
            item.transition_type == TRANSITION_TYPE_QUICK_FADE_REVIEW
            for item in decisions
        ),
        "no_cut_protect_count": sum(
            item.transition_type == TRANSITION_TYPE_NO_CUT_PROTECT for item in decisions
        ),
        "censor_safe_keep_count": sum(
            item.transition_type == TRANSITION_TYPE_CENSOR_SAFE_KEEP for item in decisions
        ),
        "technical_transition_review_count": sum(
            item.transition_type == TRANSITION_TYPE_TECHNICAL_TRANSITION_REVIEW
            for item in decisions
        ),
        "unknown_review_count": sum(
            item.transition_type == TRANSITION_TYPE_UNKNOWN_REVIEW for item in decisions
        ),
    }


def build_transition_decision_plan(
    clip_duration_recommendations: list[Any] | None = None,
    cut_list_items: list[Any] | None = None,
    unified_signals: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> TransitionDecisionPlan:
    metadata = metadata or {}
    clip_duration_recommendations = clip_duration_recommendations or []
    cut_list_items = cut_list_items or []

    if not clip_duration_recommendations and not cut_list_items:
        return TransitionDecisionPlan(
            status=TRANSITION_DECISION_STATUS_SKIPPED_NO_CLIP_DURATION_RECOMMENDATIONS,
            decisions=[],
            decision_count=0,
            recommendation="transition_decision_skipped_no_inputs",
            metadata={
                **metadata,
                "engine": "transition_decision_engine",
                "review_only": True,
            },
        )

    source_items = clip_duration_recommendations
    using_cut_list_fallback = False

    if not source_items:
        source_items = cut_list_items
        using_cut_list_fallback = True

    decisions: list[TransitionDecision] = []
    warnings: list[str] = []
    errors: list[str] = []

    for index, source_item in enumerate(source_items):
        try:
            if using_cut_list_fallback:
                normalized_cut_item = normalize_cut_list_item(source_item)
                start_seconds = normalized_cut_item.get("start_seconds")
                end_seconds = normalized_cut_item.get("end_seconds")
                related_signals = find_related_signals(
                    start_seconds,
                    end_seconds,
                    unified_signals=unified_signals,
                )
                decision = build_transition_decision(
                    recommendation=None,
                    cut_list_item=source_item,
                    related_signals=related_signals,
                    metadata={"index": index + 1, **metadata},
                )
            else:
                normalized_recommendation = normalize_clip_duration_recommendation(
                    source_item
                )
                start_seconds = normalized_recommendation.get("start_seconds")
                end_seconds = normalized_recommendation.get("end_seconds")
                related_signals = find_related_signals(
                    start_seconds,
                    end_seconds,
                    unified_signals=unified_signals,
                )
                decision = build_transition_decision(
                    recommendation=source_item,
                    cut_list_item=_match_cut_list_item(
                        normalized_recommendation,
                        cut_list_items,
                    ),
                    related_signals=related_signals,
                    metadata={"index": index + 1, **metadata},
                )

            if not decision.decision_id:
                decision.decision_id = f"transition_decision_{index + 1}"

            decisions.append(decision)
            warnings.extend(decision.warnings)
            errors.extend(decision.errors)
        except Exception as exc:
            fallback = TransitionDecision(
                decision_id=f"transition_decision_{index + 1}_technical_review",
                transition_type=TRANSITION_TYPE_TECHNICAL_TRANSITION_REVIEW,
                transition_confidence=0.85,
                priority=TRANSITION_PRIORITY_HIGH,
                proposed_action="review_transition",
                is_technical_review=True,
                reason="transition_decision_item_failed_safe_review",
                errors=[str(exc)],
                metadata={
                    **metadata,
                    "engine": "transition_decision_engine",
                    "review_only": True,
                    "index": index + 1,
                },
            )
            decisions.append(fallback)
            errors.append(str(exc))

    counts = _count_transition_types(decisions)
    status = TRANSITION_DECISION_STATUS_OK
    recommendation_text = "transition_decision_review_plan_ready"

    if warnings or errors:
        status = TRANSITION_DECISION_STATUS_COMPLETED_WITH_WARNINGS
        recommendation_text = "transition_decision_review_plan_ready_with_warnings"

    return TransitionDecisionPlan(
        status=status,
        decisions=decisions,
        decision_count=len(decisions),
        hard_cut_review_count=counts["hard_cut_review_count"],
        j_cut_review_count=counts["j_cut_review_count"],
        l_cut_review_count=counts["l_cut_review_count"],
        quick_fade_review_count=counts["quick_fade_review_count"],
        no_cut_protect_count=counts["no_cut_protect_count"],
        censor_safe_keep_count=counts["censor_safe_keep_count"],
        technical_transition_review_count=counts["technical_transition_review_count"],
        unknown_review_count=counts["unknown_review_count"],
        recommendation=recommendation_text,
        warnings=warnings,
        errors=errors,
        metadata={
            **metadata,
            "engine": "transition_decision_engine",
            "review_only": True,
            "used_cut_list_fallback": using_cut_list_fallback,
        },
    )
