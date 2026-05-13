from __future__ import annotations

from typing import Any

from models.clip_duration import (
    ClipDurationOptimizationPlan,
    ClipDurationRecommendation,
)


DEFAULT_DURATION_RULES: dict[str, dict[str, float | None]] = {
    "KEEP": {"min": 4.0, "max": 90.0, "target": 18.0},
    "REVIEW_KEEP": {"min": 3.0, "max": 75.0, "target": 15.0},
    "REVIEW_TRIM": {"min": 2.0, "max": 25.0, "target": 8.0},
    "REVIEW_REMOVE": {"min": 0.0, "max": 20.0, "target": 6.0},
    "PROTECT": {"min": 2.0, "max": 120.0, "target": None},
    "CENSOR_KEEP": {"min": 1.0, "max": 45.0, "target": None},
    "TECHNICAL_REVIEW": {"min": 0.5, "max": 30.0, "target": None},
    "UNKNOWN_REVIEW": {"min": 1.0, "max": 30.0, "target": 10.0},
}

SEGMENT_TYPE_RULE_OVERRIDES: dict[str, dict[str, float | None]] = {
    "hook_candidate": {"min": 3.0, "max": 20.0},
    "highlight": {"min": 4.0, "max": 60.0},
    "filler": {"min": 0.5, "max": 12.0},
    "transition": {"min": 0.5, "max": 8.0},
    "protected_context": {"max": 180.0, "target": None},
    "censor_required_segment": {"target": None},
}


def clamp_seconds(value: float | int | None, min_value: float = 0.0) -> float | None:
    if value is None:
        return None

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None

    return max(float(min_value), numeric_value)


def _get_item_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)

    return getattr(item, key, default)


def _first_present_value(item: Any, keys: list[str], default: Any = None) -> Any:
    for key in keys:
        value = _get_item_value(item, key, None)
        if value is not None:
            return value

    return default


def _normalize_action(action: Any) -> str:
    if action is None:
        return "UNKNOWN_REVIEW"

    normalized = str(action).strip().upper()
    if not normalized:
        return "UNKNOWN_REVIEW"

    if normalized in DEFAULT_DURATION_RULES:
        return normalized

    return "UNKNOWN_REVIEW"


def normalize_cut_list_item(item: Any) -> dict[str, Any]:
    if item is None:
        return {
            "source_item_id": None,
            "segment_id": None,
            "start_seconds": None,
            "end_seconds": None,
            "duration_seconds": None,
            "center_seconds": None,
            "proposed_action": "UNKNOWN_REVIEW",
            "segment_type": None,
            "confidence": 0.0,
            "reason": "missing_cut_list_item",
            "source_signal_ids": [],
            "metadata": {},
        }

    start_seconds = clamp_seconds(
        _first_present_value(item, ["start_seconds", "start", "start_time"])
    )
    end_seconds = clamp_seconds(
        _first_present_value(item, ["end_seconds", "end", "end_time"])
    )
    duration_seconds = _first_present_value(item, ["duration_seconds", "duration"], None)

    if duration_seconds is not None:
        duration_seconds = clamp_seconds(duration_seconds)

    if duration_seconds is None and start_seconds is not None and end_seconds is not None:
        duration_seconds = end_seconds - start_seconds

    center_seconds = _first_present_value(item, ["center_seconds", "center"], None)
    if center_seconds is None and start_seconds is not None and end_seconds is not None:
        center_seconds = (start_seconds + end_seconds) / 2.0
    else:
        center_seconds = clamp_seconds(center_seconds)

    metadata = _get_item_value(item, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {"raw_metadata": metadata}

    source_signal_ids = _get_item_value(item, "source_signal_ids", []) or []
    if not isinstance(source_signal_ids, list):
        source_signal_ids = [str(source_signal_ids)]

    return {
        "source_item_id": _first_present_value(
            item,
            ["cut_list_item_id", "item_id", "recommendation_id", "id"],
        ),
        "segment_id": _get_item_value(item, "segment_id", None),
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": duration_seconds,
        "center_seconds": center_seconds,
        "proposed_action": _normalize_action(
            _first_present_value(item, ["proposed_action", "action", "decision"])
        ),
        "segment_type": _first_present_value(
            item,
            ["segment_type", "classification", "label"],
        ),
        "confidence": float(_get_item_value(item, "confidence", 0.75) or 0.0),
        "reason": str(_get_item_value(item, "reason", "") or ""),
        "source_signal_ids": source_signal_ids,
        "metadata": metadata,
    }


def get_duration_rules_for_action(
    action: str | None,
    segment_type: str | None = None,
    profile: dict[str, Any] | None = None,
) -> dict[str, float | None]:
    normalized_action = _normalize_action(action)
    rules = dict(DEFAULT_DURATION_RULES[normalized_action])

    if segment_type:
        segment_key = str(segment_type).strip().lower()
        overrides = SEGMENT_TYPE_RULE_OVERRIDES.get(segment_key, {})
        rules.update(overrides)

    profile = profile or {}
    profile_rules = profile.get("duration_rules", {})
    if isinstance(profile_rules, dict):
        action_rules = profile_rules.get(normalized_action, {})
        if isinstance(action_rules, dict):
            rules.update(action_rules)

    return rules


def infer_duration_status(
    item: dict[str, Any],
    duration_seconds: float | None,
    rules: dict[str, float | None],
) -> str:
    action = _normalize_action(item.get("proposed_action"))
    segment_type = str(item.get("segment_type") or "").lower()
    start_seconds = item.get("start_seconds")
    end_seconds = item.get("end_seconds")

    if start_seconds is None or end_seconds is None:
        return "invalid_timing_review"

    if end_seconds < start_seconds:
        return "invalid_timing_review"

    if duration_seconds is None or duration_seconds < 0:
        return "invalid_timing_review"

    if action == "PROTECT" or segment_type == "protected_context":
        return "protect_duration"

    if action == "CENSOR_KEEP" or segment_type == "censor_required_segment":
        return "censor_keep_duration"

    if action == "TECHNICAL_REVIEW":
        return "technical_review"

    minimum_duration = float(rules.get("min") or 0.0)
    maximum_duration = float(rules.get("max") or 0.0)

    if duration_seconds < minimum_duration:
        return "extend_review"

    if duration_seconds > maximum_duration:
        if action == "REVIEW_TRIM":
            return "trim_review"
        return "too_long_review"

    return "duration_ok"


def _build_suggestion(
    normalized_item: dict[str, Any],
    duration_status: str,
    rules: dict[str, float | None],
) -> dict[str, float | None]:
    start_seconds = normalized_item.get("start_seconds")
    end_seconds = normalized_item.get("end_seconds")
    duration_seconds = normalized_item.get("duration_seconds")
    target_duration = rules.get("target")

    suggestion = {
        "suggested_start_seconds": None,
        "suggested_end_seconds": None,
        "suggested_duration_seconds": None,
        "adjustment_seconds": 0.0,
    }

    if start_seconds is None or end_seconds is None or duration_seconds is None:
        return suggestion

    if duration_status in {
        "protect_duration",
        "censor_keep_duration",
        "technical_review",
        "invalid_timing_review",
        "duration_ok",
    }:
        return suggestion

    if target_duration is None:
        return suggestion

    target_duration = float(target_duration)
    center_seconds = normalized_item.get("center_seconds")
    if center_seconds is None:
        center_seconds = (start_seconds + end_seconds) / 2.0

    suggested_start = clamp_seconds(center_seconds - (target_duration / 2.0), 0.0)
    suggested_end = clamp_seconds((suggested_start or 0.0) + target_duration, 0.0)

    suggestion["suggested_start_seconds"] = suggested_start
    suggestion["suggested_end_seconds"] = suggested_end
    suggestion["suggested_duration_seconds"] = target_duration
    suggestion["adjustment_seconds"] = target_duration - duration_seconds

    return suggestion


def _priority_for_status(duration_status: str) -> str:
    if duration_status in {
        "protect_duration",
        "censor_keep_duration",
        "technical_review",
        "invalid_timing_review",
    }:
        return "high"

    if duration_status in {
        "too_short_review",
        "too_long_review",
        "trim_review",
        "extend_review",
    }:
        return "medium"

    return "low"


def _reason_for_status(duration_status: str) -> str:
    reasons = {
        "duration_ok": "clip_duration_inside_safe_review_range",
        "too_short_review": "clip_duration_shorter_than_recommended_minimum",
        "too_long_review": "clip_duration_longer_than_recommended_maximum",
        "trim_review": "clip_duration_trim_candidate_for_manual_review",
        "extend_review": "clip_duration_extend_candidate_for_manual_review",
        "protect_duration": "clip_duration_protected_context_preserved",
        "censor_keep_duration": "clip_duration_censor_required_segment_preserved",
        "technical_review": "clip_duration_needs_technical_review",
        "invalid_timing_review": "clip_duration_invalid_timing_needs_review",
        "unknown_review": "clip_duration_unknown_decision_needs_review",
    }
    return reasons.get(duration_status, "clip_duration_unknown_decision_needs_review")


def _recommendation_id(index: int, source_item_id: Any) -> str:
    source_part = str(source_item_id or f"item_{index + 1}")
    safe_source_part = source_part.replace(" ", "_")
    return f"clip_duration_{index + 1}_{safe_source_part}"


def optimize_cut_list_item_duration(
    item: Any,
    profile: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ClipDurationRecommendation:
    normalized_item = normalize_cut_list_item(item)
    rules = get_duration_rules_for_action(
        normalized_item.get("proposed_action"),
        normalized_item.get("segment_type"),
        profile=profile,
    )

    duration_seconds = normalized_item.get("duration_seconds")
    duration_status = infer_duration_status(normalized_item, duration_seconds, rules)
    suggestion = _build_suggestion(normalized_item, duration_status, rules)

    warnings: list[str] = []
    errors: list[str] = []

    if duration_status == "invalid_timing_review":
        errors.append("invalid_clip_timing")

    if duration_seconds is None:
        warnings.append("duration_fallback_unavailable")

    if normalized_item.get("proposed_action") == "REVIEW_REMOVE":
        warnings.append("review_remove_kept_as_review_only")

    if duration_status == "censor_keep_duration":
        warnings.append("censor_required_segment_must_be_preserved_for_review")

    if duration_status == "protect_duration":
        warnings.append("protected_context_must_be_preserved_for_review")

    decision_basis = {
        "action": normalized_item.get("proposed_action"),
        "segment_type": normalized_item.get("segment_type"),
        "rules": dict(rules),
        "review_only": True,
    }

    return ClipDurationRecommendation(
        recommendation_id=str((metadata or {}).get("recommendation_id", "")),
        source_item_id=normalized_item.get("source_item_id"),
        segment_id=normalized_item.get("segment_id"),
        start_seconds=normalized_item.get("start_seconds"),
        end_seconds=normalized_item.get("end_seconds"),
        center_seconds=normalized_item.get("center_seconds"),
        duration_seconds=duration_seconds,
        proposed_action=normalized_item.get("proposed_action") or "UNKNOWN_REVIEW",
        duration_status=duration_status,
        recommended_min_duration_seconds=float(rules.get("min") or 0.0),
        recommended_max_duration_seconds=float(rules.get("max") or 0.0),
        recommended_target_duration_seconds=rules.get("target"),
        suggested_start_seconds=suggestion["suggested_start_seconds"],
        suggested_end_seconds=suggestion["suggested_end_seconds"],
        suggested_duration_seconds=suggestion["suggested_duration_seconds"],
        adjustment_seconds=float(suggestion["adjustment_seconds"] or 0.0),
        confidence=min(max(float(normalized_item.get("confidence") or 0.0), 0.0), 1.0),
        priority=_priority_for_status(duration_status),
        is_too_short=duration_status in {"too_short_review", "extend_review"},
        is_too_long=duration_status in {"too_long_review", "trim_review"},
        is_duration_ok=duration_status == "duration_ok",
        is_protected=duration_status == "protect_duration",
        is_censor_keep=duration_status == "censor_keep_duration",
        is_review_required=duration_status != "duration_ok" or normalized_item.get("proposed_action") == "REVIEW_REMOVE",
        is_invalid_timing=duration_status == "invalid_timing_review",
        reason=_reason_for_status(duration_status),
        decision_basis=decision_basis,
        source_signal_ids=list(normalized_item.get("source_signal_ids", [])),
        warnings=warnings,
        errors=errors,
        metadata={
            **dict(normalized_item.get("metadata", {}) or {}),
            **dict(metadata or {}),
            "optimizer": "clip_duration_optimizer",
            "review_only": True,
        },
    )


def _count_statuses(
    recommendations: list[ClipDurationRecommendation],
) -> dict[str, int]:
    return {
        "duration_ok_count": sum(item.duration_status == "duration_ok" for item in recommendations),
        "too_short_count": sum(item.duration_status == "too_short_review" for item in recommendations),
        "too_long_count": sum(item.duration_status == "too_long_review" for item in recommendations),
        "trim_review_count": sum(item.duration_status == "trim_review" for item in recommendations),
        "extend_review_count": sum(item.duration_status == "extend_review" for item in recommendations),
        "protect_duration_count": sum(item.duration_status == "protect_duration" for item in recommendations),
        "censor_keep_count": sum(item.duration_status == "censor_keep_duration" for item in recommendations),
        "technical_review_count": sum(item.duration_status == "technical_review" for item in recommendations),
        "invalid_timing_count": sum(item.duration_status == "invalid_timing_review" for item in recommendations),
    }


def optimize_clip_durations(
    cut_list_items: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ClipDurationOptimizationPlan:
    cut_list_items = cut_list_items or []
    metadata = metadata or {}

    if not cut_list_items:
        return ClipDurationOptimizationPlan(
            status="skipped_no_cut_list_items",
            recommendations=[],
            recommendation_count=0,
            recommendation="clip_duration_skipped_no_cut_list_items",
            metadata={
                **metadata,
                "optimizer": "clip_duration_optimizer",
                "review_only": True,
            },
        )

    recommendations: list[ClipDurationRecommendation] = []
    warnings: list[str] = []
    errors: list[str] = []

    profile = metadata.get("profile")
    if not isinstance(profile, dict):
        profile = None

    for index, item in enumerate(cut_list_items):
        try:
            recommendation = optimize_cut_list_item_duration(
                item,
                profile=profile,
                metadata={"index": index, **metadata},
            )
            recommendation.recommendation_id = _recommendation_id(
                index,
                recommendation.source_item_id,
            )
            recommendations.append(recommendation)
            warnings.extend(recommendation.warnings)
            errors.extend(recommendation.errors)
        except Exception as exc:
            recommendation = ClipDurationRecommendation(
                recommendation_id=f"clip_duration_{index + 1}_technical_review",
                proposed_action="TECHNICAL_REVIEW",
                duration_status="technical_review",
                priority="high",
                is_review_required=True,
                reason="clip_duration_item_failed_safe_review",
                warnings=[],
                errors=[str(exc)],
                metadata={
                    **metadata,
                    "optimizer": "clip_duration_optimizer",
                    "review_only": True,
                    "index": index,
                },
            )
            recommendations.append(recommendation)
            errors.append(str(exc))

    counts = _count_statuses(recommendations)
    status = "ok"
    recommendation_text = "clip_duration_review_plan_ready"

    if errors:
        status = "completed_with_warnings"
        recommendation_text = "clip_duration_review_plan_ready_with_warnings"
    elif warnings:
        status = "completed_with_warnings"
        recommendation_text = "clip_duration_review_plan_ready_with_warnings"

    return ClipDurationOptimizationPlan(
        status=status,
        recommendations=recommendations,
        recommendation_count=len(recommendations),
        duration_ok_count=counts["duration_ok_count"],
        too_short_count=counts["too_short_count"],
        too_long_count=counts["too_long_count"],
        trim_review_count=counts["trim_review_count"],
        extend_review_count=counts["extend_review_count"],
        protect_duration_count=counts["protect_duration_count"],
        censor_keep_count=counts["censor_keep_count"],
        technical_review_count=counts["technical_review_count"],
        invalid_timing_count=counts["invalid_timing_count"],
        recommendation=recommendation_text,
        warnings=warnings,
        errors=errors,
        metadata={
            **metadata,
            "optimizer": "clip_duration_optimizer",
            "review_only": True,
        },
    )
