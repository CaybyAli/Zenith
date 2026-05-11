from __future__ import annotations

from typing import Any

from models.silence_context import SilenceContextBuildResult, SilenceSegmentContext

HIGH_ENERGY_THRESHOLD: float = 0.75
CONTEXT_WINDOW_SECONDS: float = 1.0


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _read_segment_fields(segment: Any) -> tuple[float, float, float]:
    if isinstance(segment, dict):
        start = _safe_float(segment.get("start_seconds")) or 0.0
        end = _safe_float(segment.get("end_seconds")) or 0.0
        raw_dur = _safe_float(segment.get("duration_seconds"))
    else:
        start = _safe_float(getattr(segment, "start_seconds", None)) or 0.0
        end = _safe_float(getattr(segment, "end_seconds", None)) or 0.0
        raw_dur = _safe_float(getattr(segment, "duration_seconds", None))

    duration = raw_dur if raw_dur is not None else (end - start)
    return start, end, duration


def _items_in_window(
    timeline: list[dict[str, Any]],
    window_start: float,
    window_end: float,
    warnings: list[str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in timeline:
        if not isinstance(item, dict):
            warnings.append("timeline_item_not_dict")
            continue
        try:
            t = _safe_float(item.get("time_seconds"))
            if t is not None:
                if window_start <= t <= window_end:
                    result.append(item)
                continue
            t_start = _safe_float(item.get("start_seconds"))
            t_end = _safe_float(item.get("end_seconds"))
            if t_start is not None and t_end is not None:
                if t_start <= window_end and t_end >= window_start:
                    result.append(item)
                continue
            warnings.append("timeline_item_missing_time_fields")
        except Exception:
            warnings.append("timeline_item_parse_error")
    return result


def _best_energy(items: list[dict[str, Any]], warnings: list[str]) -> float | None:
    best: float | None = None
    for item in items:
        raw = item.get("energy_score")
        val = _safe_float(raw)
        if val is None:
            if raw is not None:
                warnings.append(f"energy_score_not_numeric: {raw!r}")
            continue
        if best is None or val > best:
            best = val
    return best


def _any_is_peak(items: list[dict[str, Any]]) -> bool:
    for item in items:
        if item.get("is_peak") is True:
            return True
    return False


def _best_content(items: list[dict[str, Any]], warnings: list[str]) -> float | None:
    best: float | None = None
    for item in items:
        raw = item.get("content_value")
        val = _safe_float(raw)
        if val is None:
            if raw is not None:
                warnings.append(f"content_value_not_numeric: {raw!r}")
            continue
        if best is None or val > best:
            best = val
    return best


def _speech_overlap(
    speech_segments: list[dict[str, Any]],
    window_start: float,
    window_end: float,
    warnings: list[str],
) -> bool:
    for seg in speech_segments:
        if not isinstance(seg, dict):
            warnings.append("speech_segment_not_dict")
            continue
        try:
            s = _safe_float(seg.get("start_seconds"))
            e = _safe_float(seg.get("end_seconds"))
            if s is None or e is None:
                warnings.append("speech_segment_missing_endpoints")
                continue
            if s <= window_end and e >= window_start:
                return True
        except Exception:
            warnings.append("speech_segment_parse_error")
    return False


def build_silence_segment_context(
    segment: Any,
    energy_timeline: list[dict[str, Any]] | None = None,
    content_timeline: list[dict[str, Any]] | None = None,
    speech_segments: list[dict[str, Any]] | None = None,
    high_energy_threshold: float = HIGH_ENERGY_THRESHOLD,
    context_window_seconds: float = CONTEXT_WINDOW_SECONDS,
) -> SilenceSegmentContext:
    warnings: list[str] = []
    errors: list[str] = []

    try:
        start, end, duration = _read_segment_fields(segment)
    except Exception as exc:
        errors.append(f"segment_parse_failed: {exc}")
        return SilenceSegmentContext(
            start_seconds=0.0,
            end_seconds=0.0,
            duration_seconds=0.0,
            warnings=warnings,
            errors=errors,
        )

    prev_window_start = start - context_window_seconds
    prev_window_end = start
    next_window_start = end
    next_window_end = end + context_window_seconds

    previous_energy_score: float | None = None
    next_energy_score: float | None = None
    previous_is_peak: bool = False
    next_is_peak: bool = False

    if energy_timeline is not None:
        prev_energy_items = _items_in_window(energy_timeline, prev_window_start, prev_window_end, warnings)
        next_energy_items = _items_in_window(energy_timeline, next_window_start, next_window_end, warnings)

        previous_energy_score = _best_energy(prev_energy_items, warnings)
        next_energy_score = _best_energy(next_energy_items, warnings)

        previous_is_peak = _any_is_peak(prev_energy_items) or (
            previous_energy_score is not None and previous_energy_score >= high_energy_threshold
        )
        next_is_peak = _any_is_peak(next_energy_items) or (
            next_energy_score is not None and next_energy_score >= high_energy_threshold
        )

    is_after_high_energy = (
        (previous_energy_score is not None and previous_energy_score >= high_energy_threshold)
        or previous_is_peak
    )
    is_before_high_energy = (
        (next_energy_score is not None and next_energy_score >= high_energy_threshold)
        or next_is_peak
    )

    previous_content_value: float | None = None
    next_content_value: float | None = None

    if content_timeline is not None:
        prev_content_items = _items_in_window(content_timeline, prev_window_start, prev_window_end, warnings)
        next_content_items = _items_in_window(content_timeline, next_window_start, next_window_end, warnings)
        previous_content_value = _best_content(prev_content_items, warnings)
        next_content_value = _best_content(next_content_items, warnings)

    previous_has_speech: bool | None = None
    next_has_speech: bool | None = None

    if speech_segments is not None:
        previous_has_speech = _speech_overlap(speech_segments, prev_window_start, prev_window_end, warnings)
        next_has_speech = _speech_overlap(speech_segments, next_window_start, next_window_end, warnings)

    return SilenceSegmentContext(
        start_seconds=start,
        end_seconds=end,
        duration_seconds=duration,
        previous_energy_score=previous_energy_score,
        next_energy_score=next_energy_score,
        previous_content_value=previous_content_value,
        next_content_value=next_content_value,
        previous_is_peak=previous_is_peak,
        next_is_peak=next_is_peak,
        is_after_high_energy=is_after_high_energy,
        is_before_high_energy=is_before_high_energy,
        previous_has_speech=previous_has_speech,
        next_has_speech=next_has_speech,
        warnings=warnings,
        errors=errors,
    )


def build_silence_contexts(
    segments: list[Any],
    energy_timeline: list[dict[str, Any]] | None = None,
    content_timeline: list[dict[str, Any]] | None = None,
    speech_segments: list[dict[str, Any]] | None = None,
    high_energy_threshold: float = HIGH_ENERGY_THRESHOLD,
    context_window_seconds: float = CONTEXT_WINDOW_SECONDS,
) -> SilenceContextBuildResult:
    if not isinstance(segments, list):
        return SilenceContextBuildResult(
            status="failed",
            errors=["invalid_segments_input"],
        )

    contexts: list[SilenceSegmentContext] = []
    warnings: list[str] = []
    errors: list[str] = []

    for i, seg in enumerate(segments):
        try:
            ctx = build_silence_segment_context(
                segment=seg,
                energy_timeline=energy_timeline,
                content_timeline=content_timeline,
                speech_segments=speech_segments,
                high_energy_threshold=high_energy_threshold,
                context_window_seconds=context_window_seconds,
            )
            contexts.append(ctx)
            warnings.extend(ctx.warnings)
            errors.extend(ctx.errors)
        except Exception as exc:
            warnings.append(f"segment_{i}_context_failed: {exc}")

    high_energy_count = sum(
        1 for c in contexts if c.is_after_high_energy or c.is_before_high_energy
    )

    status = "ok"
    if errors:
        status = "completed_with_warnings"
    elif warnings:
        status = "completed_with_warnings"

    return SilenceContextBuildResult(
        status=status,
        contexts=contexts,
        context_count=len(contexts),
        high_energy_context_count=high_energy_count,
        warnings=warnings,
        errors=errors,
    )


def build_silence_contexts_from_detection_result(
    detection_result: Any,
    energy_timeline: list[dict[str, Any]] | None = None,
    content_timeline: list[dict[str, Any]] | None = None,
    speech_segments: list[dict[str, Any]] | None = None,
    high_energy_threshold: float = HIGH_ENERGY_THRESHOLD,
    context_window_seconds: float = CONTEXT_WINDOW_SECONDS,
) -> SilenceContextBuildResult:
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
            return SilenceContextBuildResult(
                status="failed",
                errors=["invalid_detection_result_type"],
            )
    except Exception as exc:
        return SilenceContextBuildResult(
            status="failed",
            errors=[f"detection_result_parse_failed: {exc}"],
        )

    if not segments:
        return SilenceContextBuildResult(
            status="ok",
            contexts=[],
            context_count=0,
        )

    return build_silence_contexts(
        segments=segments,
        energy_timeline=energy_timeline,
        content_timeline=content_timeline,
        speech_segments=speech_segments,
        high_energy_threshold=high_energy_threshold,
        context_window_seconds=context_window_seconds,
    )
