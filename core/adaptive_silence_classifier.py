from __future__ import annotations

from typing import Any

from models.silence_classification import SilenceClassification, SilenceClassificationResult

FILLER_PAUSE_MAX_SECONDS: float = 0.30
SENTENCE_GAP_MAX_SECONDS: float = 0.60
DRAMATIC_PAUSE_MAX_SECONDS: float = 2.00
DEAD_AIR_MIN_SECONDS: float = 2.00


def _resolve_thresholds(profile: dict[str, Any] | None) -> tuple[float, float, float, float]:
    filler = FILLER_PAUSE_MAX_SECONDS
    sentence = SENTENCE_GAP_MAX_SECONDS
    dramatic = DRAMATIC_PAUSE_MAX_SECONDS
    dead_air = DEAD_AIR_MIN_SECONDS

    if profile:
        audio = profile.get("audio", {}) if isinstance(profile, dict) else {}
        if isinstance(audio, dict):
            filler = float(audio.get("filler_pause_max_seconds", filler))
            sentence = float(audio.get("sentence_gap_max_seconds", sentence))
            dramatic = float(audio.get("dramatic_pause_max_seconds", dramatic))
            dead_air = float(audio.get("dead_air_min_seconds", dead_air))

    return filler, sentence, dramatic, dead_air


def _is_high_energy_context(context: dict[str, Any]) -> bool:
    if not context:
        return False
    if context.get("previous_is_peak") is True:
        return True
    if context.get("next_is_peak") is True:
        return True
    if context.get("is_after_high_energy") is True:
        return True
    if context.get("is_before_high_energy") is True:
        return True
    prev_energy = context.get("previous_energy_score")
    if prev_energy is not None and float(prev_energy) >= 0.75:
        return True
    next_energy = context.get("next_energy_score")
    if next_energy is not None and float(next_energy) >= 0.75:
        return True
    return False


def _segment_to_dict(segment: Any) -> dict[str, Any]:
    if isinstance(segment, dict):
        return segment
    if hasattr(segment, "to_dict"):
        return segment.to_dict()
    return {}


def _extract_duration(segment: Any) -> float | None:
    if isinstance(segment, dict):
        val = segment.get("duration_seconds")
    elif hasattr(segment, "duration_seconds"):
        val = segment.duration_seconds
    else:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _extract_endpoints(segment: Any) -> tuple[float, float]:
    if isinstance(segment, dict):
        start = float(segment.get("start_seconds", 0.0))
        end = float(segment.get("end_seconds", 0.0))
    else:
        start = float(getattr(segment, "start_seconds", 0.0))
        end = float(getattr(segment, "end_seconds", 0.0))
    return start, end


def classify_silence_segment(
    segment: Any,
    context: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
) -> SilenceClassification:
    ctx = context or {}
    source_segment = _segment_to_dict(segment)
    duration = _extract_duration(segment)
    start, end = _extract_endpoints(segment)

    filler_max, sentence_max, dramatic_max, dead_air_min = _resolve_thresholds(profile)

    if duration is None:
        return SilenceClassification(
            start_seconds=start,
            end_seconds=end,
            duration_seconds=0.0,
            classification="unknown",
            remove_candidate=False,
            confidence=0.0,
            reason="missing_duration",
            rules_applied=["missing_duration"],
            source_segment=source_segment,
            context=ctx,
            errors=["missing_duration"],
        )

    if duration < 0:
        return SilenceClassification(
            start_seconds=start,
            end_seconds=end,
            duration_seconds=duration,
            classification="unknown",
            remove_candidate=False,
            confidence=0.0,
            reason="invalid_duration",
            rules_applied=["invalid_duration"],
            source_segment=source_segment,
            context=ctx,
            errors=["invalid_duration"],
        )

    if duration <= filler_max:
        return SilenceClassification(
            start_seconds=start,
            end_seconds=end,
            duration_seconds=duration,
            classification="filler_pause",
            remove_candidate=True,
            confidence=0.85,
            reason="duration_under_filler_pause_limit",
            rules_applied=["duration_under_filler_pause_limit"],
            source_segment=source_segment,
            context=ctx,
        )

    if duration <= sentence_max:
        return SilenceClassification(
            start_seconds=start,
            end_seconds=end,
            duration_seconds=duration,
            classification="sentence_gap",
            remove_candidate=True,
            confidence=0.75,
            reason="duration_within_sentence_gap_range",
            rules_applied=["duration_within_sentence_gap_range"],
            source_segment=source_segment,
            context=ctx,
        )

    if duration <= dramatic_max:
        if _is_high_energy_context(ctx):
            return SilenceClassification(
                start_seconds=start,
                end_seconds=end,
                duration_seconds=duration,
                classification="dramatic_pause",
                remove_candidate=False,
                confidence=0.80,
                reason="high_energy_context_suggests_dramatic_pause",
                rules_applied=["high_energy_context_suggests_dramatic_pause"],
                source_segment=source_segment,
                context=ctx,
            )
        return SilenceClassification(
            start_seconds=start,
            end_seconds=end,
            duration_seconds=duration,
            classification="unknown",
            remove_candidate=False,
            confidence=0.50,
            reason="insufficient_context",
            rules_applied=["insufficient_context"],
            source_segment=source_segment,
            context=ctx,
        )

    if duration >= dead_air_min and not _is_high_energy_context(ctx):
        return SilenceClassification(
            start_seconds=start,
            end_seconds=end,
            duration_seconds=duration,
            classification="dead_air",
            remove_candidate=True,
            confidence=0.90,
            reason="duration_exceeds_dead_air_limit",
            rules_applied=["duration_exceeds_dead_air_limit"],
            source_segment=source_segment,
            context=ctx,
        )

    return SilenceClassification(
        start_seconds=start,
        end_seconds=end,
        duration_seconds=duration,
        classification="unknown",
        remove_candidate=False,
        confidence=0.50,
        reason="insufficient_context",
        rules_applied=["insufficient_context"],
        source_segment=source_segment,
        context=ctx,
    )


def classify_silence_segments(
    segments: list[Any],
    contexts: list[dict[str, Any]] | None = None,
    profile: dict[str, Any] | None = None,
) -> SilenceClassificationResult:
    if not isinstance(segments, list):
        return SilenceClassificationResult(
            status="failed",
            errors=["invalid_segments_input"],
        )

    resolved_contexts: list[dict[str, Any]] = []
    if contexts:
        resolved_contexts = list(contexts)
    while len(resolved_contexts) < len(segments):
        resolved_contexts.append({})

    classifications: list[SilenceClassification] = []
    warnings: list[str] = []
    errors: list[str] = []

    for i, seg in enumerate(segments):
        try:
            ctx = resolved_contexts[i] if i < len(resolved_contexts) else {}
            classification = classify_silence_segment(seg, context=ctx, profile=profile)
            classifications.append(classification)
        except Exception as exc:
            warnings.append(f"segment_{i}_classification_failed: {exc}")

    counts_by_classification: dict[str, int] = {}
    remove_count = 0
    keep_count = 0

    for c in classifications:
        counts_by_classification[c.classification] = (
            counts_by_classification.get(c.classification, 0) + 1
        )
        if c.remove_candidate:
            remove_count += 1
        else:
            keep_count += 1

    status = "ok"
    if errors:
        status = "failed"
    elif warnings:
        status = "completed_with_warnings"

    return SilenceClassificationResult(
        status=status,
        classifications=classifications,
        classification_count=len(classifications),
        remove_candidate_count=remove_count,
        keep_candidate_count=keep_count,
        counts_by_classification=counts_by_classification,
        warnings=warnings,
        errors=errors,
    )


def classify_silence_detection_result(
    detection_result: Any,
    contexts: list[dict[str, Any]] | None = None,
    profile: dict[str, Any] | None = None,
) -> SilenceClassificationResult:
    try:
        if isinstance(detection_result, dict):
            raw_segments = detection_result.get("segments", [])
            if not isinstance(raw_segments, list):
                raw_segments = []
            from models.silence_detection import SilenceSegment
            segments: list[Any] = [SilenceSegment.from_dict(s) for s in raw_segments]
        elif hasattr(detection_result, "segments"):
            segments = list(detection_result.segments)
        else:
            return SilenceClassificationResult(
                status="failed",
                errors=["invalid_detection_result_type"],
            )
    except Exception as exc:
        return SilenceClassificationResult(
            status="failed",
            errors=[f"detection_result_parse_failed: {exc}"],
        )

    if not segments:
        return SilenceClassificationResult(
            status="ok",
            classifications=[],
            classification_count=0,
        )

    return classify_silence_segments(segments, contexts=contexts, profile=profile)
