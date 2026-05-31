from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping


CONTENT_GAP_PROTECTOR_SOURCE = "content_gap_protector_v2_audio_primary_dense_speech"


@dataclass(frozen=True)
class ContentGapProtectorConfig:
    speech_run_min_seconds: float = 4.0
    speech_share_min: float = 0.50
    min_dead_gap_seconds: float = 1.5
    audio_floor_percentile: float = 0.70
    reaction_medium_score: float = 0.50
    late_lobby_start_seconds: float = 900.0
    late_lobby_speech_run_min_seconds: float = 10.0
    late_lobby_speech_share_min: float = 0.75


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        number = float(str(value).strip())
    except Exception:
        return None

    if not math.isfinite(number):
        return None

    return number


def _safe_float(value: Any, default: float = 0.0) -> float:
    number = _parse_float(value)
    return default if number is None else number


def _round_seconds(value: Any) -> float:
    return round(max(0.0, _safe_float(value)), 3)


def _duration(start: float, end: float) -> float:
    return round(max(0.0, end - start), 3)


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _start_end(item: Mapping[str, Any]) -> tuple[float, float] | None:
    start = item.get("start_seconds", item.get("start", item.get("start_time")))
    end = item.get("end_seconds", item.get("end", item.get("end_time")))

    if start is None or end is None:
        return None

    start_f = _round_seconds(start)
    end_f = _round_seconds(end)

    if end_f <= start_f:
        return None

    return start_f, end_f


def _walk_time_items(raw: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                walk(item)
            return

        if isinstance(value, dict):
            if _start_end(value) is not None:
                found.append(dict(value))

            for child in value.values():
                if isinstance(child, (dict, list)):
                    walk(child)

    walk(raw)
    return found


def normalize_intervals(raw: Any, *, source: str = "unknown") -> list[dict[str, Any]]:
    if isinstance(raw, list):
        items = raw
    else:
        items = _walk_time_items(raw)

    intervals: list[dict[str, Any]] = []

    for index, item in enumerate(items, start=1):
        if not isinstance(item, Mapping):
            continue

        se = _start_end(item)
        if se is None:
            continue

        start, end = se
        normalized = dict(item)
        normalized["start_seconds"] = start
        normalized["end_seconds"] = end
        normalized["duration_seconds"] = _duration(start, end)
        normalized.setdefault("source", source)
        normalized.setdefault("interval_id", str(item.get("segment_id") or item.get("id") or f"{source}_{index:05d}"))
        intervals.append(normalized)

    return sorted(intervals, key=lambda row: (row["start_seconds"], row["end_seconds"], row.get("interval_id", "")))


def _merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    clean = sorted(
        (_round_seconds(start), _round_seconds(end))
        for start, end in intervals
        if end > start
    )

    merged: list[tuple[float, float]] = []

    for start, end in clean:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))

    return [(round(start, 3), round(end, 3)) for start, end in merged]


def derive_internal_gaps(kept_segments: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    intervals: list[tuple[float, float]] = []

    for segment in kept_segments:
        se = _start_end(segment)
        if se is not None:
            intervals.append(se)

    merged = _merge_intervals(intervals)
    gaps: list[dict[str, Any]] = []

    for index in range(1, len(merged)):
        previous_end = merged[index - 1][1]
        next_start = merged[index][0]

        if next_start > previous_end:
            gaps.append({
                "gap_id": f"gap_{len(gaps) + 1:04d}",
                "start_seconds": round(previous_end, 3),
                "end_seconds": round(next_start, 3),
                "duration_seconds": _duration(previous_end, next_start),
            })

    return gaps


def _percentile(values: list[float], percentile: float) -> float:
    clean = sorted(value for value in values if math.isfinite(value))

    if not clean:
        return 0.0

    if len(clean) == 1:
        return clean[0]

    position = (len(clean) - 1) * percentile
    lower = int(math.floor(position))
    upper = int(math.ceil(position))

    if lower == upper:
        return clean[lower]

    return clean[lower] + (clean[upper] - clean[lower]) * (position - lower)


def _has_parseable_key(items: list[Mapping[str, Any]], key: str) -> bool:
    return any(_parse_float(item.get(key)) is not None for item in items)


def _discover_audio_keys(items: list[Mapping[str, Any]]) -> list[str]:
    keys = []
    for key in ("audio_peak_score", "audio_activity"):
        if _has_parseable_key(items, key):
            keys.append(key)
    return keys


def _discover_motion_keys(items: list[Mapping[str, Any]]) -> list[str]:
    keys = []
    for key in ("motion_score", "scene_change_score"):
        if _has_parseable_key(items, key):
            keys.append(key)
    return keys


def _value_for_key(item: Mapping[str, Any], key: str) -> float | None:
    return _parse_float(item.get(key))


def _max_key_value(item: Mapping[str, Any], keys: list[str]) -> float:
    values = [_value_for_key(item, key) for key in keys]
    clean = [value for value in values if value is not None]
    return max(clean) if clean else 0.0


def _audio_value(item: Mapping[str, Any], audio_keys: list[str]) -> float:
    peak = _value_for_key(item, "audio_peak_score")
    activity = _value_for_key(item, "audio_activity")

    if peak is not None:
        return peak

    if activity is not None:
        return activity

    return _max_key_value(item, audio_keys)


def _audio_floor_values(items: list[Mapping[str, Any]]) -> tuple[str, list[float]]:
    peak_values = []
    activity_values = []

    for item in items:
        peak = _value_for_key(item, "audio_peak_score")
        activity = _value_for_key(item, "audio_activity")

        if peak is not None:
            peak_values.append(peak)

        if activity is not None:
            activity_values.append(activity)

    if peak_values:
        return "audio_peak_score", peak_values

    return "audio_activity", activity_values


def _weighted_mean(values: list[tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in values)

    if total_weight <= 0:
        return 0.0

    return sum(value * weight for value, weight in values) / total_weight


def _clip_interval(start: float, end: float, limit_start: float, limit_end: float) -> tuple[float, float] | None:
    clipped_start = max(start, limit_start)
    clipped_end = min(end, limit_end)

    if clipped_end <= clipped_start:
        return None

    return round(clipped_start, 3), round(clipped_end, 3)


def _overlap_seconds(intervals: list[Mapping[str, Any]], start: float, end: float) -> float:
    total = 0.0

    for item in intervals:
        se = _start_end(item)
        if se is None:
            continue

        total += _overlap(start, end, se[0], se[1])

    return round(total, 3)


def _longest_overlap_run(intervals: list[Mapping[str, Any]], start: float, end: float) -> float:
    clipped: list[tuple[float, float]] = []

    for item in intervals:
        se = _start_end(item)
        if se is None:
            continue

        clipped_item = _clip_interval(se[0], se[1], start, end)
        if clipped_item is not None:
            clipped.append(clipped_item)

    merged = _merge_intervals(clipped)

    if not merged:
        return 0.0

    return round(max(end_i - start_i for start_i, end_i in merged), 3)


def _state_text(item: Mapping[str, Any]) -> str:
    parts: list[str] = []

    for key in (
        "state",
        "g6_state",
        "play_state",
        "segment_state",
        "label",
        "kind",
        "type",
        "classification",
        "reason",
    ):
        if item.get(key) is not None:
            parts.append(f"{key}={item.get(key)}")

    return " | ".join(parts) if parts else "state_unknown"


def _g6_states_in_gap(
    *,
    g6_states: list[Mapping[str, Any]],
    start: float,
    end: float,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []

    for item in g6_states:
        se = _start_end(item)
        if se is None:
            continue

        overlap_seconds = _overlap(start, end, se[0], se[1])
        if overlap_seconds <= 0:
            continue

        hits.append({
            "start_seconds": se[0],
            "end_seconds": se[1],
            "overlap_seconds": round(overlap_seconds, 3),
            "state": _state_text(item),
        })

    return hits


def _state_blob(states: list[dict[str, Any]]) -> str:
    return " ".join(str(row.get("state") or "").lower() for row in states)


def _looks_like_late_dead_lobby(gap_start: float, g6_state_hits: list[dict[str, Any]], config: ContentGapProtectorConfig) -> bool:
    if gap_start < config.late_lobby_start_seconds:
        return False

    blob = _state_blob(g6_state_hits)
    has_dead_state = any(token in blob for token in ("intro_menu_lobby", "transition_dead_time", "unknown"))
    has_active = "active_play" in blob

    return has_dead_state and not has_active


def _reaction_level(item: Mapping[str, Any]) -> str:
    for key in ("level", "reaction_level", "intensity_level", "strength", "label"):
        value = item.get(key)
        if value is not None:
            return str(value).lower()

    return ""


def _reaction_score(item: Mapping[str, Any]) -> float:
    for key in ("score", "reaction_score", "intensity", "confidence"):
        if item.get(key) is not None:
            return _safe_float(item.get(key))
    return 0.0


def _reaction_is_medium_or_higher(item: Mapping[str, Any], medium_score: float) -> bool:
    level = _reaction_level(item)

    if any(token in level for token in ("medium", "high", "strong", "extreme", "loud")):
        return True

    if any(token in level for token in ("low", "weak", "small")):
        return False

    return _reaction_score(item) >= medium_score


def _reaction_hits_in_gap(
    *,
    reactions: list[Mapping[str, Any]],
    start: float,
    end: float,
    medium_score: float,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []

    for item in reactions:
        se = _start_end(item)
        if se is None:
            continue

        overlap_seconds = _overlap(start, end, se[0], se[1])
        if overlap_seconds <= 0:
            continue

        medium_or_higher = _reaction_is_medium_or_higher(item, medium_score)

        hits.append({
            "start_seconds": se[0],
            "end_seconds": se[1],
            "overlap_seconds": round(overlap_seconds, 3),
            "level": _reaction_level(item),
            "score": round(_reaction_score(item), 6),
            "medium_or_higher": medium_or_higher,
        })

    return hits


def _speech_seconds_for_segments(
    *,
    segments: list[Mapping[str, Any]],
    speech_regions: list[Mapping[str, Any]],
) -> float:
    total = 0.0

    for segment in segments:
        se = _start_end(segment)
        if se is None:
            continue

        total += _overlap_seconds(speech_regions, se[0], se[1])

    return round(total, 3)


def _build_segment_from_interval(index: int, start: float, end: float) -> dict[str, Any]:
    return {
        "segment_id": f"content_gap_protected_{index:04d}",
        "start_seconds": round(start, 3),
        "end_seconds": round(end, 3),
        "duration_seconds": _duration(start, end),
        "state": "active_play",
        "metadata": {
            "source": CONTENT_GAP_PROTECTOR_SOURCE,
            "content_gap_protector_applied": True,
        },
    }


def protect_content_gaps(
    *,
    kept_segments: list[Mapping[str, Any]],
    raw_windows: list[Mapping[str, Any]],
    combined_speech_regions: list[Mapping[str, Any]],
    reactions: list[Mapping[str, Any]] | None = None,
    g6_states: list[Mapping[str, Any]] | None = None,
    config: ContentGapProtectorConfig | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config = config or ContentGapProtectorConfig()
    reactions = reactions or []
    g6_states = g6_states or []

    normalized_kept = normalize_intervals(kept_segments, source="kept_plan_segment")
    normalized_raw = normalize_intervals(raw_windows, source="raw_action_window")
    normalized_speech = normalize_intervals(combined_speech_regions, source="combined_speech")
    normalized_reactions = normalize_intervals(reactions, source="reaction")
    normalized_g6 = normalize_intervals(g6_states, source="g6_state")

    audio_keys = _discover_audio_keys(normalized_raw)
    motion_keys = _discover_motion_keys(normalized_raw)
    audio_floor_key, audio_values_for_floor = _audio_floor_values(normalized_raw)
    audio_floor = _percentile(audio_values_for_floor, config.audio_floor_percentile) if audio_values_for_floor else 0.0

    gaps = derive_internal_gaps(normalized_kept)
    reinclude_intervals: list[tuple[float, float]] = []
    gap_rows: list[dict[str, Any]] = []

    for gap in gaps:
        gap_start = _safe_float(gap["start_seconds"])
        gap_end = _safe_float(gap["end_seconds"])
        gap_duration = _duration(gap_start, gap_end)

        audio_weighted: list[tuple[float, float]] = []
        motion_weighted: list[tuple[float, float]] = []

        audio_max = 0.0
        motion_max = 0.0

        for window in normalized_raw:
            se = _start_end(window)
            if se is None:
                continue

            overlap_seconds = _overlap(gap_start, gap_end, se[0], se[1])
            if overlap_seconds <= 0:
                continue

            audio_value = _audio_value(window, audio_keys)
            motion_value = _max_key_value(window, motion_keys)

            audio_max = max(audio_max, audio_value)
            motion_max = max(motion_max, motion_value)

            audio_weighted.append((audio_value, overlap_seconds))
            motion_weighted.append((motion_value, overlap_seconds))

        audio_mean = _weighted_mean(audio_weighted)
        motion_mean = _weighted_mean(motion_weighted)

        speech_seconds = _overlap_seconds(normalized_speech, gap_start, gap_end)
        longest_speech_run = _longest_overlap_run(normalized_speech, gap_start, gap_end)
        speech_share = round(speech_seconds / max(0.001, gap_duration), 3)

        reaction_hits = _reaction_hits_in_gap(
            reactions=normalized_reactions,
            start=gap_start,
            end=gap_end,
            medium_score=config.reaction_medium_score,
        )
        reaction_medium = any(hit["medium_or_higher"] for hit in reaction_hits)
        reaction_level = "MEDIUM_OR_HIGHER" if reaction_medium else ("LOW_OR_UNKNOWN" if reaction_hits else "NONE")

        g6_state_hits = _g6_states_in_gap(
            g6_states=normalized_g6,
            start=gap_start,
            end=gap_end,
        )

        late_dead_lobby = _looks_like_late_dead_lobby(gap_start, g6_state_hits, config)

        audio_action = bool(audio_keys and audio_floor > 0 and audio_max >= audio_floor)

        dense_speech_regular = (
            longest_speech_run >= config.speech_run_min_seconds
            or speech_share >= config.speech_share_min
        )
        dense_speech_late_lobby = (
            longest_speech_run >= config.late_lobby_speech_run_min_seconds
            and speech_share >= config.late_lobby_speech_share_min
        )

        speech_content = dense_speech_late_lobby if late_dead_lobby else dense_speech_regular

        is_content = bool(audio_action or reaction_medium or speech_content)

        if is_content:
            classification = "CONTENT"
            action = "RE_INCLUDED_FULL_GAP"
            reinclude_intervals.append((gap_start, gap_end))
        else:
            classification = "DEAD"
            action = "UNCHANGED_TRIMMED_DEAD"

        gap_rows.append({
            "gap_id": gap["gap_id"],
            "start_seconds": gap_start,
            "end_seconds": gap_end,
            "duration_seconds": gap_duration,
            "g6_states": g6_state_hits,
            "speech_seconds": speech_seconds,
            "speech_share": speech_share,
            "longest_speech_run_seconds": longest_speech_run,
            "speech_run_min_seconds": config.speech_run_min_seconds,
            "speech_share_min": config.speech_share_min,
            "late_dead_lobby": late_dead_lobby,
            "late_lobby_speech_run_min_seconds": config.late_lobby_speech_run_min_seconds,
            "late_lobby_speech_share_min": config.late_lobby_speech_share_min,
            "audio_max": round(audio_max, 6),
            "audio_mean": round(audio_mean, 6),
            "audio_floor": round(audio_floor, 6),
            "audio_floor_key": audio_floor_key,
            "audio_action": audio_action,
            "motion_max": round(motion_max, 6),
            "motion_mean": round(motion_mean, 6),
            "motion_report_only": True,
            "reaction_level": reaction_level,
            "reaction_hits": reaction_hits,
            "classification": classification,
            "action": action,
            "reinclude_start_seconds": gap_start if is_content else None,
            "reinclude_end_seconds": gap_end if is_content else None,
            "reinclude_seconds": gap_duration if is_content else 0.0,
            "content_reason": {
                "audio_action": audio_action,
                "reaction_medium_or_higher": reaction_medium,
                "speech_content": speech_content,
                "dense_speech_regular": dense_speech_regular,
                "dense_speech_late_lobby": dense_speech_late_lobby,
                "motion_used_as_primary_reason": False,
            },
        })

    original_intervals = []
    for segment in normalized_kept:
        se = _start_end(segment)
        if se is not None:
            original_intervals.append(se)

    protected_intervals = _merge_intervals(original_intervals + reinclude_intervals)
    new_segments = [
        _build_segment_from_interval(index=index, start=start, end=end)
        for index, (start, end) in enumerate(protected_intervals, start=1)
    ]

    old_duration = round(sum(_duration(start, end) for start, end in _merge_intervals(original_intervals)), 3)
    new_duration = round(sum(_duration(start, end) for start, end in protected_intervals), 3)

    old_speech_seconds = _speech_seconds_for_segments(
        segments=normalized_kept,
        speech_regions=normalized_speech,
    )
    new_speech_seconds = _speech_seconds_for_segments(
        segments=new_segments,
        speech_regions=normalized_speech,
    )

    anti_overcut_fail_count = 0
    for segment in new_segments:
        se = _start_end(segment)
        if se is None:
            anti_overcut_fail_count += 1

    def target_check(target_start: float, target_end: float) -> dict[str, Any]:
        matching = None

        for row in gap_rows:
            ov = _overlap(target_start, target_end, row["start_seconds"], row["end_seconds"])
            if ov >= 0.80 * (target_end - target_start):
                matching = row
                break

        if matching is None:
            return {
                "target": [target_start, target_end],
                "found_gap": False,
                "content": False,
                "reincluded": False,
                "status": "NEIN",
            }

        return {
            "target": [target_start, target_end],
            "found_gap": True,
            "gap": [matching["start_seconds"], matching["end_seconds"]],
            "speech_seconds": matching["speech_seconds"],
            "speech_share": matching["speech_share"],
            "longest_speech_run_seconds": matching["longest_speech_run_seconds"],
            "audio_max": matching["audio_max"],
            "audio_floor": matching["audio_floor"],
            "audio_action": matching["audio_action"],
            "motion_max": matching["motion_max"],
            "classification": matching["classification"],
            "content_reason": matching["content_reason"],
            "content": matching["classification"] == "CONTENT",
            "reincluded": matching["reinclude_seconds"] > 0,
            "status": "JA" if matching["classification"] == "CONTENT" and matching["reinclude_seconds"] > 0 else "NEIN",
        }

    late_lobby_gap_rows = [row for row in gap_rows if row["late_dead_lobby"]]
    late_dead_reincluded = [row for row in late_lobby_gap_rows if row["classification"] == "CONTENT"]

    if late_lobby_gap_rows and not late_dead_reincluded:
        late_lobby_status = "JA"
    elif late_dead_reincluded:
        late_lobby_status = "NEIN"
    else:
        late_lobby_status = "UNKNOWN_NO_LATE_DEAD_LOBBY_GAPS_FOUND"

    audit = {
        "source": CONTENT_GAP_PROTECTOR_SOURCE,
        "config": {
            "speech_run_min_seconds": config.speech_run_min_seconds,
            "speech_share_min": config.speech_share_min,
            "min_dead_gap_seconds": config.min_dead_gap_seconds,
            "audio_floor_percentile": config.audio_floor_percentile,
            "reaction_medium_score": config.reaction_medium_score,
            "late_lobby_start_seconds": config.late_lobby_start_seconds,
            "late_lobby_speech_run_min_seconds": config.late_lobby_speech_run_min_seconds,
            "late_lobby_speech_share_min": config.late_lobby_speech_share_min,
        },
        "metric_discovery": {
            "audio_keys": audio_keys,
            "motion_keys_report_only": motion_keys,
            "audio_floor_key": audio_floor_key,
            "audio_floor": round(audio_floor, 6),
            "motion_primary_allowed": False,
        },
        "gap_count": len(gap_rows),
        "content_gap_count": len([row for row in gap_rows if row["classification"] == "CONTENT"]),
        "dead_gap_count": len([row for row in gap_rows if row["classification"] == "DEAD"]),
        "reincluded_gap_count": len([row for row in gap_rows if row["reinclude_seconds"] > 0]),
        "old_plan_duration_seconds": old_duration,
        "new_plan_duration_seconds": new_duration,
        "duration_delta_seconds": round(new_duration - old_duration, 3),
        "old_kept_speech_seconds": old_speech_seconds,
        "new_kept_speech_seconds": new_speech_seconds,
        "kept_speech_not_lost": new_speech_seconds >= old_speech_seconds,
        "anti_overcut_fail_count": anti_overcut_fail_count,
        "hard_checks": {
            "round1_gap_142_166_content_and_reincluded": target_check(142.0, 166.0),
            "round1_gap_172_246_content_and_reincluded": target_check(172.3, 246.0),
            "within_round_gap_120_133_6_content": target_check(120.0, 133.596),
            "late_round_dead_lobbies_remain_dead_trimmed": {
                "status": late_lobby_status,
                "late_lobby_gap_count": len(late_lobby_gap_rows),
                "late_dead_lobby_reincluded_count": len(late_dead_reincluded),
                "late_lobby_rows": [
                    {
                        "gap_id": row["gap_id"],
                        "start_seconds": row["start_seconds"],
                        "end_seconds": row["end_seconds"],
                        "audio_max": row["audio_max"],
                        "audio_floor": row["audio_floor"],
                        "speech_share": row["speech_share"],
                        "longest_speech_run_seconds": row["longest_speech_run_seconds"],
                        "classification": row["classification"],
                    }
                    for row in late_lobby_gap_rows
                ],
            },
            "anti_overcut_zero": "JA" if anti_overcut_fail_count == 0 else "NEIN",
            "no_kept_speech_lost": "JA" if new_speech_seconds >= old_speech_seconds else "NEIN",
            "duration_under_previous_bad_29min": "JA" if new_duration < 1766.021 else "NEIN",
        },
        "gap_rows": gap_rows,
        "new_segments": new_segments,
    }

    return new_segments, audit
