from __future__ import annotations

import math
from copy import deepcopy
from typing import Any, Mapping


WORD_SNAP_2_SOURCE = "word_snap_2_combined_vad_boundary_polish"
WORD_SNAP_2_DEFAULT_SNAP_WINDOW_SECONDS = 1.0
WORD_SNAP_2_EPSILON_SECONDS = 0.001


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except Exception:
        return default
    if not math.isfinite(number):
        return default
    return number


def _round_seconds(value: Any) -> float:
    return round(max(0.0, _safe_float(value)), 3)


def _duration(start: float, end: float) -> float:
    return round(max(0.0, float(end) - float(start)), 3)


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def normalize_intervals(
    raw: Any,
    *,
    list_keys: tuple[str, ...] = ("speech_regions", "silence_gaps", "regions", "items"),
    id_prefix: str = "interval",
    source: str = "unknown",
) -> list[dict[str, Any]]:
    if isinstance(raw, Mapping):
        for key in list_keys:
            value = raw.get(key)
            if isinstance(value, list):
                raw = value
                break

    if not isinstance(raw, list):
        return []

    intervals: list[dict[str, Any]] = []

    for index, item in enumerate(raw, start=1):
        if not isinstance(item, Mapping):
            continue

        start = item.get("start_seconds", item.get("start", item.get("start_time")))
        end = item.get("end_seconds", item.get("end", item.get("end_time")))

        if start is None or end is None:
            continue

        start_f = _round_seconds(start)
        end_f = _round_seconds(end)

        if end_f <= start_f:
            continue

        intervals.append({
            "interval_id": str(
                item.get("speech_region_id")
                or item.get("silence_gap_id")
                or item.get("id")
                or f"{id_prefix}_{index:04d}"
            ),
            "start_seconds": start_f,
            "end_seconds": end_f,
            "duration_seconds": _duration(start_f, end_f),
            "source": str(item.get("source") or source),
            "raw": dict(item),
        })

    return sorted(intervals, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def edge_inside_speech_region(
    *,
    edge_seconds: float,
    combined_speech_regions: list[Mapping[str, Any]],
) -> dict[str, Any] | None:
    edge = _safe_float(edge_seconds)

    for region in combined_speech_regions:
        start = _safe_float(region.get("start_seconds"))
        end = _safe_float(region.get("end_seconds"))

        if start + WORD_SNAP_2_EPSILON_SECONDS < edge < end - WORD_SNAP_2_EPSILON_SECONDS:
            return dict(region)

    return None


def _movement_overlaps_dead_air_trim(
    *,
    old_edge_seconds: float,
    new_edge_seconds: float,
    dead_air_trims: list[Mapping[str, Any]],
) -> bool:
    start = min(old_edge_seconds, new_edge_seconds)
    end = max(old_edge_seconds, new_edge_seconds)

    if end <= start:
        return False

    for trim in dead_air_trims:
        trim_start = _safe_float(trim.get("start_seconds"))
        trim_end = _safe_float(trim.get("end_seconds"))

        if _overlap_seconds(start, end, trim_start, trim_end) > WORD_SNAP_2_EPSILON_SECONDS:
            return True

    return False


def snap_edge_to_combined_vad_pause(
    *,
    edge_kind: str,
    old_edge_seconds: float,
    combined_speech_regions: list[Mapping[str, Any]],
    dead_air_trims: list[Mapping[str, Any]] | None = None,
    snap_window_seconds: float = WORD_SNAP_2_DEFAULT_SNAP_WINDOW_SECONDS,
) -> dict[str, Any]:
    dead_air_trims = dead_air_trims or []
    old_edge = _round_seconds(old_edge_seconds)

    speech_region = edge_inside_speech_region(
        edge_seconds=old_edge,
        combined_speech_regions=combined_speech_regions,
    )

    if speech_region is None:
        return {
            "edge_kind": edge_kind,
            "old_seconds": old_edge,
            "new_seconds": old_edge,
            "delta_seconds": 0.0,
            "status": "UNCHANGED",
            "reason": "edge_not_inside_combined_speech_region",
        }

    region_start = _safe_float(speech_region.get("start_seconds"))
    region_end = _safe_float(speech_region.get("end_seconds"))

    if edge_kind == "start":
        candidate = _round_seconds(region_start)
        distance = round(old_edge - candidate, 3)
        movement_direction = "earlier"
    elif edge_kind == "end":
        candidate = _round_seconds(region_end)
        distance = round(candidate - old_edge, 3)
        movement_direction = "later"
    else:
        raise ValueError(f"invalid edge_kind: {edge_kind}")

    if distance < -WORD_SNAP_2_EPSILON_SECONDS:
        return {
            "edge_kind": edge_kind,
            "old_seconds": old_edge,
            "new_seconds": old_edge,
            "delta_seconds": 0.0,
            "status": "RESIDUAL",
            "reason": "invalid_candidate_direction",
            "speech_region": speech_region,
        }

    if distance > snap_window_seconds:
        return {
            "edge_kind": edge_kind,
            "old_seconds": old_edge,
            "new_seconds": old_edge,
            "delta_seconds": 0.0,
            "status": "RESIDUAL",
            "reason": "continuous_speech_no_pause_boundary_inside_snap_window",
            "distance_to_boundary_seconds": distance,
            "speech_region": speech_region,
        }

    if _movement_overlaps_dead_air_trim(
        old_edge_seconds=old_edge,
        new_edge_seconds=candidate,
        dead_air_trims=dead_air_trims,
    ):
        return {
            "edge_kind": edge_kind,
            "old_seconds": old_edge,
            "new_seconds": old_edge,
            "delta_seconds": 0.0,
            "status": "RESIDUAL",
            "reason": "snap_would_bring_back_dead_air_2_trim",
            "distance_to_boundary_seconds": distance,
            "speech_region": speech_region,
        }

    delta = round(candidate - old_edge, 3)

    return {
        "edge_kind": edge_kind,
        "old_seconds": old_edge,
        "new_seconds": candidate,
        "delta_seconds": delta,
        "abs_delta_seconds": abs(delta),
        "status": "SNAPPED",
        "reason": "snapped_to_combined_vad_speech_boundary",
        "movement_direction": movement_direction,
        "distance_to_boundary_seconds": distance,
        "speech_region": speech_region,
    }


def _segment_id(segment: Mapping[str, Any], index: int) -> str:
    return str(segment.get("segment_id") or segment.get("id") or f"segment_{index:04d}")


def _get_start(segment: Mapping[str, Any]) -> float:
    return _safe_float(segment.get("start_seconds", segment.get("start", segment.get("start_time", 0.0))))


def _get_end(segment: Mapping[str, Any]) -> float:
    return _safe_float(segment.get("end_seconds", segment.get("end", segment.get("end_time", 0.0))))


def _set_start(segment: dict[str, Any], value: float) -> None:
    value = _round_seconds(value)
    if "start_seconds" in segment:
        segment["start_seconds"] = value
    elif "start" in segment:
        segment["start"] = value
    else:
        segment["start_seconds"] = value


def _set_end(segment: dict[str, Any], value: float) -> None:
    value = _round_seconds(value)
    if "end_seconds" in segment:
        segment["end_seconds"] = value
    elif "end" in segment:
        segment["end"] = value
    else:
        segment["end_seconds"] = value


def apply_word_snap_2_to_segments(
    *,
    plan_segments: list[Mapping[str, Any]],
    combined_speech_regions: list[Mapping[str, Any]],
    combined_silence_gaps: list[Mapping[str, Any]] | None = None,
    dead_air_trims: list[Mapping[str, Any]] | None = None,
    snap_window_seconds: float = WORD_SNAP_2_DEFAULT_SNAP_WINDOW_SECONDS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    combined_silence_gaps = combined_silence_gaps or []
    dead_air_trims = dead_air_trims or []

    output_segments: list[dict[str, Any]] = []
    edge_reviews: list[dict[str, Any]] = []
    edge_changes: list[dict[str, Any]] = []
    residuals: list[dict[str, Any]] = []

    original_duration = 0.0
    new_duration = 0.0

    for index, segment in enumerate(plan_segments):
        new_segment = deepcopy(dict(segment))

        old_start = _round_seconds(_get_start(segment))
        old_end = _round_seconds(_get_end(segment))
        original_duration += _duration(old_start, old_end)

        start_result = snap_edge_to_combined_vad_pause(
            edge_kind="start",
            old_edge_seconds=old_start,
            combined_speech_regions=combined_speech_regions,
            dead_air_trims=dead_air_trims,
            snap_window_seconds=snap_window_seconds,
        )
        end_result = snap_edge_to_combined_vad_pause(
            edge_kind="end",
            old_edge_seconds=old_end,
            combined_speech_regions=combined_speech_regions,
            dead_air_trims=dead_air_trims,
            snap_window_seconds=snap_window_seconds,
        )

        segment_id = _segment_id(segment, index)

        for result in (start_result, end_result):
            review = {
                "segment_index": index,
                "segment_id": segment_id,
                **result,
            }

            if result["status"] in {"SNAPPED", "RESIDUAL"}:
                edge_reviews.append(review)

            if result["status"] == "SNAPPED":
                edge_changes.append(review)

            if result["status"] == "RESIDUAL":
                residuals.append(review)

        new_start = _round_seconds(start_result["new_seconds"])
        new_end = _round_seconds(end_result["new_seconds"])

        if new_end <= new_start:
            new_start = old_start
            new_end = old_end
            residuals.append({
                "segment_index": index,
                "segment_id": segment_id,
                "edge_kind": "segment",
                "old_seconds": None,
                "new_seconds": None,
                "status": "RESIDUAL",
                "reason": "snap_would_invert_or_delete_segment",
            })

        _set_start(new_segment, new_start)
        _set_end(new_segment, new_end)
        new_segment["duration_seconds"] = _duration(new_start, new_end)

        metadata = new_segment.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["word_snap_2_source"] = WORD_SNAP_2_SOURCE
        metadata["word_snap_2_applied"] = bool(start_result["status"] == "SNAPPED" or end_result["status"] == "SNAPPED")
        new_segment["metadata"] = metadata

        output_segments.append(new_segment)
        new_duration += _duration(new_start, new_end)

    total_abs_delta = round(sum(_safe_float(item.get("abs_delta_seconds")) for item in edge_changes), 3)
    duration_delta = round(new_duration - original_duration, 3)

    audit = {
        "source": WORD_SNAP_2_SOURCE,
        "snap_window_seconds": snap_window_seconds,
        "combined_speech_region_count": len(combined_speech_regions),
        "combined_silence_gap_count": len(combined_silence_gaps),
        "dead_air_trim_count": len(dead_air_trims),
        "reviewed_mid_speech_edge_count": len(edge_reviews),
        "snapped_edge_count": len(edge_changes),
        "residual_mid_speech_edge_count": len(residuals),
        "total_abs_delta_seconds": total_abs_delta,
        "duration_delta_seconds": duration_delta,
        "original_planned_output_duration_seconds": round(original_duration, 3),
        "new_planned_output_duration_seconds": round(new_duration, 3),
        "removed_active_play_seconds": 0.0,
        "removed_reaction_seconds": 0.0,
        "anti_overcut_fail_count": 0,
        "edge_reviews": edge_reviews,
        "edge_changes": edge_changes,
        "residuals": residuals,
    }

    return output_segments, audit

# ---------------------------------------------------------------------------
# WORD-SNAP-2-FIX: inner reliable word-boundary fallback for continuous speech
# ---------------------------------------------------------------------------

WORD_SNAP_2_FIX_SOURCE = "word_snap_2_fix_inner_reliable_word_boundary_fallback"
WORD_SNAP_2_FIX_DEFAULT_MAX_WORD_SECONDS = 1.2


def normalize_speech_1_words(
    raw: Any,
    *,
    max_word_seconds: float = WORD_SNAP_2_FIX_DEFAULT_MAX_WORD_SECONDS,
) -> list[dict[str, Any]]:
    if isinstance(raw, Mapping):
        if isinstance(raw.get("words"), list):
            raw = raw["words"]
        elif isinstance(raw.get("segments"), list):
            collected: list[Any] = []
            for segment in raw["segments"]:
                if isinstance(segment, Mapping) and isinstance(segment.get("words"), list):
                    collected.extend(segment["words"])
            raw = collected

    if not isinstance(raw, list):
        return []

    words: list[dict[str, Any]] = []

    for index, item in enumerate(raw, start=1):
        if not isinstance(item, Mapping):
            continue

        start = item.get("start_seconds", item.get("start", item.get("start_time")))
        end = item.get("end_seconds", item.get("end", item.get("end_time")))

        if start is None or end is None:
            continue

        start_f = _round_seconds(start)
        end_f = _round_seconds(end)

        if end_f <= start_f:
            continue

        duration = _duration(start_f, end_f)
        text = str(item.get("word") or item.get("text") or item.get("token") or "").strip()

        words.append({
            "word_id": str(item.get("word_id") or item.get("id") or f"speech_1_word_{index:05d}"),
            "word": text,
            "start_seconds": start_f,
            "end_seconds": end_f,
            "duration_seconds": duration,
            "is_reliable_boundary_word": duration <= max_word_seconds,
            "source": "speech_1_words_filtered",
        })

    return sorted(words, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def find_inner_word_boundary_fallback(
    *,
    edge_kind: str,
    old_edge_seconds: float,
    speech_1_words: list[Mapping[str, Any]],
    snap_window_seconds: float = WORD_SNAP_2_DEFAULT_SNAP_WINDOW_SECONDS,
    max_word_seconds: float = WORD_SNAP_2_FIX_DEFAULT_MAX_WORD_SECONDS,
    dead_air_trims: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    dead_air_trims = dead_air_trims or []
    old_edge = _round_seconds(old_edge_seconds)

    reliable_words: list[dict[str, Any]] = []
    stretched_words_near_edge: list[dict[str, Any]] = []

    for raw_word in speech_1_words:
        start = _safe_float(raw_word.get("start_seconds"))
        end = _safe_float(raw_word.get("end_seconds"))
        duration = _duration(start, end)
        text = str(raw_word.get("word") or "").strip()

        if end <= start:
            continue

        is_near = (
            abs(start - old_edge) <= snap_window_seconds
            or abs(end - old_edge) <= snap_window_seconds
            or (start < old_edge < end)
        )

        normalized = {
            "word": text,
            "start_seconds": _round_seconds(start),
            "end_seconds": _round_seconds(end),
            "duration_seconds": duration,
        }

        if duration <= max_word_seconds:
            reliable_words.append(normalized)
        elif is_near:
            stretched_words_near_edge.append(normalized)

    candidates: list[dict[str, Any]] = []

    for word in reliable_words:
        if edge_kind == "start":
            boundary = _safe_float(word["start_seconds"])
            boundary_kind = "word_start"
        elif edge_kind == "end":
            boundary = _safe_float(word["end_seconds"])
            boundary_kind = "word_end"
        else:
            raise ValueError(f"invalid edge_kind: {edge_kind}")

        distance = abs(boundary - old_edge)
        if distance <= snap_window_seconds:
            candidates.append({
                "boundary_seconds": _round_seconds(boundary),
                "distance_seconds": round(distance, 3),
                "word": word,
                "boundary_kind": boundary_kind,
            })

    if not candidates:
        return {
            "status": "REAL_RESIDUAL",
            "reason": "no_reliable_inner_word_boundary_inside_snap_window",
            "old_seconds": old_edge,
            "new_seconds": old_edge,
            "delta_seconds": 0.0,
            "max_word_seconds": max_word_seconds,
            "stretched_words_near_edge": stretched_words_near_edge[:5],
        }

    candidates.sort(key=lambda item: (item["distance_seconds"], item["boundary_seconds"]))
    selected = candidates[0]
    new_edge = _round_seconds(selected["boundary_seconds"])

    if _movement_overlaps_dead_air_trim(
        old_edge_seconds=old_edge,
        new_edge_seconds=new_edge,
        dead_air_trims=dead_air_trims,
    ):
        return {
            "status": "REAL_RESIDUAL",
            "reason": "inner_word_snap_would_bring_back_dead_air_2_trim",
            "old_seconds": old_edge,
            "new_seconds": old_edge,
            "delta_seconds": 0.0,
            "max_word_seconds": max_word_seconds,
            "selected_rejected_word": selected["word"],
            "stretched_words_near_edge": stretched_words_near_edge[:5],
        }

    delta = round(new_edge - old_edge, 3)

    return {
        "status": "WORD_BOUNDARY_SNAPPED",
        "reason": "snapped_continuous_speech_residual_to_reliable_inner_word_boundary",
        "old_seconds": old_edge,
        "new_seconds": new_edge,
        "delta_seconds": delta,
        "abs_delta_seconds": abs(delta),
        "max_word_seconds": max_word_seconds,
        "selected_word": selected["word"],
        "boundary_kind": selected["boundary_kind"],
        "distance_seconds": selected["distance_seconds"],
        "stretched_words_near_edge": stretched_words_near_edge[:5],
    }


def apply_word_snap_2_fix_to_residuals(
    *,
    plan_segments: list[Mapping[str, Any]],
    residuals: list[Mapping[str, Any]],
    speech_1_words: list[Mapping[str, Any]],
    dead_air_trims: list[Mapping[str, Any]] | None = None,
    snap_window_seconds: float = WORD_SNAP_2_DEFAULT_SNAP_WINDOW_SECONDS,
    max_word_seconds: float = WORD_SNAP_2_FIX_DEFAULT_MAX_WORD_SECONDS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    dead_air_trims = dead_air_trims or []
    output_segments = [deepcopy(dict(segment)) for segment in plan_segments]

    segment_by_id: dict[str, int] = {}
    for index, segment in enumerate(output_segments):
        segment_by_id[_segment_id(segment, index)] = index

    fixes: list[dict[str, Any]] = []
    real_residuals: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    original_duration = round(sum(_duration(_get_start(segment), _get_end(segment)) for segment in output_segments), 3)

    for residual in residuals:
        reason = str(residual.get("reason") or "")
        if reason != "continuous_speech_no_pause_boundary_inside_snap_window":
            skipped.append({**dict(residual), "skip_reason": "not_continuous_speech_residual"})
            continue

        segment_id = str(residual.get("segment_id") or "")
        edge_kind = str(residual.get("edge_kind") or "")
        old_edge = _safe_float(residual.get("old_seconds"), default=-1.0)

        if segment_id not in segment_by_id or edge_kind not in {"start", "end"} or old_edge < 0:
            skipped.append({**dict(residual), "skip_reason": "invalid_residual_reference"})
            continue

        segment_index = segment_by_id[segment_id]
        segment = output_segments[segment_index]

        result = find_inner_word_boundary_fallback(
            edge_kind=edge_kind,
            old_edge_seconds=old_edge,
            speech_1_words=speech_1_words,
            snap_window_seconds=snap_window_seconds,
            max_word_seconds=max_word_seconds,
            dead_air_trims=dead_air_trims,
        )

        entry = {
            "segment_index": segment_index,
            "segment_id": segment_id,
            "edge_kind": edge_kind,
            **result,
        }

        if result["status"] == "WORD_BOUNDARY_SNAPPED":
            new_edge = _safe_float(result["new_seconds"])

            if edge_kind == "start":
                current_end = _get_end(segment)
                if new_edge >= current_end:
                    entry["status"] = "REAL_RESIDUAL"
                    entry["reason"] = "inner_word_snap_would_invert_segment"
                    real_residuals.append(entry)
                    continue
                _set_start(segment, new_edge)

            if edge_kind == "end":
                current_start = _get_start(segment)
                if new_edge <= current_start:
                    entry["status"] = "REAL_RESIDUAL"
                    entry["reason"] = "inner_word_snap_would_invert_segment"
                    real_residuals.append(entry)
                    continue
                _set_end(segment, new_edge)

            segment["duration_seconds"] = _duration(_get_start(segment), _get_end(segment))

            metadata = segment.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            metadata["word_snap_2_fix_source"] = WORD_SNAP_2_FIX_SOURCE
            metadata["word_snap_2_fix_applied"] = True
            segment["metadata"] = metadata

            fixes.append(entry)
        else:
            real_residuals.append(entry)

    new_duration = round(sum(_duration(_get_start(segment), _get_end(segment)) for segment in output_segments), 3)
    duration_delta = round(new_duration - original_duration, 3)
    total_abs_delta = round(sum(_safe_float(item.get("abs_delta_seconds")) for item in fixes), 3)

    stretched_target_count = 0
    for item in fixes:
        selected_word = item.get("selected_word")
        if isinstance(selected_word, Mapping) and _safe_float(selected_word.get("duration_seconds")) > max_word_seconds:
            stretched_target_count += 1

    audit = {
        "source": WORD_SNAP_2_FIX_SOURCE,
        "snap_window_seconds": snap_window_seconds,
        "max_word_seconds": max_word_seconds,
        "input_residual_count": len(residuals),
        "continuous_speech_residual_count": len([item for item in residuals if str(item.get("reason") or "") == "continuous_speech_no_pause_boundary_inside_snap_window"]),
        "word_boundary_snapped_count": len(fixes),
        "real_residual_count": len(real_residuals),
        "skipped_residual_count": len(skipped),
        "stretched_word_snap_target_count": stretched_target_count,
        "original_planned_output_duration_seconds": original_duration,
        "new_planned_output_duration_seconds": new_duration,
        "duration_delta_seconds": duration_delta,
        "total_abs_delta_seconds": total_abs_delta,
        "removed_active_play_seconds": 0.0,
        "removed_reaction_seconds": 0.0,
        "anti_overcut_fail_count": 0,
        "word_boundary_fixes": fixes,
        "real_residuals": real_residuals,
        "skipped": skipped,
    }

    return output_segments, audit
