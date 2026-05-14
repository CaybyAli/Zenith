from __future__ import annotations

from typing import Any

from models.but_therefore_story import (
    ButThereforeStoryReport,
    STORY_RECOMMENDATION_NO_TIMELINE,
    STORY_RECOMMENDATION_READY,
    STORY_RECOMMENDATION_WARNINGS,
    STORY_ROLE_AND,
    STORY_ROLE_BUT,
    STORY_ROLE_CENSOR_REVIEW,
    STORY_ROLE_CONTINUITY_BLOCKED,
    STORY_ROLE_PAYOFF,
    STORY_ROLE_PROTECTED,
    STORY_ROLE_REACTION,
    STORY_ROLE_SETUP,
    STORY_ROLE_THEREFORE,
    STORY_ROLE_UNKNOWN,
    STORY_STATUS_NO_TIMELINE_ITEMS,
    STORY_STATUS_READY,
    STORY_STATUS_READY_WITH_WARNINGS,
    STORY_SUGGESTION_CENSOR_REVIEW,
    STORY_SUGGESTION_CONTINUITY_BLOCKED,
    STORY_SUGGESTION_FLOW_BREAK,
    STORY_SUGGESTION_MISSING_PAYOFF,
    STORY_SUGGESTION_ORPHAN_REACTION,
    STORY_SUGGESTION_PAYOFF_WITHOUT_SETUP,
    STORY_SUGGESTION_PROTECTED_PRESERVED,
    STORY_SUGGESTION_SETUP_WITHOUT_PAYOFF,
    STORY_SUGGESTION_STRONG_CHAIN,
    STORY_SUGGESTION_TOO_MANY_AND,
    STORY_SUGGESTION_WEAK_RATIO,
    TRANSITION_QUALITY_OK,
    TRANSITION_QUALITY_STRONG,
    TRANSITION_QUALITY_WEAK,
    StoryMoment,
    StoryTransition,
    clamp_score,
    story_review_metadata,
)


DEFAULT_ITEM_DURATION_SECONDS = 3.0
TARGET_STRONG_STORY_RATIO = 0.60
MAX_GOOD_AND_STREAK = 2

CONFLICT_KEYWORDS = {
    "aber",
    "but",
    "jedoch",
    "plötzlich",
    "ploetzlich",
    "warte",
    "nein",
    "oh nein",
    "fuck",
    "krass",
    "no way",
    "what",
    "clutch",
    "fail",
    "problem",
    "bro",
    "gefahr",
    "danger",
    "schock",
    "shock",
    "lost",
    "verloren",
    "enemy",
    "gegner",
}

CONSEQUENCE_KEYWORDS = {
    "deshalb",
    "deswegen",
    "therefore",
    "also",
    "darum",
    "dann",
    "danach",
    "jetzt",
    "geschafft",
    "gewonnen",
    "tot",
    "killed",
    "eliminated",
    "result",
    "ergebnis",
    "consequence",
    "folge",
    "lösung",
    "loesung",
}

REACTION_KEYWORDS = {
    "haha",
    "lol",
    "lmao",
    "lach",
    "laugh",
    "hype",
    "schock",
    "shock",
    "surprise",
    "überrasch",
    "ueberrasch",
    "chat",
    "omg",
    "oh mein gott",
    "wow",
    "face reaction",
    "reaction shot",
}

PAYOFF_KEYWORDS = {
    "payoff",
    "climax",
    "höhepunkt",
    "hoehepunkt",
    "victory",
    "win",
    "gewonnen",
    "geschafft",
    "highlight resolved",
    "auflösung",
    "aufloesung",
    "final",
    "finish",
    "kill",
    "killed",
    "eliminated",
}

SETUP_KEYWORDS = {
    "setup",
    "context",
    "kontext",
    "erklärung",
    "erklaerung",
    "vorbereitung",
    "plan",
    "intro",
    "ziel",
    "mission",
    "erstmal",
}

CONFLICT_SCORE_KEYS = (
    "conflict_score",
    "hook_score",
    "energy_score",
    "energy_peak_score",
    "peak_score",
    "clutch_score",
    "shock_score",
    "danger_score",
    "pattern_interrupt_score",
    "content_value_score",
    "final_score",
    "score",
)

CONSEQUENCE_SCORE_KEYS = (
    "consequence_score",
    "resolution_score",
    "result_score",
    "outcome_score",
    "payoff_score",
    "content_value_score",
    "final_score",
    "score",
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
    "emotion_score",
    "score",
    "confidence",
)

PAYOFF_SCORE_KEYS = (
    "payoff_score",
    "climax_score",
    "victory_score",
    "highlight_score",
    "content_value_score",
    "final_score",
    "score",
)

NEUTRAL_SCORE_KEYS = (
    "neutral_score",
    "dead_content_score",
    "low_value_score",
)


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
        "reaction_shot_placement_report",
    ):
        nested_items = _items_from_container(data.get(nested_key), keys)
        if nested_items:
            return nested_items

    return []


def _collect_items(sources: list[Any], keys: tuple[str, ...]) -> list[dict[str, Any]]:
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
    if start_seconds is not None and end_seconds is not None and end_seconds >= start_seconds:
        return end_seconds - start_seconds
    return 0.0


def _text_blob(flat: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "text",
        "transcript",
        "caption",
        "title",
        "matched_text",
        "matched_keyword",
        "keyword",
        "phrase",
        "label",
        "reason",
        "selection_reason",
        "decision_reason",
        "action",
        "final_action",
        "signal_type",
        "suggestion_type",
        "reaction_type",
        "story_role",
    ):
        value = flat.get(key)
        if value is not None:
            parts.append(str(value))
    return " ".join(parts).lower()


def _keyword_score(blob: str, keywords: set[str]) -> float:
    matches = [keyword for keyword in keywords if keyword in blob]
    if not matches:
        return 0.0
    return clamp_score(0.45 + (0.12 * min(len(matches), 4)))


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
        "conflict",
        "payoff",
        "reaction",
    ):
        if categories.get(key) is not None:
            scores.append(clamp_score(categories.get(key)))

    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 6)


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
        "placement_id",
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
    emotional_report = _safe_dict(_job_value(job, "emotional_arc_report"))
    dynamic_report = _safe_dict(_job_value(job, "dynamic_pacing_report"))
    pattern_report = _safe_dict(_job_value(job, "pattern_interrupt_report"))
    reaction_report = _safe_dict(_job_value(job, "reaction_shot_placement_report"))

    hook_items = _collect_items(
        [
            _job_value(job, "hook_candidates"),
            _job_value(job, "hook_identification"),
            hook_report,
            _job_value(job, "hook_selected_candidate"),
            hook_report.get("selected_candidate"),
        ],
        ("candidates", "hook_candidates", "items"),
    )

    return {
        "hook": hook_items,
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
        "reaction_candidates": _collect_items(
            [
                _job_value(job, "reaction_shot_candidates"),
                reaction_report,
                _job_value(job, "reaction_shot_placement"),
            ],
            ("candidates", "reaction_shot_candidates", "items"),
        ),
        "reaction_placements": _collect_items(
            [
                _job_value(job, "reaction_shot_placements"),
                reaction_report,
                _job_value(job, "reaction_shot_placement"),
            ],
            ("placements", "reaction_shot_placements", "items"),
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
            ("segment_scores", "matches", "keyword_emotion_segment_scores", "items"),
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
        or f"story_source_item_{index}"
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
        warnings.append("story_protected_preserved")
    if censor_required:
        warnings.append("story_censor_review_required")
    if continuity_blocked:
        blocking_reasons.append("story_continuity_blocked")

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
                + ["using_story_order_fallback_timing"]
            )
        elif duration <= 0.0:
            duration = max(0.0, end - start)

        item["start_seconds"] = round(float(start), 3)
        item["end_seconds"] = round(float(end), 3)
        item["duration_seconds"] = round(float(duration), 3)
        cursor = max(cursor, float(end))

    return items


def _score_related_sources(
    item_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
) -> dict[str, float]:
    scores = {
        "conflict": 0.0,
        "consequence": 0.0,
        "reaction": 0.0,
        "payoff": 0.0,
        "setup": 0.0,
    }

    source_score_map = {
        "hook": ("conflict", 0.72),
        "emotional_arc": ("payoff", 0.64),
        "emotional_suggestions": ("payoff", 0.58),
        "dynamic_pacing": ("conflict", 0.50),
        "pattern_windows": ("conflict", 0.72),
        "pattern_suggestions": ("conflict", 0.66),
        "reaction_candidates": ("reaction", 0.82),
        "reaction_placements": ("reaction", 0.78),
        "content_value": ("payoff", 0.52),
        "keyword": ("reaction", 0.48),
        "unified": ("conflict", 0.45),
    }

    for source_name, items in related_sources.items():
        matches = _items_near_item(items, item_data)
        if not matches:
            continue

        target, base_score = source_score_map.get(source_name, ("conflict", 0.40))
        scores[target] = max(scores[target], base_score)

        for match in matches:
            flat = _flatten_item_data(match)
            blob = _text_blob(flat)
            scores["conflict"] = max(
                scores["conflict"],
                _keyword_score(blob, CONFLICT_KEYWORDS),
                _score_from_keys(flat, CONFLICT_SCORE_KEYS),
            )
            scores["consequence"] = max(
                scores["consequence"],
                _keyword_score(blob, CONSEQUENCE_KEYWORDS),
                _score_from_keys(flat, CONSEQUENCE_SCORE_KEYS),
            )
            scores["reaction"] = max(
                scores["reaction"],
                _keyword_score(blob, REACTION_KEYWORDS),
                _score_from_keys(flat, REACTION_SCORE_KEYS),
            )
            scores["payoff"] = max(
                scores["payoff"],
                _keyword_score(blob, PAYOFF_KEYWORDS),
                _score_from_keys(flat, PAYOFF_SCORE_KEYS),
            )
            scores["setup"] = max(scores["setup"], _keyword_score(blob, SETUP_KEYWORDS))

    return {key: round(clamp_score(value), 6) for key, value in scores.items()}


def _classify_story_role(
    item_data: dict[str, Any],
    related_sources: dict[str, list[dict[str, Any]]],
) -> StoryMoment:
    flat = item_data["flat"]
    blob = _text_blob(flat)

    conflict_score = max(
        _keyword_score(blob, CONFLICT_KEYWORDS),
        _score_from_keys(flat, CONFLICT_SCORE_KEYS),
    )
    consequence_score = max(
        _keyword_score(blob, CONSEQUENCE_KEYWORDS),
        _score_from_keys(flat, CONSEQUENCE_SCORE_KEYS),
    )
    reaction_score = max(
        _keyword_score(blob, REACTION_KEYWORDS),
        _score_from_keys(flat, REACTION_SCORE_KEYS),
    )
    payoff_score = max(
        _keyword_score(blob, PAYOFF_KEYWORDS),
        _score_from_keys(flat, PAYOFF_SCORE_KEYS),
    )
    setup_score = _keyword_score(blob, SETUP_KEYWORDS)
    neutral_score = max(
        _score_from_keys(flat, NEUTRAL_SCORE_KEYS),
        0.35,
    )

    related_scores = _score_related_sources(item_data, related_sources)
    conflict_score = max(conflict_score, related_scores["conflict"])
    consequence_score = max(consequence_score, related_scores["consequence"])
    reaction_score = max(reaction_score, related_scores["reaction"])
    payoff_score = max(payoff_score, related_scores["payoff"])
    setup_score = max(setup_score, related_scores["setup"])

    action = str(flat.get("action") or flat.get("final_action") or "")
    if action in {"keep_high_value", "strong_moment", "highlight", "hook"}:
        conflict_score = max(conflict_score, 0.70)
        payoff_score = max(payoff_score, 0.55)
    if action in {"reaction", "face_reaction", "laugh_reaction", "hype_reaction", "shock_reaction"}:
        reaction_score = max(reaction_score, 0.82)

    evidence: list[str] = []
    if conflict_score >= 0.55:
        evidence.append("conflict_or_turning_point_signal")
    if consequence_score >= 0.55:
        evidence.append("consequence_or_resolution_signal")
    if reaction_score >= 0.55:
        evidence.append("reaction_signal")
    if payoff_score >= 0.62:
        evidence.append("payoff_or_climax_signal")
    if setup_score >= 0.55:
        evidence.append("setup_context_signal")

    if item_data["continuity_blocked"]:
        story_role = STORY_ROLE_CONTINUITY_BLOCKED
        story_score = 0.0
        evidence.append("continuity_blocked")
    elif item_data["censor_required"]:
        story_role = STORY_ROLE_CENSOR_REVIEW
        story_score = max(conflict_score, reaction_score, payoff_score, 0.50)
        evidence.append("censor_review_required")
    elif item_data["protected"]:
        story_role = STORY_ROLE_PROTECTED
        story_score = max(conflict_score, consequence_score, reaction_score, payoff_score, 0.45)
        evidence.append("protected_item_preserved")
    elif reaction_score >= 0.72:
        story_role = STORY_ROLE_REACTION
        story_score = reaction_score
    elif payoff_score >= 0.70:
        story_role = STORY_ROLE_PAYOFF
        story_score = payoff_score
    elif conflict_score >= 0.62 and conflict_score >= consequence_score:
        story_role = STORY_ROLE_BUT
        story_score = conflict_score
    elif consequence_score >= 0.60:
        story_role = STORY_ROLE_THEREFORE
        story_score = consequence_score
    elif setup_score >= 0.60:
        story_role = STORY_ROLE_SETUP
        story_score = setup_score
    elif max(conflict_score, consequence_score, reaction_score, payoff_score, setup_score) <= 0.25:
        story_role = STORY_ROLE_AND
        story_score = neutral_score
        evidence.append("neutral_continuation")
    else:
        story_role = STORY_ROLE_AND
        story_score = max(
            conflict_score,
            consequence_score,
            reaction_score,
            payoff_score,
            setup_score,
            neutral_score,
        )
        evidence.append("weak_story_signal_neutral_continuation")

    return StoryMoment(
        source_item_id=item_data["source_item_id"],
        source_segment_id=item_data["source_segment_id"],
        start_seconds=item_data["start_seconds"],
        end_seconds=item_data["end_seconds"],
        duration_seconds=item_data["duration_seconds"],
        story_role=story_role,
        story_score=round(clamp_score(story_score), 6),
        conflict_score=round(clamp_score(conflict_score), 6),
        consequence_score=round(clamp_score(consequence_score), 6),
        reaction_score=round(clamp_score(reaction_score), 6),
        neutral_score=round(clamp_score(neutral_score), 6),
        evidence=_unique(evidence),
        review_required=True,
        warnings=list(item_data["warnings"]),
        blocking_reasons=list(item_data["blocking_reasons"]),
        metadata={
            **story_review_metadata(),
            "source_label": item_data["source_label"],
            "action": action,
            "raw_text_hint": blob[:240],
            "setup_score": round(clamp_score(setup_score), 6),
            "payoff_score": round(clamp_score(payoff_score), 6),
        },
    )


def _transition_for_pair(
    previous: StoryMoment,
    current: StoryMoment,
) -> StoryTransition:
    strong_pairs = {
        (STORY_ROLE_SETUP, STORY_ROLE_BUT),
        (STORY_ROLE_BUT, STORY_ROLE_THEREFORE),
        (STORY_ROLE_BUT, STORY_ROLE_REACTION),
        (STORY_ROLE_BUT, STORY_ROLE_PAYOFF),
        (STORY_ROLE_THEREFORE, STORY_ROLE_BUT),
        (STORY_ROLE_REACTION, STORY_ROLE_PAYOFF),
        (STORY_ROLE_PAYOFF, STORY_ROLE_SETUP),
        (STORY_ROLE_PAYOFF, STORY_ROLE_AND),
    }

    ok_pairs = {
        (STORY_ROLE_SETUP, STORY_ROLE_THEREFORE),
        (STORY_ROLE_SETUP, STORY_ROLE_PAYOFF),
        (STORY_ROLE_THEREFORE, STORY_ROLE_REACTION),
        (STORY_ROLE_THEREFORE, STORY_ROLE_PAYOFF),
        (STORY_ROLE_REACTION, STORY_ROLE_BUT),
        (STORY_ROLE_AND, STORY_ROLE_BUT),
        (STORY_ROLE_AND, STORY_ROLE_THEREFORE),
        (STORY_ROLE_AND, STORY_ROLE_PAYOFF),
    }

    blocked_roles = {
        STORY_ROLE_CENSOR_REVIEW,
        STORY_ROLE_CONTINUITY_BLOCKED,
        STORY_ROLE_PROTECTED,
    }

    pair = (previous.story_role, current.story_role)
    issue_type: str | None = None
    warnings: list[str] = []

    if previous.story_role in blocked_roles or current.story_role in blocked_roles:
        quality = TRANSITION_QUALITY_OK
        score = 0.50
        warnings.append("story_transition_contains_safety_role")
    elif pair in strong_pairs:
        quality = TRANSITION_QUALITY_STRONG
        score = 0.92
    elif pair in ok_pairs:
        quality = TRANSITION_QUALITY_OK
        score = 0.72
    elif pair == (STORY_ROLE_AND, STORY_ROLE_AND):
        quality = TRANSITION_QUALITY_WEAK
        score = 0.28
        issue_type = STORY_SUGGESTION_TOO_MANY_AND
        warnings.append("and_then_and_then_transition")
    elif current.story_role == STORY_ROLE_REACTION and previous.story_role not in {
        STORY_ROLE_BUT,
        STORY_ROLE_PAYOFF,
        STORY_ROLE_THEREFORE,
    }:
        quality = TRANSITION_QUALITY_WEAK
        score = 0.35
        issue_type = STORY_SUGGESTION_ORPHAN_REACTION
        warnings.append("reaction_without_clear_trigger")
    elif current.story_role == STORY_ROLE_PAYOFF and previous.story_role not in {
        STORY_ROLE_SETUP,
        STORY_ROLE_BUT,
        STORY_ROLE_THEREFORE,
        STORY_ROLE_REACTION,
    }:
        quality = TRANSITION_QUALITY_WEAK
        score = 0.38
        issue_type = STORY_SUGGESTION_PAYOFF_WITHOUT_SETUP
        warnings.append("payoff_without_clear_setup")
    else:
        quality = TRANSITION_QUALITY_OK
        score = 0.56

    return StoryTransition(
        from_moment_id=previous.moment_id,
        to_moment_id=current.moment_id,
        from_role=previous.story_role,
        to_role=current.story_role,
        transition_quality=quality,
        transition_score=score,
        issue_type=issue_type,
        review_required=True,
        can_auto_fix=False,
        warnings=warnings,
        metadata=story_review_metadata(),
    )


def _max_and_streak(moments: list[StoryMoment]) -> int:
    current = 0
    best = 0
    for moment in moments:
        if moment.story_role == STORY_ROLE_AND:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _count_orphan_reactions(moments: list[StoryMoment]) -> int:
    count = 0
    trigger_roles = {STORY_ROLE_BUT, STORY_ROLE_PAYOFF, STORY_ROLE_THEREFORE}
    for index, moment in enumerate(moments):
        if moment.story_role != STORY_ROLE_REACTION:
            continue
        previous_roles = {
            previous.story_role
            for previous in moments[max(0, index - 2):index]
        }
        if not previous_roles.intersection(trigger_roles):
            count += 1
    return count


def _count_missing_payoffs(moments: list[StoryMoment]) -> int:
    count = 0
    payoff_roles = {STORY_ROLE_THEREFORE, STORY_ROLE_REACTION, STORY_ROLE_PAYOFF}
    for index, moment in enumerate(moments):
        if moment.story_role != STORY_ROLE_BUT:
            continue
        next_roles = {
            next_moment.story_role
            for next_moment in moments[index + 1:index + 4]
        }
        if not next_roles.intersection(payoff_roles):
            count += 1
    return count


def _has_later_role(
    moments: list[StoryMoment],
    start_index: int,
    roles: set[str],
) -> bool:
    return any(moment.story_role in roles for moment in moments[start_index + 1:])


def _has_earlier_role(
    moments: list[StoryMoment],
    end_index: int,
    roles: set[str],
) -> bool:
    return any(moment.story_role in roles for moment in moments[:end_index])


def _build_suggestion(
    suggestion_type: str,
    severity: str,
    reason: str,
    moment_id: str | None = None,
    transition_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "suggestion_type": suggestion_type,
        "severity": severity,
        "reason": reason,
        "moment_id": moment_id,
        "transition_id": transition_id,
        "review_required": True,
        "can_apply_story_changes": False,
        "metadata": {
            **story_review_metadata(),
            **dict(metadata or {}),
        },
    }


class ButThereforeStoryEngine:
    def build_report(self, job: Any) -> ButThereforeStoryReport:
        raw_items, source_label = _extract_timeline_items(job)
        job_id = _job_value(job, "job_id")

        if not raw_items:
            report = ButThereforeStoryReport(
                job_id=job_id,
                status=STORY_STATUS_NO_TIMELINE_ITEMS,
                moments=[],
                transitions=[],
                suggestions=[],
                warnings=["no_review_timeline_items_for_story_analysis"],
                blocking_reasons=[],
                recommendation=STORY_RECOMMENDATION_NO_TIMELINE,
                metadata={
                    **story_review_metadata(),
                    "timeline_source": source_label,
                },
            )
            report.enforce_review_only()
            report.refresh_metrics()
            return report

        related_sources = _extract_related_sources(job)

        normalized_items = [
            _normalize_item(item, index, source_label)
            for index, item in enumerate(raw_items)
            if isinstance(item, dict)
        ]
        normalized_items = _assign_fallback_timing(normalized_items)

        moments = [
            _classify_story_role(item_data, related_sources)
            for item_data in normalized_items
        ]

        transitions = [
            _transition_for_pair(previous, current)
            for previous, current in zip(moments, moments[1:])
        ]

        warnings: list[str] = []
        suggestions: list[dict[str, Any]] = []

        and_streak_max = _max_and_streak(moments)
        orphan_reaction_count = _count_orphan_reactions(moments)
        missing_payoff_count = _count_missing_payoffs(moments)

        for moment in moments:
            warnings.extend(moment.warnings)
            if moment.story_role == STORY_ROLE_CENSOR_REVIEW:
                suggestions.append(
                    _build_suggestion(
                        STORY_SUGGESTION_CENSOR_REVIEW,
                        "high",
                        "Censor-sensitive story item needs manual review.",
                        moment_id=moment.moment_id,
                    )
                )
            if moment.story_role == STORY_ROLE_PROTECTED:
                suggestions.append(
                    _build_suggestion(
                        STORY_SUGGESTION_PROTECTED_PRESERVED,
                        "medium",
                        "Protected story item was preserved for review.",
                        moment_id=moment.moment_id,
                    )
                )
            if moment.story_role == STORY_ROLE_CONTINUITY_BLOCKED:
                suggestions.append(
                    _build_suggestion(
                        STORY_SUGGESTION_CONTINUITY_BLOCKED,
                        "high",
                        "Continuity blocked item cannot be treated as normal story flow.",
                        moment_id=moment.moment_id,
                    )
                )

        for transition in transitions:
            warnings.extend(transition.warnings)
            if transition.issue_type:
                suggestions.append(
                    _build_suggestion(
                        transition.issue_type,
                        "medium",
                        "Story transition should be reviewed.",
                        transition_id=transition.transition_id,
                        metadata={
                            "from_role": transition.from_role,
                            "to_role": transition.to_role,
                        },
                    )
                )

        if and_streak_max > MAX_GOOD_AND_STREAK:
            warnings.append("too_many_and_moments_in_a_row")
            suggestions.append(
                _build_suggestion(
                    STORY_SUGGESTION_TOO_MANY_AND,
                    "medium",
                    "Timeline has too many neutral and_moments in a row.",
                    metadata={"and_streak_max": and_streak_max},
                )
            )

        if orphan_reaction_count > 0:
            warnings.append("orphan_reaction_moment_detected")
            suggestions.append(
                _build_suggestion(
                    STORY_SUGGESTION_ORPHAN_REACTION,
                    "medium",
                    "Reaction moment appears without a clear nearby trigger.",
                    metadata={"orphan_reaction_count": orphan_reaction_count},
                )
            )

        if missing_payoff_count > 0:
            warnings.append("missing_payoff_after_but_moment")
            suggestions.append(
                _build_suggestion(
                    STORY_SUGGESTION_MISSING_PAYOFF,
                    "medium",
                    "A but_moment has no clear consequence or payoff soon after it.",
                    metadata={"missing_payoff_count": missing_payoff_count},
                )
            )

        for index, moment in enumerate(moments):
            if moment.story_role == STORY_ROLE_SETUP and not _has_later_role(
                moments,
                index,
                {STORY_ROLE_BUT, STORY_ROLE_PAYOFF, STORY_ROLE_THEREFORE},
            ):
                warnings.append("setup_without_later_payoff")
                suggestions.append(
                    _build_suggestion(
                        STORY_SUGGESTION_SETUP_WITHOUT_PAYOFF,
                        "low",
                        "Setup moment has no later payoff or turn.",
                        moment_id=moment.moment_id,
                    )
                )

            if moment.story_role == STORY_ROLE_PAYOFF and not _has_earlier_role(
                moments,
                index,
                {STORY_ROLE_SETUP, STORY_ROLE_BUT, STORY_ROLE_THEREFORE},
            ):
                warnings.append("payoff_without_earlier_setup")
                suggestions.append(
                    _build_suggestion(
                        STORY_SUGGESTION_PAYOFF_WITHOUT_SETUP,
                        "low",
                        "Payoff moment has no clear earlier setup.",
                        moment_id=moment.moment_id,
                    )
                )

        strong_chain_count = sum(
            1
            for transition in transitions
            if transition.transition_quality == TRANSITION_QUALITY_STRONG
        )
        if strong_chain_count > 0:
            suggestions.append(
                _build_suggestion(
                    STORY_SUGGESTION_STRONG_CHAIN,
                    "info",
                    "Strong But/Therefore style chain detected.",
                    metadata={"strong_chain_count": strong_chain_count},
                )
            )

        weak_transition_count = sum(
            1
            for transition in transitions
            if transition.transition_quality == TRANSITION_QUALITY_WEAK
        )
        if weak_transition_count > 0:
            warnings.append("weak_story_transition_detected")
            suggestions.append(
                _build_suggestion(
                    STORY_SUGGESTION_FLOW_BREAK,
                    "medium",
                    "Some story transitions are weak and should be reviewed.",
                    metadata={"weak_transition_count": weak_transition_count},
                )
            )

        report = ButThereforeStoryReport(
            job_id=job_id,
            status=STORY_STATUS_READY,
            moments=moments,
            transitions=transitions,
            suggestions=suggestions,
            and_streak_max=and_streak_max,
            orphan_reaction_count=orphan_reaction_count,
            missing_payoff_count=missing_payoff_count,
            warnings=_unique(warnings),
            blocking_reasons=[],
            recommendation=STORY_RECOMMENDATION_READY,
            metadata={
                **story_review_metadata(),
                "timeline_source": source_label,
                "related_source_counts": {
                    key: len(value)
                    for key, value in related_sources.items()
                },
                "target_strong_story_ratio": TARGET_STRONG_STORY_RATIO,
            },
        )
        report.enforce_review_only()
        report.refresh_metrics()

        if report.but_therefore_ratio < TARGET_STRONG_STORY_RATIO:
            report.warnings = _unique(
                list(report.warnings or []) + ["weak_but_therefore_ratio"]
            )
            report.suggestions.append(
                _build_suggestion(
                    STORY_SUGGESTION_WEAK_RATIO,
                    "medium",
                    "Strong story moment ratio is below target.",
                    metadata={
                        "but_therefore_ratio": report.but_therefore_ratio,
                        "target_ratio": TARGET_STRONG_STORY_RATIO,
                    },
                )
            )

        if report.warnings or report.suggestions:
            report.status = STORY_STATUS_READY_WITH_WARNINGS
            report.recommendation = STORY_RECOMMENDATION_WARNINGS
        else:
            report.status = STORY_STATUS_READY
            report.recommendation = STORY_RECOMMENDATION_READY

        report.enforce_review_only()
        report.refresh_metrics()
        return report
