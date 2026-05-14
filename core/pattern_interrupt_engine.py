from __future__ import annotations

from typing import Any

from models.pattern_interrupt import (
    PATTERN_INTERRUPT_RECOMMENDATION_BLOCKED,
    PATTERN_INTERRUPT_RECOMMENDATION_FAILED,
    PATTERN_INTERRUPT_RECOMMENDATION_NO_ITEMS,
    PATTERN_INTERRUPT_RECOMMENDATION_READY,
    PATTERN_INTERRUPT_RECOMMENDATION_REVIEW,
    PATTERN_INTERRUPT_STATUS_BLOCKED,
    PATTERN_INTERRUPT_STATUS_FAILED,
    PATTERN_INTERRUPT_STATUS_NO_TIMELINE_ITEMS,
    PATTERN_INTERRUPT_STATUS_READY,
    PATTERN_INTERRUPT_STATUS_READY_WITH_WARNINGS,
    PatternInterruptReport,
    PatternInterruptSuggestion,
    PatternInterruptWindow,
)


SOURCE_SCORE_KEYS = (
    "energy_score",
    "actual_energy_score",
    "content_value_score",
    "hook_score",
    "energy_peak_score",
    "peak_score",
    "visual_energy_score",
    "audio_energy_score",
    "reaction_score",
    "face_reaction_score",
    "motion_score",
    "motion_energy_score",
    "keyword_score",
    "emotion_score",
    "murch_score",
    "final_score",
    "signal_score",
)

VISUAL_SCORE_KEYS = (
    "visual_energy_score",
    "motion_score",
    "motion_energy_score",
    "visual_score",
    "scene_change_score",
    "screen_change_score",
    "signal_score",
)

REACTION_SCORE_KEYS = (
    "reaction_score",
    "face_reaction_score",
    "face_score",
    "hook_score",
    "keyword_score",
    "emotion_score",
    "signal_score",
)

ACTION_FALLBACK_SCORES = {
    "keep_review": 0.55,
    "trim_review": 0.45,
    "remove_review": 0.30,
    "censor_keep": 0.65,
    "blocked_by_continuity": 0.40,
    "technical_review": 0.35,
    "unknown_review": 0.30,
    "protect": 0.55,
}

SEVERITY_FALLBACK_SCORES = {
    "low": 0.40,
    "medium": 0.50,
    "high": 0.65,
    "blocking": 0.35,
}

DEFAULT_ITEM_DURATION_SECONDS = 15.0
WINDOW_MIN_SECONDS = 45.0
WINDOW_TARGET_SECONDS = 60.0
WINDOW_MAX_SECONDS = 90.0
MONOTONY_THRESHOLD = 0.62
LOW_VARIATION_THRESHOLD = 0.25


def clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.0
    return max(0.0, min(1.0, score))


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            converted = to_dict()
            if isinstance(converted, dict):
                return dict(converted)
        except Exception:
            return {}

    return {}


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    parsed = _safe_optional_float(value)
    return default if parsed is None else parsed


def _job_value(job: Any, key: str, default: Any = None) -> Any:
    if job is None:
        return default
    if isinstance(job, dict):
        return job.get(key, default)
    return getattr(job, key, default)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _items_from_container(container: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if not container:
        return []

    if isinstance(container, list):
        return [dict(item) for item in container if isinstance(item, dict)]
    if isinstance(container, tuple):
        return [dict(item) for item in container if isinstance(item, dict)]

    data = _safe_dict(container)
    if not data:
        return []

    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, dict)]

    for nested_key in (
        "dashboard_package",
        "review_timeline_plan",
        "content_value_result",
        "keyword_emotion_result",
        "murch_scoring_result",
        "energy_peak_detection_result",
        "visual_energy_result",
        "face_reaction_result",
        "motion_analysis_result",
        "dynamic_pacing_report",
        "emotional_arc_report",
        "result",
    ):
        nested = data.get(nested_key)
        if nested is None:
            continue
        nested_items = _items_from_container(nested, keys)
        if nested_items:
            return nested_items

    return []


def _collect_items(sources: list[Any], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for source in sources:
        items.extend(_items_from_container(source, keys))
    return items


def _extract_timeline_items(job: Any) -> tuple[list[dict[str, Any]], str]:
    sources: list[tuple[str, Any, tuple[str, ...]]] = [
        (
            "review_timeline_dashboard_package_report",
            _job_value(job, "review_timeline_dashboard_package_report"),
            ("item_cards", "timeline_items"),
        ),
        (
            "review_timeline_dashboard_package",
            _job_value(job, "review_timeline_dashboard_package"),
            ("item_cards", "timeline_items"),
        ),
        (
            "review_timeline_dashboard_item_cards",
            _job_value(job, "review_timeline_dashboard_item_cards"),
            ("item_cards", "items"),
        ),
        (
            "review_timeline_plan_items",
            _job_value(job, "review_timeline_plan_items"),
            ("items", "review_timeline_plan_items"),
        ),
        (
            "review_timeline_plan",
            _job_value(job, "review_timeline_plan"),
            ("items", "review_timeline_plan_items"),
        ),
        (
            "review_timeline_plan_report",
            _job_value(job, "review_timeline_plan_report"),
            ("items", "review_timeline_plan_items"),
        ),
    ]

    for label, source, keys in sources:
        items = _items_from_container(source, keys)
        if items:
            return items, label

    return [], "none"


def _extract_related_sources(job: Any) -> dict[str, list[dict[str, Any]]]:
    hook_report = _safe_dict(_job_value(job, "hook_identification_report"))
    hook_candidates = _collect_items(
        [
            _job_value(job, "hook_candidates"),
            hook_report,
            _job_value(job, "hook_identification"),
        ],
        ("candidates", "hook_candidates", "items"),
    )
    selected_hook = _safe_dict(_job_value(job, "hook_selected_candidate"))
    report_selected = _safe_dict(hook_report.get("selected_candidate"))
    if selected_hook:
        hook_candidates.append(selected_hook)
    if report_selected:
        hook_candidates.append(report_selected)

    emotional_report = _safe_dict(_job_value(job, "emotional_arc_report"))
    dynamic_report = _safe_dict(_job_value(job, "dynamic_pacing_report"))

    return {
        "dynamic_pacing": _collect_items(
            [
                _job_value(job, "dynamic_pacing_segments"),
                dynamic_report,
                _job_value(job, "dynamic_pacing"),
            ],
            ("pacing_segments", "segments", "items"),
        ),
        "dynamic_suggestions": _collect_items(
            [
                _job_value(job, "dynamic_pacing_suggestions"),
                dynamic_report,
                _job_value(job, "dynamic_pacing"),
            ],
            ("suggestions", "items"),
        ),
        "emotional_arc": _collect_items(
            [
                _job_value(job, "emotional_arc_points"),
                emotional_report,
                _job_value(job, "emotional_arc"),
            ],
            ("arc_points", "emotional_arc_points", "points", "items"),
        ),
        "emotional_suggestions": _collect_items(
            [
                _job_value(job, "emotional_arc_suggestions"),
                emotional_report,
                _job_value(job, "emotional_arc"),
            ],
            ("suggestions", "items"),
        ),
        "hook": hook_candidates,
        "energy": _collect_items(
            [
                _job_value(job, "energy_peaks"),
                _job_value(job, "energy_peak_report"),
                _job_value(job, "energy_peak_detection_result"),
            ],
            ("peaks", "energy_peaks", "items", "signals"),
        ),
        "content_value": _collect_items(
            [
                _job_value(job, "content_value_scores"),
                _job_value(job, "content_value_segment_scores"),
                _job_value(job, "content_value_report"),
            ],
            ("segment_scores", "content_value_segment_scores", "items"),
        ),
        "keyword": _collect_items(
            [
                _job_value(job, "keyword_emotion_scores"),
                _job_value(job, "keyword_emotion_segment_scores"),
                _job_value(job, "keyword_emotion_matches"),
                _job_value(job, "keyword_emotion_report"),
            ],
            ("segment_scores", "matches", "keyword_emotion_segment_scores"),
        ),
        "visual": _collect_items(
            [
                _job_value(job, "visual_energy"),
                _job_value(job, "visual_energy_segments"),
                _job_value(job, "visual_energy_report"),
            ],
            ("segments", "visual_energy_segments", "items"),
        ),
        "face": _collect_items(
            [
                _job_value(job, "face_reaction_analysis"),
                _job_value(job, "face_reaction_segments"),
                _job_value(job, "face_reaction_report"),
            ],
            ("segments", "face_reaction_segments", "items"),
        ),
        "motion": _collect_items(
            [
                _job_value(job, "motion_analysis"),
                _job_value(job, "motion_analysis_segments"),
                _job_value(job, "motion_analysis_report"),
            ],
            ("segments", "motion_analysis_segments", "items"),
        ),
        "profanity": _collect_items(
            [
                _job_value(job, "profanity_censor_matches"),
                _job_value(job, "profanity_censor_segment_results"),
                _job_value(job, "profanity_censor_report"),
            ],
            ("matches", "segment_results", "items"),
        ),
        "unified": _collect_items(
            [
                _job_value(job, "unified_edit_signals"),
                _job_value(job, "unified_edit_signal_report"),
            ],
            ("signals", "unified_edit_signals", "edit_signals", "items"),
        ),
    }


def _source_metadata(item: dict[str, Any]) -> dict[str, Any]:
    metadata = _safe_dict(item.get("metadata"))
    return {
        **_safe_dict(metadata.get("source_metadata")),
        **_safe_dict(metadata.get("decision_basis")),
        **_safe_dict(metadata.get("evidence")),
        **metadata,
    }


def _flatten_item_data(item: dict[str, Any]) -> dict[str, Any]:
    metadata = _source_metadata(item)
    return {
        **metadata,
        **item,
    }


def _duration_from(
    start_seconds: float | None,
    end_seconds: float | None,
    duration_seconds: float | None,
) -> float:
    if duration_seconds is not None and duration_seconds >= 0.0:
        return duration_seconds
    if start_seconds is not None and end_seconds is not None and end_seconds >= start_seconds:
        return end_seconds - start_seconds
    return 0.0


def _normalize_timeline_item(
    item: dict[str, Any],
    index: int,
    source_label: str,
) -> dict[str, Any]:
    flat = _flatten_item_data(item)
    source_item_id = str(
        flat.get("item_id")
        or flat.get("timeline_item_id")
        or flat.get("source_item_id")
        or flat.get("id")
        or f"pattern_interrupt_source_item_{index}"
    )
    source_segment_id = flat.get("source_segment_id") or flat.get("segment_id")

    start_seconds = _safe_optional_float(
        flat.get("source_start_seconds", flat.get("start_seconds")),
    )
    end_seconds = _safe_optional_float(
        flat.get("source_end_seconds", flat.get("end_seconds")),
    )
    duration_seconds = _duration_from(
        start_seconds,
        end_seconds,
        _safe_optional_float(flat.get("duration_seconds")),
    )

    if start_seconds is not None and end_seconds is None and duration_seconds > 0.0:
        end_seconds = start_seconds + duration_seconds
    if end_seconds is not None and start_seconds is None and duration_seconds > 0.0:
        start_seconds = max(0.0, end_seconds - duration_seconds)

    action = str(flat.get("action") or flat.get("final_action") or "").strip()
    protection_status = str(flat.get("protection_status") or "").strip()
    safety_flags = [str(value) for value in _safe_list(flat.get("safety_flags"))]
    blocking_reasons = [
        str(value)
        for value in (
            _safe_list(flat.get("blocking_errors"))
            + _safe_list(flat.get("blocking_reasons"))
        )
    ]
    warnings = [str(value) for value in _safe_list(flat.get("warnings"))]

    protected = bool(flat.get("protected", False)) or protection_status in {
        "protected",
        "censor_protected",
        "continuity_blocked",
    } or action in {"protect", "censor_keep", "blocked_by_continuity"}
    censor_required = (
        bool(flat.get("censor_sfx_required", False))
        or bool(flat.get("censor_required", False))
        or bool(flat.get("sfx_required", False))
        or protection_status == "censor_protected"
        or action == "censor_keep"
    )
    continuity_blocked = bool(flat.get("continuity_blocked", False)) or (
        protection_status == "continuity_blocked"
    ) or action == "blocked_by_continuity"

    if protected and "protected_interrupt_preserved" not in safety_flags:
        safety_flags.append("protected_interrupt_preserved")
    if censor_required and "censor_interrupt_review_required" not in safety_flags:
        safety_flags.append("censor_interrupt_review_required")
    if continuity_blocked:
        blocking_reasons.append("continuity_interrupt_blocked")
        if "continuity_interrupt_blocked" not in safety_flags:
            safety_flags.append("continuity_interrupt_blocked")

    return {
        "source_item_id": source_item_id,
        "source_segment_id": (
            str(source_segment_id) if source_segment_id is not None else None
        ),
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": duration_seconds,
        "flat": flat,
        "source_label": source_label,
        "action": action,
        "protection_status": protection_status,
        "protected": protected,
        "censor_required": censor_required,
        "continuity_blocked": continuity_blocked,
        "safety_flags": safety_flags,
        "warnings": warnings,
        "blocking_reasons": blocking_reasons,
    }


def _assign_fallback_timing(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cursor = 0.0
    for item in items:
        start = _safe_optional_float(item.get("start_seconds"))
        end = _safe_optional_float(item.get("end_seconds"))
        duration = max(_safe_float(item.get("duration_seconds"), 0.0), 0.0)

        if start is None or end is None or end < start:
            if duration <= 0.0:
                duration = DEFAULT_ITEM_DURATION_SECONDS
            start = cursor
            end = start + duration
            item["warnings"] = _unique(
                list(item.get("warnings") or [])
                + ["using_pattern_interrupt_order_fallback_timing"]
            )
        elif duration <= 0.0:
            duration = max(0.0, end - start)

        item["start_seconds"] = round(float(start), 3)
        item["end_seconds"] = round(float(end), 3)
        item["duration_seconds"] = round(float(duration), 3)
        cursor = max(cursor, float(end))

    return items


def _same_identifier(item: dict[str, Any], value: str | None) -> bool:
    if value is None:
        return False
    value_text = str(value)
    for key in (
        "segment_id",
        "source_segment_id",
        "source_item_id",
        "item_id",
        "timeline_item_id",
        "candidate_id",
        "point_id",
        "id",
    ):
        if str(item.get(key) or "") == value_text:
            return True
    metadata = _safe_dict(item.get("metadata"))
    return str(metadata.get("source_segment_id") or "") == value_text


def _time_overlaps(
    item: dict[str, Any],
    start_seconds: float | None,
    end_seconds: float | None,
) -> bool:
    if start_seconds is None or end_seconds is None:
        return False

    item_start = _safe_optional_float(item.get("start_seconds"))
    item_end = _safe_optional_float(item.get("end_seconds"))
    if item_start is None:
        item_start = _safe_optional_float(item.get("source_start_seconds"))
    if item_end is None:
        item_end = _safe_optional_float(item.get("source_end_seconds"))

    if item_start is None or item_end is None:
        center = _safe_optional_float(
            item.get("center_seconds", item.get("time_seconds")),
        )
        if center is None:
            return False
        half_width = max(0.1, _safe_float(item.get("duration_seconds"), 0.2) / 2.0)
        item_start = center - half_width
        item_end = center + half_width

    return item_start < end_seconds and item_end > start_seconds


def _items_near_timeline_item(
    items: list[dict[str, Any]],
    item_data: dict[str, Any],
) -> list[dict[str, Any]]:
    source_item_id = item_data["source_item_id"]
    source_segment_id = item_data["source_segment_id"]
    start_seconds = item_data["start_seconds"]
    end_seconds = item_data["end_seconds"]

    return [
        item
        for item in items
        if _same_identifier(item, source_segment_id)
        or _same_identifier(item, source_item_id)
        or _time_overlaps(item, start_seconds, end_seconds)
    ]


def _score_values_from_item(
    item: dict[str, Any],
    keys: tuple[str, ...] = SOURCE_SCORE_KEYS,
) -> list[float]:
    flat = _flatten_item_data(item)
    scores = [
        clamp_score(flat.get(key))
        for key in keys
        if flat.get(key) is not None
    ]
    categories = _safe_dict(flat.get("categories"))
    for category in ("hype", "shock", "laugh", "frustration", "question"):
        if categories.get(category) is not None:
            scores.append(clamp_score(categories.get(category)))
    return [score for score in scores if score > 0.0]


def _weighted_average(scores: list[float]) -> float:
    if not scores:
        return 0.0
    return clamp_score(sum(scores) / len(scores))


def _fallback_score(flat: dict[str, Any]) -> tuple[float, str]:
    action = str(flat.get("action") or flat.get("final_action") or "").strip()
    if action in ACTION_FALLBACK_SCORES:
        return ACTION_FALLBACK_SCORES[action], f"action_{action}"

    severity = str(flat.get("severity") or "").strip()
    if severity in SEVERITY_FALLBACK_SCORES:
        return SEVERITY_FALLBACK_SCORES[severity], f"severity_{severity}"

    badge = str(flat.get("badge") or "").lower()
    if "high" in badge or "highlight" in badge:
        return 0.65, "badge_highlight"
    if "technical" in badge:
        return 0.35, "badge_technical"
    if "remove" in badge:
        return 0.30, "badge_remove"

    return ACTION_FALLBACK_SCORES["unknown_review"], "unknown_review"


def _variation_score(values: list[float], scale: float) -> float:
    clean_values = [float(value) for value in values]
    if len(clean_values) < 2:
        return 0.0
    return round(clamp_score((max(clean_values) - min(clean_values)) / scale), 6)


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _cut_rate_for_item(
    item_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
) -> float:
    dynamic_matches = _items_near_timeline_item(
        related_sources.get("dynamic_pacing", []),
        item_data,
    )
    dynamic_rates = [
        _safe_float(match.get("actual_cut_rate"), 0.0)
        for match in dynamic_matches
        if _safe_float(match.get("actual_cut_rate"), 0.0) > 0.0
    ]
    if dynamic_rates:
        return round(sum(dynamic_rates) / len(dynamic_rates), 6)

    flat = item_data["flat"]
    direct_rate = _safe_float(flat.get("actual_cut_rate"), 0.0)
    if direct_rate > 0.0:
        return round(direct_rate, 6)

    duration = _safe_float(item_data.get("duration_seconds"), 0.0)
    if duration <= 0.0:
        return 0.0
    return round(60.0 / duration, 6)


def _energy_score_for_item(
    item_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
) -> tuple[float, list[str], dict[str, Any]]:
    flat = item_data["flat"]
    scores = _score_values_from_item(flat)
    evidence: dict[str, Any] = {
        "direct_score_count": len(scores),
        "matched_source_counts": {},
    }

    for source_name, source_items in related_sources.items():
        if source_name.endswith("_suggestions"):
            continue
        matches = _items_near_timeline_item(source_items, item_data)
        evidence["matched_source_counts"][source_name] = len(matches)
        for match in matches:
            scores.extend(_score_values_from_item(match))

    warnings: list[str] = []
    fallback_score, fallback_reason = _fallback_score(flat)
    if scores:
        score = _weighted_average(scores)
    else:
        score = fallback_score
        warnings.append("using_pattern_interrupt_fallback_score")

    if item_data["continuity_blocked"]:
        score = min(score, ACTION_FALLBACK_SCORES["blocked_by_continuity"])
        warnings.append("continuity_interrupt_blocked")
    elif item_data["censor_required"]:
        score = min(max(score, ACTION_FALLBACK_SCORES["censor_keep"]), 0.75)
        warnings.append("censor_interrupt_review_required")
    elif item_data["protected"]:
        warnings.append("protected_interrupt_preserved")

    evidence.update(
        {
            "raw_score_count": len(scores),
            "fallback_score": fallback_score,
            "fallback_reason": fallback_reason,
            "continuity_blocked": item_data["continuity_blocked"],
            "censor_required": item_data["censor_required"],
            "protected": item_data["protected"],
        }
    )
    return round(clamp_score(score), 6), _unique(warnings), evidence


def _signal_score_for_sources(
    item_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
    source_names: tuple[str, ...],
    keys: tuple[str, ...],
) -> tuple[float, bool]:
    scores = _score_values_from_item(item_data["flat"], keys)
    for source_name in source_names:
        for match in _items_near_timeline_item(
            related_sources.get(source_name, []),
            item_data,
        ):
            scores.extend(_score_values_from_item(match, keys))
    scores = [score for score in scores if score > 0.0]
    if not scores:
        return 0.0, False
    return round(sum(scores) / len(scores), 6), True


def _has_keyword_signal(
    item_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
) -> bool:
    flat = item_data["flat"]
    text_keys = (
        "keyword",
        "matched_keyword",
        "matched_text",
        "phrase",
        "question_text",
    )
    if any(str(flat.get(key) or "").strip() for key in text_keys):
        return True
    if bool(flat.get("hype_signal", False)) or bool(flat.get("question_signal", False)):
        return True

    categories = _safe_dict(flat.get("categories"))
    if any(clamp_score(categories.get(key)) > 0.0 for key in ("hype", "question")):
        return True

    for source_name in ("keyword", "unified"):
        matches = _items_near_timeline_item(
            related_sources.get(source_name, []),
            item_data,
        )
        for match in matches:
            match_flat = _flatten_item_data(match)
            signal_type = str(match_flat.get("signal_type") or "").lower()
            if "keyword" in signal_type or "hype" in signal_type or "question" in signal_type:
                return True
            if _score_values_from_item(match, ("keyword_score", "emotion_score")):
                return True

    return False


def _has_sfx_or_censor_signal(
    item_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
) -> tuple[bool, bool]:
    flat = item_data["flat"]
    censor_signal = bool(item_data.get("censor_required"))
    sfx_signal = bool(flat.get("sfx_required", False)) or bool(
        flat.get("censor_sfx_required", False)
    )

    for source_name in ("profanity", "unified"):
        matches = _items_near_timeline_item(
            related_sources.get(source_name, []),
            item_data,
        )
        for match in matches:
            match_flat = _flatten_item_data(match)
            signal_type = str(match_flat.get("signal_type") or "").lower()
            action = str(match_flat.get("action") or "").lower()
            if (
                "censor" in signal_type
                or "profanity" in signal_type
                or "censor" in action
            ):
                censor_signal = True
            if "sfx" in signal_type or bool(match_flat.get("sfx_required", False)):
                sfx_signal = True

    return censor_signal, sfx_signal


def _suggestion_types_near_item(
    suggestions: list[dict[str, Any]],
    item_data: dict[str, Any],
) -> set[str]:
    matches = _items_near_timeline_item(suggestions, item_data)
    return {
        str(match.get("suggestion_type") or match.get("signal_type") or "")
        for match in matches
        if str(match.get("suggestion_type") or match.get("signal_type") or "")
    }


def _item_metrics(
    item_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    energy_score, score_warnings, evidence = _energy_score_for_item(
        item_data,
        related_sources,
    )
    cut_rate = _cut_rate_for_item(item_data, related_sources)
    visual_score, has_visual = _signal_score_for_sources(
        item_data,
        related_sources,
        ("visual", "motion"),
        VISUAL_SCORE_KEYS,
    )
    reaction_score, has_reaction = _signal_score_for_sources(
        item_data,
        related_sources,
        ("face", "hook", "keyword"),
        REACTION_SCORE_KEYS,
    )
    has_keyword = _has_keyword_signal(item_data, related_sources)
    has_censor, has_sfx = _has_sfx_or_censor_signal(item_data, related_sources)

    dynamic_types = _suggestion_types_near_item(
        related_sources.get("dynamic_suggestions", []),
        item_data,
    )
    emotional_types = _suggestion_types_near_item(
        related_sources.get("emotional_suggestions", []),
        item_data,
    )

    return {
        "source_item_id": item_data["source_item_id"],
        "start_seconds": item_data["start_seconds"],
        "end_seconds": item_data["end_seconds"],
        "duration_seconds": item_data["duration_seconds"],
        "energy_score": energy_score,
        "cut_rate": cut_rate,
        "visual_score": visual_score,
        "has_visual": has_visual,
        "reaction_score": reaction_score,
        "has_reaction": has_reaction,
        "has_keyword": has_keyword,
        "has_censor": has_censor,
        "has_sfx": has_sfx,
        "protected": bool(item_data["protected"]),
        "continuity_blocked": bool(item_data["continuity_blocked"]),
        "dynamic_suggestion_types": sorted(dynamic_types),
        "emotional_suggestion_types": sorted(emotional_types),
        "warnings": _unique(list(item_data["warnings"]) + score_warnings),
        "blocking_reasons": list(item_data["blocking_reasons"]),
        "score_evidence": evidence,
    }


def _group_items_for_windows(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if not items:
        return []

    total_duration = sum(float(item["duration_seconds"] or 0.0) for item in items)
    if total_duration < WINDOW_MIN_SECONDS:
        return [items]

    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []

    for item in items:
        if current:
            projected = float(item["end_seconds"]) - float(current[0]["start_seconds"])
            current_duration = (
                float(current[-1]["end_seconds"]) - float(current[0]["start_seconds"])
            )
            if projected > WINDOW_MAX_SECONDS and current_duration >= WINDOW_MIN_SECONDS:
                groups.append(current)
                current = []

        current.append(item)
        current_duration = (
            float(current[-1]["end_seconds"]) - float(current[0]["start_seconds"])
        )
        if current_duration >= WINDOW_TARGET_SECONDS:
            groups.append(current)
            current = []

    if current:
        if groups:
            merged_duration = (
                float(current[-1]["end_seconds"])
                - float(groups[-1][0]["start_seconds"])
            )
            if merged_duration <= WINDOW_MAX_SECONDS:
                groups[-1].extend(current)
            else:
                groups.append(current)
        else:
            groups.append(current)

    return groups


def _recommended_type(
    duration_seconds: float,
    energy_variation_score: float,
    pacing_variation_score: float,
    visual_variation_score: float,
    reaction_presence_score: float,
    metadata: dict[str, Any],
) -> str:
    if metadata.get("continuity_blocked"):
        return "continuity_interrupt_blocked"
    if metadata.get("censor_signal"):
        return "censor_interrupt_review_required"
    if metadata.get("dynamic_missing_breathing_room"):
        return "breathing_break_candidate"
    if metadata.get("emotional_flat_energy_curve"):
        return "energy_shift_needed"
    if metadata.get("reaction_signal") and duration_seconds >= WINDOW_MIN_SECONDS:
        return "zoom_reaction_candidate"
    if metadata.get("keyword_signal") and duration_seconds >= WINDOW_MIN_SECONDS:
        return "text_overlay_candidate"
    if energy_variation_score < LOW_VARIATION_THRESHOLD:
        return "energy_shift_needed"
    if pacing_variation_score < LOW_VARIATION_THRESHOLD:
        return "pacing_shift_needed"
    if visual_variation_score < LOW_VARIATION_THRESHOLD:
        return "visual_change_candidate"
    if reaction_presence_score <= LOW_VARIATION_THRESHOLD:
        return "reaction_insert_candidate"
    return "pattern_interrupt_needed"


def _build_window(
    group: list[dict[str, Any]],
    index: int,
    related_sources: dict[str, list[dict[str, Any]]],
) -> PatternInterruptWindow:
    metrics = [_item_metrics(item, related_sources) for item in group]
    energy_scores = [float(item["energy_score"]) for item in metrics]
    cut_rates = [float(item["cut_rate"]) for item in metrics if float(item["cut_rate"]) > 0.0]
    visual_scores = [
        float(item["visual_score"]) for item in metrics if bool(item["has_visual"])
    ]
    reaction_scores = [
        float(item["reaction_score"]) if bool(item["has_reaction"]) else 0.0
        for item in metrics
    ]

    start = float(group[0]["start_seconds"])
    end = float(group[-1]["end_seconds"])
    duration = max(0.0, end - start)

    energy_variation = _variation_score(energy_scores, 0.35)
    pacing_variation = _variation_score(cut_rates, 12.0)
    if visual_scores:
        visual_variation = _variation_score(visual_scores, 0.35)
        visual_warning: list[str] = []
    else:
        visual_variation = 0.35
        visual_warning = ["missing_visual_variation_signals"]
    reaction_presence = clamp_score(_average(reaction_scores))

    dynamic_types = {
        suggestion_type
        for metric in metrics
        for suggestion_type in metric["dynamic_suggestion_types"]
    }
    emotional_types = {
        suggestion_type
        for metric in metrics
        for suggestion_type in metric["emotional_suggestion_types"]
    }

    window_metadata = {
        "item_metrics": metrics,
        "dynamic_suggestion_types": sorted(dynamic_types),
        "emotional_suggestion_types": sorted(emotional_types),
        "dynamic_monotone_risk": "monotone_pacing_risk" in dynamic_types,
        "dynamic_missing_breathing_room": "missing_breathing_room" in dynamic_types,
        "emotional_flat_energy_curve": "flat_energy_curve" in emotional_types,
        "reaction_signal": any(bool(item["has_reaction"]) for item in metrics),
        "keyword_signal": any(bool(item["has_keyword"]) for item in metrics),
        "censor_signal": any(bool(item["has_censor"]) for item in metrics),
        "sfx_signal": any(bool(item["has_sfx"]) for item in metrics),
        "protected": any(bool(item["protected"]) for item in metrics),
        "continuity_blocked": any(
            bool(item["continuity_blocked"]) for item in metrics
        ),
    }

    monotony_score = round(
        1.0
        - _average(
            [
                energy_variation,
                pacing_variation,
                visual_variation,
                reaction_presence,
            ]
        ),
        6,
    )
    monotony_score = clamp_score(monotony_score)

    interrupt_needed = (
        (duration >= WINDOW_MIN_SECONDS and monotony_score >= MONOTONY_THRESHOLD)
        or bool(window_metadata["dynamic_monotone_risk"])
        or bool(window_metadata["dynamic_missing_breathing_room"])
        or bool(window_metadata["emotional_flat_energy_curve"])
    )
    recommended_type = (
        _recommended_type(
            duration,
            energy_variation,
            pacing_variation,
            visual_variation,
            reaction_presence,
            window_metadata,
        )
        if interrupt_needed
        else None
    )

    warnings = _unique(
        [
            warning
            for metric in metrics
            for warning in list(metric["warnings"] or [])
        ]
        + visual_warning
    )

    window = PatternInterruptWindow(
        window_id=f"pattern_interrupt_window_{index}_{group[0]['source_item_id']}",
        start_seconds=round(start, 3),
        end_seconds=round(end, 3),
        duration_seconds=round(duration, 3),
        item_ids=[str(item["source_item_id"]) for item in group],
        average_energy_score=_average(energy_scores),
        average_cut_rate=_average(cut_rates),
        energy_variation_score=energy_variation,
        pacing_variation_score=pacing_variation,
        visual_variation_score=visual_variation,
        reaction_presence_score=reaction_presence,
        monotony_score=monotony_score,
        interrupt_needed=interrupt_needed,
        recommended_interrupt_type=recommended_type,
        review_required=True,
        warnings=warnings,
        metadata=window_metadata,
    )
    window.enforce_review_only()
    return window


def _suggestion(
    suggestion_type: str,
    reason: str,
    window: PatternInterruptWindow,
    severity: str = "medium",
    source_item_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> PatternInterruptSuggestion:
    suggestion = PatternInterruptSuggestion(
        suggestion_id=(
            f"pattern_interrupt_suggestion_{suggestion_type}_"
            f"{source_item_id or window.window_id}"
        ),
        suggestion_type=suggestion_type,
        source_window_id=window.window_id,
        source_item_id=source_item_id,
        start_seconds=window.start_seconds,
        end_seconds=window.end_seconds,
        severity=severity,
        reason=reason,
        review_required=True,
        can_auto_apply=False,
        can_insert_zoom=False,
        can_insert_text_overlay=False,
        can_insert_sfx=False,
        can_reorder_timeline=False,
        can_render=False,
        metadata={
            "window_duration_seconds": window.duration_seconds,
            "window_monotony_score": window.monotony_score,
            "average_energy_score": window.average_energy_score,
            "average_cut_rate": window.average_cut_rate,
            **dict(metadata or {}),
        },
    )
    suggestion.enforce_review_only()
    return suggestion


def _add_unique_suggestion(
    suggestions: list[PatternInterruptSuggestion],
    suggestion: PatternInterruptSuggestion,
) -> None:
    key = (
        suggestion.suggestion_type,
        suggestion.source_window_id,
        suggestion.source_item_id,
    )
    for existing in suggestions:
        existing_key = (
            existing.suggestion_type,
            existing.source_window_id,
            existing.source_item_id,
        )
        if existing_key == key:
            return
    suggestions.append(suggestion)


def _window_suggestions(
    window: PatternInterruptWindow,
) -> list[PatternInterruptSuggestion]:
    suggestions: list[PatternInterruptSuggestion] = []
    metadata = dict(window.metadata or {})
    first_item_id = window.item_ids[0] if window.item_ids else None

    if window.monotony_score >= MONOTONY_THRESHOLD:
        _add_unique_suggestion(
            suggestions,
            _suggestion(
                "monotony_risk",
                "Window has low energy, pacing, visual, or reaction variation.",
                window,
                severity="high" if window.monotony_score >= 0.75 else "medium",
                source_item_id=first_item_id,
            ),
        )

    if window.interrupt_needed:
        _add_unique_suggestion(
            suggestions,
            _suggestion(
                "pattern_interrupt_needed",
                "Review window should receive a pattern interrupt proposal.",
                window,
                severity="high" if window.monotony_score >= 0.75 else "medium",
                source_item_id=first_item_id,
            ),
        )
        if (
            window.recommended_interrupt_type
            and window.recommended_interrupt_type != "pattern_interrupt_needed"
        ):
            _add_unique_suggestion(
                suggestions,
                _suggestion(
                    window.recommended_interrupt_type,
                    "Recommended interrupt type for review.",
                    window,
                    severity=(
                        "blocking"
                        if window.recommended_interrupt_type
                        == "continuity_interrupt_blocked"
                        else "medium"
                    ),
                    source_item_id=first_item_id,
                ),
            )

    if metadata.get("dynamic_missing_breathing_room"):
        _add_unique_suggestion(
            suggestions,
            _suggestion(
                "breathing_break_candidate",
                "Dynamic pacing indicates missing breathing room.",
                window,
                source_item_id=first_item_id,
                metadata={"source": "dynamic_pacing"},
            ),
        )

    if metadata.get("emotional_flat_energy_curve"):
        _add_unique_suggestion(
            suggestions,
            _suggestion(
                "energy_shift_needed",
                "Emotional arc indicates a flat energy curve.",
                window,
                source_item_id=first_item_id,
                metadata={"source": "emotional_arc"},
            ),
        )

    if metadata.get("reaction_signal"):
        _add_unique_suggestion(
            suggestions,
            _suggestion(
                "zoom_reaction_candidate",
                "Reaction signal is available for manual review.",
                window,
                source_item_id=first_item_id,
            ),
        )

    if metadata.get("keyword_signal"):
        _add_unique_suggestion(
            suggestions,
            _suggestion(
                "text_overlay_candidate",
                "Keyword or hype signal is available for manual review.",
                window,
                source_item_id=first_item_id,
            ),
        )

    if metadata.get("sfx_signal"):
        _add_unique_suggestion(
            suggestions,
            _suggestion(
                "sfx_candidate",
                "Audio or censor signal is available for manual review.",
                window,
                severity="high" if metadata.get("censor_signal") else "medium",
                source_item_id=first_item_id,
            ),
        )

    if metadata.get("censor_signal"):
        _add_unique_suggestion(
            suggestions,
            _suggestion(
                "censor_interrupt_review_required",
                "Censor-protected item stays review-only.",
                window,
                severity="high",
                source_item_id=first_item_id,
            ),
        )

    if window.pacing_variation_score < LOW_VARIATION_THRESHOLD and window.duration_seconds >= WINDOW_MIN_SECONDS:
        _add_unique_suggestion(
            suggestions,
            _suggestion(
                "pacing_shift_needed",
                "Cut-rate variation is low in this review window.",
                window,
                source_item_id=first_item_id,
            ),
        )

    if window.visual_variation_score < LOW_VARIATION_THRESHOLD and window.duration_seconds >= WINDOW_MIN_SECONDS:
        _add_unique_suggestion(
            suggestions,
            _suggestion(
                "visual_change_candidate",
                "Visual variation is low in this review window.",
                window,
                source_item_id=first_item_id,
            ),
        )

    item_metrics = [
        item for item in metadata.get("item_metrics", []) if isinstance(item, dict)
    ]
    for item in item_metrics:
        source_item_id = str(item.get("source_item_id") or "")
        if bool(item.get("protected")):
            _add_unique_suggestion(
                suggestions,
                _suggestion(
                    "protected_interrupt_preserved",
                    "Protected item is preserved and only marked for review.",
                    window,
                    source_item_id=source_item_id,
                ),
            )
        if bool(item.get("continuity_blocked")):
            _add_unique_suggestion(
                suggestions,
                _suggestion(
                    "continuity_interrupt_blocked",
                    "Continuity-blocked item prevents interrupt approval.",
                    window,
                    severity="blocking",
                    source_item_id=source_item_id,
                ),
            )

    return suggestions


def _global_blocking_reasons(job: Any) -> list[str]:
    blocking_reasons: list[str] = []
    for key in (
        "review_timeline_dashboard_blocking_errors",
        "timeline_safety_blocking_errors",
        "timeline_approval_blocking_reasons",
        "dynamic_pacing_blocking_reasons",
        "pattern_interrupt_blocking_reasons",
    ):
        blocking_reasons.extend(str(value) for value in _safe_list(_job_value(job, key)))

    dashboard_package = _safe_dict(_job_value(job, "review_timeline_dashboard_package"))
    blocking_reasons.extend(
        str(value)
        for value in _safe_list(dashboard_package.get("blocking_errors"))
    )

    safety_status = str(_job_value(job, "timeline_safety_validation_status") or "")
    if safety_status in {"blocked", "failed"}:
        blocking_reasons.append(f"timeline_safety_{safety_status}")

    return _unique(blocking_reasons)


class PatternInterruptEngine:
    source = "pattern_interrupt_engine"

    def build(
        self,
        job: Any,
        metadata: dict[str, Any] | None = None,
    ) -> PatternInterruptReport:
        safe_metadata = dict(metadata or {})
        job_id = _job_value(job, "job_id") or _job_value(job, "id")

        try:
            raw_items, source_label = _extract_timeline_items(job)
            related_sources = _extract_related_sources(job)
            global_blockers = _global_blocking_reasons(job)

            if not raw_items:
                report = PatternInterruptReport(
                    job_id=str(job_id) if job_id is not None else None,
                    status=PATTERN_INTERRUPT_STATUS_NO_TIMELINE_ITEMS,
                    windows=[],
                    suggestions=[],
                    warnings=["no_review_timeline_items_available"],
                    blocking_reasons=[],
                    recommendation=PATTERN_INTERRUPT_RECOMMENDATION_NO_ITEMS,
                    metadata={
                        **safe_metadata,
                        "source": self.source,
                        "timeline_source": source_label,
                    },
                )
                report.enforce_review_only()
                report.refresh_metrics()
                return report

            normalized_items = [
                _normalize_timeline_item(raw_item, index, source_label)
                for index, raw_item in enumerate(raw_items)
            ]
            normalized_items = _assign_fallback_timing(normalized_items)
            window_groups = _group_items_for_windows(normalized_items)
            windows = [
                _build_window(group, index, related_sources)
                for index, group in enumerate(window_groups)
            ]

            suggestions: list[PatternInterruptSuggestion] = []
            for window in windows:
                for suggestion in _window_suggestions(window):
                    _add_unique_suggestion(suggestions, suggestion)

            warnings = _unique(
                [
                    warning
                    for window in windows
                    for warning in list(window.warnings or [])
                ]
            )
            item_blockers = _unique(
                [
                    reason
                    for item in normalized_items
                    for reason in list(item["blocking_reasons"])
                ]
            )
            blocking_reasons = _unique(global_blockers + item_blockers)

            report = PatternInterruptReport(
                job_id=str(job_id) if job_id is not None else None,
                status=PATTERN_INTERRUPT_STATUS_READY,
                windows=windows,
                suggestions=suggestions,
                warnings=warnings,
                blocking_reasons=blocking_reasons,
                recommendation=PATTERN_INTERRUPT_RECOMMENDATION_READY,
                metadata={
                    **safe_metadata,
                    "source": self.source,
                    "timeline_source": source_label,
                    "related_source_counts": {
                        key: len(value)
                        for key, value in related_sources.items()
                    },
                },
            )
            report.enforce_review_only()
            report.refresh_metrics()

            if blocking_reasons:
                report.status = PATTERN_INTERRUPT_STATUS_BLOCKED
                report.recommendation = PATTERN_INTERRUPT_RECOMMENDATION_BLOCKED
            elif report.warnings or report.suggestions:
                report.status = PATTERN_INTERRUPT_STATUS_READY_WITH_WARNINGS
                report.recommendation = PATTERN_INTERRUPT_RECOMMENDATION_REVIEW
            else:
                report.status = PATTERN_INTERRUPT_STATUS_READY
                report.recommendation = PATTERN_INTERRUPT_RECOMMENDATION_READY

            report.enforce_review_only()
            report.refresh_metrics()
            return report

        except Exception as exc:
            failed = PatternInterruptReport(
                job_id=str(job_id) if job_id is not None else None,
                status=PATTERN_INTERRUPT_STATUS_FAILED,
                windows=[],
                suggestions=[],
                warnings=[],
                blocking_reasons=["pattern_interrupt_failed"],
                recommendation=PATTERN_INTERRUPT_RECOMMENDATION_FAILED,
                metadata={
                    **safe_metadata,
                    "source": self.source,
                    "error": str(exc),
                },
            )
            failed.enforce_review_only()
            return failed


def build_pattern_interrupt_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> PatternInterruptReport:
    return PatternInterruptEngine().build(job, metadata=metadata)
