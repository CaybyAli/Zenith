from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping


HIGHLIGHT_RANKING_SOURCE = "highlight_ranking_v1_budgeted_whole_segments"


@dataclass(frozen=True)
class HighlightRankingConfig:
    target_ratio: float = 0.42
    min_target_seconds: float = 480.0
    max_target_seconds: float = 1200.0
    budget_tolerance: float = 0.10

    reaction_weight: float = 0.55
    audio_weight: float = 0.30
    speech_weight: float = 0.15

    high_reaction_score: float = 0.80
    medium_reaction_score: float = 0.50
    high_reaction_prominence_percentile: float = 0.70


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

    return sorted(intervals, key=lambda row: (row["start_seconds"], row["end_seconds"], str(row.get("interval_id", ""))))


def _merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    clean = sorted((round(s, 3), round(e, 3)) for s, e in intervals if e > s)
    merged: list[tuple[float, float]] = []

    for start, end in clean:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))

    return [(round(s, 3), round(e, 3)) for s, e in merged]


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


def default_highlight_target_seconds(session_seconds: float, config: HighlightRankingConfig | None = None) -> float:
    config = config or HighlightRankingConfig()

    target = session_seconds * config.target_ratio
    target = min(target, config.max_target_seconds)
    target = max(target, config.min_target_seconds)

    return round(target, 3)


def _audio_peak_value(item: Mapping[str, Any]) -> float | None:
    primary = _parse_float(item.get("audio_peak_score"))
    if primary is not None:
        return primary

    fallback = _parse_float(item.get("audio_activity"))
    if fallback is not None:
        return fallback

    return None


def _audio_values_for_segment(
    raw_windows: list[Mapping[str, Any]],
    start: float,
    end: float,
) -> list[float]:
    values: list[float] = []

    for window in raw_windows:
        se = _start_end(window)
        if se is None:
            continue

        if _overlap(start, end, se[0], se[1]) <= 0:
            continue

        value = _audio_peak_value(window)
        if value is not None:
            values.append(value)

    return values


def _all_audio_values(raw_windows: list[Mapping[str, Any]]) -> list[float]:
    values = []

    for window in raw_windows:
        value = _audio_peak_value(window)
        if value is not None:
            values.append(value)

    return values


def _audio_prominence(segment_values: list[float], global_values: list[float]) -> dict[str, float]:
    if not segment_values or not global_values:
        return {
            "audio_max": 0.0,
            "audio_baseline_p50": 0.0,
            "audio_peak_prominence": 0.0,
            "global_audio_p50": 0.0,
            "global_audio_p70": 0.0,
            "global_audio_p95": 0.0,
        }

    audio_max = max(segment_values)
    local_p50 = _percentile(segment_values, 0.50)

    global_p50 = _percentile(global_values, 0.50)
    global_p70 = _percentile(global_values, 0.70)
    global_p95 = _percentile(global_values, 0.95)
    global_range = max(0.001, global_p95 - global_p50)

    dynamic_component = max(0.0, audio_max - local_p50) / global_range
    global_component = max(0.0, audio_max - global_p70) / global_range

    # Wichtig: nicht nur max. Flach-laute Lobby wird durch local_p50 gebremst.
    prominence = (0.75 * dynamic_component) + (0.25 * global_component)
    prominence = max(0.0, min(1.0, prominence))

    return {
        "audio_max": round(audio_max, 6),
        "audio_baseline_p50": round(local_p50, 6),
        "audio_peak_prominence": round(prominence, 6),
        "global_audio_p50": round(global_p50, 6),
        "global_audio_p70": round(global_p70, 6),
        "global_audio_p95": round(global_p95, 6),
    }


def _speech_seconds(
    speech_regions: list[Mapping[str, Any]],
    start: float,
    end: float,
) -> float:
    total = 0.0

    for region in speech_regions:
        se = _start_end(region)
        if se is None:
            continue

        total += _overlap(start, end, se[0], se[1])

    return round(total, 3)


def _reaction_level(item: Mapping[str, Any]) -> str:
    # reaction_adaptive serialisiert echtes Signal als intensity=HIGH/MEDIUM/LOW.
    # Alte level/reaction_level Felder bleiben als Fallback.
    for key in ("level", "reaction_level", "intensity", "intensity_level", "strength", "label"):
        value = item.get(key)
        if value is not None:
            text = str(value).strip().lower()
            if text and text not in {"none", "null", "nan"}:
                return text

    return ""


def _reaction_numeric_score(item: Mapping[str, Any]) -> float:
    # Fallback, falls kein intensity-Level vorhanden ist.
    # fusion_score kommt aus reaction_adaptive und ist das echte adaptive Reaktionssignal.
    for key in ("reaction_score", "score", "fusion_score", "confidence", "peak_score", "intensity"):
        value = _parse_float(item.get(key))
        if value is not None:
            return value

    return 0.0


def _reaction_strength_for_item(item: Mapping[str, Any], config: HighlightRankingConfig) -> tuple[float, bool, str]:
    level = _reaction_level(item)

    if any(token in level for token in ("extreme", "strong", "high", "loud")):
        return 1.0, True, level or "HIGH"

    if "medium" in level:
        return 0.65, False, level or "MEDIUM"

    if any(token in level for token in ("low", "weak", "small")):
        return 0.25, False, level or "LOW"

    score = _reaction_numeric_score(item)

    if score >= config.high_reaction_score:
        return 1.0, True, f"score={round(score, 6)}"

    if score >= config.medium_reaction_score:
        return 0.65, False, f"score={round(score, 6)}"

    if score > 0:
        return 0.25, False, f"score={round(score, 6)}"

    return 0.0, False, "NONE"


def _reaction_summary(
    reactions: list[Mapping[str, Any]],
    start: float,
    end: float,
    config: HighlightRankingConfig,
) -> dict[str, Any]:
    max_strength = 0.0
    max_label = "NONE"
    high_reaction = False
    hit_count = 0

    for reaction in reactions:
        se = _start_end(reaction)
        if se is None:
            continue

        if _overlap(start, end, se[0], se[1]) <= 0:
            continue

        hit_count += 1
        strength, is_high, label = _reaction_strength_for_item(reaction, config)

        if strength > max_strength:
            max_strength = strength
            max_label = label

        high_reaction = high_reaction or is_high

    return {
        "reaction_hit_count": hit_count,
        "reaction_strength": round(max_strength, 6),
        "reaction_max": max_label,
        "mandatory_high_reaction": high_reaction,
    }


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "ja", "y", "payoff", "payoff_tail"}


def _has_payoff_tail_marker(item: Mapping[str, Any]) -> bool:
    direct_keys = (
        "payoff_tail",
        "is_payoff_tail",
        "mandatory_payoff_tail",
        "round_payoff_tail",
        "payoff_tail_applied",
    )

    for key in direct_keys:
        if key in item and _boolish(item.get(key)):
            return True

    for key in ("source", "segment_role", "role", "state", "kind", "type", "keep_decision", "reason"):
        value = item.get(key)
        if value is not None and "payoff" in str(value).lower():
            return True

    metadata = item.get("metadata")
    if isinstance(metadata, Mapping):
        for key, value in metadata.items():
            low_key = str(key).lower()
            low_value = str(value).lower()
            if "payoff" in low_key and _boolish(value):
                return True
            if "payoff" in low_value:
                return True

    return False


def _payoff_tail_summary(
    payoff_tail_segments: list[Mapping[str, Any]],
    source_segment: Mapping[str, Any],
    start: float,
    end: float,
) -> dict[str, Any]:
    overlap_seconds = 0.0
    hits: list[dict[str, Any]] = []

    if _has_payoff_tail_marker(source_segment):
        overlap_seconds = max(overlap_seconds, _duration(start, end))
        hits.append({
            "start_seconds": start,
            "end_seconds": end,
            "overlap_seconds": _duration(start, end),
            "source": "source_segment_marker",
        })

    for item in payoff_tail_segments:
        se = _start_end(item)
        if se is None:
            continue

        ov = _overlap(start, end, se[0], se[1])
        if ov <= 0:
            continue

        if not _has_payoff_tail_marker(item):
            continue

        overlap_seconds += ov
        hits.append({
            "start_seconds": se[0],
            "end_seconds": se[1],
            "overlap_seconds": round(ov, 3),
            "source": str(item.get("source") or item.get("segment_role") or item.get("role") or "payoff_tail_marker"),
        })

    overlap_seconds = round(overlap_seconds, 3)

    return {
        "payoff_tail_overlap_seconds": overlap_seconds,
        "mandatory_payoff_tail": overlap_seconds > 0,
        "payoff_tail_hits": hits,
    }


def _row_for_segment(
    *,
    index: int,
    segment: Mapping[str, Any],
    raw_windows: list[Mapping[str, Any]],
    reactions: list[Mapping[str, Any]],
    speech_regions: list[Mapping[str, Any]],
    payoff_tail_segments: list[Mapping[str, Any]],
    global_audio_values: list[float],
    config: HighlightRankingConfig,
) -> dict[str, Any]:
    se = _start_end(segment)
    if se is None:
        raise ValueError(f"Invalid segment without start/end: {segment}")

    start, end = se
    duration = _duration(start, end)
    segment_values = _audio_values_for_segment(raw_windows, start, end)
    audio = _audio_prominence(segment_values, global_audio_values)

    speech_s = _speech_seconds(speech_regions, start, end)
    speech_share = round(speech_s / max(0.001, duration), 6)
    speech_engagement = round(speech_share * audio["audio_peak_prominence"], 6)

    reaction = _reaction_summary(reactions, start, end, config)
    payoff_tail = _payoff_tail_summary(payoff_tail_segments, segment, start, end)

    # Finale Mandatory-Entscheidung passiert nach allen Rows,
    # weil HIGH-Reaction erst gegen den adaptiven audio_prominence_floor gepr?ft wird.
    mandatory_keep = False
    mandatory_keep_reason = ""
    high_reaction_candidate = bool(reaction["mandatory_high_reaction"])

    importance = (
        config.reaction_weight * reaction["reaction_strength"]
        + config.audio_weight * audio["audio_peak_prominence"]
        + config.speech_weight * speech_engagement
    )
    importance = round(importance, 6)

    # Kleiner Density-Faktor: sehr lange "okay"-Strecken bekommen keinen Gratis-Vorteil.
    compactness = min(1.0, math.sqrt(180.0 / max(1.0, duration)))
    selection_score = round(importance * (0.70 + 0.30 * compactness), 6)

    return {
        "rank_input_index": index,
        "segment_id": str(segment.get("segment_id") or segment.get("id") or f"segment_{index:04d}"),
        "start_seconds": start,
        "end_seconds": end,
        "duration_seconds": duration,
        "reaction_max": reaction["reaction_max"],
        "reaction_strength": reaction["reaction_strength"],
        "reaction_hit_count": reaction["reaction_hit_count"],
        "mandatory_high_reaction": reaction["mandatory_high_reaction"],
        "mandatory_payoff_tail": payoff_tail["mandatory_payoff_tail"],
        "high_reaction_candidate": high_reaction_candidate,
        "high_reaction_corrobated": False,
        "high_reaction_prominence_floor": None,
        "mandatory_keep": mandatory_keep,
        "mandatory_keep_reason": mandatory_keep_reason,
        "payoff_tail_overlap_seconds": payoff_tail["payoff_tail_overlap_seconds"],
        "payoff_tail_hits": payoff_tail["payoff_tail_hits"],
        "audio_max": audio["audio_max"],
        "audio_baseline_p50": audio["audio_baseline_p50"],
        "audio_peak_prominence": audio["audio_peak_prominence"],
        "speech_seconds": speech_s,
        "speech_share": speech_share,
        "speech_engagement": speech_engagement,
        "importance_score": importance,
        "selection_score": selection_score,
        "kept": False,
        "keep_reason": "BUDGET_DROP_WEAKER",
        "rank": None,
        "source_segment": deepcopy(dict(segment)),
    }


def _session_seconds(segments: list[Mapping[str, Any]]) -> float:
    intervals = []

    for segment in segments:
        se = _start_end(segment)
        if se is not None:
            intervals.append(se)

    if not intervals:
        return 0.0

    start = min(s for s, _ in intervals)
    end = max(e for _, e in intervals)

    return round(end - start, 3)


def _duration_sum(rows: list[Mapping[str, Any]]) -> float:
    return round(sum(_safe_float(row.get("duration_seconds")) for row in rows), 3)


def _same_interval(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    a_se = _start_end(a)
    b_se = _start_end(b)

    if a_se is None or b_se is None:
        return False

    return round(a_se[0], 3) == round(b_se[0], 3) and round(a_se[1], 3) == round(b_se[1], 3)


def _target_interval_status(rows: list[Mapping[str, Any]], start: float, end: float) -> dict[str, Any]:
    target_duration = end - start
    best = None
    best_overlap = 0.0

    for row in rows:
        overlap_seconds = _overlap(start, end, row["start_seconds"], row["end_seconds"])
        if overlap_seconds > best_overlap:
            best = row
            best_overlap = overlap_seconds

    if best is None:
        return {
            "target": [start, end],
            "found": False,
            "kept": False,
            "status": "NEIN",
        }

    coverage = round(best_overlap / max(0.001, target_duration), 6)

    return {
        "target": [start, end],
        "found": coverage >= 0.80,
        "matched_segment": [best["start_seconds"], best["end_seconds"]],
        "coverage": coverage,
        "kept": bool(best["kept"]) and coverage >= 0.80,
        "importance_score": best["importance_score"],
        "selection_score": best["selection_score"],
        "rank": best["rank"],
        "reaction_max": best["reaction_max"],
        "audio_peak_prominence": best["audio_peak_prominence"],
        "speech_engagement": best["speech_engagement"],
        "keep_reason": best["keep_reason"],
        "status": "JA" if bool(best["kept"]) and coverage >= 0.80 else "NEIN",
    }


def rank_highlight_segments(
    *,
    content_segments: list[Mapping[str, Any]],
    raw_windows: list[Mapping[str, Any]],
    reactions: list[Mapping[str, Any]] | None = None,
    combined_speech_regions: list[Mapping[str, Any]] | None = None,
    payoff_tail_segments: list[Mapping[str, Any]] | None = None,
    target_seconds: float | None = None,
    config: HighlightRankingConfig | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config = config or HighlightRankingConfig()
    reactions = reactions or []
    combined_speech_regions = combined_speech_regions or []
    payoff_tail_segments = payoff_tail_segments or []

    normalized_segments = normalize_intervals(content_segments, source="content_segment")
    normalized_raw = normalize_intervals(raw_windows, source="raw_action_window")
    normalized_reactions = normalize_intervals(reactions, source="reaction")
    normalized_speech = normalize_intervals(combined_speech_regions, source="combined_speech")
    normalized_payoff_tails = normalize_intervals(payoff_tail_segments, source="payoff_tail")

    session_seconds = _session_seconds(normalized_segments)
    effective_target = round(
        target_seconds if target_seconds is not None else default_highlight_target_seconds(session_seconds, config),
        3,
    )
    max_allowed_seconds = round(effective_target * (1.0 + config.budget_tolerance), 3)

    global_audio_values = _all_audio_values(normalized_raw)

    rows = [
        _row_for_segment(
            index=index,
            segment=segment,
            raw_windows=normalized_raw,
            reactions=normalized_reactions,
            speech_regions=normalized_speech,
            payoff_tail_segments=normalized_payoff_tails,
            global_audio_values=global_audio_values,
            config=config,
        )
        for index, segment in enumerate(normalized_segments, start=1)
    ]

    audio_prominence_values = [
        _safe_float(row.get("audio_peak_prominence"))
        for row in rows
    ]
    high_reaction_prominence_floor = round(
        _percentile(audio_prominence_values, config.high_reaction_prominence_percentile),
        6,
    )

    for row in rows:
        row["high_reaction_prominence_floor"] = high_reaction_prominence_floor
        row["high_reaction_corrobated"] = bool(
            row["mandatory_high_reaction"]
            and _safe_float(row.get("audio_peak_prominence")) >= high_reaction_prominence_floor
        )

        # Priorit?t ist bewusst: PAYOFF_TAIL > HIGH+Action-Korroboration > Budget-Score.
        if row["mandatory_payoff_tail"]:
            row["mandatory_keep"] = True
            row["mandatory_keep_reason"] = "MANDATORY_PAYOFF_TAIL"
        elif row["high_reaction_corrobated"]:
            row["mandatory_keep"] = True
            row["mandatory_keep_reason"] = "MANDATORY_HIGH_REACTION"
        else:
            row["mandatory_keep"] = False
            row["mandatory_keep_reason"] = ""

    ranked_rows = sorted(
        rows,
        key=lambda row: (
            row["mandatory_keep"],
            row["selection_score"],
            row["importance_score"],
            -row["duration_seconds"],
        ),
        reverse=True,
    )

    kept_rows: list[dict[str, Any]] = []

    for rank, row in enumerate(ranked_rows, start=1):
        row["rank"] = rank

    mandatory_rows = [row for row in ranked_rows if row["mandatory_keep"]]
    optional_rows = [row for row in ranked_rows if not row["mandatory_keep"]]

    current_duration = 0.0

    for row in mandatory_rows:
        row["kept"] = True
        row["keep_reason"] = row["mandatory_keep_reason"] or "MANDATORY_KEEP"
        kept_rows.append(row)
        current_duration = round(current_duration + row["duration_seconds"], 3)

    for row in optional_rows:
        candidate_duration = round(current_duration + row["duration_seconds"], 3)

        if candidate_duration <= max_allowed_seconds:
            row["kept"] = True
            row["keep_reason"] = "BUDGET_KEEP_RANKED"
            kept_rows.append(row)
            current_duration = candidate_duration
        else:
            row["kept"] = False
            row["keep_reason"] = "BUDGET_DROP_WEAKER"

    # Falls zu wenig Material übrig bleibt, fülle mit besten ganzen Strecken auf.
    if current_duration < config.min_target_seconds:
        for row in optional_rows:
            if row["kept"]:
                continue

            candidate_duration = round(current_duration + row["duration_seconds"], 3)
            if candidate_duration <= max_allowed_seconds or current_duration < config.min_target_seconds:
                row["kept"] = True
                row["keep_reason"] = "MIN_DURATION_BACKFILL_WHOLE_SEGMENT"
                kept_rows.append(row)
                current_duration = candidate_duration

            if current_duration >= config.min_target_seconds:
                break

    kept_rows_chronological = sorted(
        [row for row in rows if row["kept"]],
        key=lambda row: (row["start_seconds"], row["end_seconds"]),
    )

    output_segments: list[dict[str, Any]] = []
    for index, row in enumerate(kept_rows_chronological, start=1):
        segment = deepcopy(row["source_segment"])
        segment["segment_id"] = f"highlight_ranked_{index:04d}"
        segment["start_seconds"] = row["start_seconds"]
        segment["end_seconds"] = row["end_seconds"]
        segment["duration_seconds"] = row["duration_seconds"]
        segment.setdefault("metadata", {})
        if isinstance(segment["metadata"], dict):
            segment["metadata"]["source"] = HIGHLIGHT_RANKING_SOURCE
            segment["metadata"]["highlight_rank"] = row["rank"]
            segment["metadata"]["highlight_importance_score"] = row["importance_score"]
            segment["metadata"]["highlight_keep_reason"] = row["keep_reason"]
            segment["metadata"]["highlight_mandatory_payoff_tail"] = row["mandatory_payoff_tail"]
            segment["metadata"]["highlight_payoff_tail_overlap_seconds"] = row["payoff_tail_overlap_seconds"]
        output_segments.append(segment)

    final_duration = round(sum(row["duration_seconds"] for row in kept_rows_chronological), 3)

    input_intervals = {(row["start_seconds"], row["end_seconds"]) for row in rows}
    output_intervals = {(seg["start_seconds"], seg["end_seconds"]) for seg in output_segments}
    no_mid_segment_cut = all(interval in input_intervals for interval in output_intervals)

    late_lobby_targets = [
        ("late_918_967", 918.596, 967.612),
        ("late_1114_1124", 1114.5, 1124.0),
        ("late_1158_1166", 1158.13, 1166.0),
        ("late_1198_1226", 1198.628, 1226.0),
        ("late_1622_1648", 1622.372, 1648.0),
        ("late_1764_1772", 1764.0, 1772.0),
    ]

    late_lobby_status = []
    for name, start, end in late_lobby_targets:
        status = _target_interval_status(rows, start, end)
        status["name"] = name
        late_lobby_status.append(status)

    audit = {
        "source": HIGHLIGHT_RANKING_SOURCE,
        "config": {
            "target_ratio": config.target_ratio,
            "min_target_seconds": config.min_target_seconds,
            "max_target_seconds": config.max_target_seconds,
            "budget_tolerance": config.budget_tolerance,
            "reaction_weight": config.reaction_weight,
            "audio_weight": config.audio_weight,
            "speech_weight": config.speech_weight,
            "high_reaction_score": config.high_reaction_score,
            "medium_reaction_score": config.medium_reaction_score,
            "high_reaction_prominence_percentile": config.high_reaction_prominence_percentile,
        },
        "session_seconds": session_seconds,
        "target_seconds": effective_target,
        "max_allowed_seconds": max_allowed_seconds,
        "input_segment_count": len(rows),
        "kept_segment_count": len([row for row in rows if row["kept"]]),
        "dropped_segment_count": len([row for row in rows if not row["kept"]]),
        "input_duration_seconds": _duration_sum(rows),
        "final_duration_seconds": final_duration,
        "high_reaction_prominence_floor": high_reaction_prominence_floor,
        "global_audio": {
            "count": len(global_audio_values),
            "p50": round(_percentile(global_audio_values, 0.50), 6),
            "p70": round(_percentile(global_audio_values, 0.70), 6),
            "p85": round(_percentile(global_audio_values, 0.85), 6),
            "p95": round(_percentile(global_audio_values, 0.95), 6),
        },
        "hard_checks": {
            "duration_within_budget_plus_10_percent": "JA" if final_duration <= max_allowed_seconds else "NEIN",
            "duration_at_least_480_seconds": "JA" if final_duration >= config.min_target_seconds else "NEIN",
            "round1_fight_142_246_kept": _target_interval_status(rows, 142.0, 246.0),
            "death_payoff_1786_1810_high_reaction_kept": _target_interval_status(rows, 1786.0, 1810.0),
            "death_payoff_1792_1810_payoff_tail_kept": _target_interval_status(rows, 1792.0, 1810.417),
            "late_lobby_status": late_lobby_status,
            "no_mid_segment_cut": "JA" if no_mid_segment_cut else "NEIN",
        },
        "ranked_rows": [
            {key: value for key, value in row.items() if key != "source_segment"}
            for row in sorted(rows, key=lambda r: (r["start_seconds"], r["end_seconds"]))
        ],
        "output_segments": output_segments,
    }

    return output_segments, audit
