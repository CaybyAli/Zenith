from __future__ import annotations

import uuid
from typing import Any

from core.audio_normalization_signal_adapter import (
    adapt_audio_normalization_run_report_to_signals,
)
from core.beat_detection_signal_adapter import adapt_beat_detection_run_report_to_signals
from core.energy_peak_signal_adapter import adapt_energy_peak_run_report_to_signals
from core.filler_word_signal_adapter import adapt_filler_word_run_report_to_signals
from core.scene_change_signal_adapter import adapt_scene_change_report_to_signals
from core.motion_analysis_signal_adapter import adapt_motion_analysis_report_to_signals
from models.unified_edit_signal_result import UnifiedEditSignalResult


SOURCE_ENERGY_PEAK = "energy_peak"
SOURCE_FILLER_WORD = "filler_word"
SOURCE_AUDIO_NORMALIZATION = "audio_normalization"
SOURCE_BEAT_DETECTION = "beat_detection"
SOURCE_SCENE_CHANGE = "scene_change"
SOURCE_MOTION_ANALYSIS = "motion_analysis"
SOURCE_SILENCE_CLASSIFICATION = "silence_classification"
SOURCE_SILENCE_DETECTION = "silence_detection"

DEFAULT_DEDUP_CENTER_TOLERANCE_SECONDS = 0.15

_KNOWN_PRIORITIES = ("high", "medium", "low")


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
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


def _signal_id() -> str:
    return f"usig_{uuid.uuid4().hex[:12]}"


def _normalize_priority(value: Any, signal_score: float) -> str:
    if isinstance(value, str):
        priority = value.strip().lower()
        if priority in _KNOWN_PRIORITIES:
            return priority

    if signal_score >= 0.8:
        return "high"
    if signal_score >= 0.55:
        return "medium"
    return "low"


def _normalize_signal(
    signal: dict[str, Any],
    source: str,
) -> dict[str, Any] | None:
    if not isinstance(signal, dict):
        return None

    signal_type = str(signal.get("signal_type") or "unknown").strip() or "unknown"

    start = _safe_optional_float(signal.get("start_seconds"))
    end = _safe_optional_float(signal.get("end_seconds"))
    center = _safe_optional_float(signal.get("center_seconds"))

    if center is None and start is not None and end is not None:
        center = (start + end) / 2.0
    elif center is None and start is not None:
        center = start
    elif center is None and end is not None:
        center = end

    duration = _safe_optional_float(signal.get("duration_seconds"))
    if duration is None and start is not None and end is not None:
        duration = max(0.0, end - start)

    signal_score = _safe_float(signal.get("signal_score"), 0.0)
    if signal_score < 0.0:
        signal_score = 0.0
    if signal_score > 1.0:
        signal_score = 1.0

    priority = _normalize_priority(signal.get("priority"), signal_score)

    confidence = _safe_optional_float(signal.get("confidence"))

    action_hint = signal.get("action_hint")
    if not action_hint:
        action_hint = _infer_action_hint(source, signal_type)

    reason = signal.get("reason") or f"{source}:{signal_type}"

    metadata = dict(signal.get("metadata") or {})
    metadata.setdefault("original_source", str(signal.get("source") or source))

    payload = dict(signal)

    return {
        "signal_id": str(signal.get("signal_id") or _signal_id()),
        "signal_type": signal_type,
        "source": source,
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": center,
        "duration_seconds": duration,
        "signal_score": float(signal_score),
        "priority": priority,
        "action_hint": str(action_hint or ""),
        "reason": str(reason),
        "confidence": confidence,
        "metadata": metadata,
        "source_payload": payload,
    }


def _infer_action_hint(source: str, signal_type: str) -> str:
    if source == SOURCE_FILLER_WORD:
        return "remove_filler_candidate"
    if source == SOURCE_ENERGY_PEAK:
        return "keep_peak_moment"
    if source == SOURCE_BEAT_DETECTION:
        return "align_cut_to_beat"
    if source == SOURCE_AUDIO_NORMALIZATION:
        if signal_type == "audio_clipping_warning":
            return "review_audio_clipping"
        if signal_type == "audio_silent_warning":
            return "review_silent_audio"
        return "review_audio_level"
    if source == SOURCE_SILENCE_CLASSIFICATION:
        return "remove_silence_candidate"
    if source == SOURCE_SILENCE_DETECTION:
        return "review_silence_segment"
    return "review"


def _safe_collect(adapter_call, label: str, warnings: list[str], errors: list[str]) -> list[dict[str, Any]]:
    try:
        result = adapter_call()
    except Exception as exc:
        errors.append(f"{label}_adapter_failed:{exc}")
        return []

    if result is None:
        return []

    signals_attr = getattr(result, "signals", None)
    if signals_attr is None and isinstance(result, dict):
        signals_attr = result.get("signals")

    if not isinstance(signals_attr, list):
        return []

    status_attr = getattr(result, "status", None)
    if isinstance(status_attr, str) and status_attr.startswith("failed"):
        warnings.append(f"{label}_adapter_status_failed")

    return [signal for signal in signals_attr if isinstance(signal, dict)]


def _collect_silence_classification_signals(
    job: Any,
) -> list[dict[str, Any]]:
    classifications = _job_attr(job, "silence_classifications")
    if not isinstance(classifications, list) or not classifications:
        return []

    signals: list[dict[str, Any]] = []

    for index, item in enumerate(classifications):
        if not isinstance(item, dict):
            continue

        remove_candidate = bool(item.get("remove_candidate"))
        classification_label = str(item.get("classification") or "").strip().lower()
        start = _safe_optional_float(item.get("start_seconds"))
        end = _safe_optional_float(item.get("end_seconds"))

        if start is None or end is None or end <= start:
            continue

        if remove_candidate:
            signal_type = "silence_remove_candidate"
            base_score = 0.75
        elif classification_label in {"keep", "silence_keep", "speech_pause"}:
            signal_type = "silence_keep_candidate"
            base_score = 0.3
        else:
            signal_type = f"silence_{classification_label or 'segment'}"
            base_score = 0.5

        confidence = _safe_optional_float(item.get("confidence"))
        signal_score = base_score
        if confidence is not None:
            signal_score = max(signal_score, min(1.0, confidence))

        signals.append(
            {
                "signal_type": signal_type,
                "source": SOURCE_SILENCE_CLASSIFICATION,
                "start_seconds": start,
                "end_seconds": end,
                "center_seconds": (start + end) / 2.0,
                "duration_seconds": end - start,
                "signal_score": signal_score,
                "priority": _normalize_priority(None, signal_score),
                "confidence": confidence,
                "reason": str(item.get("reason") or f"silence_{classification_label or 'segment'}"),
                "metadata": {
                    "classification": classification_label,
                    "remove_candidate": remove_candidate,
                    "source_index": index,
                },
            }
        )

    return signals


def _collect_silence_detection_signals(
    job: Any,
) -> list[dict[str, Any]]:
    detection_report = _job_attr(job, "silence_detection_report")
    if not isinstance(detection_report, dict) or not detection_report:
        return []

    segments = detection_report.get("silence_segments")
    if not isinstance(segments, list):
        segments = detection_report.get("segments")

    if not isinstance(segments, list) or not segments:
        return []

    classifications = _job_attr(job, "silence_classifications")
    if isinstance(classifications, list) and classifications:
        return []

    signals: list[dict[str, Any]] = []

    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            continue

        start = _safe_optional_float(segment.get("start_seconds"))
        end = _safe_optional_float(segment.get("end_seconds"))
        if start is None or end is None or end <= start:
            continue

        duration = end - start
        signal_score = 0.55 if duration >= 0.6 else 0.4
        signal_type = "silence_dead_air_candidate" if duration >= 1.0 else "silence_segment"

        signals.append(
            {
                "signal_type": signal_type,
                "source": SOURCE_SILENCE_DETECTION,
                "start_seconds": start,
                "end_seconds": end,
                "center_seconds": (start + end) / 2.0,
                "duration_seconds": duration,
                "signal_score": signal_score,
                "priority": _normalize_priority(None, signal_score),
                "confidence": None,
                "reason": "silence_detected",
                "metadata": {
                    "source_index": index,
                    "raw_segment": dict(segment),
                },
            }
        )

    return signals


def _job_attr(job: Any, name: str) -> Any:
    if job is None:
        return None
    if isinstance(job, dict):
        return job.get(name)
    return getattr(job, name, None)


def _sort_key(signal: dict[str, Any]) -> tuple[float, int, float]:
    center = _safe_float(signal.get("center_seconds"), 0.0)
    priority_text = str(signal.get("priority") or "low").lower()
    priority_rank = {"high": 0, "medium": 1, "low": 2}.get(priority_text, 3)
    score = -_safe_float(signal.get("signal_score"), 0.0)
    return (center, priority_rank, score)


def _deduplicate_signals(
    signals: list[dict[str, Any]],
    tolerance_seconds: float = DEFAULT_DEDUP_CENTER_TOLERANCE_SECONDS,
) -> tuple[list[dict[str, Any]], int]:
    if not signals:
        return [], 0

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    untimed_signals: list[dict[str, Any]] = []

    for signal in signals:
        center = signal.get("center_seconds")
        if center is None:
            untimed_signals.append(signal)
            continue

        key = (str(signal.get("source")), str(signal.get("signal_type")))
        grouped.setdefault(key, []).append(signal)

    deduped: list[dict[str, Any]] = []
    duplicate_count = 0

    for items in grouped.values():
        items.sort(key=lambda s: _safe_float(s.get("center_seconds"), 0.0))

        cluster: list[dict[str, Any]] = []
        cluster_center: float | None = None

        for item in items:
            center = _safe_float(item.get("center_seconds"), 0.0)
            if cluster_center is None or abs(center - cluster_center) <= tolerance_seconds:
                cluster.append(item)
                cluster_center = center if cluster_center is None else (cluster_center + center) / 2.0
                continue

            kept, merged = _collapse_cluster(cluster)
            deduped.append(kept)
            duplicate_count += merged
            cluster = [item]
            cluster_center = center

        if cluster:
            kept, merged = _collapse_cluster(cluster)
            deduped.append(kept)
            duplicate_count += merged

    deduped.extend(untimed_signals)

    return deduped, duplicate_count


def _collapse_cluster(
    cluster: list[dict[str, Any]],
) -> tuple[dict[str, Any], int]:
    if len(cluster) == 1:
        return cluster[0], 0

    cluster.sort(key=lambda s: _safe_float(s.get("signal_score"), 0.0), reverse=True)
    winner = dict(cluster[0])

    merged_sources: list[dict[str, Any]] = []
    for other in cluster[1:]:
        merged_sources.append(
            {
                "signal_id": other.get("signal_id"),
                "signal_type": other.get("signal_type"),
                "source": other.get("source"),
                "center_seconds": other.get("center_seconds"),
                "signal_score": other.get("signal_score"),
                "priority": other.get("priority"),
            }
        )

    metadata = dict(winner.get("metadata") or {})
    metadata["merged_sources"] = list(metadata.get("merged_sources") or []) + merged_sources
    metadata["duplicate_count"] = int(metadata.get("duplicate_count") or 0) + len(merged_sources)
    winner["metadata"] = metadata

    return winner, len(merged_sources)


def _compute_timeline_coverage(signals: list[dict[str, Any]]) -> float:
    intervals: list[tuple[float, float]] = []

    for signal in signals:
        start = _safe_optional_float(signal.get("start_seconds"))
        end = _safe_optional_float(signal.get("end_seconds"))

        if start is None or end is None or end <= start:
            center = _safe_optional_float(signal.get("center_seconds"))
            if center is None:
                continue
            half = max(0.05, _safe_float(signal.get("duration_seconds"), 0.1) / 2.0)
            start = max(0.0, center - half)
            end = center + half

        intervals.append((start, end))

    if not intervals:
        return 0.0

    intervals.sort()
    covered = 0.0
    cur_start, cur_end = intervals[0]

    for start, end in intervals[1:]:
        if start <= cur_end:
            cur_end = max(cur_end, end)
        else:
            covered += cur_end - cur_start
            cur_start, cur_end = start, end

    covered += cur_end - cur_start
    return round(covered, 3)


def build_unified_edit_signal_result(
    job: Any,
    dedup_tolerance_seconds: float = DEFAULT_DEDUP_CENTER_TOLERANCE_SECONDS,
    metadata: dict[str, Any] | None = None,
) -> UnifiedEditSignalResult:
    safe_metadata: dict[str, Any] = dict(metadata or {})
    warnings: list[str] = []
    errors: list[str] = []
    source_counts: dict[str, int] = {}

    raw_signals: list[dict[str, Any]] = []

    energy_signals = _safe_collect(
        lambda: adapt_energy_peak_run_report_to_signals(
            _job_attr(job, "energy_peak_report"),
        ),
        label=SOURCE_ENERGY_PEAK,
        warnings=warnings,
        errors=errors,
    )
    if energy_signals:
        source_counts[SOURCE_ENERGY_PEAK] = len(energy_signals)
        for signal in energy_signals:
            normalized = _normalize_signal(signal, SOURCE_ENERGY_PEAK)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_ENERGY_PEAK}")

    filler_signals = _safe_collect(
        lambda: adapt_filler_word_run_report_to_signals(
            _job_attr(job, "filler_word_report"),
        ),
        label=SOURCE_FILLER_WORD,
        warnings=warnings,
        errors=errors,
    )
    if filler_signals:
        source_counts[SOURCE_FILLER_WORD] = len(filler_signals)
        for signal in filler_signals:
            normalized = _normalize_signal(signal, SOURCE_FILLER_WORD)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_FILLER_WORD}")

    audio_signals = _safe_collect(
        lambda: adapt_audio_normalization_run_report_to_signals(
            _job_attr(job, "audio_normalization_report"),
        ),
        label=SOURCE_AUDIO_NORMALIZATION,
        warnings=warnings,
        errors=errors,
    )
    if audio_signals:
        source_counts[SOURCE_AUDIO_NORMALIZATION] = len(audio_signals)
        for signal in audio_signals:
            normalized = _normalize_signal(signal, SOURCE_AUDIO_NORMALIZATION)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_AUDIO_NORMALIZATION}")

    beat_signals = _safe_collect(
        lambda: adapt_beat_detection_run_report_to_signals(
            _job_attr(job, "beat_detection_report"),
        ),
        label=SOURCE_BEAT_DETECTION,
        warnings=warnings,
        errors=errors,
    )
    if beat_signals:
        source_counts[SOURCE_BEAT_DETECTION] = len(beat_signals)
        for signal in beat_signals:
            normalized = _normalize_signal(signal, SOURCE_BEAT_DETECTION)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_BEAT_DETECTION}")

    scene_change_report = _job_attr(job, "scene_change_report")
    if not scene_change_report:
        scene_changes = _job_attr(job, "scene_changes")
        if isinstance(scene_changes, list) and scene_changes:
            scene_change_report = {"scene_changes": scene_changes}

    scene_change_signals = _safe_collect(
        lambda: adapt_scene_change_report_to_signals(scene_change_report),
        label=SOURCE_SCENE_CHANGE,
        warnings=warnings,
        errors=errors,
    )
    if scene_change_signals:
        source_counts[SOURCE_SCENE_CHANGE] = len(scene_change_signals)
        for signal in scene_change_signals:
            normalized = _normalize_signal(signal, SOURCE_SCENE_CHANGE)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_SCENE_CHANGE}")

    motion_analysis_report = _job_attr(job, "motion_analysis_report")
    if not motion_analysis_report:
        motion_analysis_segments = _job_attr(job, "motion_analysis_segments")
        if isinstance(motion_analysis_segments, list) and motion_analysis_segments:
            motion_analysis_report = {"motion_segments": motion_analysis_segments}

    if not motion_analysis_report:
        motion_analysis_result = _job_attr(job, "motion_analysis_result")
        if motion_analysis_result:
            motion_analysis_report = motion_analysis_result

    motion_analysis_signals = _safe_collect(
        lambda: adapt_motion_analysis_report_to_signals(motion_analysis_report),
        label=SOURCE_MOTION_ANALYSIS,
        warnings=warnings,
        errors=errors,
    )
    if motion_analysis_signals:
        source_counts[SOURCE_MOTION_ANALYSIS] = len(motion_analysis_signals)
        for signal in motion_analysis_signals:
            normalized = _normalize_signal(signal, SOURCE_MOTION_ANALYSIS)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_MOTION_ANALYSIS}")

    silence_class_signals = _collect_silence_classification_signals(job)
    
    if silence_class_signals:
        source_counts[SOURCE_SILENCE_CLASSIFICATION] = len(silence_class_signals)
        for signal in silence_class_signals:
            normalized = _normalize_signal(signal, SOURCE_SILENCE_CLASSIFICATION)
            if normalized is not None:
                raw_signals.append(normalized)

    silence_det_signals = _collect_silence_detection_signals(job)
    if silence_det_signals:
        source_counts[SOURCE_SILENCE_DETECTION] = len(silence_det_signals)
        for signal in silence_det_signals:
            normalized = _normalize_signal(signal, SOURCE_SILENCE_DETECTION)
            if normalized is not None:
                raw_signals.append(normalized)

    deduped_signals, duplicate_count = _deduplicate_signals(
        raw_signals,
        tolerance_seconds=dedup_tolerance_seconds,
    )
    deduped_signals.sort(key=_sort_key)

    type_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}

    for signal in deduped_signals:
        signal_type = signal.get("signal_type") or "unknown"
        priority = signal.get("priority") or "low"
        type_counts[signal_type] = type_counts.get(signal_type, 0) + 1
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

    scores = [_safe_float(s.get("signal_score"), 0.0) for s in deduped_signals]
    max_score = max(scores) if scores else 0.0
    avg_score = (sum(scores) / len(scores)) if scores else 0.0
    coverage = _compute_timeline_coverage(deduped_signals)

    if not deduped_signals:
        status = "skipped_no_signals"
        recommendation = "no_edit_signals_available"
    elif errors:
        status = "completed_with_warnings"
        recommendation = "review_warnings"
    elif warnings:
        non_empty_warnings = [
            warning for warning in warnings if not warning.startswith("no_signals_from_")
        ]
        if non_empty_warnings:
            status = "completed_with_warnings"
            recommendation = "review_warnings"
        else:
            status = "ok"
            recommendation = "use_unified_edit_signals"
    else:
        status = "ok"
        recommendation = "use_unified_edit_signals"

    return UnifiedEditSignalResult(
        status=status,
        signals=deduped_signals,
        signal_count=len(deduped_signals),
        source_counts=source_counts,
        type_counts=type_counts,
        priority_counts=priority_counts,
        duplicate_count=duplicate_count,
        max_signal_score=round(max_score, 6),
        avg_signal_score=round(avg_score, 6),
        timeline_coverage_seconds=coverage,
        recommendation=recommendation,
        warnings=warnings,
        errors=errors,
        metadata=safe_metadata,
    )


def apply_unified_edit_signal_result_to_job(
    job: Any,
    result: UnifiedEditSignalResult,
) -> Any:
    job.unified_edit_signal_report = result.to_dict()
    job.unified_edit_signal_status = result.status
    job.unified_edit_signals = list(result.signals)
    job.unified_edit_signal_count = int(result.signal_count)
    job.unified_edit_signal_summary = result.summary()
    job.unified_edit_signal_recommendation = result.recommendation

    if hasattr(job, "touch"):
        job.touch()

    return job


def run_unified_edit_signal_registry_for_job(
    job: Any,
    dedup_tolerance_seconds: float = DEFAULT_DEDUP_CENTER_TOLERANCE_SECONDS,
    metadata: dict[str, Any] | None = None,
) -> UnifiedEditSignalResult:
    result = build_unified_edit_signal_result(
        job=job,
        dedup_tolerance_seconds=dedup_tolerance_seconds,
        metadata=metadata,
    )
    apply_unified_edit_signal_result_to_job(job, result)
    return result
