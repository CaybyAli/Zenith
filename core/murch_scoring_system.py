from __future__ import annotations

from typing import Any

from models.murch_scoring import (
    MURCH_TIER_HIGH,
    MURCH_TIER_LOW,
    MURCH_TIER_MEDIUM,
    MURCH_TIER_PROTECTED,
    MURCH_TIER_TECHNICAL_WARNING,
    MURCH_TIER_UNKNOWN,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_OK,
    STATUS_SKIPPED_NO_SEGMENTS,
    MurchScoreBreakdown,
    MurchScoringResult,
    MurchSegmentScore,
)


EMOTION_SIGNAL_TYPES = {
    "segment_highlight_candidate",
    "segment_hook_candidate",
    "content_value_high_segment",
    "content_value_hook_candidate",
    "keyword_hype_segment",
    "keyword_shock_segment",
    "keyword_laugh_segment",
    "face_high_reaction_segment",
    "visual_peak_energy_segment",
    "energy_peak_segment",
    "high_energy_segment",
    "audio_peak_segment",
}

STORY_SIGNAL_TYPES = {
    "segment_protected_context",
    "interaction_question_answer_segment",
    "interaction_context_needed_segment",
    "sentence_question_context_protection",
    "sentence_boundary_protection",
    "sentence_protection_zone",
    "content_value_protected_context",
    "content_value_high_segment",
}

RHYTHM_SIGNAL_TYPES = {
    "beat_peak_segment",
    "beat_strong_segment",
    "energy_peak_segment",
    "high_energy_segment",
    "visual_peak_energy_segment",
    "visual_high_energy_segment",
    "motion_high_segment",
    "motion_peak_segment",
}

EYE_TRACE_SIGNAL_TYPES = {
    "face_high_reaction_segment",
    "visual_peak_energy_segment",
    "visual_high_energy_segment",
    "motion_high_segment",
    "motion_peak_segment",
    "screen_gameplay_segment",
    "screen_victory_segment",
    "scene_hard_cut_point",
    "scene_soft_transition",
}

TECHNICAL_SIGNAL_TYPES = {
    "stutter_segment_candidate",
    "freeze_segment_candidate",
    "visual_technical_warning_segment",
    "content_value_technical_warning",
    "screen_black_segment",
    "screen_loading_segment",
}

DEAD_SIGNAL_TYPES = {
    "dead_content_dead_air_candidate",
    "dead_content_low_value_candidate",
    "dead_content_high_score_candidate",
    "content_value_low_segment",
    "motion_dead_visual_candidate",
}

CENSOR_SIGNAL_TYPES = {
    "profanity_censor_sfx_required",
    "profanity_censor_word_timed_overlay",
    "profanity_censor_segment_fallback_overlay",
}

PROTECTED_SIGNAL_TYPES = {
    "segment_protected_context",
    "interaction_question_answer_segment",
    "interaction_context_needed_segment",
    "sentence_question_context_protection",
    "sentence_boundary_protection",
    "sentence_protection_zone",
    "content_value_protected_context",
}


def clamp_score(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0

    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


def default_murch_weights() -> dict[str, float]:
    return {
        "emotion": 0.51,
        "story": 0.23,
        "rhythm": 0.10,
        "eye_trace": 0.07,
        "screen_direction": 0.05,
        "spatial_continuity": 0.04,
    }


def _read_field(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _as_dict(item: Any) -> dict[str, Any]:
    if item is None:
        return {}
    if isinstance(item, dict):
        return dict(item)
    if hasattr(item, "to_dict"):
        return dict(item.to_dict())
    return dict(getattr(item, "__dict__", {}) or {})


def _normalize_signal(signal: Any) -> dict[str, Any]:
    data = _as_dict(signal)
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}

    return {
        "signal_id": str(data.get("signal_id") or data.get("id") or ""),
        "signal_type": str(
            data.get("signal_type")
            or data.get("type")
            or data.get("label")
            or metadata.get("signal_type")
            or ""
        ),
        "source": str(data.get("source") or metadata.get("source") or ""),
        "score": clamp_score(
            data.get("score")
            or data.get("segment_score")
            or data.get("confidence")
            or metadata.get("score")
            or 0.0
        ),
        "confidence": clamp_score(
            data.get("confidence")
            or data.get("score")
            or metadata.get("confidence")
            or 0.0
        ),
        "start_seconds": data.get("start_seconds"),
        "end_seconds": data.get("end_seconds"),
        "center_seconds": data.get("center_seconds"),
        "metadata": metadata,
        "raw": data,
    }


def _extract_signals(unified_signals: Any) -> list[dict[str, Any]]:
    if unified_signals is None:
        return []

    if isinstance(unified_signals, dict):
        raw_signals = unified_signals.get("signals") or []
    elif hasattr(unified_signals, "signals"):
        raw_signals = getattr(unified_signals, "signals") or []
    else:
        raw_signals = unified_signals or []

    if not isinstance(raw_signals, (list, tuple)):
        return []

    return [_normalize_signal(signal) for signal in raw_signals]


def _segment_signal_ids(segment: Any) -> set[str]:
    source_signal_ids = _read_field(segment, "source_signal_ids", []) or []
    return {str(signal_id) for signal_id in source_signal_ids if signal_id}


def _segment_time_value(segment: Any, key: str) -> float | None:
    value = _read_field(segment, key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _signal_time_value(signal: dict[str, Any], key: str) -> float | None:
    value = signal.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _times_overlap(segment: Any, signal: dict[str, Any]) -> bool:
    segment_start = _segment_time_value(segment, "start_seconds")
    segment_end = _segment_time_value(segment, "end_seconds")
    signal_start = _signal_time_value(signal, "start_seconds")
    signal_end = _signal_time_value(signal, "end_seconds")
    signal_center = _signal_time_value(signal, "center_seconds")

    if segment_start is None or segment_end is None:
        return False

    if signal_center is not None:
        return segment_start <= signal_center <= segment_end

    if signal_start is None or signal_end is None:
        return False

    return signal_start <= segment_end and signal_end >= segment_start


def _related_signals_for_segment(
    segment: Any,
    unified_signals: Any,
) -> list[dict[str, Any]]:
    signals = _extract_signals(unified_signals)
    if not signals:
        return []

    source_ids = _segment_signal_ids(segment)
    if source_ids:
        matched = [
            signal
            for signal in signals
            if signal.get("signal_id") and signal.get("signal_id") in source_ids
        ]
        if matched:
            return matched

    overlapped = [
        signal
        for signal in signals
        if _times_overlap(segment, signal)
    ]
    if overlapped:
        return overlapped

    return []


def _signal_types_from_segment_and_signals(
    segment: Any,
    related_signals: list[dict[str, Any]],
) -> set[str]:
    evidence = _read_field(segment, "evidence", {}) or {}
    if not isinstance(evidence, dict):
        evidence = {}

    signal_types = set()
    for signal_type in evidence.get("signal_types") or []:
        if signal_type:
            signal_types.add(str(signal_type))

    for signal in related_signals:
        signal_type = signal.get("signal_type")
        if signal_type:
            signal_types.add(str(signal_type))

    recommendation = str(_read_field(segment, "recommendation", "") or "")
    segment_type = str(_read_field(segment, "segment_type", "") or "")

    if _read_field(segment, "is_highlight_candidate", False):
        signal_types.add("segment_highlight_candidate")
    if _read_field(segment, "is_hook_candidate", False):
        signal_types.add("segment_hook_candidate")
    if _read_field(segment, "is_protected_context", False):
        signal_types.add("segment_protected_context")
    if _read_field(segment, "is_dead_candidate", False):
        signal_types.add("dead_content_dead_air_candidate")
    if _read_field(segment, "is_technical_warning", False):
        signal_types.add("visual_technical_warning_segment")
    if _read_field(segment, "censor_required", False):
        signal_types.add("profanity_censor_sfx_required")

    if "highlight" in segment_type:
        signal_types.add("segment_highlight_candidate")
    if "hook" in segment_type:
        signal_types.add("segment_hook_candidate")
    if "protected" in segment_type:
        signal_types.add("segment_protected_context")
    if "dead" in segment_type or "filler" in segment_type:
        signal_types.add("dead_content_low_value_candidate")
    if "technical" in segment_type:
        signal_types.add("visual_technical_warning_segment")
    if "censor" in segment_type:
        signal_types.add("profanity_censor_sfx_required")

    if "protect" in recommendation:
        signal_types.add("segment_protected_context")

    return signal_types


def _max_related_signal_score(
    related_signals: list[dict[str, Any]],
    signal_types: set[str],
) -> float:
    scores = [
        max(signal.get("score", 0.0), signal.get("confidence", 0.0), 0.75)
        for signal in related_signals
        if signal.get("signal_type") in signal_types
    ]
    return clamp_score(max(scores) if scores else 0.0)


def _base_segment_score(segment: Any) -> float:
    return clamp_score(
        _read_field(segment, "segment_score", 0.0)
        or _read_field(segment, "confidence", 0.0)
        or 0.0
    )


def _score_from_signal_presence(
    signal_types: set[str],
    wanted_types: set[str],
    base: float = 0.72,
) -> float:
    return base if signal_types.intersection(wanted_types) else 0.0


def build_murch_breakdown(
    segment: Any,
    related_signals: Any = None,
    metadata: dict[str, Any] | None = None,
) -> MurchScoreBreakdown:
    normalized_related_signals = _extract_signals(related_signals)
    signal_types = _signal_types_from_segment_and_signals(
        segment,
        normalized_related_signals,
    )

    segment_score = _base_segment_score(segment)
    content_value_score = clamp_score(_read_field(segment, "content_value_score", 0.0))
    dead_content_score = clamp_score(_read_field(segment, "dead_content_score", 0.0))
    protection_score = clamp_score(_read_field(segment, "protection_score", 0.0))
    technical_risk_score = clamp_score(_read_field(segment, "technical_risk_score", 0.0))
    hook_candidate_score = clamp_score(_read_field(segment, "hook_candidate_score", 0.0))

    emotion_score = clamp_score(
        max(
            segment_score if _read_field(segment, "is_highlight_candidate", False) else 0.0,
            hook_candidate_score,
            content_value_score,
            _score_from_signal_presence(signal_types, EMOTION_SIGNAL_TYPES),
            _max_related_signal_score(normalized_related_signals, EMOTION_SIGNAL_TYPES),
        )
    )

    story_score = clamp_score(
        max(
            content_value_score * 0.85,
            protection_score,
            _score_from_signal_presence(signal_types, STORY_SIGNAL_TYPES, base=0.70),
            _max_related_signal_score(normalized_related_signals, STORY_SIGNAL_TYPES),
            0.58 if str(_read_field(segment, "segment_type", "")) == "normal_content" else 0.0,
        )
    )

    rhythm_penalty = max(dead_content_score * 0.55, technical_risk_score * 0.35)
    rhythm_score = clamp_score(
        max(
            segment_score * 0.70,
            _score_from_signal_presence(signal_types, RHYTHM_SIGNAL_TYPES, base=0.70),
            _max_related_signal_score(normalized_related_signals, RHYTHM_SIGNAL_TYPES),
        )
        - rhythm_penalty
    )

    eye_trace_score = clamp_score(
        max(
            _score_from_signal_presence(signal_types, EYE_TRACE_SIGNAL_TYPES, base=0.68),
            _max_related_signal_score(normalized_related_signals, EYE_TRACE_SIGNAL_TYPES),
            0.58 if emotion_score >= 0.70 else 0.0,
        )
        - technical_risk_score * 0.20
    )

    screen_direction_score = clamp_score(
        0.62
        + _score_from_signal_presence(signal_types, {"motion_high_segment", "motion_peak_segment"}, base=0.12)
        - technical_risk_score * 0.30
    )

    spatial_continuity_score = clamp_score(
        0.64
        + protection_score * 0.12
        - technical_risk_score * 0.35
        - _score_from_signal_presence(signal_types, TECHNICAL_SIGNAL_TYPES, base=0.18)
    )

    weights = default_murch_weights()
    weighted_score = clamp_score(
        emotion_score * weights["emotion"]
        + story_score * weights["story"]
        + rhythm_score * weights["rhythm"]
        + eye_trace_score * weights["eye_trace"]
        + screen_direction_score * weights["screen_direction"]
        + spatial_continuity_score * weights["spatial_continuity"]
    )

    risk_penalty = clamp_score(dead_content_score * 0.18 + technical_risk_score * 0.12)
    weighted_score = clamp_score(weighted_score - risk_penalty)

    evidence = {
        "signal_types": sorted(signal_types),
        "segment_score": segment_score,
        "content_value_score": content_value_score,
        "dead_content_score": dead_content_score,
        "protection_score": protection_score,
        "technical_risk_score": technical_risk_score,
        "hook_candidate_score": hook_candidate_score,
        "risk_penalty": risk_penalty,
    }

    warnings: list[str] = []
    if dead_content_score >= 0.70:
        warnings.append("Dead or low-value content risk affects Murch score.")
    if technical_risk_score >= 0.70:
        warnings.append("Technical risk affects Murch score.")

    return MurchScoreBreakdown(
        emotion_score=emotion_score,
        story_score=story_score,
        rhythm_score=rhythm_score,
        eye_trace_score=eye_trace_score,
        screen_direction_score=screen_direction_score,
        spatial_continuity_score=spatial_continuity_score,
        weighted_score=weighted_score,
        weights=weights,
        evidence=evidence,
        warnings=warnings,
        errors=[],
        metadata=dict(metadata or {}),
    )


def classify_murch_tier(
    murch_score: float,
    protection_score: float = 0.0,
    technical_risk_score: float = 0.0,
) -> str:
    score = clamp_score(murch_score)
    protection = clamp_score(protection_score)
    technical_risk = clamp_score(technical_risk_score)

    if technical_risk >= 0.75:
        return MURCH_TIER_TECHNICAL_WARNING
    if protection >= 0.75:
        return MURCH_TIER_PROTECTED
    if score >= 0.72:
        return MURCH_TIER_HIGH
    if score >= 0.45:
        return MURCH_TIER_MEDIUM
    if score >= 0.0:
        return MURCH_TIER_LOW

    return MURCH_TIER_UNKNOWN


def _recommendation_for_segment_score(
    tier: str,
    censor_required: bool = False,
) -> str:
    if censor_required:
        return "review_murch_score_with_censor_sfx"
    if tier == MURCH_TIER_PROTECTED:
        return "review_protected_murch_context"
    if tier == MURCH_TIER_TECHNICAL_WARNING:
        return "review_technical_murch_warning"
    if tier == MURCH_TIER_HIGH:
        return "review_high_murch_score_segment"
    if tier == MURCH_TIER_MEDIUM:
        return "review_medium_murch_score_segment"
    if tier == MURCH_TIER_LOW:
        return "review_low_murch_score_segment"
    return "review_murch_score_segment"


def score_segment_with_murch(
    segment: Any,
    related_signals: Any = None,
    metadata: dict[str, Any] | None = None,
) -> MurchSegmentScore:
    segment_data = _as_dict(segment)
    breakdown = build_murch_breakdown(
        segment,
        related_signals=related_signals,
        metadata=metadata,
    )

    protection_score = clamp_score(_read_field(segment, "protection_score", 0.0))
    dead_content_risk_score = clamp_score(_read_field(segment, "dead_content_score", 0.0))
    technical_risk_score = clamp_score(_read_field(segment, "technical_risk_score", 0.0))
    censor_required = bool(_read_field(segment, "censor_required", False))

    signal_types = set(breakdown.evidence.get("signal_types") or [])
    if signal_types.intersection(CENSOR_SIGNAL_TYPES):
        censor_required = True
    if signal_types.intersection(PROTECTED_SIGNAL_TYPES):
        protection_score = max(protection_score, 0.80)
    if signal_types.intersection(DEAD_SIGNAL_TYPES):
        dead_content_risk_score = max(dead_content_risk_score, 0.70)
    if signal_types.intersection(TECHNICAL_SIGNAL_TYPES):
        technical_risk_score = max(technical_risk_score, 0.75)

    risk_score = clamp_score(
        max(dead_content_risk_score * 0.70, technical_risk_score * 0.85)
    )

    tier = classify_murch_tier(
        breakdown.weighted_score,
        protection_score=protection_score,
        technical_risk_score=technical_risk_score,
    )
    recommendation = _recommendation_for_segment_score(
        tier,
        censor_required=censor_required,
    )

    warnings = list(_read_field(segment, "warnings", []) or [])
    warnings.extend(breakdown.warnings)

    errors = list(_read_field(segment, "errors", []) or [])

    segment_id = str(
        _read_field(segment, "segment_id", "")
        or segment_data.get("id")
        or segment_data.get("window_id")
        or ""
    )

    return MurchSegmentScore(
        segment_id=segment_id,
        start_seconds=_read_field(segment, "start_seconds"),
        end_seconds=_read_field(segment, "end_seconds"),
        center_seconds=_read_field(segment, "center_seconds"),
        duration_seconds=_read_field(segment, "duration_seconds"),
        segment_type=str(_read_field(segment, "segment_type", "unknown") or "unknown"),
        murch_score=breakdown.weighted_score,
        murch_tier=tier,
        emotion_score=breakdown.emotion_score,
        story_score=breakdown.story_score,
        rhythm_score=breakdown.rhythm_score,
        eye_trace_score=breakdown.eye_trace_score,
        screen_direction_score=breakdown.screen_direction_score,
        spatial_continuity_score=breakdown.spatial_continuity_score,
        protection_score=protection_score,
        risk_score=risk_score,
        dead_content_risk_score=dead_content_risk_score,
        technical_risk_score=technical_risk_score,
        censor_required=censor_required,
        is_high_murch_score=tier == MURCH_TIER_HIGH,
        is_medium_murch_score=tier == MURCH_TIER_MEDIUM,
        is_low_murch_score=tier == MURCH_TIER_LOW,
        is_protected_context=tier == MURCH_TIER_PROTECTED or protection_score >= 0.75,
        is_censor_required=censor_required,
        recommendation=recommendation,
        evidence=breakdown.to_dict(),
        source_segment_id=segment_id,
        source_signal_ids=list(_read_field(segment, "source_signal_ids", []) or []),
        warnings=warnings,
        errors=errors,
        metadata=dict(metadata or {}),
    )


def _summary_recommendation(
    segment_scores: list[MurchSegmentScore],
) -> str:
    if not segment_scores:
        return "murch_scoring_skipped_no_segments"
    if any(score.murch_tier == MURCH_TIER_TECHNICAL_WARNING for score in segment_scores):
        return "review_murch_scoring_with_technical_warnings"
    if any(score.censor_required for score in segment_scores):
        return "review_murch_scoring_with_censor_sfx"
    if any(score.murch_tier == MURCH_TIER_PROTECTED for score in segment_scores):
        return "review_murch_scoring_with_protected_context"
    return "review_murch_scoring_result"


def score_segments_with_murch(
    segment_classifications: Any,
    unified_signals: Any = None,
    metadata: dict[str, Any] | None = None,
) -> MurchScoringResult:
    if segment_classifications is None:
        segments = []
    elif isinstance(segment_classifications, dict):
        segments = segment_classifications.get("segments") or segment_classifications.get("segment_scores") or []
    elif hasattr(segment_classifications, "segments"):
        segments = getattr(segment_classifications, "segments") or []
    else:
        segments = segment_classifications or []

    if not isinstance(segments, (list, tuple)) or not segments:
        return MurchScoringResult(
            status=STATUS_SKIPPED_NO_SEGMENTS,
            segment_scores=[],
            segment_score_count=0,
            recommendation="murch_scoring_skipped_no_segments",
            warnings=["No segment classifications available for Murch scoring."],
            errors=[],
            metadata=dict(metadata or {}),
        )

    segment_scores: list[MurchSegmentScore] = []
    warnings: list[str] = []
    errors: list[str] = []

    for index, segment in enumerate(segments):
        try:
            related_signals = _related_signals_for_segment(segment, unified_signals)
            segment_score = score_segment_with_murch(
                segment,
                related_signals=related_signals,
                metadata={
                    **dict(metadata or {}),
                    "segment_index": index,
                },
            )
            segment_scores.append(segment_score)
            warnings.extend(segment_score.warnings)
            errors.extend(segment_score.errors)
        except Exception as exc:
            errors.append(f"Murch scoring failed for segment index {index}: {exc}")

    if not segment_scores:
        return MurchScoringResult(
            status=STATUS_COMPLETED_WITH_WARNINGS,
            segment_scores=[],
            segment_score_count=0,
            recommendation="review_murch_scoring_errors",
            warnings=warnings,
            errors=errors,
            metadata=dict(metadata or {}),
        )

    murch_values = [score.murch_score for score in segment_scores]

    high_score_count = sum(1 for score in segment_scores if score.murch_tier == MURCH_TIER_HIGH)
    medium_score_count = sum(1 for score in segment_scores if score.murch_tier == MURCH_TIER_MEDIUM)
    low_score_count = sum(1 for score in segment_scores if score.murch_tier == MURCH_TIER_LOW)
    protected_context_count = sum(1 for score in segment_scores if score.is_protected_context)
    censor_required_count = sum(1 for score in segment_scores if score.censor_required)
    technical_warning_count = sum(
        1
        for score in segment_scores
        if score.murch_tier == MURCH_TIER_TECHNICAL_WARNING
    )

    status = STATUS_OK if not errors and not warnings else STATUS_COMPLETED_WITH_WARNINGS

    return MurchScoringResult(
        status=status,
        segment_scores=segment_scores,
        segment_score_count=len(segment_scores),
        high_score_count=high_score_count,
        medium_score_count=medium_score_count,
        low_score_count=low_score_count,
        protected_context_count=protected_context_count,
        censor_required_count=censor_required_count,
        technical_warning_count=technical_warning_count,
        avg_murch_score=clamp_score(sum(murch_values) / len(murch_values)),
        max_murch_score=clamp_score(max(murch_values)),
        min_murch_score=clamp_score(min(murch_values)),
        recommendation=_summary_recommendation(segment_scores),
        warnings=warnings,
        errors=errors,
        metadata=dict(metadata or {}),
    )
