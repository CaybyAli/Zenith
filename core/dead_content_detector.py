from __future__ import annotations

from typing import Any

from models.dead_content import (
    CANDIDATE_TYPE_DEAD_AIR,
    CANDIDATE_TYPE_FILLER_PAUSE,
    CANDIDATE_TYPE_LOADING_OR_MENU,
    CANDIDATE_TYPE_LOW_VALUE,
    CANDIDATE_TYPE_LOW_VISUAL_DEAD,
    CANDIDATE_TYPE_PRIVATE_OR_META,
    CANDIDATE_TYPE_PROTECTED_CONTEXT,
    CANDIDATE_TYPE_UNKNOWN,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_SKIPPED_NO_INPUTS,
    DeadContentCandidate,
    DeadContentDetectionResult,
    DeadContentSegmentScore,
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
            "dead_content_result",
            "keyword_emotion_result",
            "interaction_classification_result",
            "detection_result",
            "classification_result",
            "visual_energy_result",
            "screen_content_result",
            "sentence_boundary_result",
        ):
            nested = source_dict.get(nested_key)
            if isinstance(nested, dict):
                nested_items = _extract_report_items(nested, keys)
                if nested_items:
                    return nested_items

    return [dict(item) for item in candidates if isinstance(item, dict)]


def _items_near_segment(
    items: list[dict[str, Any]],
    start_seconds: float | None,
    end_seconds: float | None,
) -> list[dict[str, Any]]:
    if start_seconds is None or end_seconds is None:
        return []
    return [
        item
        for item in items
        if _time_overlaps(item, start_seconds, end_seconds)
    ]


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
    sentence_boundary_report: Any = None,
    keyword_emotion_report: Any = None,
    interaction_classification_report: Any = None,
    filler_word_report: Any = None,
    silence_classification_report: Any = None,
    visual_energy_report: Any = None,
    screen_content_report: Any = None,
) -> dict[str, list[dict[str, Any]]]:
    return {
        "sentence_boundaries": _extract_report_items(
            sentence_boundary_report,
            ("boundaries",),
        ),
        "sentence_protection_zones": _extract_report_items(
            sentence_boundary_report,
            ("protection_zones",),
        ),
        "keyword_scores": _extract_report_items(
            keyword_emotion_report,
            ("segment_scores", "matches"),
        ),
        "interaction_segments": _extract_report_items(
            interaction_classification_report,
            ("segment_classifications", "points"),
        ),
        "filler_occurrences": _extract_report_items(
            filler_word_report,
            ("occurrences",),
        ),
        "silence_classifications": _extract_report_items(
            silence_classification_report,
            ("classifications", "silence_classifications"),
        ),
        "visual_energy_segments": _extract_report_items(
            visual_energy_report,
            ("visual_energy_segments", "segments"),
        ),
        "screen_content_segments": _extract_report_items(
            screen_content_report,
            ("screen_content_segments", "segments"),
        ),
    }


def _score_text_value(text: str, duration_seconds: float | None) -> tuple[float, dict[str, Any]]:
    words = [part for part in text.split(" ") if part]
    word_count = len(words)
    empty_text = word_count == 0
    very_short = word_count <= 2
    short_duration = duration_seconds is not None and duration_seconds <= 0.6

    if empty_text:
        low_text_score = 0.95
    elif very_short:
        low_text_score = 0.72
    elif word_count <= 5 and short_duration:
        low_text_score = 0.55
    else:
        low_text_score = 0.15

    content_value_score = clamp_score(1.0 - low_text_score)
    return low_text_score, {
        "word_count": word_count,
        "empty_text": empty_text,
        "very_short_text": very_short,
        "short_duration": short_duration,
        "content_value_score_from_text": content_value_score,
    }


def _keyword_value(
    keyword_items: list[dict[str, Any]],
) -> tuple[float, float, list[str]]:
    if not keyword_items:
        return 0.65, 0.0, []
    scores: list[float] = []
    categories: list[str] = []
    for item in keyword_items:
        categories_dict = _safe_dict(item.get("categories"))
        for category in ("hype", "shock", "laugh", "frustration", "question"):
            score = clamp_score(
                categories_dict.get(category, item.get(f"{category}_score")),
            )
            if score > 0.0:
                scores.append(score)
                categories.append(category)
        overall = clamp_score(item.get("overall_keyword_score"))
        if overall > 0.0:
            scores.append(overall)
        if str(item.get("dominant_category") or "") in {
            "hype",
            "shock",
            "laugh",
            "question",
        }:
            categories.append(str(item.get("dominant_category")))
    high_value_score = max(scores) if scores else 0.0
    low_keyword_score = clamp_score(1.0 - high_value_score)
    return low_keyword_score, high_value_score, sorted(set(categories))


def _interaction_value(
    interaction_items: list[dict[str, Any]],
) -> tuple[float, float, bool, bool, list[str]]:
    if not interaction_items:
        return 0.55, 0.0, False, False, []

    interaction_types: list[str] = []
    context_needed = False
    private_or_meta = False
    value_scores: list[float] = []

    for item in interaction_items:
        interaction_type = str(
            item.get("interaction_type")
            or item.get("classification")
            or "unknown"
        )
        interaction_types.append(interaction_type)
        confidence = clamp_score(item.get("confidence") or 0.65)
        if bool(item.get("context_needed")):
            context_needed = True
        if bool(item.get("is_private_or_meta_candidate")) or (
            interaction_type == "private_or_meta_candidate"
        ):
            private_or_meta = True
        if interaction_type in {"interaction", "question_answer", "chat_reaction"}:
            value_scores.append(max(0.65, confidence))
        elif interaction_type in {"callout", "commentary"}:
            value_scores.append(max(0.45, confidence * 0.75))
        elif interaction_type == "monologue":
            value_scores.append(0.3)
        else:
            value_scores.append(0.2)

    value = max(value_scores) if value_scores else 0.0
    return clamp_score(1.0 - value), value, context_needed, private_or_meta, interaction_types


def _silence_value(silence_items: list[dict[str, Any]]) -> tuple[float, bool]:
    if not silence_items:
        return 0.0, False
    scores: list[float] = []
    dead_air = False
    for item in silence_items:
        label = str(item.get("classification") or item.get("silence_type") or "")
        duration = _safe_float(item.get("duration_seconds"), 0.0)
        remove_candidate = bool(item.get("remove_candidate"))
        if label in {"dead_air", "silence_remove", "long_silence"} or remove_candidate:
            dead_air = True
            scores.append(0.85)
        elif duration >= 1.0:
            dead_air = True
            scores.append(0.75)
        elif duration > 0.0:
            scores.append(0.45)
    return clamp_score(max(scores) if scores else 0.0), dead_air


def _visual_value(visual_items: list[dict[str, Any]]) -> tuple[float, float]:
    if not visual_items:
        return 0.0, 0.0
    low_scores: list[float] = []
    high_scores: list[float] = []
    for item in visual_items:
        classification = str(item.get("classification") or "")
        avg_score = clamp_score(item.get("avg_visual_energy_score"))
        max_score = clamp_score(item.get("max_visual_energy_score"))
        if classification == "low_visual_energy":
            low_scores.append(max(0.65, 1.0 - avg_score))
        elif classification in {"high_visual_energy", "peak_visual_energy"}:
            high_scores.append(max(max_score, avg_score, 0.7))
        elif avg_score > 0.0:
            if avg_score <= 0.25:
                low_scores.append(1.0 - avg_score)
            elif avg_score >= 0.65:
                high_scores.append(avg_score)
    return (
        clamp_score(max(low_scores) if low_scores else 0.0),
        clamp_score(max(high_scores) if high_scores else 0.0),
    )


def _screen_value(screen_items: list[dict[str, Any]]) -> tuple[float, float, bool, list[str]]:
    if not screen_items:
        return 0.0, 0.0, False, []
    penalty_scores: list[float] = []
    value_scores: list[float] = []
    types: list[str] = []
    loading_or_menu = False
    for item in screen_items:
        screen_type = str(item.get("screen_type") or item.get("original_screen_type") or "")
        types.append(screen_type)
        confidence = clamp_score(
            item.get("confidence")
            or item.get("avg_confidence")
            or item.get("max_confidence")
            or 0.65
        )
        if screen_type in {"menu", "lobby", "loading", "black_screen"}:
            loading_or_menu = True
            penalty_scores.append(max(0.75, confidence))
        elif screen_type in {"gameplay", "victory_screen"}:
            value_scores.append(max(0.65, confidence))
        elif screen_type in {"scoreboard", "death_screen"}:
            penalty_scores.append(0.35)
            value_scores.append(0.35)
    return (
        clamp_score(max(penalty_scores) if penalty_scores else 0.0),
        clamp_score(max(value_scores) if value_scores else 0.0),
        loading_or_menu,
        sorted(set(types)),
    )


def _filler_value(filler_items: list[dict[str, Any]], duration_seconds: float | None) -> float:
    if not filler_items:
        return 0.0
    count = len(filler_items)
    duration = sum(_safe_float(item.get("duration_seconds"), 0.0) for item in filler_items)
    if duration_seconds and duration_seconds > 0:
        ratio = min(1.0, duration / duration_seconds)
    else:
        ratio = 0.0
    return clamp_score(0.25 + min(0.45, count * 0.15) + min(0.3, ratio))


def _context_protection(
    *,
    text: str,
    sentence_items: list[dict[str, Any]],
    protection_zone_items: list[dict[str, Any]],
    keyword_high_value: float,
    keyword_categories: list[str],
    interaction_value_score: float,
    interaction_context_needed: bool,
    interaction_types: list[str],
    visual_high_score: float,
    screen_value_score: float,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    if text.endswith("?"):
        reasons.append("text_open_question")
        score = max(score, 0.8)

    for item in sentence_items:
        boundary_type = str(item.get("boundary_type") or "")
        if boundary_type in {
            "unsafe_sentence_boundary",
            "open_sentence_fragment",
            "question_boundary",
            "open_question",
        }:
            reasons.append(f"sentence_boundary:{boundary_type}")
            score = max(score, 0.85)

    if protection_zone_items:
        reasons.append("sentence_protection_zone")
        score = max(score, 0.9)

    if keyword_high_value >= 0.6 or any(
        category in {"hype", "shock", "laugh"} for category in keyword_categories
    ):
        reasons.append("keyword_emotion_high_value")
        score = max(score, keyword_high_value)

    if interaction_context_needed:
        reasons.append("interaction_context_needed")
        score = max(score, 0.85)

    if any(item == "question_answer" for item in interaction_types):
        reasons.append("interaction_question_answer")
        score = max(score, 0.85)
    elif interaction_value_score >= 0.7:
        reasons.append("interaction_value")
        score = max(score, interaction_value_score)

    if visual_high_score >= 0.7:
        reasons.append("visual_energy_high")
        score = max(score, visual_high_score)

    if screen_value_score >= 0.65:
        reasons.append("screen_content_value")
        score = max(score, screen_value_score)

    return clamp_score(score), sorted(set(reasons))


def classify_dead_content_candidate(
    score: float,
    evidence: dict[str, Any],
    protected_by_context: bool = False,
) -> str:
    if protected_by_context:
        return CANDIDATE_TYPE_PROTECTED_CONTEXT
    if bool(evidence.get("private_or_meta_candidate")):
        return CANDIDATE_TYPE_PRIVATE_OR_META
    if bool(evidence.get("loading_or_menu_candidate")):
        return CANDIDATE_TYPE_LOADING_OR_MENU
    if bool(evidence.get("dead_air_candidate")):
        return CANDIDATE_TYPE_DEAD_AIR
    if clamp_score(evidence.get("filler_score")) >= 0.65:
        return CANDIDATE_TYPE_FILLER_PAUSE
    if clamp_score(evidence.get("low_visual_score")) >= 0.65 and score >= 0.55:
        return CANDIDATE_TYPE_LOW_VISUAL_DEAD
    if score >= 0.5:
        return CANDIDATE_TYPE_LOW_VALUE
    return CANDIDATE_TYPE_UNKNOWN


def _recommendation_for_candidate(
    candidate_type: str,
    score: float,
    protected_by_context: bool,
) -> str:
    if protected_by_context:
        return "review_protected_context"
    if candidate_type == CANDIDATE_TYPE_PRIVATE_OR_META:
        return "review_private_or_meta_candidate"
    if candidate_type == CANDIDATE_TYPE_LOADING_OR_MENU:
        return "review_loading_or_menu_candidate"
    if score >= 0.5 and candidate_type != CANDIDATE_TYPE_UNKNOWN:
        return "review_dead_content_candidate"
    return "no_dead_content_priority"


def score_dead_content_segment(
    segment: Any,
    source_index: int = 0,
    related_sources: dict[str, list[dict[str, Any]]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> DeadContentSegmentScore:
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
    text = _normalize_text(
        segment_dict.get("text")
        or segment_dict.get("normalized_text")
        or segment_dict.get("transcript")
    )
    segment_id = str(
        segment_dict.get("segment_id")
        or segment_dict.get("id")
        or f"dead_content_segment_{source_index}"
    )

    related = related_sources or {}
    sentence_items = _items_near_segment(
        related.get("sentence_boundaries", []),
        start_seconds,
        end_seconds,
    )
    protection_zone_items = _items_near_segment(
        related.get("sentence_protection_zones", []),
        start_seconds,
        end_seconds,
    )
    keyword_items = _items_near_segment(
        related.get("keyword_scores", []),
        start_seconds,
        end_seconds,
    )
    interaction_items = _items_near_segment(
        related.get("interaction_segments", []),
        start_seconds,
        end_seconds,
    )
    filler_items = _items_near_segment(
        related.get("filler_occurrences", []),
        start_seconds,
        end_seconds,
    )
    silence_items = _items_near_segment(
        related.get("silence_classifications", []),
        start_seconds,
        end_seconds,
    )
    visual_items = _items_near_segment(
        related.get("visual_energy_segments", []),
        start_seconds,
        end_seconds,
    )
    screen_items = _items_near_segment(
        related.get("screen_content_segments", []),
        start_seconds,
        end_seconds,
    )

    low_text_score, text_evidence = _score_text_value(text, duration_seconds)
    low_keyword_score, keyword_high_value, keyword_categories = _keyword_value(keyword_items)
    (
        low_interaction_score,
        interaction_value_score,
        interaction_context_needed,
        private_or_meta,
        interaction_types,
    ) = _interaction_value(interaction_items)
    silence_score, dead_air = _silence_value(silence_items)
    low_visual_score, visual_high_score = _visual_value(visual_items)
    screen_penalty_score, screen_value_score, loading_or_menu, screen_types = _screen_value(screen_items)
    filler_score = _filler_value(filler_items, duration_seconds)

    context_protection_score, protection_reasons = _context_protection(
        text=text,
        sentence_items=sentence_items,
        protection_zone_items=protection_zone_items,
        keyword_high_value=keyword_high_value,
        keyword_categories=keyword_categories,
        interaction_value_score=interaction_value_score,
        interaction_context_needed=interaction_context_needed,
        interaction_types=interaction_types,
        visual_high_score=visual_high_score,
        screen_value_score=screen_value_score,
    )
    protected_by_context = context_protection_score >= 0.65

    raw_score = (
        low_text_score * 0.22
        + silence_score * 0.20
        + low_visual_score * 0.14
        + low_keyword_score * 0.12
        + low_interaction_score * 0.12
        + filler_score * 0.10
        + screen_penalty_score * 0.16
    )
    content_value_score = clamp_score(
        max(keyword_high_value, interaction_value_score, visual_high_score, screen_value_score)
    )
    score = clamp_score(raw_score - (context_protection_score * 0.35) - (content_value_score * 0.15))
    if low_text_score >= 0.9 and context_protection_score < 0.65:
        score = max(score, 0.62)
    elif low_text_score >= 0.7 and content_value_score < 0.35 and context_protection_score < 0.65:
        score = max(score, 0.54)

    evidence = {
        **text_evidence,
        "silence_score": silence_score,
        "dead_air_candidate": dead_air,
        "low_visual_score": low_visual_score,
        "visual_high_score": visual_high_score,
        "low_keyword_score": low_keyword_score,
        "keyword_high_value_score": keyword_high_value,
        "keyword_categories": keyword_categories,
        "low_interaction_score": low_interaction_score,
        "interaction_value_score": interaction_value_score,
        "interaction_context_needed": interaction_context_needed,
        "interaction_types": interaction_types,
        "private_or_meta_candidate": private_or_meta,
        "filler_score": filler_score,
        "filler_count": len(filler_items),
        "screen_penalty_score": screen_penalty_score,
        "screen_value_score": screen_value_score,
        "screen_types": screen_types,
        "loading_or_menu_candidate": loading_or_menu,
        "context_protection_score": context_protection_score,
        "protection_reasons": protection_reasons,
    }
    candidate_type = classify_dead_content_candidate(
        score,
        evidence,
        protected_by_context=protected_by_context,
    )
    review_required = candidate_type != CANDIDATE_TYPE_UNKNOWN
    recommendation = _recommendation_for_candidate(
        candidate_type,
        score,
        protected_by_context,
    )

    return DeadContentSegmentScore(
        segment_id=segment_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
        text=text,
        dead_content_score=round(score, 6),
        content_value_score=round(content_value_score, 6),
        silence_score=round(silence_score, 6),
        low_visual_score=round(low_visual_score, 6),
        low_keyword_score=round(low_keyword_score, 6),
        low_interaction_score=round(low_interaction_score, 6),
        filler_score=round(filler_score, 6),
        screen_penalty_score=round(screen_penalty_score, 6),
        context_protection_score=round(context_protection_score, 6),
        candidate_type=candidate_type,
        review_required=review_required,
        protected_by_context=protected_by_context,
        recommendation=recommendation,
        evidence=evidence,
        metadata={
            **dict(metadata or {}),
            "source_segment_index": source_index,
            "source_segment_id": segment_id,
        },
        warnings=warnings,
        errors=errors,
    )


def build_dead_content_candidates(
    segment_scores: list[DeadContentSegmentScore],
    metadata: dict[str, Any] | None = None,
) -> list[DeadContentCandidate]:
    candidates: list[DeadContentCandidate] = []
    for index, score in enumerate(segment_scores):
        if not score.review_required:
            continue
        candidate_type = score.candidate_type
        if candidate_type == CANDIDATE_TYPE_UNKNOWN:
            continue
        protection_reasons = [
            str(item)
            for item in _safe_list(score.evidence.get("protection_reasons"))
        ]
        if score.start_seconds is not None and score.end_seconds is not None:
            center_seconds = (score.start_seconds + score.end_seconds) / 2.0
        else:
            center_seconds = None
        candidates.append(
            DeadContentCandidate(
                candidate_id=f"dead_content_candidate_{index}_{score.segment_id}",
                start_seconds=score.start_seconds,
                end_seconds=score.end_seconds,
                center_seconds=center_seconds,
                duration_seconds=score.duration_seconds,
                text=score.text,
                candidate_type=candidate_type,
                dead_content_score=score.dead_content_score,
                confidence=clamp_score(
                    max(score.dead_content_score, score.context_protection_score)
                ),
                review_required=True,
                protected_by_context=score.protected_by_context,
                protection_reasons=protection_reasons,
                evidence=dict(score.evidence),
                source_segment_index=int(score.metadata.get("source_segment_index", index)),
                recommendation=score.recommendation,
                metadata={
                    **dict(metadata or {}),
                    "source_segment_id": score.segment_id,
                    "content_value_score": score.content_value_score,
                },
                warnings=list(score.warnings),
                errors=list(score.errors),
            )
        )
    return candidates


def build_dead_content_result(
    segment_scores: list[DeadContentSegmentScore],
    candidates: list[DeadContentCandidate],
    metadata: dict[str, Any] | None = None,
) -> DeadContentDetectionResult:
    warnings: list[str] = []
    errors: list[str] = []
    for score in segment_scores:
        warnings.extend(score.warnings)
        errors.extend(score.errors)
    for candidate in candidates:
        warnings.extend(candidate.warnings)
        errors.extend(candidate.errors)

    type_counts: dict[str, int] = {}
    for candidate in candidates:
        type_counts[candidate.candidate_type] = (
            type_counts.get(candidate.candidate_type, 0) + 1
        )

    if errors:
        status = STATUS_COMPLETED_WITH_WARNINGS
        recommendation = "review_dead_content_warnings"
    elif warnings:
        status = STATUS_COMPLETED_WITH_WARNINGS
        recommendation = "review_dead_content_warnings"
    else:
        status = STATUS_OK
        recommendation = (
            "review_dead_content_candidates"
            if candidates
            else "no_dead_content_priority"
        )

    return DeadContentDetectionResult(
        status=status,
        candidates=candidates,
        segment_scores=segment_scores,
        candidate_count=len(candidates),
        segment_score_count=len(segment_scores),
        dead_air_candidate_count=type_counts.get(CANDIDATE_TYPE_DEAD_AIR, 0),
        low_value_candidate_count=type_counts.get(CANDIDATE_TYPE_LOW_VALUE, 0),
        filler_pause_candidate_count=type_counts.get(CANDIDATE_TYPE_FILLER_PAUSE, 0),
        loading_or_menu_candidate_count=type_counts.get(
            CANDIDATE_TYPE_LOADING_OR_MENU,
            0,
        ),
        private_or_meta_candidate_count=type_counts.get(
            CANDIDATE_TYPE_PRIVATE_OR_META,
            0,
        ),
        protected_candidate_count=type_counts.get(CANDIDATE_TYPE_PROTECTED_CONTEXT, 0),
        high_confidence_candidate_count=sum(
            1 for candidate in candidates if candidate.confidence >= 0.75
        ),
        recommendation=recommendation,
        warnings=warnings,
        errors=errors,
        metadata=dict(metadata or {}),
    )


def detect_dead_content(
    job_or_sources: Any = None,
    transcript_segments: Any = None,
    sentence_boundary_report: Any = None,
    keyword_emotion_report: Any = None,
    interaction_classification_report: Any = None,
    filler_word_report: Any = None,
    silence_classification_report: Any = None,
    visual_energy_report: Any = None,
    screen_content_report: Any = None,
    metadata: dict[str, Any] | None = None,
) -> DeadContentDetectionResult:
    try:
        segments = _extract_transcript_segments(transcript_segments, job_or_sources)
        if not segments:
            return DeadContentDetectionResult(
                status=STATUS_SKIPPED_NO_INPUTS,
                candidates=[],
                segment_scores=[],
                candidate_count=0,
                segment_score_count=0,
                recommendation="dead_content_skipped_no_inputs",
                warnings=["no_transcript_segments_available"],
                errors=[],
                metadata=dict(metadata or {}),
            )

        if sentence_boundary_report is None:
            sentence_boundary_report = _job_attr(job_or_sources, "sentence_boundary_report")
        if keyword_emotion_report is None:
            keyword_emotion_report = _job_attr(job_or_sources, "keyword_emotion_report")
        if interaction_classification_report is None:
            interaction_classification_report = _job_attr(
                job_or_sources,
                "interaction_classification_report",
            )
        if filler_word_report is None:
            filler_word_report = _job_attr(job_or_sources, "filler_word_report")
        if silence_classification_report is None:
            silence_classification_report = (
                _job_attr(job_or_sources, "silence_classification_report")
                or {"classifications": _job_attr(job_or_sources, "silence_classifications")}
            )
        if visual_energy_report is None:
            visual_energy_report = _job_attr(job_or_sources, "visual_energy_report")
        if screen_content_report is None:
            screen_content_report = _job_attr(job_or_sources, "screen_content_report")

        related_sources = _collect_related_sources(
            sentence_boundary_report=sentence_boundary_report,
            keyword_emotion_report=keyword_emotion_report,
            interaction_classification_report=interaction_classification_report,
            filler_word_report=filler_word_report,
            silence_classification_report=silence_classification_report,
            visual_energy_report=visual_energy_report,
            screen_content_report=screen_content_report,
        )
        segment_scores = [
            score_dead_content_segment(
                segment,
                source_index=index,
                related_sources=related_sources,
                metadata=metadata,
            )
            for index, segment in enumerate(segments)
        ]
        candidates = build_dead_content_candidates(segment_scores, metadata=metadata)
        return build_dead_content_result(segment_scores, candidates, metadata=metadata)
    except Exception as exc:
        return DeadContentDetectionResult(
            status=STATUS_FAILED,
            candidates=[],
            segment_scores=[],
            candidate_count=0,
            segment_score_count=0,
            recommendation="dead_content_detection_failed",
            warnings=[],
            errors=[f"dead_content_detection_failed:{exc}"],
            metadata=dict(metadata or {}),
        )
