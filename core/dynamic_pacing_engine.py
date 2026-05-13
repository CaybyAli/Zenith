from __future__ import annotations

from typing import Any

from models.dynamic_pacing import (
    DYNAMIC_PACING_RECOMMENDATION_BLOCKED,
    DYNAMIC_PACING_RECOMMENDATION_FAILED,
    DYNAMIC_PACING_RECOMMENDATION_NO_ITEMS,
    DYNAMIC_PACING_RECOMMENDATION_READY,
    DYNAMIC_PACING_RECOMMENDATION_REVIEW,
    DYNAMIC_PACING_STATUS_BLOCKED,
    DYNAMIC_PACING_STATUS_FAILED,
    DYNAMIC_PACING_STATUS_NO_TIMELINE_ITEMS,
    DYNAMIC_PACING_STATUS_READY,
    DYNAMIC_PACING_STATUS_READY_WITH_WARNINGS,
    PACING_STATUS_CENSOR_REVIEW,
    PACING_STATUS_CONTINUITY_BLOCKED,
    PACING_STATUS_GOOD,
    PACING_STATUS_PROTECTED_PRESERVED,
    PACING_STATUS_TOO_FAST,
    PACING_STATUS_TOO_SLOW,
    PACING_STATUS_UNKNOWN,
    DynamicPacingReport,
    PacingSegment,
    PacingSuggestion,
    target_cut_rate_for_energy,
)


SOURCE_SCORE_KEYS = (
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
    "energy_score",
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

FAST_CUT_RATE_THRESHOLD = 20.0
SLOW_CUT_RATE_THRESHOLD = 10.0
MONOTONY_DURATION_TOLERANCE_SECONDS = 0.5
MONOTONY_CUT_RATE_TOLERANCE = 2.0


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

    return {
        "emotional_arc": _collect_items(
            [
                _job_value(job, "emotional_arc_points"),
                emotional_report,
                _job_value(job, "emotional_arc"),
            ],
            ("arc_points", "emotional_arc_points", "points", "items"),
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
        or f"dynamic_pacing_source_item_{index}"
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

    if protected and "protected_pacing_preserved" not in safety_flags:
        safety_flags.append("protected_pacing_preserved")
    if censor_required and "censor_pacing_review_required" not in safety_flags:
        safety_flags.append("censor_pacing_review_required")
    if continuity_blocked:
        blocking_reasons.append("continuity_pacing_blocked")
        if "continuity_pacing_blocked" not in safety_flags:
            safety_flags.append("continuity_pacing_blocked")

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

    return item_start < end_seconds and item_end > start_seconds


def _items_near_segment(
    items: list[dict[str, Any]],
    segment_data: dict[str, Any],
) -> list[dict[str, Any]]:
    source_item_id = segment_data["source_item_id"]
    source_segment_id = segment_data["source_segment_id"]
    start_seconds = segment_data["start_seconds"]
    end_seconds = segment_data["end_seconds"]

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


def _arc_phase_from_emotional_matches(matches: list[dict[str, Any]]) -> str:
    for match in matches:
        arc_phase = str(match.get("arc_phase") or "").strip()
        if arc_phase:
            return arc_phase
    return "unknown"


def _energy_score(
    segment_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
) -> tuple[float, str, list[str], dict[str, Any]]:
    flat = segment_data["flat"]
    warnings: list[str] = []
    evidence: dict[str, Any] = {
        "direct_score_count": 0,
        "matched_source_counts": {},
    }

    emotional_matches = _items_near_segment(
        related_sources.get("emotional_arc", []),
        segment_data,
    )
    emotional_scores = [
        clamp_score(match.get("actual_energy_score"))
        for match in emotional_matches
        if match.get("actual_energy_score") is not None
    ]
    emotional_scores = [score for score in emotional_scores if score > 0.0]
    evidence["matched_source_counts"]["emotional_arc"] = len(emotional_matches)

    direct_scores = _score_values_from_item(flat)
    evidence["direct_score_count"] = len(direct_scores)

    related_scores: list[float] = []
    for source_name, source_items in related_sources.items():
        if source_name == "emotional_arc":
            continue
        matches = _items_near_segment(source_items, segment_data)
        evidence["matched_source_counts"][source_name] = len(matches)
        for match in matches:
            related_scores.extend(_score_values_from_item(match))

    fallback_score, fallback_reason = _fallback_score(flat)
    if emotional_scores:
        score = _weighted_average(emotional_scores)
        score_source = "emotional_arc_points"
    else:
        scores = direct_scores + related_scores
        if scores:
            score = _weighted_average(scores)
            score_source = "scores"
        else:
            score = fallback_score
            score_source = fallback_reason
            warnings.append("using_dynamic_pacing_fallback_score")

    action = str(flat.get("action") or flat.get("final_action") or "")
    if segment_data["continuity_blocked"]:
        score = min(score, ACTION_FALLBACK_SCORES["blocked_by_continuity"])
        warnings.append("continuity_pacing_blocked")
    elif segment_data["censor_required"] or action == "censor_keep":
        score = min(max(score, ACTION_FALLBACK_SCORES["censor_keep"]), 0.75)
        warnings.append("censor_pacing_review_required")
    elif segment_data["protected"]:
        warnings.append("protected_pacing_preserved")

    evidence.update(
        {
            "emotional_score_count": len(emotional_scores),
            "related_score_count": len(related_scores),
            "fallback_score": fallback_score,
            "fallback_reason": fallback_reason,
            "score_source": score_source,
            "continuity_blocked": segment_data["continuity_blocked"],
            "censor_required": segment_data["censor_required"],
            "protected": segment_data["protected"],
        }
    )

    arc_phase = _arc_phase_from_emotional_matches(emotional_matches)
    if arc_phase == "unknown":
        arc_phase = str(flat.get("arc_phase") or "unknown")

    return round(clamp_score(score), 6), arc_phase, _unique(warnings), evidence


def _actual_cut_rate(duration_seconds: float) -> float:
    if duration_seconds <= 0.0:
        return 0.0
    return round(60.0 / duration_seconds, 6)


def _pacing_status(
    segment_data: dict[str, Any],
    actual_cut_rate: float,
    target_min: float,
    target_max: float,
) -> str:
    if segment_data["continuity_blocked"]:
        return PACING_STATUS_CONTINUITY_BLOCKED
    if segment_data["censor_required"]:
        return PACING_STATUS_CENSOR_REVIEW
    if segment_data["protected"]:
        return PACING_STATUS_PROTECTED_PRESERVED
    if actual_cut_rate <= 0.0:
        return PACING_STATUS_UNKNOWN
    if actual_cut_rate < target_min:
        return PACING_STATUS_TOO_SLOW
    if actual_cut_rate > target_max:
        return PACING_STATUS_TOO_FAST
    return PACING_STATUS_GOOD


def _build_segment(
    segment_data: dict[str, Any],
    index: int,
    related_sources: dict[str, list[dict[str, Any]]],
) -> PacingSegment:
    energy_score, arc_phase, score_warnings, evidence = _energy_score(
        segment_data,
        related_sources,
    )
    target_min, target_max = target_cut_rate_for_energy(energy_score)
    actual_rate = _actual_cut_rate(float(segment_data["duration_seconds"] or 0.0))
    status = _pacing_status(segment_data, actual_rate, target_min, target_max)
    warnings = _unique(
        list(segment_data["warnings"])
        + list(score_warnings)
        + list(segment_data["blocking_reasons"])
    )

    segment = PacingSegment(
        segment_id=f"pacing_segment_{index}_{segment_data['source_item_id']}",
        source_item_id=segment_data["source_item_id"],
        source_segment_id=segment_data["source_segment_id"],
        start_seconds=(
            round(segment_data["start_seconds"], 3)
            if segment_data["start_seconds"] is not None
            else None
        ),
        end_seconds=(
            round(segment_data["end_seconds"], 3)
            if segment_data["end_seconds"] is not None
            else None
        ),
        duration_seconds=round(float(segment_data["duration_seconds"] or 0.0), 3),
        energy_score=energy_score,
        arc_phase=arc_phase,
        target_cut_rate_min=target_min,
        target_cut_rate_max=target_max,
        actual_cut_rate=actual_rate,
        pacing_status=status,
        review_required=True,
        warnings=warnings,
        metadata={
            "source_label": segment_data["source_label"],
            "action": segment_data["action"],
            "protection_status": segment_data["protection_status"],
            "protected": segment_data["protected"],
            "censor_required": segment_data["censor_required"],
            "continuity_blocked": segment_data["continuity_blocked"],
            "safety_flags": list(segment_data["safety_flags"]),
            "score_evidence": evidence,
            "source_metadata": _source_metadata(segment_data["flat"]),
        },
    )
    segment.enforce_review_only()
    return segment


def _suggestion(
    suggestion_type: str,
    reason: str,
    severity: str = "medium",
    source_item_id: str | None = None,
    source_segment_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> PacingSuggestion:
    suggestion = PacingSuggestion(
        suggestion_id=(
            f"pacing_suggestion_{suggestion_type}_"
            f"{source_item_id or 'global'}"
        ),
        suggestion_type=suggestion_type,
        source_item_id=source_item_id,
        source_segment_id=source_segment_id,
        severity=severity,
        reason=reason,
        review_required=True,
        can_auto_apply=False,
        metadata=dict(metadata or {}),
    )
    suggestion.enforce_review_only()
    return suggestion


def _segment_suggestions(segment: PacingSegment) -> list[PacingSuggestion]:
    metadata = {
        "segment_id": segment.segment_id,
        "start_seconds": segment.start_seconds,
        "end_seconds": segment.end_seconds,
        "duration_seconds": segment.duration_seconds,
        "energy_score": segment.energy_score,
        "target_cut_rate_min": segment.target_cut_rate_min,
        "target_cut_rate_max": segment.target_cut_rate_max,
        "actual_cut_rate": segment.actual_cut_rate,
        "arc_phase": segment.arc_phase,
    }
    suggestions: list[PacingSuggestion] = []

    if segment.pacing_status == PACING_STATUS_TOO_SLOW:
        severity = "high" if segment.energy_score >= 0.80 else "medium"
        suggestions.append(
            _suggestion(
                "pacing_too_slow_for_energy",
                "Actual cut rate is below the energy-based review range.",
                severity=severity,
                source_item_id=segment.source_item_id,
                source_segment_id=segment.source_segment_id,
                metadata=metadata,
            )
        )
        suggestions.append(
            _suggestion(
                "clip_too_long_review",
                "Clip duration makes the review cut rate slower than target.",
                severity=severity,
                source_item_id=segment.source_item_id,
                source_segment_id=segment.source_segment_id,
                metadata=metadata,
            )
        )
    elif segment.pacing_status == PACING_STATUS_TOO_FAST:
        severity = "high" if segment.energy_score < 0.50 else "medium"
        suggestions.append(
            _suggestion(
                "pacing_too_fast_for_energy",
                "Actual cut rate is above the energy-based review range.",
                severity=severity,
                source_item_id=segment.source_item_id,
                source_segment_id=segment.source_segment_id,
                metadata=metadata,
            )
        )
        suggestions.append(
            _suggestion(
                "clip_too_short_review",
                "Clip duration makes the review cut rate faster than target.",
                severity=severity,
                source_item_id=segment.source_item_id,
                source_segment_id=segment.source_segment_id,
                metadata=metadata,
            )
        )
    elif segment.pacing_status == PACING_STATUS_UNKNOWN:
        suggestions.append(
            _suggestion(
                "pacing_unknown_review",
                "Clip duration is unavailable for cut-rate review.",
                severity="medium",
                source_item_id=segment.source_item_id,
                source_segment_id=segment.source_segment_id,
                metadata=metadata,
            )
        )
    elif segment.pacing_status == PACING_STATUS_CENSOR_REVIEW:
        suggestions.append(
            _suggestion(
                "censor_pacing_review_required",
                "Censor-protected item is preserved for pacing review only.",
                severity="high",
                source_item_id=segment.source_item_id,
                source_segment_id=segment.source_segment_id,
                metadata=metadata,
            )
        )
    elif segment.pacing_status == PACING_STATUS_PROTECTED_PRESERVED:
        suggestions.append(
            _suggestion(
                "protected_pacing_preserved",
                "Protected item is preserved and only marked for pacing review.",
                severity="medium",
                source_item_id=segment.source_item_id,
                source_segment_id=segment.source_segment_id,
                metadata=metadata,
            )
        )
    elif segment.pacing_status == PACING_STATUS_CONTINUITY_BLOCKED:
        suggestions.append(
            _suggestion(
                "continuity_pacing_blocked",
                "Continuity-blocked item prevents pacing approval.",
                severity="blocking",
                source_item_id=segment.source_item_id,
                source_segment_id=segment.source_segment_id,
                metadata=metadata,
            )
        )

    return suggestions


def _run_lengths(segments: list[PacingSegment]) -> tuple[int, int]:
    max_fast = 0
    max_slow = 0
    current_fast = 0
    current_slow = 0

    for segment in segments:
        actual_rate = float(segment.actual_cut_rate or 0.0)
        if actual_rate >= FAST_CUT_RATE_THRESHOLD:
            current_fast += 1
        else:
            current_fast = 0
        if 0.0 < actual_rate <= SLOW_CUT_RATE_THRESHOLD:
            current_slow += 1
        else:
            current_slow = 0
        max_fast = max(max_fast, current_fast)
        max_slow = max(max_slow, current_slow)

    return max_fast, max_slow


def _first_fast_run_end_segment(
    segments: list[PacingSegment],
    required_count: int = 3,
) -> PacingSegment | None:
    current_fast = 0
    for segment in segments:
        if float(segment.actual_cut_rate or 0.0) >= FAST_CUT_RATE_THRESHOLD:
            current_fast += 1
        else:
            current_fast = 0
        if current_fast >= required_count:
            return segment
    return None


def _monotony_score(segments: list[PacingSegment]) -> float:
    scorable = [
        segment
        for segment in segments
        if float(segment.duration_seconds or 0.0) > 0.0
        and float(segment.actual_cut_rate or 0.0) > 0.0
    ]
    if len(scorable) < 4:
        return 0.0

    similar_pairs = 0
    for previous, current in zip(scorable, scorable[1:]):
        duration_delta = abs(
            float(previous.duration_seconds or 0.0)
            - float(current.duration_seconds or 0.0)
        )
        cut_rate_delta = abs(
            float(previous.actual_cut_rate or 0.0)
            - float(current.actual_cut_rate or 0.0)
        )
        if (
            duration_delta <= MONOTONY_DURATION_TOLERANCE_SECONDS
            and cut_rate_delta <= MONOTONY_CUT_RATE_TOLERANCE
        ):
            similar_pairs += 1

    return round(similar_pairs / max(len(scorable) - 1, 1), 6)


def _global_blocking_reasons(job: Any) -> list[str]:
    blocking_reasons: list[str] = []
    for key in (
        "review_timeline_dashboard_blocking_errors",
        "timeline_safety_blocking_errors",
        "timeline_approval_blocking_reasons",
        "dynamic_pacing_blocking_reasons",
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


def _build_review_suggestions(
    segments: list[PacingSegment],
    fast_run_count: int,
    monotony_score: float,
) -> list[PacingSuggestion]:
    suggestions: list[PacingSuggestion] = []
    for segment in segments:
        suggestions.extend(_segment_suggestions(segment))

    if fast_run_count >= 3:
        end_segment = _first_fast_run_end_segment(segments, required_count=3)
        suggestions.append(
            _suggestion(
                "missing_breathing_room",
                "Three or more fast-cut clips appear consecutively.",
                severity="medium",
                source_item_id=(
                    end_segment.source_item_id if end_segment is not None else None
                ),
                source_segment_id=(
                    end_segment.source_segment_id if end_segment is not None else None
                ),
                metadata={
                    "fast_run_count": fast_run_count,
                    "threshold": 3,
                    "review_only": True,
                },
            )
        )

    if monotony_score >= 0.75:
        suggestions.append(
            _suggestion(
                "monotone_pacing_risk",
                "Several adjacent clips have similar duration and cut rate.",
                severity="medium",
                metadata={
                    "monotony_score": monotony_score,
                    "duration_tolerance_seconds": (
                        MONOTONY_DURATION_TOLERANCE_SECONDS
                    ),
                    "cut_rate_tolerance": MONOTONY_CUT_RATE_TOLERANCE,
                },
            )
        )

    return suggestions


def _breathing_room_score(fast_run_count: int, segment_count: int) -> float:
    if segment_count == 0:
        return 0.0
    if fast_run_count < 3:
        return 1.0
    penalty = min(1.0, (fast_run_count - 2) / 3.0)
    return round(1.0 - penalty, 6)


class DynamicPacingEngine:
    source = "dynamic_pacing_engine"

    def build(
        self,
        job: Any,
        metadata: dict[str, Any] | None = None,
    ) -> DynamicPacingReport:
        safe_metadata = dict(metadata or {})
        job_id = _job_value(job, "job_id") or _job_value(job, "id")

        try:
            raw_items, source_label = _extract_timeline_items(job)
            related_sources = _extract_related_sources(job)
            global_blockers = _global_blocking_reasons(job)

            if not raw_items:
                report = DynamicPacingReport(
                    job_id=str(job_id) if job_id is not None else None,
                    status=DYNAMIC_PACING_STATUS_NO_TIMELINE_ITEMS,
                    pacing_segments=[],
                    suggestions=[],
                    warnings=["no_review_timeline_items_available"],
                    blocking_reasons=[],
                    recommendation=DYNAMIC_PACING_RECOMMENDATION_NO_ITEMS,
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
            pacing_segments = [
                _build_segment(item, index, related_sources)
                for index, item in enumerate(normalized_items)
            ]

            fast_run_count, slow_run_count = _run_lengths(pacing_segments)
            monotony_score = _monotony_score(pacing_segments)
            breathing_room_score = _breathing_room_score(
                fast_run_count,
                len(pacing_segments),
            )
            suggestions = _build_review_suggestions(
                pacing_segments,
                fast_run_count,
                monotony_score,
            )

            warnings = _unique(
                [
                    warning
                    for segment in pacing_segments
                    for warning in list(segment.warnings or [])
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

            report = DynamicPacingReport(
                job_id=str(job_id) if job_id is not None else None,
                status=DYNAMIC_PACING_STATUS_READY,
                pacing_segments=pacing_segments,
                suggestions=suggestions,
                monotony_score=monotony_score,
                breathing_room_score=breathing_room_score,
                fast_run_count=fast_run_count,
                slow_run_count=slow_run_count,
                warnings=warnings,
                blocking_reasons=blocking_reasons,
                recommendation=DYNAMIC_PACING_RECOMMENDATION_READY,
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
                report.status = DYNAMIC_PACING_STATUS_BLOCKED
                report.recommendation = DYNAMIC_PACING_RECOMMENDATION_BLOCKED
            elif report.warnings or report.suggestions:
                report.status = DYNAMIC_PACING_STATUS_READY_WITH_WARNINGS
                report.recommendation = DYNAMIC_PACING_RECOMMENDATION_REVIEW
            else:
                report.status = DYNAMIC_PACING_STATUS_READY
                report.recommendation = DYNAMIC_PACING_RECOMMENDATION_READY

            report.enforce_review_only()
            report.refresh_metrics()
            return report

        except Exception as exc:
            failed = DynamicPacingReport(
                job_id=str(job_id) if job_id is not None else None,
                status=DYNAMIC_PACING_STATUS_FAILED,
                pacing_segments=[],
                suggestions=[],
                warnings=[],
                blocking_reasons=["dynamic_pacing_failed"],
                recommendation=DYNAMIC_PACING_RECOMMENDATION_FAILED,
                metadata={
                    **safe_metadata,
                    "source": self.source,
                    "error": str(exc),
                },
            )
            failed.enforce_review_only()
            return failed


def build_dynamic_pacing_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> DynamicPacingReport:
    return DynamicPacingEngine().build(job, metadata=metadata)
