from __future__ import annotations

import copy
import math
from typing import Any, Mapping


DEAD_AIR_1_SOURCE = "dead_air_1_speech_aware_low_action_trim"
DEFAULT_MIN_DEAD_GAP_SECONDS = 1.5
DEFAULT_EDGE_BUFFER_SECONDS = 0.2
DEFAULT_ACTION_FLOOR_PERCENTILE = 25.0


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


def _field(item: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(item, Mapping) and name in item:
            return item[name]
        if hasattr(item, name):
            return getattr(item, name)
    return default


def percentile(values: list[float], pct: float, *, default: float = 0.0) -> float:
    cleaned = sorted(float(v) for v in values if math.isfinite(float(v)))
    if not cleaned:
        return default
    if len(cleaned) == 1:
        return round(cleaned[0], 6)

    pct = max(0.0, min(100.0, float(pct)))
    pos = (len(cleaned) - 1) * (pct / 100.0)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return round(cleaned[lo], 6)

    weight = pos - lo
    return round(cleaned[lo] + ((cleaned[hi] - cleaned[lo]) * weight), 6)


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _overlaps(start_a: float, end_a: float, start_b: float, end_b: float) -> bool:
    return _overlap_seconds(start_a, end_a, start_b, end_b) > 0.0001


def normalize_silence_gaps(raw_gaps: Any) -> list[dict[str, Any]]:
    if isinstance(raw_gaps, Mapping):
        for key in ("silence_gaps", "gaps", "items"):
            if isinstance(raw_gaps.get(key), list):
                raw_gaps = raw_gaps[key]
                break

    if not isinstance(raw_gaps, list):
        return []

    gaps: list[dict[str, Any]] = []
    for index, item in enumerate(raw_gaps, start=1):
        if not isinstance(item, Mapping):
            continue
        start = _field(item, "start_seconds", "start", "start_time", default=None)
        end = _field(item, "end_seconds", "end", "end_time", default=None)
        if start is None or end is None:
            continue

        start_f = _round_seconds(start)
        end_f = _round_seconds(end)
        if end_f <= start_f:
            continue

        gaps.append({
            "silence_gap_id": str(_field(item, "silence_gap_id", "gap_id", "id", default=f"silence_gap_{index:04d}")),
            "start_seconds": start_f,
            "end_seconds": end_f,
            "duration_seconds": _duration(start_f, end_f),
        })

    return sorted(gaps, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def normalize_speech_segments(raw_segments: Any) -> list[dict[str, Any]]:
    if isinstance(raw_segments, Mapping):
        for key in ("speech_segments", "segments", "items"):
            if isinstance(raw_segments.get(key), list):
                raw_segments = raw_segments[key]
                break

    if not isinstance(raw_segments, list):
        return []

    result: list[dict[str, Any]] = []
    for index, item in enumerate(raw_segments, start=1):
        if not isinstance(item, Mapping):
            continue
        start = _field(item, "start_seconds", "start", "start_time", default=None)
        end = _field(item, "end_seconds", "end", "end_time", default=None)
        if start is None or end is None:
            continue
        start_f = _round_seconds(start)
        end_f = _round_seconds(end)
        if end_f <= start_f:
            continue
        result.append({
            "speech_segment_id": str(_field(item, "speech_segment_id", "segment_id", "id", default=f"speech_{index:04d}")),
            "start_seconds": start_f,
            "end_seconds": end_f,
            "duration_seconds": _duration(start_f, end_f),
            "text": str(_field(item, "text", "transcript", default="") or "").strip(),
        })

    return sorted(result, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def derive_silence_gaps_from_speech_segments(
    speech_segments: list[Mapping[str, Any]],
    *,
    media_duration_seconds: float,
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    cursor = 0.0

    for index, speech in enumerate(sorted(speech_segments, key=lambda item: _safe_float(item.get("start_seconds"))), start=1):
        start = _round_seconds(speech.get("start_seconds"))
        end = _round_seconds(speech.get("end_seconds"))
        if start > cursor:
            gaps.append({
                "silence_gap_id": f"derived_silence_gap_{len(gaps) + 1:04d}",
                "start_seconds": _round_seconds(cursor),
                "end_seconds": start,
                "duration_seconds": _duration(cursor, start),
                "derived_from_speech_segments": True,
            })
        cursor = max(cursor, end)

    media_end = _round_seconds(media_duration_seconds)
    if cursor < media_end:
        gaps.append({
            "silence_gap_id": f"derived_silence_gap_{len(gaps) + 1:04d}",
            "start_seconds": _round_seconds(cursor),
            "end_seconds": media_end,
            "duration_seconds": _duration(cursor, media_end),
            "derived_from_speech_segments": True,
        })

    return gaps


def _action_score_from_item(item: Mapping[str, Any]) -> float:
    evidence = item.get("evidence") if isinstance(item.get("evidence"), Mapping) else {}

    direct = _field(evidence, "active_score", "avg_active_score", default=None)
    if direct is not None:
        return round(max(0.0, min(1.0, _safe_float(direct))), 6)

    direct = _field(item, "active_score", "action_score", default=None)
    if direct is not None:
        return round(max(0.0, min(1.0, _safe_float(direct))), 6)

    motion = _safe_float(_field(item, "motion_score", default=_field(evidence, "avg_motion_score", default=0.0)))
    audio = _safe_float(_field(item, "audio_activity", default=_field(evidence, "avg_audio_activity", default=0.0)))
    peak = _safe_float(_field(item, "audio_peak_score", default=0.0))
    stability = _safe_float(_field(evidence, "avg_stability_bundle", default=_field(item, "visual_stability", default=0.5)))

    # Fallback nur wenn active_score fehlt:
    # Motion + Gameplay-Audio hoch = eher Action.
    # Stabile Szene mit wenig Motion = eher wenig Action.
    score = (0.45 * motion) + (0.35 * audio) + (0.10 * peak) + (0.10 * (1.0 - stability))
    return round(max(0.0, min(1.0, score)), 6)


def normalize_g6_action_windows(raw_g6: Any) -> list[dict[str, Any]]:
    if isinstance(raw_g6, Mapping) and isinstance(raw_g6.get("raw_windows"), list) and raw_g6["raw_windows"]:
        raw_items = raw_g6["raw_windows"]
        source_kind = "raw_windows"
    elif isinstance(raw_g6, Mapping) and isinstance(raw_g6.get("segments"), list):
        raw_items = raw_g6["segments"]
        source_kind = "segments_fallback"
    elif isinstance(raw_g6, list):
        raw_items = raw_g6
        source_kind = "list"
    else:
        raw_items = []
        source_kind = "empty"

    windows: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, Mapping):
            continue
        start = _field(item, "start_seconds", "start", "start_time", default=None)
        end = _field(item, "end_seconds", "end", "end_time", default=None)
        if start is None or end is None:
            continue

        start_f = _round_seconds(start)
        end_f = _round_seconds(end)
        if end_f <= start_f:
            continue

        windows.append({
            "g6_window_id": f"g6_window_{index:05d}",
            "start_seconds": start_f,
            "end_seconds": end_f,
            "duration_seconds": _duration(start_f, end_f),
            "state": str(_field(item, "state", default="unknown")),
            "intensity": str(_field(item, "intensity", default="unknown")),
            "action_score": _action_score_from_item(item),
            "source_kind": source_kind,
        })

    return sorted(windows, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def adaptive_action_floor(
    g6_windows: list[Mapping[str, Any]],
    *,
    percentile_value: float = DEFAULT_ACTION_FLOOR_PERCENTILE,
) -> dict[str, Any]:
    active_scores = [
        _safe_float(item.get("action_score"))
        for item in g6_windows
        if str(item.get("state")) == "active_play"
    ]

    if not active_scores:
        active_scores = [_safe_float(item.get("action_score")) for item in g6_windows]

    threshold = percentile(active_scores, percentile_value, default=0.0)

    return {
        "percentile": float(percentile_value),
        "threshold": round(threshold, 6),
        "sample_count": len(active_scores),
        "score_min": round(min(active_scores), 6) if active_scores else 0.0,
        "score_p25": percentile(active_scores, 25, default=0.0),
        "score_p50": percentile(active_scores, 50, default=0.0),
        "score_p75": percentile(active_scores, 75, default=0.0),
        "score_max": round(max(active_scores), 6) if active_scores else 0.0,
    }


def _action_summary_for_range(
    g6_windows: list[Mapping[str, Any]],
    *,
    start_seconds: float,
    end_seconds: float,
) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    weighted = 0.0
    total = 0.0

    for item in g6_windows:
        start = _safe_float(item.get("start_seconds"))
        end = _safe_float(item.get("end_seconds"))
        overlap = _overlap_seconds(start_seconds, end_seconds, start, end)
        if overlap <= 0:
            continue
        score = _safe_float(item.get("action_score"))
        weighted += score * overlap
        total += overlap
        hits.append({
            "start_seconds": start,
            "end_seconds": end,
            "overlap_seconds": round(overlap, 3),
            "state": item.get("state"),
            "intensity": item.get("intensity"),
            "action_score": score,
        })

    if total <= 0:
        return {
            "avg_action_score": 1.0,
            "max_action_score": 1.0,
            "g6_window_count": 0,
            "g6_windows": [],
        }

    return {
        "avg_action_score": round(weighted / total, 6),
        "max_action_score": round(max(_safe_float(item["action_score"]) for item in hits), 6),
        "g6_window_count": len(hits),
        "g6_windows": hits,
    }


def _has_speech_overlap(
    speech_segments: list[Mapping[str, Any]],
    *,
    start_seconds: float,
    end_seconds: float,
) -> bool:
    for speech in speech_segments:
        if _overlaps(
            start_seconds,
            end_seconds,
            _safe_float(speech.get("start_seconds")),
            _safe_float(speech.get("end_seconds")),
        ):
            return True
    return False


def _is_active_segment(segment: Mapping[str, Any]) -> bool:
    return str(segment.get("state") or "") == "active_play"


def _clean_existing_dead_air(plan_data: dict[str, Any]) -> dict[str, Any]:
    cleaned = copy.deepcopy(plan_data)
    cleaned.pop("dead_air_1_audit", None)
    cleaned.pop("dead_air_1_contract", None)
    cleaned.pop("dead_air_1_trimmed_gaps", None)
    return cleaned


def _find_active_segment_overlaps(
    timeline_segments: list[Mapping[str, Any]],
    *,
    start_seconds: float,
    end_seconds: float,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []

    for segment in timeline_segments:
        if not isinstance(segment, Mapping):
            continue
        if not _is_active_segment(segment):
            continue

        seg_start = _safe_float(segment.get("start_seconds"))
        seg_end = _safe_float(segment.get("end_seconds"))
        overlap_start = max(start_seconds, seg_start)
        overlap_end = min(end_seconds, seg_end)

        if overlap_end <= overlap_start:
            continue

        hits.append({
            "segment": segment,
            "overlap_start_seconds": round(overlap_start, 3),
            "overlap_end_seconds": round(overlap_end, 3),
        })

    return hits


def _merge_ranges(ranges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(ranges, key=lambda item: (item["trim_start_seconds"], item["trim_end_seconds"]))
    merged: list[dict[str, Any]] = []

    for item in ordered:
        if not merged:
            merged.append(dict(item))
            continue
        previous = merged[-1]
        if item["trim_start_seconds"] <= previous["trim_end_seconds"] + 0.001:
            previous["trim_end_seconds"] = max(previous["trim_end_seconds"], item["trim_end_seconds"])
            previous["duration_seconds"] = _duration(previous["trim_start_seconds"], previous["trim_end_seconds"])
            previous.setdefault("merged_from", []).append(item)
        else:
            merged.append(dict(item))

    return merged


def apply_dead_air_trim(
    plan_data: dict[str, Any],
    silence_gaps: list[Mapping[str, Any]],
    g6_action_windows: list[Mapping[str, Any]],
    *,
    speech_segments: list[Mapping[str, Any]] | None = None,
    min_dead_gap_seconds: float = DEFAULT_MIN_DEAD_GAP_SECONDS,
    edge_buffer_seconds: float = DEFAULT_EDGE_BUFFER_SECONDS,
    action_floor_percentile: float = DEFAULT_ACTION_FLOOR_PERCENTILE,
) -> dict[str, Any]:
    if min_dead_gap_seconds < 0:
        raise ValueError("min_dead_gap_seconds must be >= 0")
    if edge_buffer_seconds < 0:
        raise ValueError("edge_buffer_seconds must be >= 0")

    cleaned = _clean_existing_dead_air(plan_data)
    timeline_segments = [
        dict(segment)
        for segment in cleaned.get("timeline_segments") or []
        if isinstance(segment, Mapping)
    ]

    speech_items = list(speech_segments or [])
    floor = adaptive_action_floor(g6_action_windows, percentile_value=action_floor_percentile)
    threshold = float(floor["threshold"])

    evaluations: list[dict[str, Any]] = []
    trim_ranges: list[dict[str, Any]] = []

    for gap in silence_gaps:
        gap_start = _safe_float(gap.get("start_seconds"))
        gap_end = _safe_float(gap.get("end_seconds"))
        gap_duration = _duration(gap_start, gap_end)

        base_eval = {
            "silence_gap_id": gap.get("silence_gap_id"),
            "gap_start_seconds": round(gap_start, 3),
            "gap_end_seconds": round(gap_end, 3),
            "gap_duration_seconds": gap_duration,
            "min_dead_gap_seconds": round(float(min_dead_gap_seconds), 3),
            "action_floor_threshold": threshold,
            "trim_added": False,
            "reason": "",
        }

        if gap_duration < min_dead_gap_seconds:
            base_eval["reason"] = "below_min_dead_gap_seconds"
            evaluations.append(base_eval)
            continue

        active_overlaps = _find_active_segment_overlaps(
            timeline_segments,
            start_seconds=gap_start,
            end_seconds=gap_end,
        )

        if not active_overlaps:
            base_eval["reason"] = "not_inside_kept_active_play_segment"
            evaluations.append(base_eval)
            continue

        for overlap in active_overlaps:
            segment = overlap["segment"]
            raw_start = float(overlap["overlap_start_seconds"])
            raw_end = float(overlap["overlap_end_seconds"])

            trim_start = _round_seconds(raw_start + edge_buffer_seconds)
            trim_end = _round_seconds(raw_end - edge_buffer_seconds)

            evaluation = dict(base_eval)
            evaluation["segment_id"] = segment.get("segment_id")
            evaluation["block_id"] = segment.get("block_id")
            evaluation["raw_overlap_start_seconds"] = raw_start
            evaluation["raw_overlap_end_seconds"] = raw_end
            evaluation["trim_start_seconds"] = trim_start
            evaluation["trim_end_seconds"] = trim_end

            if trim_end <= trim_start:
                evaluation["reason"] = "edge_buffer_removed_gap"
                evaluations.append(evaluation)
                continue

            if _has_speech_overlap(speech_items, start_seconds=trim_start, end_seconds=trim_end):
                evaluation["reason"] = "speech_overlap_safety_block"
                evaluations.append(evaluation)
                continue

            action = _action_summary_for_range(
                g6_action_windows,
                start_seconds=trim_start,
                end_seconds=trim_end,
            )
            evaluation["avg_action_score"] = action["avg_action_score"]
            evaluation["max_action_score"] = action["max_action_score"]
            evaluation["g6_window_count"] = action["g6_window_count"]

            if float(action["max_action_score"]) > threshold:
                evaluation["reason"] = "action_above_adaptive_floor"
                evaluations.append(evaluation)
                continue

            trim = {
                "trim_id": f"dead_air_trim_{len(trim_ranges) + 1:04d}",
                "segment_id": segment.get("segment_id"),
                "block_id": segment.get("block_id"),
                "trim_start_seconds": trim_start,
                "trim_end_seconds": trim_end,
                "duration_seconds": _duration(trim_start, trim_end),
                "silence_gap_id": gap.get("silence_gap_id"),
                "gap_start_seconds": round(gap_start, 3),
                "gap_end_seconds": round(gap_end, 3),
                "avg_action_score": action["avg_action_score"],
                "max_action_score": action["max_action_score"],
                "action_floor_threshold": threshold,
                "source": DEAD_AIR_1_SOURCE,
            }
            trim_ranges.append(trim)

            evaluation.update(trim)
            evaluation["trim_added"] = True
            evaluation["reason"] = "silence_and_low_action_trimmed"
            evaluations.append(evaluation)

    trim_ranges = _merge_ranges(trim_ranges)

    trims_by_segment: dict[str, list[dict[str, Any]]] = {}
    for trim in trim_ranges:
        segment_id = str(trim.get("segment_id") or "")
        trims_by_segment.setdefault(segment_id, []).append(trim)

    new_segments: list[dict[str, Any]] = []

    for segment in timeline_segments:
        segment_id = str(segment.get("segment_id") or "")
        segment_trims = sorted(
            trims_by_segment.get(segment_id, []),
            key=lambda item: item["trim_start_seconds"],
        )

        if not segment_trims:
            new_segments.append(segment)
            continue

        seg_start = _safe_float(segment.get("start_seconds"))
        seg_end = _safe_float(segment.get("end_seconds"))
        cursor = seg_start
        piece_index = 1

        for trim in segment_trims:
            trim_start = max(seg_start, _safe_float(trim.get("trim_start_seconds")))
            trim_end = min(seg_end, _safe_float(trim.get("trim_end_seconds")))

            if trim_start > cursor:
                piece = dict(segment)
                piece["segment_id"] = f"{segment_id}_dead_air_keep_{piece_index:03d}"
                piece["start_seconds"] = _round_seconds(cursor)
                piece["end_seconds"] = _round_seconds(trim_start)
                piece["duration_seconds"] = _duration(piece["start_seconds"], piece["end_seconds"])
                metadata = dict(piece.get("metadata") or {})
                metadata["dead_air_1_split_from_segment_id"] = segment_id
                metadata["dead_air_1_trimmed"] = True
                piece["metadata"] = metadata
                new_segments.append(piece)
                piece_index += 1

            cursor = max(cursor, trim_end)

        if cursor < seg_end:
            piece = dict(segment)
            piece["segment_id"] = f"{segment_id}_dead_air_keep_{piece_index:03d}"
            piece["start_seconds"] = _round_seconds(cursor)
            piece["end_seconds"] = _round_seconds(seg_end)
            piece["duration_seconds"] = _duration(piece["start_seconds"], piece["end_seconds"])
            metadata = dict(piece.get("metadata") or {})
            metadata["dead_air_1_split_from_segment_id"] = segment_id
            metadata["dead_air_1_trimmed"] = True
            piece["metadata"] = metadata
            new_segments.append(piece)

    new_segments = [
        segment for segment in new_segments
        if _duration(_safe_float(segment.get("start_seconds")), _safe_float(segment.get("end_seconds"))) > 0.001
    ]

    new_segments = sorted(
        new_segments,
        key=lambda item: (
            _safe_float(item.get("start_seconds")),
            _safe_float(item.get("end_seconds")),
            str(item.get("segment_id") or ""),
        ),
    )

    for segment in new_segments:
        segment["duration_seconds"] = _duration(
            _safe_float(segment.get("start_seconds")),
            _safe_float(segment.get("end_seconds")),
        )

    original_duration = round(sum(_safe_float(item.get("duration_seconds")) for item in timeline_segments), 3)
    new_duration = round(sum(_safe_float(item.get("duration_seconds")) for item in new_segments), 3)
    total_trimmed = round(max(0.0, original_duration - new_duration), 3)

    cleaned["timeline_segments"] = new_segments
    cleaned["dead_air_1_trimmed_gaps"] = trim_ranges
    cleaned["dead_air_1_audit"] = {
        "engine": DEAD_AIR_1_SOURCE,
        "min_dead_gap_seconds": round(float(min_dead_gap_seconds), 3),
        "edge_buffer_seconds": round(float(edge_buffer_seconds), 3),
        "action_floor_percentile": round(float(action_floor_percentile), 3),
        "adaptive_action_floor": floor,
        "trim_count": len(trim_ranges),
        "total_trimmed_seconds": total_trimmed,
        "anti_overcut_fail_count": 0,
        "removed_speech_seconds": 0.0,
        "removed_high_action_seconds": 0.0,
        "evaluations": evaluations,
    }
    cleaned["dead_air_1_contract"] = {
        "original_planned_output_duration_seconds": original_duration,
        "new_planned_output_duration_seconds": new_duration,
        "total_trimmed_seconds": total_trimmed,
        "segment_action": "split_active_play_segments_around_silence_low_action_gaps",
    }

    duration_contract = dict(cleaned.get("duration_contract") or {})
    duration_contract["planned_output_duration_seconds"] = new_duration
    duration_contract["dead_air_1_trimmed_seconds"] = total_trimmed
    cleaned["duration_contract"] = duration_contract

    notes = list(cleaned.get("notes") or [])
    notes.append(
        f"dead_air_1 min_gap={float(min_dead_gap_seconds):.3f}s "
        f"edge_buffer={float(edge_buffer_seconds):.3f}s "
        f"action_floor_p{float(action_floor_percentile):.1f}={threshold:.6f} "
        f"trimmed={total_trimmed:.3f}s"
    )
    cleaned["notes"] = notes

    return cleaned
