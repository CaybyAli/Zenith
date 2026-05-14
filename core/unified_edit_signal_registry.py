from __future__ import annotations

import uuid
from typing import Any

from core.audio_normalization_signal_adapter import (
    adapt_audio_normalization_run_report_to_signals,
)
from core.beat_detection_signal_adapter import adapt_beat_detection_run_report_to_signals
from core.energy_peak_signal_adapter import adapt_energy_peak_run_report_to_signals
from core.filler_word_signal_adapter import adapt_filler_word_run_report_to_signals
from core.interaction_classification_signal_adapter import (
    adapt_interaction_classification_report_to_signals,
)
from core.keyword_emotion_signal_adapter import adapt_keyword_emotion_report_to_signals
from core.dead_content_signal_adapter import adapt_dead_content_report_to_signals
from core.content_value_signal_adapter import adapt_content_value_report_to_signals
from core.profanity_censor_signal_adapter import adapt_profanity_censor_report_to_signals
from core.scene_change_signal_adapter import adapt_scene_change_report_to_signals
from core.motion_analysis_signal_adapter import adapt_motion_analysis_report_to_signals
from core.face_reaction_signal_adapter import adapt_face_reaction_report_to_signals
from core.stutter_detection_signal_adapter import adapt_stutter_detection_report_to_signals
from core.screen_content_signal_adapter import adapt_screen_content_report_to_signals
from core.sentence_boundary_signal_adapter import adapt_sentence_boundary_report_to_signals
from core.visual_energy_signal_adapter import adapt_visual_energy_report_to_signals
from core.segment_classification_signal_adapter import (
    adapt_segment_classification_report_to_signals,
)
from core.murch_scoring_signal_adapter import adapt_murch_scoring_report_to_signals
from core.cut_list_signal_adapter import adapt_cut_list_report_to_signals
from core.clip_duration_signal_adapter import adapt_clip_duration_report_to_signals
from core.transition_decision_signal_adapter import (
    adapt_transition_decision_report_to_signals,
)
from core.continuity_check_signal_adapter import adapt_continuity_check_report_to_signals
from core.final_cut_list_signal_adapter import adapt_final_cut_list_report_to_signals
from core.review_timeline_plan_signal_adapter import (
    adapt_review_timeline_plan_report_to_signals,
)
from core.timeline_approval_gate_signal_adapter import (
    adapt_timeline_approval_gate_report_to_signals,
)
from core.timeline_safety_validator_signal_adapter import (
    adapt_timeline_safety_validator_report_to_signals,
)
from core.review_timeline_dashboard_package_signal_adapter import (
    adapt_review_timeline_dashboard_package_report_to_signals,
)
from core.hook_identification_signal_adapter import (
    adapt_hook_identification_report_to_signals,
)
from core.emotional_arc_signal_adapter import (
    adapt_emotional_arc_report_to_signals,
)
from core.dynamic_pacing_signal_adapter import (
    adapt_dynamic_pacing_report_to_signals,
)
from core.pattern_interrupt_signal_adapter import (
    adapt_pattern_interrupt_report_to_signals,
)
from core.reaction_shot_placement_signal_adapter import (
    adapt_reaction_shot_placement_report_to_signals,
)
from core.but_therefore_story_signal_adapter import (
    adapt_but_therefore_story_report_to_signals,
)
from core.final_quality_validator_signal_adapter import (
    build_final_quality_validator_signals,
)
from models.unified_edit_signal_result import UnifiedEditSignalResult


SOURCE_ENERGY_PEAK = "energy_peak"
SOURCE_FILLER_WORD = "filler_word"
SOURCE_INTERACTION_CLASSIFICATION = "interaction_classification"
SOURCE_KEYWORD_EMOTION = "keyword_emotion"
SOURCE_DEAD_CONTENT = "dead_content"
SOURCE_CONTENT_VALUE = "content_value"
SOURCE_PROFANITY_CENSOR = "profanity_censor"
SOURCE_AUDIO_NORMALIZATION = "audio_normalization"
SOURCE_BEAT_DETECTION = "beat_detection"
SOURCE_SCENE_CHANGE = "scene_change"
SOURCE_MOTION_ANALYSIS = "motion_analysis"
SOURCE_FACE_REACTION = "face_reaction"
SOURCE_STUTTER_DETECTION = "stutter_detection"
SOURCE_SCREEN_CONTENT = "screen_content"
SOURCE_SENTENCE_BOUNDARY = "sentence_boundary"
SOURCE_VISUAL_ENERGY = "visual_energy"
SOURCE_SEGMENT_CLASSIFIER = "segment_classifier"
SOURCE_MURCH_SCORING = "murch_scoring"
SOURCE_CUT_LIST_GENERATOR = "cut_list_generator"
SOURCE_CLIP_DURATION_OPTIMIZER = "clip_duration_optimizer"
SOURCE_TRANSITION_DECISION = "transition_decision"
SOURCE_CONTINUITY_CHECK = "continuity_check"
SOURCE_CUT_LIST_FINALIZER = "cut_list_finalizer"
SOURCE_REVIEW_TIMELINE_PLAN = "review_timeline_plan"
SOURCE_TIMELINE_APPROVAL_GATE = "timeline_approval_gate"
SOURCE_TIMELINE_SAFETY_VALIDATOR = "timeline_safety_validator"
SOURCE_REVIEW_TIMELINE_DASHBOARD_PACKAGE = "review_timeline_dashboard_package"
SOURCE_HOOK_IDENTIFICATION = "hook_identification"
SOURCE_EMOTIONAL_ARC = "emotional_arc"
SOURCE_DYNAMIC_PACING = "dynamic_pacing"
SOURCE_PATTERN_INTERRUPT = "pattern_interrupt"
SOURCE_REACTION_SHOT_PLACEMENT = "reaction_shot_placement"
SOURCE_BUT_THEREFORE_STORY = "but_therefore_story"
SOURCE_FINAL_QUALITY_VALIDATOR = "final_quality_validator"
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

    sentence_boundary_report = _job_attr(job, "sentence_boundary_report")
    if not sentence_boundary_report:
        sentence_boundary_boundaries = _job_attr(job, "sentence_boundary_boundaries")
        sentence_boundary_zones = _job_attr(job, "sentence_boundary_protection_zones")
        if isinstance(sentence_boundary_boundaries, list) or isinstance(
            sentence_boundary_zones,
            list,
        ):
            sentence_boundary_report = {
                "boundaries": sentence_boundary_boundaries
                if isinstance(sentence_boundary_boundaries, list)
                else [],
                "protection_zones": sentence_boundary_zones
                if isinstance(sentence_boundary_zones, list)
                else [],
            }

    sentence_boundary_signals = _safe_collect(
        lambda: adapt_sentence_boundary_report_to_signals(sentence_boundary_report),
        label=SOURCE_SENTENCE_BOUNDARY,
        warnings=warnings,
        errors=errors,
    )
    if sentence_boundary_signals:
        source_counts[SOURCE_SENTENCE_BOUNDARY] = len(sentence_boundary_signals)
        for signal in sentence_boundary_signals:
            normalized = _normalize_signal(signal, SOURCE_SENTENCE_BOUNDARY)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_SENTENCE_BOUNDARY}")

    keyword_emotion_report = _job_attr(job, "keyword_emotion_report")
    if not keyword_emotion_report:
        keyword_emotion_scores = _job_attr(job, "keyword_emotion_segment_scores")
        keyword_emotion_matches = _job_attr(job, "keyword_emotion_matches")
        if isinstance(keyword_emotion_scores, list) or isinstance(
            keyword_emotion_matches,
            list,
        ):
            keyword_emotion_report = {
                "segment_scores": keyword_emotion_scores
                if isinstance(keyword_emotion_scores, list)
                else [],
                "matches": keyword_emotion_matches
                if isinstance(keyword_emotion_matches, list)
                else [],
            }

    keyword_emotion_signals = _safe_collect(
        lambda: adapt_keyword_emotion_report_to_signals(keyword_emotion_report),
        label=SOURCE_KEYWORD_EMOTION,
        warnings=warnings,
        errors=errors,
    )
    if keyword_emotion_signals:
        source_counts[SOURCE_KEYWORD_EMOTION] = len(keyword_emotion_signals)
        for signal in keyword_emotion_signals:
            normalized = _normalize_signal(signal, SOURCE_KEYWORD_EMOTION)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_KEYWORD_EMOTION}")

    interaction_classification_report = _job_attr(
        job,
        "interaction_classification_report",
    )
    if not interaction_classification_report:
        interaction_classification_segments = _job_attr(
            job,
            "interaction_classification_segments",
        )
        interaction_classification_points = _job_attr(
            job,
            "interaction_classification_points",
        )
        if isinstance(interaction_classification_segments, list) or isinstance(
            interaction_classification_points,
            list,
        ):
            interaction_classification_report = {
                "segment_classifications": (
                    interaction_classification_segments
                    if isinstance(interaction_classification_segments, list)
                    and interaction_classification_segments
                    else interaction_classification_points
                    if isinstance(interaction_classification_points, list)
                    else []
                ),
            }

    interaction_classification_signals = _safe_collect(
        lambda: adapt_interaction_classification_report_to_signals(
            interaction_classification_report,
        ),
        label=SOURCE_INTERACTION_CLASSIFICATION,
        warnings=warnings,
        errors=errors,
    )
    if interaction_classification_signals:
        source_counts[SOURCE_INTERACTION_CLASSIFICATION] = len(
            interaction_classification_signals
        )
        for signal in interaction_classification_signals:
            normalized = _normalize_signal(
                signal,
                SOURCE_INTERACTION_CLASSIFICATION,
            )
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_INTERACTION_CLASSIFICATION}")

    dead_content_report = _job_attr(job, "dead_content_report")
    if not dead_content_report:
        dead_content_candidates = _job_attr(job, "dead_content_candidates")
        dead_content_segment_scores = _job_attr(job, "dead_content_segment_scores")
        if isinstance(dead_content_candidates, list) or isinstance(
            dead_content_segment_scores,
            list,
        ):
            dead_content_report = {
                "candidates": dead_content_candidates
                if isinstance(dead_content_candidates, list)
                else [],
                "segment_scores": dead_content_segment_scores
                if isinstance(dead_content_segment_scores, list)
                else [],
            }

    dead_content_signals = _safe_collect(
        lambda: adapt_dead_content_report_to_signals(dead_content_report),
        label=SOURCE_DEAD_CONTENT,
        warnings=warnings,
        errors=errors,
    )
    if dead_content_signals:
        source_counts[SOURCE_DEAD_CONTENT] = len(dead_content_signals)
        for signal in dead_content_signals:
            normalized = _normalize_signal(signal, SOURCE_DEAD_CONTENT)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_DEAD_CONTENT}")

    content_value_report = _job_attr(job, "content_value_report")
    if not content_value_report:
        content_value_segment_scores = _job_attr(
            job,
            "content_value_segment_scores",
        )
        if isinstance(content_value_segment_scores, list):
            content_value_report = {
                "segment_scores": content_value_segment_scores
            }

    content_value_signals = _safe_collect(
        lambda: adapt_content_value_report_to_signals(content_value_report),
        label=SOURCE_CONTENT_VALUE,
        warnings=warnings,
        errors=errors,
    )
    if content_value_signals:
        source_counts[SOURCE_CONTENT_VALUE] = len(content_value_signals)
        for signal in content_value_signals:
            normalized = _normalize_signal(signal, SOURCE_CONTENT_VALUE)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_CONTENT_VALUE}")

    profanity_censor_report = _job_attr(job, "profanity_censor_report")
    if not profanity_censor_report:
        profanity_censor_matches = _job_attr(job, "profanity_censor_matches")
        profanity_censor_segment_results = _job_attr(
            job,
            "profanity_censor_segment_results",
        )
        if isinstance(profanity_censor_matches, list) or isinstance(
            profanity_censor_segment_results,
            list,
        ):
            profanity_censor_report = {
                "matches": profanity_censor_matches
                if isinstance(profanity_censor_matches, list)
                else [],
                "segment_results": profanity_censor_segment_results
                if isinstance(profanity_censor_segment_results, list)
                else [],
            }

    profanity_censor_signals = _safe_collect(
        lambda: adapt_profanity_censor_report_to_signals(
            profanity_censor_report,
        ),
        label=SOURCE_PROFANITY_CENSOR,
        warnings=warnings,
        errors=errors,
    )
    if profanity_censor_signals:
        source_counts[SOURCE_PROFANITY_CENSOR] = len(profanity_censor_signals)
        for signal in profanity_censor_signals:
            normalized = _normalize_signal(signal, SOURCE_PROFANITY_CENSOR)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_PROFANITY_CENSOR}")

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

    face_reaction_report = _job_attr(job, "face_reaction_report")
    if not face_reaction_report:
        face_reaction_segments = _job_attr(job, "face_reaction_segments")
        if isinstance(face_reaction_segments, list) and face_reaction_segments:
            face_reaction_report = {
                "face_reaction_segments": face_reaction_segments
            }

    if not face_reaction_report:
        face_reaction_result = _job_attr(job, "face_reaction_result")
        if face_reaction_result:
            face_reaction_report = face_reaction_result

    face_reaction_signals = _safe_collect(
        lambda: adapt_face_reaction_report_to_signals(face_reaction_report),
        label=SOURCE_FACE_REACTION,
        warnings=warnings,
        errors=errors,
    )
    if face_reaction_signals:
        source_counts[SOURCE_FACE_REACTION] = len(face_reaction_signals)
        for signal in face_reaction_signals:
            normalized = _normalize_signal(signal, SOURCE_FACE_REACTION)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_FACE_REACTION}")

    stutter_detection_report = _job_attr(job, "stutter_detection_report")
    if not stutter_detection_report:
        stutter_detection_segments = _job_attr(job, "stutter_detection_segments")
        if isinstance(stutter_detection_segments, list) and stutter_detection_segments:
            stutter_detection_report = {
                "stutter_detection_segments": stutter_detection_segments
            }

    if not stutter_detection_report:
        stutter_detection_result = _job_attr(job, "stutter_detection_result")
        if stutter_detection_result:
            stutter_detection_report = stutter_detection_result

    stutter_detection_signals = _safe_collect(
        lambda: adapt_stutter_detection_report_to_signals(stutter_detection_report),
        label=SOURCE_STUTTER_DETECTION,
        warnings=warnings,
        errors=errors,
    )
    if stutter_detection_signals:
        source_counts[SOURCE_STUTTER_DETECTION] = len(stutter_detection_signals)
        for signal in stutter_detection_signals:
            normalized = _normalize_signal(signal, SOURCE_STUTTER_DETECTION)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_STUTTER_DETECTION}")

    screen_content_report = _job_attr(job, "screen_content_report")
    if not screen_content_report:
        screen_content_segments = _job_attr(job, "screen_content_segments")
        if isinstance(screen_content_segments, list) and screen_content_segments:
            screen_content_report = {
                "screen_content_segments": screen_content_segments
            }

    if not screen_content_report:
        screen_content_result = _job_attr(job, "screen_content_result")
        if screen_content_result:
            screen_content_report = screen_content_result

    screen_content_signals = _safe_collect(
        lambda: adapt_screen_content_report_to_signals(screen_content_report),
        label=SOURCE_SCREEN_CONTENT,
        warnings=warnings,
        errors=errors,
    )
    if screen_content_signals:
        source_counts[SOURCE_SCREEN_CONTENT] = len(screen_content_signals)
        for signal in screen_content_signals:
            normalized = _normalize_signal(signal, SOURCE_SCREEN_CONTENT)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_SCREEN_CONTENT}")

    visual_energy_report = _job_attr(job, "visual_energy_report")
    if not visual_energy_report:
        visual_energy_segments = _job_attr(job, "visual_energy_segments")
        if isinstance(visual_energy_segments, list) and visual_energy_segments:
            visual_energy_report = {
                "visual_energy_segments": visual_energy_segments
            }

    if not visual_energy_report:
        visual_energy_result = _job_attr(job, "visual_energy_result")
        if visual_energy_result:
            visual_energy_report = visual_energy_result

    visual_energy_signals = _safe_collect(
        lambda: adapt_visual_energy_report_to_signals(visual_energy_report),
        label=SOURCE_VISUAL_ENERGY,
        warnings=warnings,
        errors=errors,
    )
    if visual_energy_signals:
        source_counts[SOURCE_VISUAL_ENERGY] = len(visual_energy_signals)
        for signal in visual_energy_signals:
            normalized = _normalize_signal(signal, SOURCE_VISUAL_ENERGY)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_VISUAL_ENERGY}")

    segment_classification_report = _job_attr(job, "segment_classification_report")
    if not segment_classification_report:
        segment_classification_segments = _job_attr(
            job,
            "segment_classification_segments",
        )
        if isinstance(segment_classification_segments, list) and segment_classification_segments:
            segment_classification_report = {
                "segments": segment_classification_segments
            }

    segment_classification_signals = _safe_collect(
        lambda: adapt_segment_classification_report_to_signals(
            segment_classification_report,
        ),
        label=SOURCE_SEGMENT_CLASSIFIER,
        warnings=warnings,
        errors=errors,
    )
    if segment_classification_signals:
        source_counts[SOURCE_SEGMENT_CLASSIFIER] = len(segment_classification_signals)
        for signal in segment_classification_signals:
            normalized = _normalize_signal(signal, SOURCE_SEGMENT_CLASSIFIER)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_SEGMENT_CLASSIFIER}")

    murch_scoring_report = _job_attr(job, "murch_scoring_report")
    if not murch_scoring_report:
        murch_scoring_segment_scores = _job_attr(
            job,
            "murch_scoring_segment_scores",
        )
        if isinstance(murch_scoring_segment_scores, list) and murch_scoring_segment_scores:
            murch_scoring_report = {
                "segment_scores": murch_scoring_segment_scores
            }

    murch_scoring_signals = _safe_collect(
        lambda: adapt_murch_scoring_report_to_signals(
            murch_scoring_report,
        ),
        label=SOURCE_MURCH_SCORING,
        warnings=warnings,
        errors=errors,
    )
    if murch_scoring_signals:
        source_counts[SOURCE_MURCH_SCORING] = len(murch_scoring_signals)
        for signal in murch_scoring_signals:
            normalized = _normalize_signal(signal, SOURCE_MURCH_SCORING)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_MURCH_SCORING}")

    cut_list_report = _job_attr(job, "cut_list_report")
    if not cut_list_report:
        cut_list_items = _job_attr(job, "cut_list_items")
        if isinstance(cut_list_items, list) and cut_list_items:
            cut_list_report = {"items": cut_list_items}

    cut_list_signals = _safe_collect(
        lambda: adapt_cut_list_report_to_signals(cut_list_report),
        label=SOURCE_CUT_LIST_GENERATOR,
        warnings=warnings,
        errors=errors,
    )
    if cut_list_signals:
        source_counts[SOURCE_CUT_LIST_GENERATOR] = len(cut_list_signals)
        for signal in cut_list_signals:
            normalized = _normalize_signal(signal, SOURCE_CUT_LIST_GENERATOR)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_CUT_LIST_GENERATOR}")

    clip_duration_report = _job_attr(job, "clip_duration_report")
    if not clip_duration_report:
        clip_duration_recommendations = _job_attr(
            job,
            "clip_duration_recommendations",
        )
        if isinstance(clip_duration_recommendations, list) and clip_duration_recommendations:
            clip_duration_report = {
                "recommendations": clip_duration_recommendations
            }

    clip_duration_signals = _safe_collect(
        lambda: adapt_clip_duration_report_to_signals(clip_duration_report),
        label=SOURCE_CLIP_DURATION_OPTIMIZER,
        warnings=warnings,
        errors=errors,
    )
    if clip_duration_signals:
        source_counts[SOURCE_CLIP_DURATION_OPTIMIZER] = len(clip_duration_signals)
        for signal in clip_duration_signals:
            normalized = _normalize_signal(signal, SOURCE_CLIP_DURATION_OPTIMIZER)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_CLIP_DURATION_OPTIMIZER}")

    transition_decision_report = _job_attr(job, "transition_decision_report")
    if not transition_decision_report:
        transition_decision_decisions = _job_attr(
            job,
            "transition_decision_decisions",
        )
        if isinstance(transition_decision_decisions, list) and transition_decision_decisions:
            transition_decision_report = {
                "decisions": transition_decision_decisions
            }

    transition_decision_signals = _safe_collect(
        lambda: adapt_transition_decision_report_to_signals(transition_decision_report),
        label=SOURCE_TRANSITION_DECISION,
        warnings=warnings,
        errors=errors,
    )
    if transition_decision_signals:
        source_counts[SOURCE_TRANSITION_DECISION] = len(transition_decision_signals)
        for signal in transition_decision_signals:
            normalized = _normalize_signal(signal, SOURCE_TRANSITION_DECISION)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_TRANSITION_DECISION}")

    continuity_check_report = _job_attr(job, "continuity_check_report")
    if not continuity_check_report:
        continuity_check_issues = _job_attr(
            job,
            "continuity_check_issues",
        )
        if isinstance(continuity_check_issues, list) and continuity_check_issues:
            continuity_check_report = {
                "issues": continuity_check_issues
            }

    continuity_check_signals = _safe_collect(
        lambda: adapt_continuity_check_report_to_signals(continuity_check_report),
        label=SOURCE_CONTINUITY_CHECK,
        warnings=warnings,
        errors=errors,
    )
    if continuity_check_signals:
        source_counts[SOURCE_CONTINUITY_CHECK] = len(continuity_check_signals)
        for signal in continuity_check_signals:
            normalized = _normalize_signal(signal, SOURCE_CONTINUITY_CHECK)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_CONTINUITY_CHECK}")

    final_cut_list_report = _job_attr(job, "final_cut_list_report")
    if not final_cut_list_report:
        final_cut_list_items = _job_attr(
            job,
            "final_cut_list_items",
        )
        if isinstance(final_cut_list_items, list) and final_cut_list_items:
            final_cut_list_report = {
                "final_items": final_cut_list_items
            }

    final_cut_list_signals = _safe_collect(
        lambda: adapt_final_cut_list_report_to_signals(final_cut_list_report),
        label=SOURCE_CUT_LIST_FINALIZER,
        warnings=warnings,
        errors=errors,
    )
    review_timeline_plan_report = _job_attr(job, "review_timeline_plan_report")
    if not review_timeline_plan_report:
        review_timeline_plan_items = _job_attr(job, "review_timeline_plan_items")
        if isinstance(review_timeline_plan_items, list) and review_timeline_plan_items:
            review_timeline_plan_report = {
                "items": review_timeline_plan_items,
                "metadata": {
                    "source": SOURCE_REVIEW_TIMELINE_PLAN,
                    "review_only": True,
                    "approval_required": True,
                },
            }

    review_timeline_plan_signals = _safe_collect(
        lambda: adapt_review_timeline_plan_report_to_signals(
            review_timeline_plan_report,
        ),
        label=SOURCE_REVIEW_TIMELINE_PLAN,
        warnings=warnings,
        errors=errors,
    )
    if review_timeline_plan_signals:
        source_counts[SOURCE_REVIEW_TIMELINE_PLAN] = len(
            review_timeline_plan_signals
        )
        for signal in review_timeline_plan_signals:
            normalized = _normalize_signal(signal, SOURCE_REVIEW_TIMELINE_PLAN)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_REVIEW_TIMELINE_PLAN}")

    timeline_approval_gate_report = _job_attr(job, "timeline_approval_gate_report")
    if not timeline_approval_gate_report:
        timeline_approval_gate = _job_attr(job, "timeline_approval_gate")
        if isinstance(timeline_approval_gate, dict) and timeline_approval_gate:
            timeline_approval_gate_report = {
                "timeline_approval_gate": timeline_approval_gate,
                "metadata": {
                    "source": SOURCE_TIMELINE_APPROVAL_GATE,
                    "review_only": True,
                    "approval_gate_only": True,
                    "media_unchanged": True,
                },
            }

    timeline_approval_gate_signals = _safe_collect(
        lambda: adapt_timeline_approval_gate_report_to_signals(
            timeline_approval_gate_report,
        ),
        label=SOURCE_TIMELINE_APPROVAL_GATE,
        warnings=warnings,
        errors=errors,
    )
    if timeline_approval_gate_signals:
        source_counts[SOURCE_TIMELINE_APPROVAL_GATE] = len(
            timeline_approval_gate_signals
        )
        for signal in timeline_approval_gate_signals:
            normalized = _normalize_signal(signal, SOURCE_TIMELINE_APPROVAL_GATE)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_TIMELINE_APPROVAL_GATE}")

    timeline_safety_validator_report = _job_attr(
        job,
        "timeline_safety_validator_report",
    )
    if not timeline_safety_validator_report:
        timeline_safety_validator_report = _job_attr(
            job,
            "timeline_safety_validator",
        )

    timeline_safety_validator_signals = _safe_collect(
        lambda: adapt_timeline_safety_validator_report_to_signals(
            timeline_safety_validator_report,
        ),
        label=SOURCE_TIMELINE_SAFETY_VALIDATOR,
        warnings=warnings,
        errors=errors,
    )
    if timeline_safety_validator_signals:
        source_counts[SOURCE_TIMELINE_SAFETY_VALIDATOR] = len(
            timeline_safety_validator_signals
        )
        for signal in timeline_safety_validator_signals:
            normalized = _normalize_signal(
                signal,
                SOURCE_TIMELINE_SAFETY_VALIDATOR,
            )
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_TIMELINE_SAFETY_VALIDATOR}")

    dashboard_package_signals = _safe_collect(
        lambda: adapt_review_timeline_dashboard_package_report_to_signals(
            _job_attr(job, "review_timeline_dashboard_package_report"),
        ),
        label=SOURCE_REVIEW_TIMELINE_DASHBOARD_PACKAGE,
        warnings=warnings,
        errors=errors,
    )
    if dashboard_package_signals:
        source_counts[SOURCE_REVIEW_TIMELINE_DASHBOARD_PACKAGE] = len(
            dashboard_package_signals
        )
        for signal in dashboard_package_signals:
            normalized = _normalize_signal(
                signal,
                SOURCE_REVIEW_TIMELINE_DASHBOARD_PACKAGE,
            )
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(
            f"no_signals_from_{SOURCE_REVIEW_TIMELINE_DASHBOARD_PACKAGE}"
        )

    hook_identification_report = _job_attr(job, "hook_identification_report")
    if not hook_identification_report:
        hook_identification_report = _job_attr(job, "hook_identification")

    hook_identification_signals = _safe_collect(
        lambda: adapt_hook_identification_report_to_signals(
            hook_identification_report,
        ),
        label=SOURCE_HOOK_IDENTIFICATION,
        warnings=warnings,
        errors=errors,
    )
    if hook_identification_signals:
        source_counts[SOURCE_HOOK_IDENTIFICATION] = len(
            hook_identification_signals
        )
        for signal in hook_identification_signals:
            normalized = _normalize_signal(signal, SOURCE_HOOK_IDENTIFICATION)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_HOOK_IDENTIFICATION}")

    emotional_arc_report = _job_attr(job, "emotional_arc_report")
    if not emotional_arc_report:
        emotional_arc_report = _job_attr(job, "emotional_arc")

    emotional_arc_signals = _safe_collect(
        lambda: adapt_emotional_arc_report_to_signals(
            emotional_arc_report,
        ),
        label=SOURCE_EMOTIONAL_ARC,
        warnings=warnings,
        errors=errors,
    )
    if emotional_arc_signals:
        source_counts[SOURCE_EMOTIONAL_ARC] = len(emotional_arc_signals)
        for signal in emotional_arc_signals:
            normalized = _normalize_signal(signal, SOURCE_EMOTIONAL_ARC)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_EMOTIONAL_ARC}")

    dynamic_pacing_report = _job_attr(job, "dynamic_pacing_report")
    if not dynamic_pacing_report:
        dynamic_pacing_report = _job_attr(job, "dynamic_pacing")

    dynamic_pacing_signals = _safe_collect(
        lambda: adapt_dynamic_pacing_report_to_signals(
            dynamic_pacing_report,
        ),
        label=SOURCE_DYNAMIC_PACING,
        warnings=warnings,
        errors=errors,
    )
    if dynamic_pacing_signals:
        source_counts[SOURCE_DYNAMIC_PACING] = len(dynamic_pacing_signals)
        for signal in dynamic_pacing_signals:
            normalized = _normalize_signal(signal, SOURCE_DYNAMIC_PACING)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_DYNAMIC_PACING}")

    pattern_interrupt_report = _job_attr(job, "pattern_interrupt_report")
    if not pattern_interrupt_report:
        pattern_interrupt_report = _job_attr(job, "pattern_interrupt")

    pattern_interrupt_signals = _safe_collect(
        lambda: adapt_pattern_interrupt_report_to_signals(
            pattern_interrupt_report,
        ),
        label=SOURCE_PATTERN_INTERRUPT,
        warnings=warnings,
        errors=errors,
    )
    if pattern_interrupt_signals:
        source_counts[SOURCE_PATTERN_INTERRUPT] = len(pattern_interrupt_signals)
        for signal in pattern_interrupt_signals:
            normalized = _normalize_signal(signal, SOURCE_PATTERN_INTERRUPT)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_PATTERN_INTERRUPT}")

    reaction_shot_placement_report = _job_attr(
        job,
        "reaction_shot_placement_report",
    )
    if not reaction_shot_placement_report:
        reaction_shot_placement_report = _job_attr(
            job,
            "reaction_shot_placement",
        )

    reaction_shot_placement_signals = _safe_collect(
        lambda: adapt_reaction_shot_placement_report_to_signals(
            reaction_shot_placement_report,
        ),
        label=SOURCE_REACTION_SHOT_PLACEMENT,
        warnings=warnings,
        errors=errors,
    )
    if reaction_shot_placement_signals:
        source_counts[SOURCE_REACTION_SHOT_PLACEMENT] = len(
            reaction_shot_placement_signals
        )
        for signal in reaction_shot_placement_signals:
            normalized = _normalize_signal(
                signal,
                SOURCE_REACTION_SHOT_PLACEMENT,
            )
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_REACTION_SHOT_PLACEMENT}")

    but_therefore_story_report = _job_attr(
        job,
        "but_therefore_story_report",
    )
    if not but_therefore_story_report:
        but_therefore_story_report = _job_attr(
            job,
            "but_therefore_story",
        )

    but_therefore_story_signals = _safe_collect(
        lambda: adapt_but_therefore_story_report_to_signals(
            but_therefore_story_report,
        ),
        label=SOURCE_BUT_THEREFORE_STORY,
        warnings=warnings,
        errors=errors,
    )
    if but_therefore_story_signals:
        source_counts[SOURCE_BUT_THEREFORE_STORY] = len(
            but_therefore_story_signals
        )
        for signal in but_therefore_story_signals:
            normalized = _normalize_signal(
                signal,
                SOURCE_BUT_THEREFORE_STORY,
            )
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_BUT_THEREFORE_STORY}")

    final_quality_report = _job_attr(job, "final_quality_validation_report")
    if not final_quality_report:
        final_quality_report = _job_attr(job, "final_quality_validator")

    if final_quality_report:
        final_quality_validator_signals = _safe_collect(
            lambda: {"signals": build_final_quality_validator_signals(job)},
            label=SOURCE_FINAL_QUALITY_VALIDATOR,
            warnings=warnings,
            errors=errors,
        )
        if final_quality_validator_signals:
            source_counts[SOURCE_FINAL_QUALITY_VALIDATOR] = len(
                final_quality_validator_signals
            )
            for signal in final_quality_validator_signals:
                normalized = _normalize_signal(
                    signal,
                    SOURCE_FINAL_QUALITY_VALIDATOR,
                )
                if normalized is not None:
                    raw_signals.append(normalized)
        else:
            warnings.append(f"no_signals_from_{SOURCE_FINAL_QUALITY_VALIDATOR}")
    else:
        warnings.append(f"no_signals_from_{SOURCE_FINAL_QUALITY_VALIDATOR}")

    if final_cut_list_signals:
        source_counts[SOURCE_CUT_LIST_FINALIZER] = len(final_cut_list_signals)
        for signal in final_cut_list_signals:
            normalized = _normalize_signal(signal, SOURCE_CUT_LIST_FINALIZER)
            if normalized is not None:
                raw_signals.append(normalized)
    else:
        warnings.append(f"no_signals_from_{SOURCE_CUT_LIST_FINALIZER}")

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
