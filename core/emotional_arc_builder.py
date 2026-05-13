from __future__ import annotations

from typing import Any

from models.emotional_arc import (
    EMOTIONAL_ARC_PHASE_RANGES,
    EMOTIONAL_ARC_RECOMMENDATION_BLOCKED,
    EMOTIONAL_ARC_RECOMMENDATION_FAILED,
    EMOTIONAL_ARC_RECOMMENDATION_NO_ITEMS,
    EMOTIONAL_ARC_RECOMMENDATION_READY,
    EMOTIONAL_ARC_RECOMMENDATION_REVIEW,
    EMOTIONAL_ARC_STATUS_BLOCKED,
    EMOTIONAL_ARC_STATUS_FAILED,
    EMOTIONAL_ARC_STATUS_NO_TIMELINE_ITEMS,
    EMOTIONAL_ARC_STATUS_READY,
    EMOTIONAL_ARC_STATUS_READY_WITH_WARNINGS,
    EMOTIONAL_ARC_TARGET_SCORES,
    EmotionalArcPoint,
    EmotionalArcReport,
    EmotionalArcSuggestion,
)


SOURCE_SCORE_KEYS = (
    "hook_score",
    "content_value_score",
    "final_score",
    "murch_score",
    "energy_peak_score",
    "peak_score",
    "energy_score",
    "visual_energy_score",
    "audio_energy_score",
    "reaction_score",
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

    return {
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
        "murch": _collect_items(
            [
                _job_value(job, "murch_score"),
                _job_value(job, "murch_scoring_segment_scores"),
                _job_value(job, "murch_scoring_report"),
            ],
            ("segment_scores", "murch_scoring_segment_scores", "items"),
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
        or f"emotional_arc_source_item_{index}"
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
    censor_required = bool(flat.get("censor_sfx_required", False)) or (
        protection_status == "censor_protected"
    ) or action == "censor_keep"
    continuity_blocked = bool(flat.get("continuity_blocked", False)) or (
        protection_status == "continuity_blocked"
    ) or action == "blocked_by_continuity"

    if protected and "protected_arc_preserved_review_only" not in safety_flags:
        safety_flags.append("protected_arc_preserved_review_only")
    if censor_required and "censor_arc_review_required" not in safety_flags:
        safety_flags.append("censor_arc_review_required")
    if continuity_blocked:
        blocking_reasons.append("continuity_arc_blocked")
        if "continuity_arc_blocked" not in safety_flags:
            safety_flags.append("continuity_arc_blocked")

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

    return item_start <= end_seconds and item_end >= start_seconds


def _items_near_point(
    items: list[dict[str, Any]],
    point_data: dict[str, Any],
) -> list[dict[str, Any]]:
    source_item_id = point_data["source_item_id"]
    source_segment_id = point_data["source_segment_id"]
    start_seconds = point_data["start_seconds"]
    end_seconds = point_data["end_seconds"]

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


def _actual_energy_score(
    point_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
) -> tuple[float, list[str], dict[str, Any]]:
    flat = point_data["flat"]
    scores = _score_values_from_item(flat)
    evidence: dict[str, Any] = {
        "direct_score_count": len(scores),
        "matched_source_counts": {},
    }

    for source_name, source_items in related_sources.items():
        matches = _items_near_point(source_items, point_data)
        evidence["matched_source_counts"][source_name] = len(matches)
        for match in matches:
            scores.extend(_score_values_from_item(match))

    warnings: list[str] = []
    fallback_score, fallback_reason = _fallback_score(flat)
    if scores:
        score = _weighted_average(scores)
    else:
        score = fallback_score
        warnings.append("using_emotional_arc_fallback_score")

    action = str(flat.get("action") or flat.get("final_action") or "")
    if point_data["continuity_blocked"]:
        score = min(score, ACTION_FALLBACK_SCORES["blocked_by_continuity"])
        warnings.append("continuity_arc_blocked")
    elif point_data["censor_required"] or action == "censor_keep":
        score = min(max(score, ACTION_FALLBACK_SCORES["censor_keep"]), 0.75)
        warnings.append("censor_arc_review_required")
    elif point_data["protected"]:
        warnings.append("protected_arc_preserved")

    evidence.update(
        {
            "raw_score_count": len(scores),
            "fallback_score": fallback_score,
            "fallback_reason": fallback_reason,
            "continuity_blocked": point_data["continuity_blocked"],
            "censor_required": point_data["censor_required"],
            "protected": point_data["protected"],
        }
    )

    return round(clamp_score(score), 6), _unique(warnings), evidence


def _arc_phase_for_ratio(ratio: float) -> str:
    safe_ratio = max(0.0, min(1.0, ratio))
    for phase, phase_range in EMOTIONAL_ARC_PHASE_RANGES.items():
        start, end = phase_range
        if phase == "outro":
            if start <= safe_ratio <= end:
                return phase
        elif start <= safe_ratio < end:
            return phase
    return "outro"


def _position_ratio(
    index: int,
    item_count: int,
    cumulative_duration: float,
    duration_seconds: float,
    total_duration: float,
) -> float:
    if item_count <= 1:
        return 0.0
    if total_duration > 0.0:
        midpoint = cumulative_duration + max(duration_seconds, 0.0) * 0.5
        return round(max(0.0, min(1.0, midpoint / total_duration)), 6)
    return round(index / max(item_count - 1, 1), 6)


def _build_arc_point(
    point_data: dict[str, Any],
    index: int,
    timeline_position_ratio: float,
    related_sources: dict[str, list[dict[str, Any]]],
) -> EmotionalArcPoint:
    arc_phase = _arc_phase_for_ratio(timeline_position_ratio)
    target_score = EMOTIONAL_ARC_TARGET_SCORES[arc_phase]
    actual_score, score_warnings, evidence = _actual_energy_score(
        point_data,
        related_sources,
    )
    warnings = _unique(
        list(point_data["warnings"])
        + list(score_warnings)
        + list(point_data["blocking_reasons"])
    )

    point = EmotionalArcPoint(
        point_id=f"emotional_arc_point_{index}_{point_data['source_item_id']}",
        source_item_id=point_data["source_item_id"],
        source_segment_id=point_data["source_segment_id"],
        start_seconds=(
            round(point_data["start_seconds"], 3)
            if point_data["start_seconds"] is not None
            else None
        ),
        end_seconds=(
            round(point_data["end_seconds"], 3)
            if point_data["end_seconds"] is not None
            else None
        ),
        duration_seconds=round(float(point_data["duration_seconds"] or 0.0), 3),
        timeline_position_ratio=timeline_position_ratio,
        actual_energy_score=actual_score,
        target_energy_score=target_score,
        deviation_score=round(abs(actual_score - target_score), 6),
        arc_phase=arc_phase,
        label=f"{arc_phase}:{point_data['source_item_id']}",
        review_required=True,
        warnings=warnings,
        metadata={
            "source_label": point_data["source_label"],
            "action": point_data["action"],
            "protection_status": point_data["protection_status"],
            "protected": point_data["protected"],
            "censor_required": point_data["censor_required"],
            "continuity_blocked": point_data["continuity_blocked"],
            "safety_flags": list(point_data["safety_flags"]),
            "score_evidence": evidence,
            "source_metadata": _source_metadata(point_data["flat"]),
        },
    )
    point.enforce_review_only()
    return point


def _global_blocking_reasons(job: Any) -> list[str]:
    blocking_reasons: list[str] = []
    for key in (
        "review_timeline_dashboard_blocking_errors",
        "timeline_safety_blocking_errors",
        "timeline_approval_blocking_reasons",
        "emotional_arc_blocking_reasons",
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


def _phase_scores(points: list[EmotionalArcPoint], phase: str) -> list[float]:
    return [
        float(point.actual_energy_score or 0.0)
        for point in points
        if point.arc_phase == phase
    ]


def _score_max(scores: list[float]) -> float:
    return round(max(scores), 6) if scores else 0.0


def _compute_hook_strength(
    points: list[EmotionalArcPoint],
    related_sources: dict[str, list[dict[str, Any]]],
) -> float:
    hook_scores = _phase_scores(points, "hook")
    for candidate in related_sources.get("hook", []):
        hook_scores.extend(_score_values_from_item(candidate, ("hook_score", "confidence")))
    return _score_max(hook_scores)


def _compute_climax_strength(points: list[EmotionalArcPoint]) -> float:
    climax_scores = _phase_scores(points, "climax")
    if not climax_scores:
        climax_scores = [
            float(point.actual_energy_score or 0.0) * 0.9
            for point in points
            if 0.70 <= float(point.timeline_position_ratio or 0.0) <= 0.92
        ]
    return _score_max(climax_scores)


def _compute_breathing_room_score(points: list[EmotionalArcPoint]) -> float:
    breathing_scores = [
        float(point.actual_energy_score or 0.0)
        for point in points
        if point.arc_phase in {"calm", "wind_down", "outro"}
    ]
    if not breathing_scores:
        breathing_scores = [
            float(point.actual_energy_score or 0.0)
            for point in points
            if float(point.timeline_position_ratio or 0.0) >= 0.35
        ]
    if not breathing_scores:
        return 0.0
    min_score = min(breathing_scores)
    return round(clamp_score((0.75 - min_score) / 0.30), 6)


def _suggestion(
    suggestion_type: str,
    reason: str,
    severity: str = "medium",
    source_item_id: str | None = None,
    arc_phase: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> EmotionalArcSuggestion:
    suggestion = EmotionalArcSuggestion(
        suggestion_id=f"emotional_arc_suggestion_{suggestion_type}_{source_item_id or 'global'}",
        suggestion_type=suggestion_type,
        source_item_id=source_item_id,
        arc_phase=arc_phase,
        severity=severity,
        reason=reason,
        review_required=True,
        can_auto_apply=False,
        metadata=dict(metadata or {}),
    )
    suggestion.enforce_review_only()
    return suggestion


def _has_suggestion(
    suggestions: list[EmotionalArcSuggestion],
    suggestion_type: str,
    source_item_id: str | None = None,
) -> bool:
    return any(
        suggestion.suggestion_type == suggestion_type
        and suggestion.source_item_id == source_item_id
        for suggestion in suggestions
    )


def _build_suggestions(report: EmotionalArcReport) -> list[EmotionalArcSuggestion]:
    points = report.arc_points
    suggestions: list[EmotionalArcSuggestion] = []

    if report.hook_strength_score < 0.70:
        suggestions.append(
            _suggestion(
                "weak_hook",
                "Hook energy is below the target review threshold.",
                severity="high",
                arc_phase="hook",
                metadata={"hook_strength_score": report.hook_strength_score},
            )
        )

    if report.climax_strength_score < 0.78:
        suggestions.append(
            _suggestion(
                "missing_climax",
                "No clear emotional climax was detected in the review timeline.",
                severity="high",
                arc_phase="climax",
                metadata={"climax_strength_score": report.climax_strength_score},
            )
        )

    if report.flatness_score >= 0.82 and len(points) >= 3:
        suggestions.append(
            _suggestion(
                "flat_energy_curve",
                "Several timeline items have similar emotional energy.",
                severity="medium",
                metadata={"flatness_score": report.flatness_score},
            )
        )

    if report.breathing_room_score < 0.45 and len(points) >= 3:
        suggestions.append(
            _suggestion(
                "missing_breathing_room",
                "No clear lower-energy recovery segment was detected.",
                severity="medium",
                arc_phase="calm",
                metadata={"breathing_room_score": report.breathing_room_score},
            )
        )

    build_scores = _phase_scores(points, "build_up") + _phase_scores(points, "tension")
    highlight_scores = _phase_scores(points, "first_highlight") + _phase_scores(
        points,
        "climax",
    )
    if build_scores and highlight_scores and max(highlight_scores) - min(build_scores) < 0.12:
        suggestions.append(
            _suggestion(
                "weak_build_up",
                "Build-up does not rise enough before the highlight or climax.",
                severity="medium",
                arc_phase="build_up",
            )
        )

    consecutive_high = 0
    for point in points:
        if float(point.actual_energy_score or 0.0) >= 0.82:
            consecutive_high += 1
        else:
            consecutive_high = 0
        if consecutive_high >= 3:
            suggestions.append(
                _suggestion(
                    "too_many_high_energy_segments",
                    "Three or more high-energy items appear consecutively.",
                    severity="medium",
                    source_item_id=point.source_item_id,
                    arc_phase=point.arc_phase,
                )
            )
            break

    for previous, current in zip(points, points[1:]):
        drop = float(previous.actual_energy_score or 0.0) - float(
            current.actual_energy_score or 0.0
        )
        if drop >= 0.35:
            suggestions.append(
                _suggestion(
                    "abrupt_emotional_drop",
                    "Energy drops abruptly between adjacent review items.",
                    severity="medium",
                    source_item_id=current.source_item_id,
                    arc_phase=current.arc_phase,
                    metadata={
                        "previous_source_item_id": previous.source_item_id,
                        "drop_score": round(drop, 6),
                    },
                )
            )

    for point in points:
        if bool(point.metadata.get("censor_required")) and not _has_suggestion(
            suggestions,
            "censor_arc_review_required",
            point.source_item_id,
        ):
            suggestions.append(
                _suggestion(
                    "censor_arc_review_required",
                    "Censor-protected item is preserved for emotional arc review.",
                    severity="high",
                    source_item_id=point.source_item_id,
                    arc_phase=point.arc_phase,
                )
            )
        if bool(point.metadata.get("continuity_blocked")) and not _has_suggestion(
            suggestions,
            "continuity_arc_blocked",
            point.source_item_id,
        ):
            suggestions.append(
                _suggestion(
                    "continuity_arc_blocked",
                    "Continuity-blocked item prevents arc approval.",
                    severity="blocking",
                    source_item_id=point.source_item_id,
                    arc_phase=point.arc_phase,
                )
            )
        if bool(point.metadata.get("protected")) and not _has_suggestion(
            suggestions,
            "protected_arc_preserved",
            point.source_item_id,
        ):
            suggestions.append(
                _suggestion(
                    "protected_arc_preserved",
                    "Protected item is preserved and only marked for review.",
                    severity="medium",
                    source_item_id=point.source_item_id,
                    arc_phase=point.arc_phase,
                )
            )

    return suggestions


class EmotionalArcBuilder:
    source = "emotional_arc_builder"

    def build(
        self,
        job: Any,
        metadata: dict[str, Any] | None = None,
    ) -> EmotionalArcReport:
        safe_metadata = dict(metadata or {})
        job_id = _job_value(job, "job_id") or _job_value(job, "id")

        try:
            raw_items, source_label = _extract_timeline_items(job)
            related_sources = _extract_related_sources(job)
            global_blockers = _global_blocking_reasons(job)

            if not raw_items:
                report = EmotionalArcReport(
                    job_id=str(job_id) if job_id is not None else None,
                    status=EMOTIONAL_ARC_STATUS_NO_TIMELINE_ITEMS,
                    arc_points=[],
                    suggestions=[],
                    warnings=["no_review_timeline_items_available"],
                    blocking_reasons=[],
                    recommendation=EMOTIONAL_ARC_RECOMMENDATION_NO_ITEMS,
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

            total_duration = sum(
                max(float(item["duration_seconds"] or 0.0), 0.0)
                for item in normalized_items
            )
            arc_points: list[EmotionalArcPoint] = []
            cumulative_duration = 0.0

            for index, item in enumerate(normalized_items):
                duration = max(float(item["duration_seconds"] or 0.0), 0.0)
                position_ratio = _position_ratio(
                    index,
                    len(normalized_items),
                    cumulative_duration,
                    duration,
                    total_duration,
                )
                arc_points.append(
                    _build_arc_point(
                        item,
                        index,
                        position_ratio,
                        related_sources,
                    )
                )
                cumulative_duration += duration

            warnings = _unique(
                [
                    warning
                    for point in arc_points
                    for warning in list(point.warnings or [])
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

            report = EmotionalArcReport(
                job_id=str(job_id) if job_id is not None else None,
                status=EMOTIONAL_ARC_STATUS_READY,
                arc_points=arc_points,
                suggestions=[],
                warnings=warnings,
                blocking_reasons=blocking_reasons,
                recommendation=EMOTIONAL_ARC_RECOMMENDATION_READY,
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
            report.hook_strength_score = _compute_hook_strength(
                arc_points,
                related_sources,
            )
            report.climax_strength_score = _compute_climax_strength(arc_points)
            report.breathing_room_score = _compute_breathing_room_score(arc_points)
            report.enforce_review_only()
            report.refresh_metrics()
            report.suggestions = _build_suggestions(report)

            if blocking_reasons:
                report.status = EMOTIONAL_ARC_STATUS_BLOCKED
                report.recommendation = EMOTIONAL_ARC_RECOMMENDATION_BLOCKED
            elif report.warnings or report.suggestions:
                report.status = EMOTIONAL_ARC_STATUS_READY_WITH_WARNINGS
                report.recommendation = EMOTIONAL_ARC_RECOMMENDATION_REVIEW
            else:
                report.status = EMOTIONAL_ARC_STATUS_READY
                report.recommendation = EMOTIONAL_ARC_RECOMMENDATION_READY

            report.enforce_review_only()
            report.refresh_metrics()
            return report

        except Exception as exc:
            failed = EmotionalArcReport(
                job_id=str(job_id) if job_id is not None else None,
                status=EMOTIONAL_ARC_STATUS_FAILED,
                arc_points=[],
                suggestions=[],
                warnings=[],
                blocking_reasons=["emotional_arc_failed"],
                recommendation=EMOTIONAL_ARC_RECOMMENDATION_FAILED,
                metadata={
                    **safe_metadata,
                    "source": self.source,
                    "error": str(exc),
                },
            )
            failed.enforce_review_only()
            return failed


def build_emotional_arc_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> EmotionalArcReport:
    return EmotionalArcBuilder().build(job, metadata=metadata)
