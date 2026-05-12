from __future__ import annotations

from typing import Any

from models.content_value import (
    REVIEW_LABEL_HIGH,
    REVIEW_LABEL_LOW,
    REVIEW_LABEL_MEDIUM,
    REVIEW_LABEL_NONE,
    REVIEW_LABEL_PROTECTED,
    REVIEW_LABEL_TECHNICAL_WARNING,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_SKIPPED_NO_INPUTS,
    VALUE_TIER_HIGH,
    VALUE_TIER_LOW,
    VALUE_TIER_MEDIUM,
    VALUE_TIER_PROTECTED,
    VALUE_TIER_TECHNICAL_WARNING,
    VALUE_TIER_UNKNOWN,
    ContentValueResult,
    ContentValueSegmentScore,
)


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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _job_attr(job: Any, name: str) -> Any:
    if job is None:
        return None
    if isinstance(job, dict):
        return job.get(name)
    return getattr(job, name, None)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _derive_duration(
    start_seconds: float | None,
    end_seconds: float | None,
    duration_seconds: float | None = None,
) -> float | None:
    if duration_seconds is not None:
        return max(0.0, duration_seconds)
    if start_seconds is None or end_seconds is None:
        return None
    return max(0.0, end_seconds - start_seconds)


def _derive_center(
    start_seconds: float | None,
    end_seconds: float | None,
    center_seconds: float | None = None,
) -> float | None:
    if center_seconds is not None:
        return center_seconds
    if start_seconds is None or end_seconds is None:
        return None
    return (start_seconds + end_seconds) / 2.0


def _time_overlaps(
    source: dict[str, Any],
    start_seconds: float | None,
    end_seconds: float | None,
) -> bool:
    if start_seconds is None or end_seconds is None:
        return False
    source_start = _safe_optional_float(source.get("start_seconds"))
    source_end = _safe_optional_float(source.get("end_seconds"))
    if source_start is None or source_end is None:
        center = _safe_optional_float(source.get("center_seconds"))
        if center is None:
            return False
        source_start = center
        source_end = center
    return source_start <= end_seconds and source_end >= start_seconds


def _same_segment(source: dict[str, Any], segment_id: str) -> bool:
    if not segment_id:
        return False
    for key in ("segment_id", "source_segment_id", "id", "transcript_segment_id"):
        if str(source.get(key) or "") == segment_id:
            return True
    metadata = _safe_dict(source.get("metadata"))
    return str(metadata.get("source_segment_id") or "") == segment_id


def _items_near_segment(
    items: list[dict[str, Any]],
    start_seconds: float | None,
    end_seconds: float | None,
    segment_id: str = "",
) -> list[dict[str, Any]]:
    matches = [
        item for item in items if _time_overlaps(item, start_seconds, end_seconds)
    ]
    if matches:
        return matches
    return [item for item in items if _same_segment(item, segment_id)]


def _extract_report_items(source: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    source_dict = _safe_dict(source)
    candidates: list[Any] = []
    for key in keys:
        value = source_dict.get(key)
        if isinstance(value, list):
            candidates = value
            break

    if not candidates:
        for nested_key in (
            "content_value_result",
            "keyword_emotion_result",
            "interaction_classification_result",
            "sentence_boundary_result",
            "dead_content_result",
            "detection_result",
            "classification_result",
            "visual_energy_result",
            "face_reaction_result",
            "motion_analysis_result",
            "screen_content_result",
            "scene_change_result",
            "energy_peak_detection_result",
            "stutter_detection_result",
        ):
            nested = source_dict.get(nested_key)
            if isinstance(nested, dict):
                nested_items = _extract_report_items(nested, keys)
                if nested_items:
                    return nested_items

    return [dict(item) for item in candidates if isinstance(item, dict)]


def _extract_transcript_segments(
    transcript_segments: Any,
    job_or_sources: Any = None,
) -> list[dict[str, Any]]:
    if transcript_segments is None:
        transcript_segments = _job_attr(job_or_sources, "transcript_segments")
    if not isinstance(transcript_segments, list):
        return []
    return [dict(item) for item in transcript_segments if isinstance(item, dict)]


def _collect_related_sources(
    *,
    keyword_emotion_report: Any = None,
    interaction_classification_report: Any = None,
    sentence_boundary_report: Any = None,
    dead_content_report: Any = None,
    filler_word_report: Any = None,
    silence_classification_report: Any = None,
    visual_energy_report: Any = None,
    face_reaction_report: Any = None,
    motion_analysis_report: Any = None,
    screen_content_report: Any = None,
    scene_change_report: Any = None,
    energy_peak_report: Any = None,
    audio_normalization_report: Any = None,
    stutter_detection_report: Any = None,
) -> dict[str, list[dict[str, Any]]]:
    return {
        "keyword_scores": _extract_report_items(
            keyword_emotion_report,
            ("segment_scores", "matches", "keyword_emotion_segment_scores"),
        ),
        "interaction_segments": _extract_report_items(
            interaction_classification_report,
            ("segment_classifications", "points", "interaction_classification_segments"),
        ),
        "sentence_boundaries": _extract_report_items(
            sentence_boundary_report,
            ("boundaries", "sentence_boundary_boundaries"),
        ),
        "sentence_protection_zones": _extract_report_items(
            sentence_boundary_report,
            ("protection_zones", "sentence_boundary_protection_zones"),
        ),
        "dead_content_items": _extract_report_items(
            dead_content_report,
            ("candidates", "segment_scores", "dead_content_segment_scores"),
        ),
        "filler_occurrences": _extract_report_items(
            filler_word_report,
            ("occurrences", "filler_word_occurrences"),
        ),
        "silence_classifications": _extract_report_items(
            silence_classification_report,
            ("classifications", "silence_classifications"),
        ),
        "visual_energy_segments": _extract_report_items(
            visual_energy_report,
            ("visual_energy_segments", "segments"),
        ),
        "face_reaction_segments": _extract_report_items(
            face_reaction_report,
            ("face_reaction_segments", "segments"),
        ),
        "motion_analysis_segments": _extract_report_items(
            motion_analysis_report,
            ("motion_analysis_segments", "motion_segments", "segments"),
        ),
        "screen_content_segments": _extract_report_items(
            screen_content_report,
            ("screen_content_segments", "segments"),
        ),
        "scene_changes": _extract_report_items(
            scene_change_report,
            ("scene_changes", "changes"),
        ),
        "energy_peaks": _extract_report_items(
            energy_peak_report,
            ("peaks", "energy_peaks", "beats"),
        ),
        "audio_normalization_items": [_safe_dict(audio_normalization_report)]
        if _safe_dict(audio_normalization_report)
        else [],
        "stutter_segments": _extract_report_items(
            stutter_detection_report,
            ("stutter_detection_segments", "segments", "points"),
        ),
    }


def _max_existing_score(item: dict[str, Any], keys: tuple[str, ...]) -> float:
    return max((clamp_score(item.get(key)) for key in keys), default=0.0)


def _score_speech(text: str, duration_seconds: float | None) -> tuple[float, dict[str, Any]]:
    words = [part for part in text.split(" ") if part]
    word_count = len(words)
    has_duration = duration_seconds is not None and duration_seconds > 0.0
    if word_count == 0:
        score = 0.0
    elif word_count >= 4 and has_duration:
        score = 0.9
    elif word_count >= 2:
        score = 0.65
    else:
        score = 0.35
    return clamp_score(score), {
        "word_count": word_count,
        "has_text": word_count > 0,
        "has_valid_duration": has_duration,
    }


def _score_keywords(items: list[dict[str, Any]]) -> tuple[float, list[str]]:
    categories: list[str] = []
    scores: list[float] = []
    high_categories = {"hype", "shock", "laugh", "question", "high_value_keyword"}
    for item in items:
        categories_dict = _safe_dict(item.get("categories"))
        for category in high_categories:
            score = clamp_score(
                categories_dict.get(category, item.get(f"{category}_score")),
            )
            if score > 0.0:
                scores.append(score)
                categories.append(category)
        for key in ("overall_keyword_score", "keyword_value_score", "score", "confidence"):
            score = clamp_score(item.get(key))
            if score > 0.0:
                scores.append(score)
        label = str(
            item.get("dominant_category")
            or item.get("keyword_type")
            or item.get("category")
            or ""
        )
        if label in high_categories:
            categories.append(label)
            scores.append(max(0.8, clamp_score(item.get("confidence"))))
        if bool(item.get("is_high_value_keyword")):
            categories.append("high_value_keyword")
            scores.append(0.9)
    return clamp_score(max(scores) if scores else 0.0), sorted(set(categories))


def _score_interactions(items: list[dict[str, Any]]) -> tuple[float, float, list[str]]:
    scores: list[float] = []
    types: list[str] = []
    protection = 0.0
    for item in items:
        interaction_type = str(
            item.get("interaction_type")
            or item.get("classification")
            or item.get("type")
            or ""
        )
        types.append(interaction_type)
        confidence = clamp_score(item.get("confidence") or 0.65)
        if interaction_type in {"interaction", "question_answer", "chat_reaction"}:
            scores.append(max(0.75, confidence))
        elif interaction_type in {"callout", "context_needed"}:
            scores.append(max(0.65, confidence))
        elif interaction_type in {"commentary", "monologue"}:
            scores.append(max(0.3, confidence * 0.5))
        if bool(item.get("context_needed")) or interaction_type == "context_needed":
            protection = max(protection, 0.85)
        if interaction_type == "question_answer":
            protection = max(protection, 0.8)
    return (
        clamp_score(max(scores) if scores else 0.0),
        clamp_score(protection),
        sorted(set(filter(None, types))),
    )


def _score_visual(items: list[dict[str, Any]]) -> tuple[float, bool]:
    scores: list[float] = []
    technical = False
    for item in items:
        classification = str(item.get("classification") or item.get("visual_tier") or "")
        if classification in {"high_visual_energy", "peak_visual_energy", "visual_peak"}:
            scores.append(0.85)
        if classification in {"visual_technical_warning", "black_screen"}:
            technical = True
        score = _max_existing_score(
            item,
            ("visual_value_score", "avg_visual_energy_score", "max_visual_energy_score", "score"),
        )
        if score > 0.0:
            scores.append(score)
    return clamp_score(max(scores) if scores else 0.0), technical


def _score_face(items: list[dict[str, Any]]) -> float:
    scores: list[float] = []
    for item in items:
        label = str(item.get("reaction_type") or item.get("classification") or "")
        if label in {"high_reaction", "laugh", "shock", "surprise"}:
            scores.append(0.85)
        scores.append(
            _max_existing_score(
                item,
                ("face_reaction_value_score", "reaction_score", "score", "confidence"),
            )
        )
    return clamp_score(max(scores) if scores else 0.0)


def _score_motion(items: list[dict[str, Any]]) -> float:
    scores: list[float] = []
    for item in items:
        label = str(item.get("motion_classification") or item.get("classification") or "")
        if label in {"high_motion", "high_motion_segment"}:
            scores.append(0.8)
        scores.append(
            _max_existing_score(
                item,
                ("motion_value_score", "motion_score", "avg_motion_score", "score"),
            )
        )
    return clamp_score(max(scores) if scores else 0.0)


def _score_screen(items: list[dict[str, Any]]) -> tuple[float, float, bool, list[str]]:
    value_scores: list[float] = []
    penalty_scores: list[float] = []
    technical = False
    screen_types: list[str] = []
    for item in items:
        screen_type = str(item.get("screen_type") or item.get("original_screen_type") or "")
        screen_types.append(screen_type)
        confidence = clamp_score(
            item.get("confidence")
            or item.get("avg_confidence")
            or item.get("max_confidence")
            or 0.65
        )
        if screen_type in {"gameplay", "victory_screen"}:
            value_scores.append(max(0.75, confidence))
        elif screen_type in {"menu", "lobby", "loading"}:
            penalty_scores.append(max(0.65, confidence))
        elif screen_type == "black_screen":
            technical = True
            penalty_scores.append(max(0.85, confidence))
        elif screen_type in {"scoreboard", "death_screen"}:
            value_scores.append(0.35)
            penalty_scores.append(0.25)
    return (
        clamp_score(max(value_scores) if value_scores else 0.0),
        clamp_score(max(penalty_scores) if penalty_scores else 0.0),
        technical,
        sorted(set(filter(None, screen_types))),
    )


def _score_audio(
    energy_items: list[dict[str, Any]],
    silence_items: list[dict[str, Any]],
    audio_items: list[dict[str, Any]],
) -> tuple[float, float, bool]:
    value_scores: list[float] = []
    penalty_scores: list[float] = []
    technical = False
    for item in energy_items:
        label = str(item.get("peak_type") or item.get("classification") or "")
        if label in {"high_energy_peak", "local_max_peak", "beat", "strong_audio_peak"}:
            value_scores.append(0.85)
        value_scores.append(
            _max_existing_score(
                item,
                ("peak_score", "energy_score", "beat_strength", "score", "confidence"),
            )
        )
    for item in silence_items:
        label = str(item.get("classification") or item.get("silence_type") or "")
        duration = _safe_float(item.get("duration_seconds"), 0.0)
        if bool(item.get("remove_candidate")) or label in {
            "dead_air",
            "long_silence",
            "silence_remove",
        }:
            penalty_scores.append(0.85)
        elif duration >= 0.75:
            penalty_scores.append(0.65)
    for item in audio_items:
        if bool(item.get("audio_clipping_warning")) or bool(
            item.get("would_clip_after_gain")
        ):
            technical = True
        clipping_ratio = clamp_score(item.get("clipping_ratio"))
        if clipping_ratio > 0.0:
            technical = True
            penalty_scores.append(max(0.75, clipping_ratio))
        if str(item.get("level_status") or "") in {"clipping", "technical_warning"}:
            technical = True
            penalty_scores.append(0.85)
    if value_scores and not penalty_scores:
        value = max(value_scores)
    elif value_scores:
        value = max(0.0, max(value_scores) - max(penalty_scores) * 0.35)
    else:
        value = 0.15 if not penalty_scores else 0.0
    return (
        clamp_score(value),
        clamp_score(max(penalty_scores) if penalty_scores else 0.0),
        technical,
    )


def _score_story_context(
    *,
    text: str,
    sentence_items: list[dict[str, Any]],
    protection_zone_items: list[dict[str, Any]],
    interaction_protection: float,
    scene_items: list[dict[str, Any]],
) -> tuple[float, float, list[str]]:
    scores: list[float] = []
    protection_scores: list[float] = []
    reasons: list[str] = []
    if text.endswith("?"):
        scores.append(0.7)
        protection_scores.append(0.8)
        reasons.append("open_question")
    for item in sentence_items:
        boundary_type = str(item.get("boundary_type") or item.get("classification") or "")
        if boundary_type in {"safe_sentence_boundary", "complete_sentence"}:
            scores.append(0.55)
            reasons.append(f"sentence:{boundary_type}")
        if boundary_type in {
            "unsafe_sentence_boundary",
            "open_sentence_fragment",
            "question_boundary",
            "open_question",
        }:
            scores.append(0.65)
            protection_scores.append(0.85)
            reasons.append(f"sentence:{boundary_type}")
    if protection_zone_items:
        scores.append(0.75)
        protection_scores.append(0.9)
        reasons.append("sentence_protection_zone")
    if interaction_protection > 0.0:
        scores.append(interaction_protection)
        protection_scores.append(interaction_protection)
        reasons.append("interaction_context")
    if scene_items:
        scores.append(0.35)
        reasons.append("scene_change_nearby")
    return (
        clamp_score(max(scores) if scores else 0.0),
        clamp_score(max(protection_scores) if protection_scores else 0.0),
        sorted(set(reasons)),
    )


def _score_dead_content(
    dead_items: list[dict[str, Any]],
    filler_items: list[dict[str, Any]],
    screen_penalty_score: float,
    audio_penalty_score: float,
) -> tuple[float, float, list[str]]:
    penalty_scores: list[float] = []
    protection_scores: list[float] = []
    reasons: list[str] = []
    for item in dead_items:
        candidate_type = str(item.get("candidate_type") or "")
        dead_score = clamp_score(
            item.get("dead_content_score")
            or item.get("score")
            or item.get("confidence")
        )
        if dead_score > 0.0:
            penalty_scores.append(dead_score)
        if candidate_type in {
            "dead_air_candidate",
            "low_value_content_candidate",
            "filler_pause_candidate",
            "loading_or_menu_candidate",
            "low_visual_dead_candidate",
        }:
            penalty_scores.append(max(0.75, dead_score))
            reasons.append(candidate_type)
        if candidate_type == "protected_context_candidate" or bool(
            item.get("protected_by_context")
        ):
            protection_scores.append(0.85)
            reasons.append("dead_content_protected_context")
    if filler_items:
        penalty_scores.append(min(1.0, 0.25 + len(filler_items) * 0.15))
        reasons.append("filler_words")
    if screen_penalty_score > 0.0:
        penalty_scores.append(screen_penalty_score)
        reasons.append("screen_penalty")
    if audio_penalty_score > 0.0:
        penalty_scores.append(audio_penalty_score)
        reasons.append("audio_penalty")
    return (
        clamp_score(max(penalty_scores) if penalty_scores else 0.0),
        clamp_score(max(protection_scores) if protection_scores else 0.0),
        sorted(set(reasons)),
    )


def _score_technical(
    *,
    visual_technical: bool,
    screen_technical: bool,
    audio_technical: bool,
    stutter_items: list[dict[str, Any]],
) -> tuple[float, list[str]]:
    scores: list[float] = []
    reasons: list[str] = []
    if visual_technical:
        scores.append(0.8)
        reasons.append("visual_technical_warning")
    if screen_technical:
        scores.append(0.85)
        reasons.append("screen_technical_warning")
    if audio_technical:
        scores.append(0.85)
        reasons.append("audio_technical_warning")
    for item in stutter_items:
        label = str(
            item.get("stutter_type")
            or item.get("classification")
            or item.get("candidate_type")
            or ""
        )
        confidence = clamp_score(item.get("confidence") or item.get("score") or 0.75)
        if label in {"stutter", "freeze", "duplicate_frame", "stutter_segment"} or bool(
            item.get("technical_warning")
        ):
            scores.append(max(0.78, confidence))
            reasons.append(label or "stutter_detection")
    return clamp_score(max(scores) if scores else 0.0), sorted(set(reasons))


def classify_content_value_tier(
    final_score: float,
    protection_score: float = 0.0,
    technical_penalty_score: float = 0.0,
) -> str:
    final = clamp_score(final_score)
    protection = clamp_score(protection_score)
    technical = clamp_score(technical_penalty_score)
    if technical >= 0.75:
        return VALUE_TIER_TECHNICAL_WARNING
    if protection >= 0.70 and final < 0.55:
        return VALUE_TIER_PROTECTED
    if final >= 0.70:
        return VALUE_TIER_HIGH
    if final >= 0.40:
        return VALUE_TIER_MEDIUM
    if final < 0.40:
        return VALUE_TIER_LOW
    return VALUE_TIER_UNKNOWN


def _review_label_for_tier(value_tier: str) -> str:
    if value_tier == VALUE_TIER_HIGH:
        return REVIEW_LABEL_HIGH
    if value_tier == VALUE_TIER_MEDIUM:
        return REVIEW_LABEL_MEDIUM
    if value_tier == VALUE_TIER_LOW:
        return REVIEW_LABEL_LOW
    if value_tier == VALUE_TIER_PROTECTED:
        return REVIEW_LABEL_PROTECTED
    if value_tier == VALUE_TIER_TECHNICAL_WARNING:
        return REVIEW_LABEL_TECHNICAL_WARNING
    return REVIEW_LABEL_NONE


def score_content_value_segment(
    segment: Any,
    source_index: int = 0,
    related_sources: dict[str, list[dict[str, Any]]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ContentValueSegmentScore:
    warnings: list[str] = []
    errors: list[str] = []
    segment_dict = _safe_dict(segment)
    if not segment_dict:
        warnings.append("invalid_segment_defaulted")

    start_seconds = _safe_optional_float(segment_dict.get("start_seconds"))
    end_seconds = _safe_optional_float(segment_dict.get("end_seconds"))
    duration_seconds = _derive_duration(
        start_seconds,
        end_seconds,
        _safe_optional_float(segment_dict.get("duration_seconds")),
    )
    center_seconds = _derive_center(
        start_seconds,
        end_seconds,
        _safe_optional_float(segment_dict.get("center_seconds")),
    )
    text = _normalize_text(
        segment_dict.get("text")
        or segment_dict.get("normalized_text")
        or segment_dict.get("transcript")
    )
    segment_id = str(
        segment_dict.get("segment_id")
        or segment_dict.get("id")
        or f"content_value_segment_{source_index}"
    )

    related = related_sources or {}
    keyword_items = _items_near_segment(
        related.get("keyword_scores", []),
        start_seconds,
        end_seconds,
        segment_id,
    )
    interaction_items = _items_near_segment(
        related.get("interaction_segments", []),
        start_seconds,
        end_seconds,
        segment_id,
    )
    sentence_items = _items_near_segment(
        related.get("sentence_boundaries", []),
        start_seconds,
        end_seconds,
        segment_id,
    )
    protection_zone_items = _items_near_segment(
        related.get("sentence_protection_zones", []),
        start_seconds,
        end_seconds,
        segment_id,
    )
    dead_items = _items_near_segment(
        related.get("dead_content_items", []),
        start_seconds,
        end_seconds,
        segment_id,
    )
    filler_items = _items_near_segment(
        related.get("filler_occurrences", []),
        start_seconds,
        end_seconds,
        segment_id,
    )
    silence_items = _items_near_segment(
        related.get("silence_classifications", []),
        start_seconds,
        end_seconds,
        segment_id,
    )
    visual_items = _items_near_segment(
        related.get("visual_energy_segments", []),
        start_seconds,
        end_seconds,
        segment_id,
    )
    face_items = _items_near_segment(
        related.get("face_reaction_segments", []),
        start_seconds,
        end_seconds,
        segment_id,
    )
    motion_items = _items_near_segment(
        related.get("motion_analysis_segments", []),
        start_seconds,
        end_seconds,
        segment_id,
    )
    screen_items = _items_near_segment(
        related.get("screen_content_segments", []),
        start_seconds,
        end_seconds,
        segment_id,
    )
    scene_items = _items_near_segment(
        related.get("scene_changes", []),
        start_seconds,
        end_seconds,
        segment_id,
    )
    energy_items = _items_near_segment(
        related.get("energy_peaks", []),
        start_seconds,
        end_seconds,
        segment_id,
    )
    stutter_items = _items_near_segment(
        related.get("stutter_segments", []),
        start_seconds,
        end_seconds,
        segment_id,
    )

    speech_value_score, speech_evidence = _score_speech(text, duration_seconds)
    keyword_value_score, keyword_categories = _score_keywords(keyword_items)
    (
        interaction_value_score,
        interaction_protection,
        interaction_types,
    ) = _score_interactions(interaction_items)
    visual_value_score, visual_technical = _score_visual(visual_items)
    face_reaction_value_score = _score_face(face_items)
    motion_value_score = _score_motion(motion_items)
    (
        screen_value_score,
        screen_penalty_score,
        screen_technical,
        screen_types,
    ) = _score_screen(screen_items)
    audio_value_score, audio_penalty_score, audio_technical = _score_audio(
        energy_items,
        silence_items,
        related.get("audio_normalization_items", []),
    )
    story_context_score, story_protection, story_reasons = _score_story_context(
        text=text,
        sentence_items=sentence_items,
        protection_zone_items=protection_zone_items,
        interaction_protection=interaction_protection,
        scene_items=scene_items,
    )
    dead_content_penalty_score, dead_protection, dead_reasons = _score_dead_content(
        dead_items,
        filler_items,
        screen_penalty_score,
        audio_penalty_score,
    )
    technical_penalty_score, technical_reasons = _score_technical(
        visual_technical=visual_technical,
        screen_technical=screen_technical,
        audio_technical=audio_technical,
        stutter_items=stutter_items,
    )
    protection_score = clamp_score(max(story_protection, dead_protection))

    raw_positive = (
        speech_value_score * 0.10
        + keyword_value_score * 0.18
        + interaction_value_score * 0.16
        + visual_value_score * 0.14
        + face_reaction_value_score * 0.10
        + motion_value_score * 0.06
        + screen_value_score * 0.08
        + audio_value_score * 0.10
        + story_context_score * 0.08
    )
    penalty = (
        dead_content_penalty_score * 0.20
        + technical_penalty_score * 0.12
    )
    final_score = clamp_score(raw_positive - penalty + protection_score * 0.05)
    content_value_score = clamp_score(raw_positive)
    value_tier = classify_content_value_tier(
        final_score,
        protection_score=protection_score,
        technical_penalty_score=technical_penalty_score,
    )
    review_label = _review_label_for_tier(value_tier)
    is_hook_candidate = (
        final_score >= 0.78
        or (
            keyword_value_score >= 0.75
            and max(
                visual_value_score,
                face_reaction_value_score,
                audio_value_score,
            )
            >= 0.70
            and technical_penalty_score < 0.75
        )
    )

    evidence = {
        **speech_evidence,
        "keyword_categories": keyword_categories,
        "interaction_types": interaction_types,
        "screen_types": screen_types,
        "story_context_reasons": story_reasons,
        "dead_content_penalty_reasons": dead_reasons,
        "technical_reasons": technical_reasons,
        "related_counts": {
            "keywords": len(keyword_items),
            "interactions": len(interaction_items),
            "dead_content": len(dead_items),
            "visual_energy": len(visual_items),
            "face_reaction": len(face_items),
            "motion": len(motion_items),
            "screen": len(screen_items),
            "energy_peaks": len(energy_items),
            "stutter": len(stutter_items),
        },
    }

    return ContentValueSegmentScore(
        segment_id=segment_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        center_seconds=center_seconds,
        duration_seconds=duration_seconds,
        text=text,
        content_value_score=round(content_value_score, 6),
        speech_value_score=round(speech_value_score, 6),
        keyword_value_score=round(keyword_value_score, 6),
        interaction_value_score=round(interaction_value_score, 6),
        visual_value_score=round(visual_value_score, 6),
        face_reaction_value_score=round(face_reaction_value_score, 6),
        motion_value_score=round(motion_value_score, 6),
        screen_value_score=round(screen_value_score, 6),
        audio_value_score=round(audio_value_score, 6),
        story_context_score=round(story_context_score, 6),
        dead_content_penalty_score=round(dead_content_penalty_score, 6),
        technical_penalty_score=round(technical_penalty_score, 6),
        protection_score=round(protection_score, 6),
        final_score=round(final_score, 6),
        value_tier=value_tier,
        review_label=review_label,
        is_high_value=value_tier == VALUE_TIER_HIGH,
        is_mid_value=value_tier == VALUE_TIER_MEDIUM,
        is_low_value=value_tier == VALUE_TIER_LOW,
        is_protected_context=value_tier == VALUE_TIER_PROTECTED,
        is_hook_candidate=is_hook_candidate,
        is_technical_warning=value_tier == VALUE_TIER_TECHNICAL_WARNING,
        evidence=evidence,
        source_segment_index=source_index,
        recommendation=review_label,
        metadata={
            **dict(metadata or {}),
            "source_segment_id": segment_id,
        },
        warnings=warnings,
        errors=errors,
    )


def build_content_value_result(
    segment_scores: list[ContentValueSegmentScore],
    metadata: dict[str, Any] | None = None,
) -> ContentValueResult:
    warnings: list[str] = []
    errors: list[str] = []
    for score in segment_scores:
        warnings.extend(score.warnings)
        errors.extend(score.errors)

    values = [clamp_score(score.final_score) for score in segment_scores]
    high_count = sum(1 for score in segment_scores if score.is_high_value)
    mid_count = sum(1 for score in segment_scores if score.is_mid_value)
    low_count = sum(1 for score in segment_scores if score.is_low_value)
    protected_count = sum(
        1 for score in segment_scores if score.is_protected_context
    )
    hook_count = sum(1 for score in segment_scores if score.is_hook_candidate)
    technical_count = sum(
        1 for score in segment_scores if score.is_technical_warning
    )

    if errors or warnings:
        status = STATUS_COMPLETED_WITH_WARNINGS
        recommendation = "review_content_value_warnings"
    elif segment_scores:
        status = STATUS_OK
        recommendation = "review_content_value_segments"
    else:
        status = STATUS_SKIPPED_NO_INPUTS
        recommendation = "content_value_skipped_no_inputs"

    return ContentValueResult(
        status=status,
        segment_scores=segment_scores,
        segment_score_count=len(segment_scores),
        high_value_count=high_count,
        mid_value_count=mid_count,
        low_value_count=low_count,
        protected_context_count=protected_count,
        hook_candidate_count=hook_count,
        technical_warning_count=technical_count,
        avg_content_value_score=round(sum(values) / len(values), 6)
        if values
        else 0.0,
        max_content_value_score=round(max(values), 6) if values else 0.0,
        min_content_value_score=round(min(values), 6) if values else 0.0,
        recommendation=recommendation,
        warnings=warnings,
        errors=errors,
        metadata=dict(metadata or {}),
    )


def calculate_content_value(
    job_or_sources: Any = None,
    transcript_segments: Any = None,
    keyword_emotion_report: Any = None,
    interaction_classification_report: Any = None,
    sentence_boundary_report: Any = None,
    dead_content_report: Any = None,
    filler_word_report: Any = None,
    silence_classification_report: Any = None,
    visual_energy_report: Any = None,
    face_reaction_report: Any = None,
    motion_analysis_report: Any = None,
    screen_content_report: Any = None,
    scene_change_report: Any = None,
    energy_peak_report: Any = None,
    audio_normalization_report: Any = None,
    stutter_detection_report: Any = None,
    metadata: dict[str, Any] | None = None,
) -> ContentValueResult:
    try:
        segments = _extract_transcript_segments(transcript_segments, job_or_sources)
        if not segments:
            return ContentValueResult(
                status=STATUS_SKIPPED_NO_INPUTS,
                segment_scores=[],
                segment_score_count=0,
                recommendation="content_value_skipped_no_inputs",
                warnings=["no_transcript_segments_available"],
                errors=[],
                metadata=dict(metadata or {}),
            )

        if keyword_emotion_report is None:
            keyword_emotion_report = _job_attr(job_or_sources, "keyword_emotion_report")
        if interaction_classification_report is None:
            interaction_classification_report = _job_attr(
                job_or_sources,
                "interaction_classification_report",
            )
        if sentence_boundary_report is None:
            sentence_boundary_report = _job_attr(job_or_sources, "sentence_boundary_report")
        if dead_content_report is None:
            dead_content_report = _job_attr(job_or_sources, "dead_content_report")
        if filler_word_report is None:
            filler_word_report = _job_attr(job_or_sources, "filler_word_report")
        if silence_classification_report is None:
            silence_classification_report = (
                _job_attr(job_or_sources, "silence_classification_report")
                or {"classifications": _job_attr(job_or_sources, "silence_classifications")}
            )
        if visual_energy_report is None:
            visual_energy_report = _job_attr(job_or_sources, "visual_energy_report")
        if face_reaction_report is None:
            face_reaction_report = _job_attr(job_or_sources, "face_reaction_report")
        if motion_analysis_report is None:
            motion_analysis_report = _job_attr(job_or_sources, "motion_analysis_report")
        if screen_content_report is None:
            screen_content_report = _job_attr(job_or_sources, "screen_content_report")
        if scene_change_report is None:
            scene_change_report = _job_attr(job_or_sources, "scene_change_report")
        if energy_peak_report is None:
            energy_peak_report = _job_attr(job_or_sources, "energy_peak_report")
        if audio_normalization_report is None:
            audio_normalization_report = _job_attr(
                job_or_sources,
                "audio_normalization_report",
            )
        if stutter_detection_report is None:
            stutter_detection_report = _job_attr(job_or_sources, "stutter_detection_report")

        related_sources = _collect_related_sources(
            keyword_emotion_report=keyword_emotion_report,
            interaction_classification_report=interaction_classification_report,
            sentence_boundary_report=sentence_boundary_report,
            dead_content_report=dead_content_report,
            filler_word_report=filler_word_report,
            silence_classification_report=silence_classification_report,
            visual_energy_report=visual_energy_report,
            face_reaction_report=face_reaction_report,
            motion_analysis_report=motion_analysis_report,
            screen_content_report=screen_content_report,
            scene_change_report=scene_change_report,
            energy_peak_report=energy_peak_report,
            audio_normalization_report=audio_normalization_report,
            stutter_detection_report=stutter_detection_report,
        )
        segment_scores = [
            score_content_value_segment(
                segment,
                source_index=index,
                related_sources=related_sources,
                metadata=metadata,
            )
            for index, segment in enumerate(segments)
        ]
        return build_content_value_result(segment_scores, metadata=metadata)
    except Exception as exc:
        return ContentValueResult(
            status=STATUS_FAILED,
            segment_scores=[],
            segment_score_count=0,
            recommendation="content_value_failed",
            warnings=[],
            errors=[f"content_value_calculation_failed:{exc}"],
            metadata=dict(metadata or {}),
        )
