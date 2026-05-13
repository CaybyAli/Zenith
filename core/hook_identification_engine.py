from __future__ import annotations

from typing import Any

from models.hook_identification import (
    HOOK_IDENTIFICATION_RECOMMENDATION_BLOCKED,
    HOOK_IDENTIFICATION_RECOMMENDATION_FAILED,
    HOOK_IDENTIFICATION_RECOMMENDATION_NO_CANDIDATE,
    HOOK_IDENTIFICATION_RECOMMENDATION_REVIEW,
    HOOK_IDENTIFICATION_STATUS_BLOCKED,
    HOOK_IDENTIFICATION_STATUS_CANDIDATE_FOUND,
    HOOK_IDENTIFICATION_STATUS_FAILED,
    HOOK_IDENTIFICATION_STATUS_NO_SAFE_CANDIDATE,
    HookCandidate,
    HookIdentificationReport,
)


IDEAL_HOOK_MIN_SECONDS = 3.0
IDEAL_HOOK_MAX_SECONDS = 8.0
DEFAULT_MIN_HOOK_SCORE = 0.55


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
        "scene_change_result",
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


def _extract_review_layer_items(job: Any) -> tuple[list[dict[str, Any]], str]:
    dashboard_report = _safe_dict(
        _job_value(job, "review_timeline_dashboard_package_report"),
    )
    dashboard_package = _safe_dict(
        _job_value(job, "review_timeline_dashboard_package"),
    )

    sources: list[tuple[str, Any, tuple[str, ...]]] = [
        (
            "review_timeline_dashboard_package_report",
            dashboard_report,
            ("item_cards", "timeline_items"),
        ),
        (
            "review_timeline_dashboard_package",
            dashboard_package,
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
        (
            "final_cut_list_items",
            _job_value(job, "final_cut_list_items"),
            ("final_items", "final_cut_list_items", "items"),
        ),
        (
            "final_cut_list_report",
            _job_value(job, "final_cut_list_report"),
            ("final_items", "final_cut_list_items", "items"),
        ),
    ]

    for label, source, keys in sources:
        items = _items_from_container(source, keys)
        if items:
            return items, label

    return [], "none"


def _extract_related_sources(job: Any) -> dict[str, list[dict[str, Any]]]:
    return {
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
                _job_value(job, "content_value_segment_scores"),
                _job_value(job, "content_value_report"),
            ],
            ("segment_scores", "content_value_segment_scores", "items"),
        ),
        "keyword": _collect_items(
            [
                _job_value(job, "keyword_emotion_segment_scores"),
                _job_value(job, "keyword_emotion_matches"),
                _job_value(job, "keyword_emotion_report"),
            ],
            ("segment_scores", "matches", "keyword_emotion_segment_scores"),
        ),
        "visual": _collect_items(
            [
                _job_value(job, "visual_energy_segments"),
                _job_value(job, "visual_energy_report"),
            ],
            ("segments", "visual_energy_segments", "items"),
        ),
        "face": _collect_items(
            [
                _job_value(job, "face_reaction_segments"),
                _job_value(job, "face_reaction_report"),
            ],
            ("segments", "face_reaction_segments", "items"),
        ),
        "motion": _collect_items(
            [
                _job_value(job, "motion_analysis_segments"),
                _job_value(job, "motion_analysis_report"),
            ],
            ("segments", "motion_analysis_segments", "items"),
        ),
        "murch": _collect_items(
            [
                _job_value(job, "murch_scoring_segment_scores"),
                _job_value(job, "murch_scoring_report"),
            ],
            ("segment_scores", "murch_scoring_segment_scores", "items"),
        ),
        "scene": _collect_items(
            [
                _job_value(job, "scene_changes"),
                _job_value(job, "scene_change_report"),
            ],
            ("scene_changes", "changes", "items"),
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
    nested = _safe_dict(metadata.get("source_metadata"))
    decision_basis = _safe_dict(metadata.get("decision_basis"))
    evidence = _safe_dict(metadata.get("evidence"))
    return {
        **nested,
        **decision_basis,
        **evidence,
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


def _normalize_source_item(
    item: dict[str, Any],
    index: int,
    source_label: str,
) -> dict[str, Any]:
    flat = _flatten_item_data(item)

    source_item_id = str(
        flat.get("item_id")
        or flat.get("timeline_item_id")
        or flat.get("final_item_id")
        or flat.get("source_final_item_id")
        or flat.get("source_item_id")
        or flat.get("id")
        or f"hook_source_item_{index}"
    )
    source_segment_id = flat.get("source_segment_id") or flat.get("segment_id")

    timeline_start = _safe_optional_float(flat.get("start_seconds"))
    timeline_end = _safe_optional_float(flat.get("end_seconds"))
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

    if protected and "protected_review_only" not in safety_flags:
        safety_flags.append("protected_review_only")
    if censor_required and "censor_segment_preserved_review_only" not in safety_flags:
        safety_flags.append("censor_segment_preserved_review_only")
    if continuity_blocked and "continuity_blocked_review_only" not in safety_flags:
        safety_flags.append("continuity_blocked_review_only")

    return {
        "source_item_id": source_item_id,
        "source_segment_id": str(source_segment_id) if source_segment_id is not None else None,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": duration_seconds,
        "timeline_start_seconds": timeline_start,
        "timeline_end_seconds": timeline_end,
        "flat": flat,
        "source_label": source_label,
        "protected": protected,
        "censor_required": censor_required,
        "continuity_blocked": continuity_blocked,
        "safety_flags": safety_flags,
        "warnings": [str(value) for value in _safe_list(flat.get("warnings"))],
        "blocking_reasons": [
            str(value)
            for value in (
                _safe_list(flat.get("blocking_errors"))
                + _safe_list(flat.get("blocking_reasons"))
            )
        ],
    }


def _same_segment(item: dict[str, Any], segment_id: str | None) -> bool:
    if not segment_id:
        return False
    for key in (
        "segment_id",
        "source_segment_id",
        "source_item_id",
        "item_id",
        "timeline_item_id",
        "id",
    ):
        if str(item.get(key) or "") == str(segment_id):
            return True
    metadata = _safe_dict(item.get("metadata"))
    return str(metadata.get("source_segment_id") or "") == str(segment_id)


def _time_overlaps(
    item: dict[str, Any],
    start_seconds: float | None,
    end_seconds: float | None,
) -> bool:
    if start_seconds is None or end_seconds is None:
        return False

    item_start = _safe_optional_float(item.get("start_seconds"))
    item_end = _safe_optional_float(item.get("end_seconds"))

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


def _items_near_candidate(
    items: list[dict[str, Any]],
    candidate_data: dict[str, Any],
) -> list[dict[str, Any]]:
    start_seconds = candidate_data["start_seconds"]
    end_seconds = candidate_data["end_seconds"]
    segment_id = candidate_data["source_segment_id"]
    source_item_id = candidate_data["source_item_id"]

    matches = [
        item
        for item in items
        if _same_segment(item, segment_id)
        or _same_segment(item, source_item_id)
        or _time_overlaps(item, start_seconds, end_seconds)
    ]
    return matches


def _max_score(item: dict[str, Any], keys: tuple[str, ...]) -> float:
    scores = [clamp_score(item.get(key)) for key in keys if item.get(key) is not None]
    return max(scores) if scores else 0.0


def _category_score(item: dict[str, Any], category: str) -> float:
    categories = _safe_dict(item.get("categories"))
    return clamp_score(
        categories.get(category)
        if category in categories
        else item.get(f"{category}_score"),
    )


def _source_type(item: dict[str, Any]) -> str:
    return str(item.get("source") or _safe_dict(item.get("metadata")).get("original_source") or "")


def _score_energy(
    candidate_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
) -> tuple[float, dict[str, Any]]:
    flat = candidate_data["flat"]
    scores: list[float] = [
        _max_score(
            flat,
            (
                "energy_peak_score",
                "energy_score",
                "peak_score",
                "audio_energy",
                "visual_energy",
                "motion_energy",
            ),
        )
    ]
    evidence: dict[str, Any] = {}

    energy_items = _items_near_candidate(related_sources["energy"], candidate_data)
    for item in energy_items:
        score = _max_score(
            item,
            ("peak_score", "energy_score", "signal_score", "confidence", "beat_strength"),
        )
        if str(item.get("peak_type") or "") in {"combined", "high_energy", "local_maximum"}:
            score = max(score, 0.85)
        if _safe_float(item.get("rise_delta"), 0.0) >= 0.25:
            score = max(score, 0.7)
        scores.append(score)

    visual_items = _items_near_candidate(related_sources["visual"], candidate_data)
    for item in visual_items:
        score = _max_score(
            item,
            (
                "max_visual_energy_score",
                "avg_visual_energy_score",
                "visual_energy_score",
                "combined_video_score",
                "signal_score",
                "confidence",
            ),
        )
        if str(item.get("classification") or "") in {
            "high_visual_energy",
            "peak_visual_energy",
        }:
            score = max(score, 0.8)
        scores.append(score)

    motion_items = _items_near_candidate(related_sources["motion"], candidate_data)
    for item in motion_items:
        score = _max_score(
            item,
            ("motion_score", "avg_motion_score", "max_motion_score", "signal_score"),
        )
        if str(item.get("classification") or item.get("motion_classification") or "") in {
            "high_motion",
            "high_motion_segment",
        }:
            score = max(score, 0.75)
        scores.append(score)

    unified_items = _items_near_candidate(related_sources["unified"], candidate_data)
    for item in unified_items:
        if _source_type(item) in {"energy_peak", "visual_energy", "motion_analysis"}:
            scores.append(clamp_score(item.get("signal_score")))

    content_fallback = _max_score(
        flat,
        ("content_value_score", "final_score", "murch_score"),
    )
    if not any(score > 0.0 for score in scores) and content_fallback > 0.0:
        scores.append(content_fallback * 0.5)
        evidence["fallback"] = "content_value_energy_fallback"
    if bool(flat.get("high_value")) or bool(flat.get("is_high_value")):
        scores.append(0.45)

    evidence.update(
        {
            "energy_item_count": len(energy_items),
            "visual_item_count": len(visual_items),
            "motion_item_count": len(motion_items),
        }
    )
    return clamp_score(max(scores) if scores else 0.0), evidence


def _score_surprise(
    candidate_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
) -> tuple[float, dict[str, Any]]:
    flat = candidate_data["flat"]
    scores: list[float] = [
        _max_score(
            flat,
            (
                "surprise_factor_score",
                "surprise_score",
                "shock_score",
                "question_score",
                "laugh_score",
            ),
        )
    ]
    evidence: dict[str, Any] = {}

    keyword_items = _items_near_candidate(related_sources["keyword"], candidate_data)
    for item in keyword_items:
        dominant = str(item.get("dominant_category") or item.get("category") or "")
        category_scores = [
            _category_score(item, "shock"),
            _category_score(item, "question"),
            _category_score(item, "laugh"),
            _category_score(item, "hype"),
        ]
        score = max(category_scores + [_max_score(item, ("overall_keyword_score", "confidence"))])
        if dominant in {"shock", "question", "laugh", "hype"}:
            score = max(score, 0.72)
        scores.append(score)

    face_items = _items_near_candidate(related_sources["face"], candidate_data)
    for item in face_items:
        reaction_type = str(item.get("reaction_type") or item.get("classification") or "")
        score = _max_score(
            item,
            ("max_reaction_score", "avg_reaction_score", "reaction_score", "confidence"),
        )
        if reaction_type in {
            "shock_candidate",
            "laugh_candidate",
            "mouth_open_candidate",
            "hype_candidate",
            "expressive_reaction_candidate",
            "shock",
            "laugh",
            "surprise",
        }:
            score = max(score, 0.78)
        scores.append(score)

    scene_items = _items_near_candidate(related_sources["scene"], candidate_data)
    for item in scene_items:
        score = _max_score(item, ("scene_change_score", "score", "confidence"))
        if str(item.get("change_type") or item.get("scene_change_type") or "") in {
            "hard",
            "hard_cut",
            "major_change",
        }:
            score = max(score, 0.65)
        scores.append(score)

    energy_items = _items_near_candidate(related_sources["energy"], candidate_data)
    for item in energy_items:
        if _safe_float(item.get("rise_delta"), 0.0) >= 0.25:
            scores.append(min(1.0, 0.55 + _safe_float(item.get("rise_delta"), 0.0)))

    unified_items = _items_near_candidate(related_sources["unified"], candidate_data)
    for item in unified_items:
        signal_type = str(item.get("signal_type") or "")
        if any(token in signal_type for token in ("shock", "question", "surprise", "scene")):
            scores.append(clamp_score(item.get("signal_score")))

    content_fallback = _max_score(flat, ("content_value_score", "final_score"))
    if not any(score > 0.0 for score in scores) and content_fallback > 0.0:
        scores.append(content_fallback * 0.35)
        evidence["fallback"] = "content_value_surprise_fallback"
    if bool(flat.get("high_value")) or bool(flat.get("is_high_value")):
        scores.append(0.35)

    evidence.update(
        {
            "keyword_item_count": len(keyword_items),
            "face_item_count": len(face_items),
            "scene_item_count": len(scene_items),
        }
    )
    return clamp_score(max(scores) if scores else 0.0), evidence


def _score_emotional_value(
    candidate_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
) -> tuple[float, float, dict[str, Any]]:
    flat = candidate_data["flat"]
    scores: list[float] = [
        _max_score(
            flat,
            (
                "emotional_value_score",
                "emotion_score",
                "content_value_score",
                "final_score",
                "murch_score",
                "reaction_score",
            ),
        )
    ]
    content_scores: list[float] = [
        _max_score(flat, ("content_value_score", "final_score", "murch_score"))
    ]
    evidence: dict[str, Any] = {}

    keyword_items = _items_near_candidate(related_sources["keyword"], candidate_data)
    for item in keyword_items:
        score = _max_score(
            item,
            (
                "emotion_score",
                "overall_keyword_score",
                "hype_score",
                "frustration_score",
                "shock_score",
                "laugh_score",
                "question_score",
                "confidence",
            ),
        )
        scores.append(score)

    content_items = _items_near_candidate(related_sources["content_value"], candidate_data)
    for item in content_items:
        score = _max_score(
            item,
            ("final_score", "content_value_score", "speech_value_score", "keyword_value_score"),
        )
        scores.append(score)
        content_scores.append(score)
        if bool(item.get("is_high_value")) or str(item.get("value_tier") or "") == "high":
            scores.append(max(score, 0.78))
            content_scores.append(max(score, 0.78))

    murch_items = _items_near_candidate(related_sources["murch"], candidate_data)
    for item in murch_items:
        score = _max_score(
            item,
            ("murch_score", "final_score", "score", "confidence"),
        )
        scores.append(score)
        content_scores.append(score)

    face_items = _items_near_candidate(related_sources["face"], candidate_data)
    for item in face_items:
        scores.append(
            _max_score(
                item,
                ("max_reaction_score", "avg_reaction_score", "reaction_score", "confidence"),
            )
        )

    unified_items = _items_near_candidate(related_sources["unified"], candidate_data)
    for item in unified_items:
        if _source_type(item) in {
            "keyword_emotion",
            "content_value",
            "murch_scoring",
            "face_reaction",
        }:
            score = clamp_score(item.get("signal_score"))
            scores.append(score)
            if _source_type(item) in {"content_value", "murch_scoring"}:
                content_scores.append(score)

    if bool(flat.get("high_value")) or bool(flat.get("is_high_value")):
        scores.append(0.72)
        content_scores.append(0.72)

    evidence.update(
        {
            "keyword_item_count": len(keyword_items),
            "content_value_item_count": len(content_items),
            "murch_item_count": len(murch_items),
            "face_item_count": len(face_items),
        }
    )
    return (
        clamp_score(max(scores) if scores else 0.0),
        clamp_score(max(content_scores) if content_scores else 0.0),
        evidence,
    )


def _duration_preference(candidate: HookCandidate) -> int:
    duration = float(candidate.duration_seconds or 0.0)
    if IDEAL_HOOK_MIN_SECONDS <= duration <= IDEAL_HOOK_MAX_SECONDS:
        return 1
    return 0


def _build_candidate(
    candidate_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
    index: int,
) -> HookCandidate:
    warnings = list(candidate_data["warnings"])
    blocking_reasons = list(candidate_data["blocking_reasons"])
    safety_flags = list(candidate_data["safety_flags"])

    if candidate_data["start_seconds"] is None or candidate_data["end_seconds"] is None:
        warnings.append("hook_candidate_missing_timing")

    duration = float(candidate_data["duration_seconds"] or 0.0)
    if duration < IDEAL_HOOK_MIN_SECONDS:
        warnings.append("hook_duration_too_short_preferred_3_to_8_seconds")
    elif duration > IDEAL_HOOK_MAX_SECONDS:
        warnings.append("hook_duration_too_long_preferred_3_to_8_seconds")

    if candidate_data["protected"]:
        safety_flags.append("protected_context_preserved")
    if candidate_data["censor_required"]:
        safety_flags.append("censor_segment_preserved")
    if candidate_data["continuity_blocked"]:
        blocking_reasons.append("continuity_blocked_review_required")

    energy_peak_score, energy_evidence = _score_energy(candidate_data, related_sources)
    surprise_factor_score, surprise_evidence = _score_surprise(
        candidate_data,
        related_sources,
    )
    emotional_value_score, content_value_score, emotional_evidence = (
        _score_emotional_value(candidate_data, related_sources)
    )

    missing_components: list[str] = []
    if energy_peak_score <= 0.0:
        missing_components.append("energy_peak")
    if surprise_factor_score <= 0.0:
        missing_components.append("surprise_factor")
    if emotional_value_score <= 0.0:
        missing_components.append("emotional_value")

    if missing_components:
        warnings.append("using_fallback_hook_scoring")
        for component in missing_components:
            warnings.append(f"missing_{component}_data")

    hook_score = clamp_score(
        energy_peak_score * 0.40
        + surprise_factor_score * 0.30
        + emotional_value_score * 0.30
    )

    available_component_count = sum(
        1
        for score in (
            energy_peak_score,
            surprise_factor_score,
            emotional_value_score,
        )
        if score > 0.0
    )
    confidence = clamp_score(
        hook_score * 0.70 + (available_component_count / 3.0) * 0.30,
    )
    if blocking_reasons:
        confidence = min(confidence, 0.65)

    if hook_score >= 0.75:
        reason = "strong_hook_candidate_review_only"
    elif hook_score >= DEFAULT_MIN_HOOK_SCORE:
        reason = "hook_candidate_requires_review"
    else:
        reason = "low_hook_score_review_only"

    candidate = HookCandidate(
        candidate_id=f"hook_candidate_{index}_{candidate_data['source_item_id']}",
        source_item_id=candidate_data["source_item_id"],
        source_segment_id=candidate_data["source_segment_id"],
        start_seconds=(
            round(candidate_data["start_seconds"], 3)
            if candidate_data["start_seconds"] is not None
            else None
        ),
        end_seconds=(
            round(candidate_data["end_seconds"], 3)
            if candidate_data["end_seconds"] is not None
            else None
        ),
        duration_seconds=round(duration, 3),
        hook_score=round(hook_score, 6),
        energy_peak_score=round(energy_peak_score, 6),
        surprise_factor_score=round(surprise_factor_score, 6),
        emotional_value_score=round(emotional_value_score, 6),
        content_value_score=round(content_value_score, 6),
        confidence=round(confidence, 6),
        reason=reason,
        review_required=True,
        review_only=True,
        safety_flags=_unique(safety_flags),
        warnings=_unique(warnings),
        blocking_reasons=_unique(blocking_reasons),
        metadata={
            "source_label": candidate_data["source_label"],
            "timeline_start_seconds": candidate_data["timeline_start_seconds"],
            "timeline_end_seconds": candidate_data["timeline_end_seconds"],
            "preferred_duration_min_seconds": IDEAL_HOOK_MIN_SECONDS,
            "preferred_duration_max_seconds": IDEAL_HOOK_MAX_SECONDS,
            "duration_preferred": _duration_preference(
                HookCandidate(duration_seconds=duration),
            )
            == 1,
            "score_formula": {
                "energy_peak_weight": 0.40,
                "surprise_factor_weight": 0.30,
                "emotional_value_weight": 0.30,
            },
            "score_evidence": {
                "energy": energy_evidence,
                "surprise": surprise_evidence,
                "emotional": emotional_evidence,
            },
            "source_metadata": _source_metadata(candidate_data["flat"]),
        },
    )
    candidate.enforce_review_only()
    return candidate


def _global_blocking_reasons(job: Any) -> list[str]:
    blocking_reasons: list[str] = []
    blocking_reasons.extend(
        str(value)
        for value in _safe_list(_job_value(job, "review_timeline_dashboard_blocking_errors"))
    )
    blocking_reasons.extend(
        str(value)
        for value in _safe_list(_job_value(job, "timeline_safety_blocking_errors"))
    )
    blocking_reasons.extend(
        str(value)
        for value in _safe_list(_job_value(job, "timeline_approval_blocking_reasons"))
    )

    dashboard_package = _safe_dict(_job_value(job, "review_timeline_dashboard_package"))
    blocking_reasons.extend(
        str(value)
        for value in _safe_list(dashboard_package.get("blocking_errors"))
    )

    dashboard_report = _safe_dict(_job_value(job, "review_timeline_dashboard_package_report"))
    report_package = _safe_dict(dashboard_report.get("dashboard_package"))
    blocking_reasons.extend(
        str(value)
        for value in _safe_list(report_package.get("blocking_errors"))
    )

    dashboard_status = str(
        _job_value(job, "review_timeline_dashboard_package_status") or ""
    )
    if dashboard_status == "blocked":
        blocking_reasons.append("review_timeline_dashboard_blocked")

    safety_status = str(_job_value(job, "timeline_safety_validation_status") or "")
    if safety_status in {"blocked", "failed"}:
        blocking_reasons.append(f"timeline_safety_{safety_status}")

    return _unique(blocking_reasons)


class HookIdentificationEngine:
    source = "hook_identification_engine"

    def identify(
        self,
        job: Any,
        metadata: dict[str, Any] | None = None,
        min_hook_score: float = DEFAULT_MIN_HOOK_SCORE,
    ) -> HookIdentificationReport:
        safe_metadata = dict(metadata or {})
        job_id = _job_value(job, "job_id") or _job_value(job, "id")
        report = HookIdentificationReport(
            job_id=str(job_id) if job_id is not None else None,
            metadata={
                **safe_metadata,
                "source": self.source,
                "min_hook_score": min_hook_score,
            },
        )

        try:
            raw_items, source_label = _extract_review_layer_items(job)
            related_sources = _extract_related_sources(job)
            global_blockers = _global_blocking_reasons(job)

            warnings: list[str] = []
            if not raw_items:
                warnings.append("no_review_timeline_items_available")

            candidates: list[HookCandidate] = []
            for index, raw_item in enumerate(raw_items):
                candidate_data = _normalize_source_item(
                    raw_item,
                    index=index,
                    source_label=source_label,
                )
                candidates.append(
                    _build_candidate(
                        candidate_data,
                        related_sources=related_sources,
                        index=index,
                    )
                )

            candidates.sort(
                key=lambda candidate: (
                    float(candidate.hook_score or 0.0),
                    _duration_preference(candidate),
                    float(candidate.confidence or 0.0),
                ),
                reverse=True,
            )

            safe_candidates = [
                candidate
                for candidate in candidates
                if not candidate.blocking_reasons
                and float(candidate.hook_score or 0.0) >= min_hook_score
            ]

            if global_blockers:
                selected_candidate = None
                status = HOOK_IDENTIFICATION_STATUS_BLOCKED
                recommendation = HOOK_IDENTIFICATION_RECOMMENDATION_BLOCKED
            elif safe_candidates:
                selected_candidate = safe_candidates[0]
                status = HOOK_IDENTIFICATION_STATUS_CANDIDATE_FOUND
                recommendation = HOOK_IDENTIFICATION_RECOMMENDATION_REVIEW
            else:
                selected_candidate = None
                status = HOOK_IDENTIFICATION_STATUS_NO_SAFE_CANDIDATE
                recommendation = HOOK_IDENTIFICATION_RECOMMENDATION_NO_CANDIDATE
                if candidates and not any(
                    float(candidate.hook_score or 0.0) >= min_hook_score
                    for candidate in candidates
                ):
                    global_blockers.append("no_candidate_above_minimum_hook_score")
                if candidates and all(candidate.blocking_reasons for candidate in candidates):
                    global_blockers.append("all_hook_candidates_blocked")

            for candidate in candidates:
                warnings.extend(candidate.warnings)

            report.status = status
            report.selected_candidate = selected_candidate
            report.candidates = candidates
            report.warnings = _unique(warnings)
            report.blocking_reasons = _unique(global_blockers)
            report.recommendation = recommendation
            report.metadata.update(
                {
                    "candidate_source": source_label,
                    "related_source_counts": {
                        key: len(value)
                        for key, value in related_sources.items()
                    },
                }
            )
            report.enforce_review_only()
            report.refresh_counts()
            return report

        except Exception as exc:
            failed = HookIdentificationReport(
                job_id=str(job_id) if job_id is not None else None,
                status=HOOK_IDENTIFICATION_STATUS_FAILED,
                selected_candidate=None,
                candidates=[],
                warnings=[],
                blocking_reasons=["hook_identification_failed"],
                recommendation=HOOK_IDENTIFICATION_RECOMMENDATION_FAILED,
                metadata={
                    **safe_metadata,
                    "source": self.source,
                    "error": str(exc),
                },
            )
            failed.enforce_review_only()
            return failed


def identify_hook_candidates_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
    min_hook_score: float = DEFAULT_MIN_HOOK_SCORE,
) -> HookIdentificationReport:
    return HookIdentificationEngine().identify(
        job,
        metadata=metadata,
        min_hook_score=min_hook_score,
    )
