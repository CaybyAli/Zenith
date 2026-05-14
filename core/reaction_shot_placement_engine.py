from __future__ import annotations

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
    REACTION_SHOT_RECOMMENDATION_BLOCKED,
    REACTION_SHOT_RECOMMENDATION_NO_CANDIDATES,
    REACTION_SHOT_RECOMMENDATION_NO_TIMELINE,
    REACTION_SHOT_RECOMMENDATION_READY,
    REACTION_SHOT_RECOMMENDATION_WARNINGS,
    REACTION_SHOT_STATUS_BLOCKED,
    REACTION_SHOT_STATUS_NO_CANDIDATES,
    REACTION_SHOT_STATUS_NO_TIMELINE_ITEMS,
    REACTION_SHOT_STATUS_READY,
    REACTION_SHOT_STATUS_READY_WITH_WARNINGS,
    REACTION_TYPE_CHAT,
    REACTION_TYPE_FRUSTRATION,
    REACTION_TYPE_HYPE,
    REACTION_TYPE_LAUGH,
    REACTION_TYPE_SHOCK,
    REACTION_TYPE_SURPRISE,
    REACTION_TYPE_UNKNOWN,
    SUGGESTED_POSITION_AFTER_TRIGGER,
    SUGGESTED_POSITION_KEEP_ORIGINAL,
    SUGGESTED_POSITION_MANUAL_REVIEW,
    ReactionShotCandidate,
    ReactionShotPlacement,
    ReactionShotPlacementReport,
)

REACTION_SCORE_KEYS = (
    "reaction_score",
    "face_reaction_score",
    "audio_reaction_score",
    "keyword_reaction_score",
    "expressiveness_score",
    "laugh_score",
    "hype_score",
    "shock_score",
    "surprise_score",
    "frustration_score",
    "emotion_score",
    "signal_score",
    "score",
    "confidence",
)

TRIGGER_SCORE_KEYS = (
    "hook_score",
    "emotional_score",
    "emotion_score",
    "climax_score",
    "energy_score",
    "actual_energy_score",
    "content_value_score",
    "energy_peak_score",
    "peak_score",
    "visual_energy_score",
    "motion_score",
    "murch_score",
    "final_score",
    "signal_score",
    "score",
    "confidence",
)

REACTION_KEYWORDS = {
    "haha": REACTION_TYPE_LAUGH,
    "lol": REACTION_TYPE_LAUGH,
    "lmao": REACTION_TYPE_LAUGH,
    "no way": REACTION_TYPE_SHOCK,
    "alter": REACTION_TYPE_HYPE,
    "krass": REACTION_TYPE_HYPE,
    "what": REACTION_TYPE_SURPRISE,
    "oh mein gott": REACTION_TYPE_SURPRISE,
    "omg": REACTION_TYPE_SURPRISE,
    "wow": REACTION_TYPE_SURPRISE,
    "bro": REACTION_TYPE_HYPE,
    "chat": REACTION_TYPE_CHAT,
}

ACTION_TRIGGER_SCORES = {
    "keep_high_value": 0.84,
    "strong_moment": 0.82,
    "highlight": 0.86,
    "hook": 0.80,
    "keep_review": 0.62,
    "censor_keep": 0.68,
    "protect": 0.55,
    "blocked_by_continuity": 0.45,
}

ACTION_REACTION_SCORES = {
    "reaction": 0.82,
    "face_reaction": 0.86,
    "laugh_reaction": 0.88,
    "hype_reaction": 0.88,
    "shock_reaction": 0.90,
    "keep_high_value": 0.62,
    "keep_review": 0.55,
    "censor_keep": 0.64,
    "protect": 0.52,
    "blocked_by_continuity": 0.35,
}

DEFAULT_ITEM_DURATION_SECONDS = 3.0
IDEAL_MIN_REACTION_SECONDS = 1.5
IDEAL_MAX_REACTION_SECONDS = 3.0
STRONG_MAX_REACTION_SECONDS = 5.0
GOOD_AFTER_TRIGGER_SECONDS = 8.0


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
        "report",
        "result",
        "dashboard_package",
        "review_timeline_plan",
        "hook_identification_report",
        "emotional_arc_report",
        "dynamic_pacing_report",
        "pattern_interrupt_report",
        "face_reaction_analysis",
        "face_reaction_result",
        "content_value_result",
        "keyword_emotion_result",
        "energy_peak_detection_result",
        "visual_energy_result",
        "motion_analysis_result",
    ):
        nested = data.get(nested_key)
        nested_items = _items_from_container(nested, keys)
        if nested_items:
            return nested_items

    return []


def _collect_items(
    sources: list[Any],
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for source in sources:
        items.extend(_items_from_container(source, keys))
    return items


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
    if (
        start_seconds is not None
        and end_seconds is not None
        and end_seconds >= start_seconds
    ):
        return end_seconds - start_seconds
    return 0.0


def _text_blob(flat: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "text",
        "transcript",
        "caption",
        "matched_text",
        "matched_keyword",
        "keyword",
        "phrase",
        "label",
        "reason",
        "selection_reason",
        "decision_reason",
        "action",
        "signal_type",
        "suggestion_type",
        "reaction_type",
    ):
        value = flat.get(key)
        if value is not None:
            parts.append(str(value))
    return " ".join(parts).lower()


def _score_from_keys(flat: dict[str, Any], keys: tuple[str, ...]) -> float:
    scores = [
        clamp_score(flat.get(key))
        for key in keys
        if flat.get(key) is not None
    ]
    categories = _safe_dict(flat.get("categories"))
    for key in (
        "hype",
        "shock",
        "laugh",
        "frustration",
        "surprise",
        "question",
        "emotion",
    ):
        if categories.get(key) is not None:
            scores.append(clamp_score(categories.get(key)))
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 6)


def _keyword_reaction_type(flat: dict[str, Any]) -> tuple[str, float]:
    blob = _text_blob(flat)
    for keyword, reaction_type in REACTION_KEYWORDS.items():
        if keyword in blob:
            return reaction_type, 0.80
    return REACTION_TYPE_UNKNOWN, 0.0


def _explicit_reaction_type(flat: dict[str, Any]) -> str:
    raw_type = str(
        flat.get("reaction_type")
        or flat.get("emotion_type")
        or flat.get("dominant_emotion")
        or flat.get("signal_type")
        or flat.get("suggestion_type")
        or ""
    ).lower()

    if "laugh" in raw_type or "funny" in raw_type:
        return REACTION_TYPE_LAUGH
    if "shock" in raw_type:
        return REACTION_TYPE_SHOCK
    if "frustrat" in raw_type or "rage" in raw_type:
        return REACTION_TYPE_FRUSTRATION
    if "surprise" in raw_type:
        return REACTION_TYPE_SURPRISE
    if "chat" in raw_type:
        return REACTION_TYPE_CHAT
    if "hype" in raw_type or "reaction" in raw_type:
        return REACTION_TYPE_HYPE

    keyword_type, _keyword_score = _keyword_reaction_type(flat)
    return keyword_type


def _extract_timeline_items(job: Any) -> tuple[list[dict[str, Any]], str]:
    sources: list[tuple[str, Any, tuple[str, ...]]] = [
        (
            "review_timeline_dashboard_package_report",
            _job_value(job, "review_timeline_dashboard_package_report"),
            ("item_cards", "timeline_items", "items"),
        ),
        (
            "review_timeline_dashboard_package",
            _job_value(job, "review_timeline_dashboard_package"),
            ("item_cards", "timeline_items", "items"),
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
    selected_hook = _safe_dict(_job_value(job, "hook_selected_candidate"))
    report_selected = _safe_dict(hook_report.get("selected_candidate"))

    hook_candidates = _collect_items(
        [
            _job_value(job, "hook_candidates"),
            _job_value(job, "hook_identification"),
            hook_report,
        ],
        ("candidates", "hook_candidates", "items"),
    )
    if selected_hook:
        hook_candidates.append(selected_hook)
    if report_selected:
        hook_candidates.append(report_selected)

    emotional_report = _safe_dict(_job_value(job, "emotional_arc_report"))
    dynamic_report = _safe_dict(_job_value(job, "dynamic_pacing_report"))
    pattern_report = _safe_dict(_job_value(job, "pattern_interrupt_report"))

    return {
        "hook": hook_candidates,
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
        "dynamic_pacing": _collect_items(
            [
                _job_value(job, "dynamic_pacing_segments"),
                dynamic_report,
                _job_value(job, "dynamic_pacing"),
            ],
            ("pacing_segments", "segments", "items"),
        ),
        "pattern_windows": _collect_items(
            [
                _job_value(job, "pattern_interrupt_windows"),
                pattern_report,
                _job_value(job, "pattern_interrupt"),
            ],
            ("windows", "pattern_interrupt_windows", "items"),
        ),
        "pattern_suggestions": _collect_items(
            [
                _job_value(job, "pattern_interrupt_suggestions"),
                pattern_report,
                _job_value(job, "pattern_interrupt"),
            ],
            ("suggestions", "pattern_interrupt_suggestions", "items"),
        ),
        "face": _collect_items(
            [
                _job_value(job, "face_reaction_analysis"),
                _job_value(job, "face_reaction_segments"),
                _job_value(job, "face_reaction_report"),
            ],
            ("segments", "face_reaction_segments", "items"),
        ),
        "content_value": _collect_items(
            [
                _job_value(job, "content_value_scores"),
                _job_value(job, "content_value_segment_scores"),
                _job_value(job, "content_value_report"),
            ],
            ("segment_scores", "content_value_segment_scores", "items"),
        ),
        "energy": _collect_items(
            [
                _job_value(job, "energy_peaks"),
                _job_value(job, "energy_peak_report"),
                _job_value(job, "energy_peak_detection_result"),
            ],
            ("peaks", "energy_peaks", "items", "signals"),
        ),
        "keyword": _collect_items(
            [
                _job_value(job, "keyword_emotion_scores"),
                _job_value(job, "keyword_emotion_segment_scores"),
                _job_value(job, "keyword_emotion_matches"),
                _job_value(job, "keyword_emotion_report"),
            ],
            ("segment_scores", "matches", "keyword_emotion_segment_scores", "items"),
        ),
        "visual": _collect_items(
            [
                _job_value(job, "visual_energy"),
                _job_value(job, "visual_energy_segments"),
                _job_value(job, "visual_energy_report"),
            ],
            ("segments", "visual_energy_segments", "items"),
        ),
        "motion": _collect_items(
            [
                _job_value(job, "motion_analysis"),
                _job_value(job, "motion_analysis_segments"),
                _job_value(job, "motion_analysis_report"),
            ],
            ("segments", "motion_analysis_segments", "items"),
        ),
        "unified": _collect_items(
            [
                _job_value(job, "unified_edit_signals"),
                _job_value(job, "unified_edit_signal_report"),
            ],
            ("signals", "unified_edit_signals", "edit_signals", "items"),
        ),
    }


def _normalize_item(
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
        or f"reaction_shot_source_item_{index}"
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
    warnings = [str(value) for value in _safe_list(flat.get("warnings"))]
    blocking_reasons = [
        str(value)
        for value in (
            _safe_list(flat.get("blocking_errors"))
            + _safe_list(flat.get("blocking_reasons"))
        )
    ]

    protected = (
        bool(flat.get("protected", False))
        or protection_status in {
            "protected",
            "censor_protected",
            "continuity_blocked",
        }
        or action in {"protect", "censor_keep", "blocked_by_continuity"}
    )
    censor_required = (
        bool(flat.get("censor_required", False))
        or bool(flat.get("censor_sfx_required", False))
        or bool(flat.get("sfx_required", False))
        or protection_status == "censor_protected"
        or action == "censor_keep"
    )
    continuity_blocked = (
        bool(flat.get("continuity_blocked", False))
        or protection_status == "continuity_blocked"
        or action == "blocked_by_continuity"
    )

    if protected:
        warnings.append("reaction_shot_protected_preserved")
    if censor_required:
        warnings.append("reaction_shot_censor_review_required")
    if continuity_blocked:
        blocking_reasons.append("reaction_shot_continuity_blocked")

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
        "protected": protected,
        "censor_required": censor_required,
        "continuity_blocked": continuity_blocked,
        "warnings": _unique(warnings),
        "blocking_reasons": _unique(blocking_reasons),
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
                + ["using_reaction_shot_order_fallback_timing"]
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
    flat = _flatten_item_data(item)

    for key in (
        "segment_id",
        "source_segment_id",
        "source_item_id",
        "item_id",
        "timeline_item_id",
        "candidate_id",
        "point_id",
        "window_id",
        "suggestion_id",
        "id",
    ):
        if str(flat.get(key) or "") == value_text:
            return True

    metadata = _safe_dict(flat.get("metadata"))
    return str(metadata.get("source_segment_id") or "") == value_text


def _time_overlaps(
    item: dict[str, Any],
    start_seconds: float | None,
    end_seconds: float | None,
) -> bool:
    if start_seconds is None or end_seconds is None:
        return False

    flat = _flatten_item_data(item)
    item_start = _safe_optional_float(
        flat.get("source_start_seconds", flat.get("start_seconds")),
    )
    item_end = _safe_optional_float(
        flat.get("source_end_seconds", flat.get("end_seconds")),
    )

    if item_start is None or item_end is None:
        center = _safe_optional_float(
            flat.get("center_seconds", flat.get("time_seconds")),
        )
        if center is None:
            return False
        half_width = max(0.1, _safe_float(flat.get("duration_seconds"), 0.2) / 2.0)
        item_start = center - half_width
        item_end = center + half_width

    return item_start < end_seconds and item_end > start_seconds


def _items_near_item(
    items: list[dict[str, Any]],
    item_data: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        item
        for item in items
        if _same_identifier(item, item_data.get("source_segment_id"))
        or _same_identifier(item, item_data.get("source_item_id"))
        or _time_overlaps(
            item,
            item_data.get("start_seconds"),
            item_data.get("end_seconds"),
        )
    ]


def _trigger_type_from_source(source_name: str, flat: dict[str, Any]) -> str:
    signal_text = _text_blob(flat)

    if source_name == "hook" or "hook" in signal_text:
        return PLACEMENT_TYPE_AFTER_HOOK
    if source_name in {"emotional_arc", "emotional_suggestions"}:
        return PLACEMENT_TYPE_AFTER_CLIMAX
    if source_name in {"pattern_windows", "pattern_suggestions"}:
        return PLACEMENT_TYPE_AFTER_PATTERN_INTERRUPT
    if "climax" in signal_text:
        return PLACEMENT_TYPE_AFTER_CLIMAX
    if "pattern" in signal_text or "interrupt" in signal_text:
        return PLACEMENT_TYPE_AFTER_PATTERN_INTERRUPT

    return PLACEMENT_TYPE_AFTER_HIGHLIGHT


def _trigger_score_for_item(
    item_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
) -> tuple[float, str, list[str], dict[str, Any]]:
    flat = item_data["flat"]
    scores = [_score_from_keys(flat, TRIGGER_SCORE_KEYS)]
    matched_sources: dict[str, int] = {}
    placement_type = PLACEMENT_TYPE_AFTER_HIGHLIGHT
    warnings: list[str] = []

    action = str(flat.get("action") or flat.get("final_action") or "")
    if action in ACTION_TRIGGER_SCORES:
        scores.append(ACTION_TRIGGER_SCORES[action])

    blob = _text_blob(flat)
    if "highlight" in blob or "strong_moment" in blob:
        scores.append(0.86)
    if "hook" in blob:
        scores.append(0.80)
        placement_type = PLACEMENT_TYPE_AFTER_HOOK

    for source_name in (
        "hook",
        "emotional_arc",
        "emotional_suggestions",
        "dynamic_pacing",
        "pattern_windows",
        "pattern_suggestions",
        "content_value",
        "energy",
        "keyword",
        "visual",
        "motion",
        "unified",
    ):
        matches = _items_near_item(
            related_sources.get(source_name, []),
            item_data,
        )
        matched_sources[source_name] = len(matches)
        for match in matches:
            match_flat = _flatten_item_data(match)
            score = _score_from_keys(match_flat, TRIGGER_SCORE_KEYS)
            if score > 0.0:
                scores.append(score)
            if source_name in {
                "hook",
                "emotional_arc",
                "emotional_suggestions",
                "pattern_windows",
                "pattern_suggestions",
            }:
                placement_type = _trigger_type_from_source(source_name, match_flat)

    clean_scores = [score for score in scores if score > 0.0]
    if not clean_scores:
        clean_scores = [0.0]

    score = round(sum(clean_scores) / len(clean_scores), 6)

    if item_data["continuity_blocked"]:
        score = min(score, 0.45)
        warnings.append("reaction_shot_continuity_blocked")
        placement_type = PLACEMENT_TYPE_BLOCKED_BY_CONTINUITY
    elif item_data["censor_required"]:
        score = max(score, 0.62)
        warnings.append("reaction_shot_censor_review_required")
        placement_type = PLACEMENT_TYPE_CENSOR_REVIEW
    elif item_data["protected"]:
        warnings.append("reaction_shot_protected_preserved")
        placement_type = PLACEMENT_TYPE_PROTECTED_PRESERVED

    evidence = {
        "matched_sources": matched_sources,
        "action": action,
        "source_label": item_data["source_label"],
        "raw_score_count": len(clean_scores),
    }

    return clamp_score(score), placement_type, _unique(warnings), evidence


def _build_trigger_moments(
    timeline_items: list[dict[str, Any]],
    related_sources: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    triggers: list[dict[str, Any]] = []

    for item_data in timeline_items:
        score, placement_type, warnings, evidence = _trigger_score_for_item(
            item_data,
            related_sources,
        )
        if score < 0.58 and placement_type == PLACEMENT_TYPE_AFTER_HIGHLIGHT:
            continue

        triggers.append(
            {
                "trigger_item_id": item_data["source_item_id"],
                "trigger_segment_id": item_data["source_segment_id"],
                "trigger_start_seconds": item_data["start_seconds"],
                "trigger_end_seconds": item_data["end_seconds"],
                "trigger_score": round(score, 6),
                "placement_type": placement_type,
                "warnings": _unique(list(item_data["warnings"]) + warnings),
                "blocking_reasons": list(item_data["blocking_reasons"]),
                "metadata": {
                    "trigger_evidence": evidence,
                    "source_label": item_data["source_label"],
                    "review_only": True,
                    "media_unchanged": True,
                },
            }
        )

    return sorted(
        triggers,
        key=lambda item: (
            -float(item.get("trigger_score") or 0.0),
            float(item.get("trigger_start_seconds") or 0.0),
        ),
    )


def _candidate_from_item(
    item_data: dict[str, Any],
    index: int,
    source_name: str,
) -> ReactionShotCandidate | None:
    flat = item_data["flat"]
    reaction_type = _explicit_reaction_type(flat)
    keyword_type, keyword_score = _keyword_reaction_type(flat)

    if reaction_type == REACTION_TYPE_UNKNOWN and keyword_type != REACTION_TYPE_UNKNOWN:
        reaction_type = keyword_type

    direct_reaction_score = _score_from_keys(flat, REACTION_SCORE_KEYS)
    action = str(flat.get("action") or flat.get("final_action") or "")
    action_score = ACTION_REACTION_SCORES.get(action, 0.0)

    face_score = clamp_score(
        flat.get("face_reaction_score")
        or flat.get("face_score")
        or flat.get("expressiveness_score")
        or 0.0
    )
    audio_score = clamp_score(
        flat.get("audio_reaction_score")
        or flat.get("audio_score")
        or flat.get("voice_spike_score")
        or 0.0
    )
    expressiveness_score = clamp_score(
        flat.get("expressiveness_score")
        or max(face_score, audio_score, direct_reaction_score)
    )

    blob = _text_blob(flat)
    reaction_text_hint = any(
        word in blob
        for word in (
            "reaction",
            "laugh",
            "shock",
            "hype",
            "surprise",
            "frustration",
            "face",
            "chat",
        )
    )

    raw_scores = [
        direct_reaction_score,
        keyword_score,
        action_score,
        face_score,
        audio_score,
        expressiveness_score,
    ]
    clean_scores = [score for score in raw_scores if score > 0.0]

    if source_name == "face" and not clean_scores:
        clean_scores.append(0.65)
    if reaction_text_hint and not clean_scores:
        clean_scores.append(0.60)

    if not clean_scores:
        return None

    reaction_score = round(sum(clean_scores) / len(clean_scores), 6)
    confidence = round(
        clamp_score((reaction_score * 0.7) + (expressiveness_score * 0.3)),
        6,
    )

    start_seconds = _safe_optional_float(item_data.get("start_seconds"))
    end_seconds = _safe_optional_float(item_data.get("end_seconds"))
    duration_seconds = _safe_float(item_data.get("duration_seconds"), 0.0)

    warnings = list(item_data["warnings"])
    blocking_reasons = list(item_data["blocking_reasons"])

    if duration_seconds < 1.0:
        warnings.append("too_short_reaction")
    if duration_seconds > STRONG_MAX_REACTION_SECONDS:
        warnings.append("too_long_reaction")
    elif duration_seconds > IDEAL_MAX_REACTION_SECONDS and expressiveness_score < 0.75:
        warnings.append("long_reaction_needs_strong_expression_review")

    if item_data["continuity_blocked"]:
        blocking_reasons.append("reaction_shot_continuity_blocked")
    if item_data["censor_required"]:
        warnings.append("reaction_shot_censor_review_required")
    if item_data["protected"]:
        warnings.append("reaction_shot_protected_preserved")

    return ReactionShotCandidate(
        source_item_id=item_data["source_item_id"],
        source_segment_id=item_data["source_segment_id"],
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=round(duration_seconds, 6),
        reaction_type=reaction_type,
        reaction_score=round(clamp_score(reaction_score), 6),
        expressiveness_score=round(clamp_score(expressiveness_score), 6),
        audio_reaction_score=round(clamp_score(audio_score), 6),
        face_reaction_score=round(clamp_score(face_score), 6),
        keyword_reaction_score=round(clamp_score(keyword_score), 6),
        confidence=confidence,
        review_required=True,
        warnings=_unique(warnings),
        blocking_reasons=_unique(blocking_reasons),
        metadata={
            "phase": "2B-41",
            "source_name": source_name,
            "source_index": index,
            "review_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_41": True,
        },
    )


def _build_reaction_candidates(
    timeline_items: list[dict[str, Any]],
    related_sources: dict[str, list[dict[str, Any]]],
) -> list[ReactionShotCandidate]:
    candidates: list[ReactionShotCandidate] = []
    seen: set[tuple[str | None, float | None, float | None]] = set()

    source_groups: list[tuple[str, list[dict[str, Any]]]] = [
        ("face", related_sources.get("face", [])),
        ("keyword", related_sources.get("keyword", [])),
        ("hook", related_sources.get("hook", [])),
        ("emotional_arc", related_sources.get("emotional_arc", [])),
        ("pattern_suggestions", related_sources.get("pattern_suggestions", [])),
        ("unified", related_sources.get("unified", [])),
        ("timeline", [item["flat"] for item in timeline_items]),
    ]

    for source_name, source_items in source_groups:
        for index, raw_item in enumerate(source_items):
            item_data = _normalize_item(raw_item, index, source_name)
            item_data = _assign_fallback_timing([item_data])[0]
            candidate = _candidate_from_item(item_data, index, source_name)
            if candidate is None:
                continue

            key = (
                candidate.source_segment_id or candidate.source_item_id,
                candidate.start_seconds,
                candidate.end_seconds,
            )
            if key in seen:
                continue
            seen.add(key)
            candidates.append(candidate)

    return sorted(
        candidates,
        key=lambda candidate: (
            -float(candidate.confidence or 0.0),
            float(candidate.start_seconds or 0.0),
        ),
    )


def _timing_score(
    trigger: dict[str, Any],
    candidate: ReactionShotCandidate,
) -> tuple[float, list[str], str]:
    trigger_end = _safe_optional_float(trigger.get("trigger_end_seconds"))
    candidate_start = _safe_optional_float(candidate.start_seconds)

    if trigger_end is None or candidate_start is None:
        return 0.35, ["reaction_timing_unknown"], SUGGESTED_POSITION_MANUAL_REVIEW

    delta = candidate_start - trigger_end

    if 0.0 <= delta <= GOOD_AFTER_TRIGGER_SECONDS:
        return 1.0, [], SUGGESTED_POSITION_AFTER_TRIGGER
    if delta > GOOD_AFTER_TRIGGER_SECONDS:
        distance_penalty = min(delta / 30.0, 0.5)
        return (
            round(max(0.35, 0.75 - distance_penalty), 6),
            ["reaction_far_after_trigger_review"],
            SUGGESTED_POSITION_AFTER_TRIGGER,
        )

    return (
        0.30,
        ["reaction_before_trigger_manual_review"],
        SUGGESTED_POSITION_MANUAL_REVIEW,
    )


def _duration_score(candidate: ReactionShotCandidate) -> tuple[float, list[str]]:
    duration = float(candidate.duration_seconds or 0.0)
    expressiveness = float(candidate.expressiveness_score or 0.0)

    if IDEAL_MIN_REACTION_SECONDS <= duration <= IDEAL_MAX_REACTION_SECONDS:
        return 1.0, []
    if IDEAL_MAX_REACTION_SECONDS < duration <= STRONG_MAX_REACTION_SECONDS:
        if expressiveness >= 0.75:
            return 0.85, ["strong_reaction_long_duration_review"]
        return 0.60, ["long_reaction_needs_strong_expression_review"]
    if duration < 1.0:
        return 0.35, ["too_short_reaction"]
    if duration < IDEAL_MIN_REACTION_SECONDS:
        return 0.65, ["short_reaction_review"]

    return 0.30, ["too_long_reaction"]


def _has_consecutive_reaction_risk(
    candidate: ReactionShotCandidate,
    all_candidates: list[ReactionShotCandidate],
) -> bool:
    candidate_start = _safe_optional_float(candidate.start_seconds)
    candidate_end = _safe_optional_float(candidate.end_seconds)
    if candidate_start is None or candidate_end is None:
        return False

    for other in all_candidates:
        if other.candidate_id == candidate.candidate_id:
            continue

        other_start = _safe_optional_float(other.start_seconds)
        other_end = _safe_optional_float(other.end_seconds)
        if other_start is None or other_end is None:
            continue

        gap_a = abs(other_start - candidate_end)
        gap_b = abs(candidate_start - other_end)
        if min(gap_a, gap_b) <= 1.0:
            return True

    return False


def _best_candidate_for_trigger(
    trigger: dict[str, Any],
    candidates: list[ReactionShotCandidate],
) -> tuple[ReactionShotCandidate | None, float, list[str], str]:
    best_candidate: ReactionShotCandidate | None = None
    best_score = -1.0
    best_warnings: list[str] = []
    best_position = SUGGESTED_POSITION_MANUAL_REVIEW

    for candidate in candidates:
        timing_score, timing_warnings, position = _timing_score(trigger, candidate)
        duration_score, duration_warnings = _duration_score(candidate)

        safety_penalty = 0.0
        if candidate.blocking_reasons:
            safety_penalty += 0.45
        if "reaction_shot_censor_review_required" in candidate.warnings:
            safety_penalty += 0.10

        score = (
            (float(trigger.get("trigger_score") or 0.0) * 0.30)
            + (float(candidate.confidence or 0.0) * 0.35)
            + (timing_score * 0.25)
            + (duration_score * 0.10)
            - safety_penalty
        )
        score = clamp_score(score)

        if score > best_score:
            best_candidate = candidate
            best_score = score
            best_warnings = _unique(
                list(candidate.warnings or [])
                + timing_warnings
                + duration_warnings
            )
            best_position = position

    if best_candidate is None:
        return None, 0.0, [], SUGGESTED_POSITION_MANUAL_REVIEW

    if _has_consecutive_reaction_risk(best_candidate, candidates):
        best_warnings.append("consecutive_reaction_risk")
        best_score = min(best_score, 0.82)

    return best_candidate, round(best_score, 6), _unique(best_warnings), best_position


def _manual_placeholder_for_trigger(trigger: dict[str, Any]) -> ReactionShotPlacement:
    return ReactionShotPlacement(
        trigger_item_id=trigger.get("trigger_item_id"),
        trigger_segment_id=trigger.get("trigger_segment_id"),
        reaction_candidate_id=None,
        placement_type=PLACEMENT_TYPE_MANUAL_PLACEHOLDER,
        suggested_position=SUGGESTED_POSITION_MANUAL_REVIEW,
        trigger_start_seconds=trigger.get("trigger_start_seconds"),
        trigger_end_seconds=trigger.get("trigger_end_seconds"),
        reaction_start_seconds=None,
        reaction_end_seconds=None,
        suggested_duration_seconds=0.0,
        placement_score=0.0,
        review_required=True,
        can_auto_place=False,
        warnings=_unique(
            list(trigger.get("warnings") or [])
            + ["missing_reaction_placeholder"]
        ),
        blocking_reasons=list(trigger.get("blocking_reasons") or []),
        metadata={
            "phase": "2B-41",
            "manual_placeholder": True,
            "review_only": True,
            "media_unchanged": True,
            "trigger_score": trigger.get("trigger_score"),
        },
    )


def _placement_for_trigger(
    trigger: dict[str, Any],
    candidates: list[ReactionShotCandidate],
) -> ReactionShotPlacement:
    if trigger.get("placement_type") == PLACEMENT_TYPE_BLOCKED_BY_CONTINUITY:
        return ReactionShotPlacement(
            trigger_item_id=trigger.get("trigger_item_id"),
            trigger_segment_id=trigger.get("trigger_segment_id"),
            reaction_candidate_id=None,
            placement_type=PLACEMENT_TYPE_BLOCKED_BY_CONTINUITY,
            suggested_position=SUGGESTED_POSITION_MANUAL_REVIEW,
            trigger_start_seconds=trigger.get("trigger_start_seconds"),
            trigger_end_seconds=trigger.get("trigger_end_seconds"),
            placement_score=0.0,
            review_required=True,
            can_auto_place=False,
            warnings=list(trigger.get("warnings") or []),
            blocking_reasons=_unique(
                list(trigger.get("blocking_reasons") or [])
                + ["reaction_shot_continuity_blocked"]
            ),
            metadata={
                "phase": "2B-41",
                "review_only": True,
                "media_unchanged": True,
                "blocked": True,
            },
        )

    if not candidates:
        return _manual_placeholder_for_trigger(trigger)

    candidate, score, warnings, position = _best_candidate_for_trigger(
        trigger,
        candidates,
    )
    if candidate is None or score < 0.25:
        return _manual_placeholder_for_trigger(trigger)

    placement_type = str(
        trigger.get("placement_type") or PLACEMENT_TYPE_AFTER_HIGHLIGHT
    )
    if placement_type in {
        PLACEMENT_TYPE_CENSOR_REVIEW,
        PLACEMENT_TYPE_PROTECTED_PRESERVED,
    }:
        position = SUGGESTED_POSITION_KEEP_ORIGINAL

    blocking_reasons = _unique(
        list(trigger.get("blocking_reasons") or [])
        + list(candidate.blocking_reasons or [])
    )
    if blocking_reasons:
        score = min(score, 0.50)

    return ReactionShotPlacement(
        trigger_item_id=trigger.get("trigger_item_id"),
        trigger_segment_id=trigger.get("trigger_segment_id"),
        reaction_candidate_id=candidate.candidate_id,
        placement_type=placement_type,
        suggested_position=position,
        trigger_start_seconds=trigger.get("trigger_start_seconds"),
        trigger_end_seconds=trigger.get("trigger_end_seconds"),
        reaction_start_seconds=candidate.start_seconds,
        reaction_end_seconds=candidate.end_seconds,
        suggested_duration_seconds=round(
            float(candidate.duration_seconds or 0.0),
            6,
        ),
        placement_score=round(clamp_score(score), 6),
        review_required=True,
        can_auto_place=False,
        warnings=_unique(list(trigger.get("warnings") or []) + warnings),
        blocking_reasons=blocking_reasons,
        metadata={
            "phase": "2B-41",
            "review_only": True,
            "media_unchanged": True,
            "trigger_score": trigger.get("trigger_score"),
            "candidate_confidence": candidate.confidence,
            "candidate_reaction_type": candidate.reaction_type,
            "suggestion_only": True,
            "no_execution_in_2b_41": True,
        },
    )


class ReactionShotPlacementEngine:
    def build_report(self, job: Any) -> ReactionShotPlacementReport:
        job_id = _job_value(job, "job_id") or _job_value(job, "id")

        raw_timeline_items, timeline_source = _extract_timeline_items(job)
        related_sources = _extract_related_sources(job)

        normalized_items = [
            _normalize_item(item, index, timeline_source)
            for index, item in enumerate(raw_timeline_items)
            if isinstance(item, dict)
        ]
        normalized_items = _assign_fallback_timing(normalized_items)

        report = ReactionShotPlacementReport(
            job_id=str(job_id) if job_id is not None else None,
            metadata={
                "phase": "2B-41",
                "block": "block7_story_pacing",
                "review_only": True,
                "reaction_shot_placement_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_41": True,
                "no_render_in_2b_41": True,
                "no_timeline_reorder_in_2b_41": True,
                "no_reaction_apply_in_2b_41": True,
                "no_reaction_insert_in_2b_41": True,
                "no_facecam_move_in_2b_41": True,
                "no_zoom_insert_in_2b_41": True,
                "timeline_source": timeline_source,
            },
        )

        if not normalized_items:
            report.status = REACTION_SHOT_STATUS_NO_TIMELINE_ITEMS
            report.recommendation = REACTION_SHOT_RECOMMENDATION_NO_TIMELINE
            report.warnings = ["reaction_shot_no_timeline_items"]
            report.enforce_review_only()
            report.refresh_metrics()
            return report

        candidates = _build_reaction_candidates(normalized_items, related_sources)
        triggers = _build_trigger_moments(normalized_items, related_sources)

        report.candidates = candidates

        if not triggers:
            report.status = REACTION_SHOT_STATUS_NO_CANDIDATES
            report.recommendation = REACTION_SHOT_RECOMMENDATION_NO_CANDIDATES
            report.warnings = ["reaction_shot_no_trigger_moments"]
            report.enforce_review_only()
            report.refresh_metrics()
            return report

        placements = [
            _placement_for_trigger(trigger, candidates)
            for trigger in triggers
        ]
        report.placements = placements

        warnings = []
        blocking_reasons = []
        for candidate in candidates:
            warnings.extend(candidate.warnings or [])
            blocking_reasons.extend(candidate.blocking_reasons or [])
        for placement in placements:
            warnings.extend(placement.warnings or [])
            blocking_reasons.extend(placement.blocking_reasons or [])

        report.warnings = _unique(warnings)
        report.blocking_reasons = _unique(blocking_reasons)

        if report.blocking_reasons:
            report.status = REACTION_SHOT_STATUS_BLOCKED
            report.recommendation = REACTION_SHOT_RECOMMENDATION_BLOCKED
        elif report.warnings:
            report.status = REACTION_SHOT_STATUS_READY_WITH_WARNINGS
            report.recommendation = REACTION_SHOT_RECOMMENDATION_WARNINGS
        elif candidates:
            report.status = REACTION_SHOT_STATUS_READY
            report.recommendation = REACTION_SHOT_RECOMMENDATION_READY
        else:
            report.status = REACTION_SHOT_STATUS_NO_CANDIDATES
            report.recommendation = REACTION_SHOT_RECOMMENDATION_NO_CANDIDATES

        report.enforce_review_only()
        report.refresh_metrics()
        return report

    def analyze(self, job: Any) -> ReactionShotPlacementReport:
        return self.build_report(job)

    def run(self, job: Any) -> ReactionShotPlacementReport:
        return self.build_report(job)
