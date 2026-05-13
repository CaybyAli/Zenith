from __future__ import annotations

from typing import Any

from models.segment_classification import (
    SEGMENT_TYPE_CENSOR_REQUIRED_SEGMENT,
    SEGMENT_TYPE_DEAD_CANDIDATE,
    SEGMENT_TYPE_FILLER,
    SEGMENT_TYPE_HIGHLIGHT,
    SEGMENT_TYPE_HOOK_CANDIDATE,
    SEGMENT_TYPE_NORMAL_CONTENT,
    SEGMENT_TYPE_PROTECTED_CONTEXT,
    SEGMENT_TYPE_TECHNICAL_WARNING,
    SEGMENT_TYPE_TRANSITION,
    SEGMENT_TYPE_UNKNOWN,
    STATUS_OK,
    STATUS_SKIPPED_NO_UNIFIED_SIGNALS,
    SegmentClassification,
    SegmentClassificationResult,
)


HIGHLIGHT_SIGNAL_TYPES = {
    "content_value_high_segment",
    "keyword_hype_segment",
    "keyword_shock_segment",
    "keyword_laugh_segment",
    "face_high_reaction_segment",
    "visual_peak_energy_segment",
    "energy_peak_segment",
    "high_energy_segment",
}

HOOK_SIGNAL_TYPES = {
    "content_value_hook_candidate",
    "hook_candidate_segment",
    "opening_hook_candidate",
}

PROTECTED_SIGNAL_TYPES = {
    "sentence_boundary_protection",
    "sentence_question_context_protection",
    "sentence_protection_zone",
    "interaction_question_answer_segment",
    "interaction_context_needed_segment",
    "dead_content_protected_context_candidate",
    "content_value_protected_context",
}

DEAD_SIGNAL_TYPES = {
    "dead_content_dead_air_candidate",
    "dead_content_low_value_candidate",
    "dead_content_high_score_candidate",
    "content_value_low_segment",
    "screen_loading_segment",
    "motion_dead_visual_candidate",
}

CENSOR_SIGNAL_TYPES = {
    "profanity_censor_sfx_required",
    "profanity_censor_word_timed_overlay",
    "profanity_censor_segment_fallback_overlay",
}

TECHNICAL_SIGNAL_TYPES = {
    "stutter_segment_candidate",
    "freeze_segment_candidate",
    "visual_technical_warning_segment",
    "content_value_technical_warning",
}

TRANSITION_SIGNAL_TYPES = {
    "scene_hard_cut_point",
    "scene_soft_transition",
    "screen_menu_segment",
    "screen_scoreboard_segment",
}

FILLER_SIGNAL_TYPES = {
    "filler_word",
    "filler_words",
    "filler_word_signal",
    "filler_pause_candidate",
    "filler_pause_segment",
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


def _first_present(data: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in data and data.get(key) is not None:
            return data.get(key)
    return None


def _as_float_or_none(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_field(signal: Any, key: str, default: Any = None) -> Any:
    if isinstance(signal, dict):
        return signal.get(key, default)

    return getattr(signal, key, default)


def normalize_signal(signal: Any) -> dict[str, Any]:
    if signal is None:
        return {
            "signal_id": "",
            "signal_type": "",
            "source": "",
            "start_seconds": None,
            "end_seconds": None,
            "center_seconds": None,
            "score": 0.0,
            "confidence": 0.0,
            "priority": "",
            "action_hint": "",
            "metadata": {},
            "raw": {},
        }

    if isinstance(signal, dict):
        raw = dict(signal)
    elif hasattr(signal, "to_dict"):
        raw = dict(signal.to_dict())
    else:
        raw = {
            "signal_id": _read_field(signal, "signal_id", ""),
            "id": _read_field(signal, "id", ""),
            "signal_type": _read_field(signal, "signal_type", ""),
            "type": _read_field(signal, "type", ""),
            "source": _read_field(signal, "source", ""),
            "start_seconds": _read_field(signal, "start_seconds", None),
            "end_seconds": _read_field(signal, "end_seconds", None),
            "center_seconds": _read_field(signal, "center_seconds", None),
            "score": _read_field(signal, "score", None),
            "confidence": _read_field(signal, "confidence", None),
            "priority": _read_field(signal, "priority", ""),
            "action_hint": _read_field(signal, "action_hint", ""),
            "metadata": _read_field(signal, "metadata", {}),
        }

    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}

    signal_type = str(
        _first_present(raw, ["signal_type", "type", "label", "kind"])
        or metadata.get("signal_type")
        or ""
    )

    start_seconds = _as_float_or_none(
        _first_present(raw, ["start_seconds", "start", "start_time", "start_sec"])
    )
    end_seconds = _as_float_or_none(
        _first_present(raw, ["end_seconds", "end", "end_time", "end_sec"])
    )
    center_seconds = _as_float_or_none(
        _first_present(raw, ["center_seconds", "timestamp_seconds", "timestamp", "time_seconds"])
    )

    if center_seconds is None and start_seconds is not None and end_seconds is not None:
        center_seconds = (start_seconds + end_seconds) / 2.0
    elif center_seconds is None and start_seconds is not None:
        center_seconds = start_seconds
    elif center_seconds is None and end_seconds is not None:
        center_seconds = end_seconds

    score = clamp_score(
        _first_present(raw, ["score", "segment_score", "value", "weight"])
        or metadata.get("score")
        or 0.0
    )
    confidence = clamp_score(
        _first_present(raw, ["confidence", "confidence_score"])
        or metadata.get("confidence")
        or score
    )

    return {
        "signal_id": str(_first_present(raw, ["signal_id", "id"]) or ""),
        "signal_type": signal_type,
        "source": str(raw.get("source") or metadata.get("source") or ""),
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "score": score,
        "confidence": confidence,
        "priority": str(raw.get("priority") or metadata.get("priority") or ""),
        "action_hint": str(raw.get("action_hint") or metadata.get("action_hint") or ""),
        "metadata": metadata,
        "raw": raw,
    }


def _signal_position(signal: dict[str, Any]) -> float:
    center_seconds = signal.get("center_seconds")
    if center_seconds is not None:
        return float(center_seconds)

    start_seconds = signal.get("start_seconds")
    if start_seconds is not None:
        return float(start_seconds)

    end_seconds = signal.get("end_seconds")
    if end_seconds is not None:
        return float(end_seconds)

    return 0.0


def _make_window(signals: list[dict[str, Any]], index: int) -> dict[str, Any]:
    starts = [
        signal.get("start_seconds")
        for signal in signals
        if signal.get("start_seconds") is not None
    ]
    ends = [
        signal.get("end_seconds")
        for signal in signals
        if signal.get("end_seconds") is not None
    ]
    centers = [
        signal.get("center_seconds")
        for signal in signals
        if signal.get("center_seconds") is not None
    ]

    start_seconds = min(starts) if starts else (min(centers) if centers else None)
    end_seconds = max(ends) if ends else (max(centers) if centers else None)

    if start_seconds is not None and end_seconds is not None:
        center_seconds = (float(start_seconds) + float(end_seconds)) / 2.0
        duration_seconds = max(0.0, float(end_seconds) - float(start_seconds))
    elif centers:
        center_seconds = float(centers[0])
        duration_seconds = None
    else:
        center_seconds = None
        duration_seconds = None

    return {
        "window_id": f"segment_window_{index + 1}",
        "signals": signals,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
    }


def build_signal_windows(
    unified_signals: list[Any] | tuple[Any, ...] | None,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not unified_signals:
        return []

    options = dict(metadata or {})
    cluster_gap_seconds = float(options.get("cluster_gap_seconds", 2.5))

    normalized_signals = [normalize_signal(signal) for signal in unified_signals]
    normalized_signals = [
        signal for signal in normalized_signals if signal.get("signal_type")
    ]

    if not normalized_signals:
        return []

    normalized_signals.sort(key=_signal_position)

    windows: list[dict[str, Any]] = []
    current_signals: list[dict[str, Any]] = []
    current_end: float | None = None
    current_center: float | None = None

    for signal in normalized_signals:
        signal_start = signal.get("start_seconds")
        signal_end = signal.get("end_seconds")
        signal_center = signal.get("center_seconds")

        has_time = (
            signal_start is not None
            or signal_end is not None
            or signal_center is not None
        )

        if not current_signals:
            current_signals = [signal]
            current_end = signal_end if signal_end is not None else signal_center
            current_center = signal_center
            continue

        if not has_time:
            windows.append(_make_window(current_signals, len(windows)))
            current_signals = [signal]
            current_end = None
            current_center = None
            continue

        close_to_current_end = (
            current_end is not None
            and signal_start is not None
            and float(signal_start) <= float(current_end) + cluster_gap_seconds
        )
        close_to_current_center = (
            current_center is not None
            and signal_center is not None
            and abs(float(signal_center) - float(current_center)) <= cluster_gap_seconds
        )

        if close_to_current_end or close_to_current_center:
            current_signals.append(signal)
            if signal_end is not None:
                current_end = max(float(current_end or signal_end), float(signal_end))
            elif signal_center is not None:
                current_end = max(float(current_end or signal_center), float(signal_center))
            if signal_center is not None:
                current_center = float(signal_center)
        else:
            windows.append(_make_window(current_signals, len(windows)))
            current_signals = [signal]
            current_end = signal_end if signal_end is not None else signal_center
            current_center = signal_center

    if current_signals:
        windows.append(_make_window(current_signals, len(windows)))

    return windows


def _max_score_for_types(signals: list[dict[str, Any]], signal_types: set[str]) -> float:
    matching_scores = [
        max(signal.get("score", 0.0), signal.get("confidence", 0.0), 0.75)
        for signal in signals
        if signal.get("signal_type") in signal_types
    ]
    return clamp_score(max(matching_scores) if matching_scores else 0.0)


def infer_segment_type(evidence: dict[str, Any]) -> str:
    if evidence.get("censor_required"):
        return SEGMENT_TYPE_CENSOR_REQUIRED_SEGMENT

    if evidence.get("protection_score", 0.0) >= 0.75:
        return SEGMENT_TYPE_PROTECTED_CONTEXT

    if evidence.get("hook_candidate_score", 0.0) >= 0.75:
        return SEGMENT_TYPE_HOOK_CANDIDATE

    if evidence.get("content_value_score", 0.0) >= 0.75:
        return SEGMENT_TYPE_HIGHLIGHT

    if evidence.get("dead_content_score", 0.0) >= 0.75:
        return SEGMENT_TYPE_DEAD_CANDIDATE

    if evidence.get("technical_risk_score", 0.0) >= 0.75:
        return SEGMENT_TYPE_TECHNICAL_WARNING

    if evidence.get("transition_score", 0.0) >= 0.75:
        return SEGMENT_TYPE_TRANSITION

    if evidence.get("filler_score", 0.0) >= 0.75:
        return SEGMENT_TYPE_FILLER

    if evidence.get("signal_types"):
        return SEGMENT_TYPE_NORMAL_CONTENT

    return SEGMENT_TYPE_UNKNOWN


def classify_signal_window(
    window: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> SegmentClassification:
    signals = list(window.get("signals") or [])
    signal_types = [str(signal.get("signal_type") or "") for signal in signals]
    source_signal_ids = [
        str(signal.get("signal_id"))
        for signal in signals
        if signal.get("signal_id")
    ]

    content_value_score = max(
        _max_score_for_types(signals, HIGHLIGHT_SIGNAL_TYPES),
        _max_score_for_types(signals, HOOK_SIGNAL_TYPES),
    )
    hook_candidate_score = _max_score_for_types(signals, HOOK_SIGNAL_TYPES)
    protection_score = _max_score_for_types(signals, PROTECTED_SIGNAL_TYPES)
    dead_content_score = _max_score_for_types(signals, DEAD_SIGNAL_TYPES)
    technical_risk_score = _max_score_for_types(signals, TECHNICAL_SIGNAL_TYPES)
    transition_score = _max_score_for_types(signals, TRANSITION_SIGNAL_TYPES)
    filler_score = _max_score_for_types(signals, FILLER_SIGNAL_TYPES)
    censor_required = any(
        signal.get("signal_type") in CENSOR_SIGNAL_TYPES for signal in signals
    )

    evidence = {
        "signal_types": signal_types,
        "source_count": len(signals),
        "content_value_score": content_value_score,
        "dead_content_score": dead_content_score,
        "protection_score": protection_score,
        "technical_risk_score": technical_risk_score,
        "hook_candidate_score": hook_candidate_score,
        "transition_score": transition_score,
        "filler_score": filler_score,
        "censor_required": censor_required,
    }

    segment_type = infer_segment_type(evidence)

    is_highlight_candidate = segment_type == SEGMENT_TYPE_HIGHLIGHT
    is_hook_candidate = segment_type == SEGMENT_TYPE_HOOK_CANDIDATE
    is_protected_context = (
        segment_type == SEGMENT_TYPE_PROTECTED_CONTEXT or protection_score >= 0.75
    )
    is_dead_candidate = segment_type == SEGMENT_TYPE_DEAD_CANDIDATE
    is_transition_candidate = segment_type == SEGMENT_TYPE_TRANSITION
    is_technical_warning = segment_type == SEGMENT_TYPE_TECHNICAL_WARNING

    segment_score = clamp_score(
        max(
            content_value_score,
            hook_candidate_score,
            protection_score,
            dead_content_score,
            technical_risk_score,
            transition_score,
            filler_score,
            0.5 if censor_required else 0.0,
        )
    )

    confidence = clamp_score(max(segment_score, 0.65 if signal_types else 0.0))

    recommendation = "review_segment"
    if segment_type == SEGMENT_TYPE_HIGHLIGHT:
        recommendation = "review_segment_highlight_candidate"
    elif segment_type == SEGMENT_TYPE_HOOK_CANDIDATE:
        recommendation = "review_segment_hook_candidate"
    elif segment_type == SEGMENT_TYPE_PROTECTED_CONTEXT:
        recommendation = "protect_segment_context"
    elif segment_type == SEGMENT_TYPE_DEAD_CANDIDATE:
        recommendation = "review_segment_dead_candidate"
    elif segment_type == SEGMENT_TYPE_CENSOR_REQUIRED_SEGMENT:
        recommendation = "preserve_segment_with_censor_sfx_review"
    elif segment_type == SEGMENT_TYPE_TECHNICAL_WARNING:
        recommendation = "review_segment_technical_warning"
    elif segment_type == SEGMENT_TYPE_TRANSITION:
        recommendation = "review_segment_transition"
    elif segment_type == SEGMENT_TYPE_FILLER:
        recommendation = "review_segment_filler_candidate"
    elif segment_type == SEGMENT_TYPE_NORMAL_CONTENT:
        recommendation = "review_segment_normal_content"

    return SegmentClassification(
        segment_id=str(window.get("window_id") or "segment_window"),
        start_seconds=window.get("start_seconds"),
        end_seconds=window.get("end_seconds"),
        center_seconds=window.get("center_seconds"),
        duration_seconds=window.get("duration_seconds"),
        segment_type=segment_type,
        confidence=confidence,
        segment_score=segment_score,
        content_value_score=content_value_score,
        dead_content_score=dead_content_score,
        protection_score=protection_score,
        technical_risk_score=technical_risk_score,
        hook_candidate_score=hook_candidate_score,
        censor_required=censor_required,
        is_highlight_candidate=is_highlight_candidate,
        is_hook_candidate=is_hook_candidate,
        is_protected_context=is_protected_context,
        is_dead_candidate=is_dead_candidate,
        is_transition_candidate=is_transition_candidate,
        is_technical_warning=is_technical_warning,
        recommendation=recommendation,
        evidence=evidence,
        source_signal_ids=source_signal_ids,
        warnings=[],
        errors=[],
        metadata=dict(metadata or {}),
    )


def _count_segments(segments: list[SegmentClassification], segment_type: str) -> int:
    return sum(1 for segment in segments if segment.segment_type == segment_type)


def classify_segments_from_unified_signals(
    unified_signals: list[Any] | tuple[Any, ...] | None,
    metadata: dict[str, Any] | None = None,
) -> SegmentClassificationResult:
    if not unified_signals:
        return SegmentClassificationResult(
            status=STATUS_SKIPPED_NO_UNIFIED_SIGNALS,
            segments=[],
            segment_count=0,
            recommendation="segment_classifier_skipped_no_unified_signals",
            warnings=["No unified edit signals available for segment classification."],
            metadata=dict(metadata or {}),
        )

    windows = build_signal_windows(unified_signals, metadata=metadata)

    if not windows:
        return SegmentClassificationResult(
            status=STATUS_SKIPPED_NO_UNIFIED_SIGNALS,
            segments=[],
            segment_count=0,
            recommendation="segment_classifier_skipped_no_unified_signals",
            warnings=["No usable unified edit signals available for segment classification."],
            metadata=dict(metadata or {}),
        )

    segments = [
        classify_signal_window(window, metadata=metadata)
        for window in windows
    ]

    return SegmentClassificationResult(
        status=STATUS_OK,
        segments=segments,
        segment_count=len(segments),
        highlight_count=_count_segments(segments, SEGMENT_TYPE_HIGHLIGHT),
        hook_candidate_count=_count_segments(segments, SEGMENT_TYPE_HOOK_CANDIDATE),
        protected_context_count=_count_segments(segments, SEGMENT_TYPE_PROTECTED_CONTEXT),
        dead_candidate_count=_count_segments(segments, SEGMENT_TYPE_DEAD_CANDIDATE),
        filler_count=_count_segments(segments, SEGMENT_TYPE_FILLER),
        transition_count=_count_segments(segments, SEGMENT_TYPE_TRANSITION),
        censor_required_count=_count_segments(
            segments,
            SEGMENT_TYPE_CENSOR_REQUIRED_SEGMENT,
        ),
        technical_warning_count=_count_segments(
            segments,
            SEGMENT_TYPE_TECHNICAL_WARNING,
        ),
        recommendation="review_segment_classification",
        warnings=[],
        errors=[],
        metadata={
            **dict(metadata or {}),
            "source_window_count": len(windows),
        },
    )
