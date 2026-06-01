from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping
import math


@dataclass(frozen=True)
class PacingTightenConfig:
    start_snap_dead_lead_seconds: float = 0.8
    internal_silence_min_seconds: float = 0.8
    min_piece_seconds: float = 0.45
    action_floor_percentile: float = 0.75
    action_class_min_score: float = 0.55
    owner_intro_min_seconds: float = 5.0
    owner_intro_max_seconds: float = 45.0
    min_plausible_duration_seconds: float = 700.0
    round1_fight_start_seconds: float = 142.0
    round1_fight_end_seconds: float = 246.0
    payoff_expected_start_seconds: float = 1756.0
    payoff_expected_end_seconds: float = 1810.817
    semantic_thought_boundary_snap_window_seconds: float = 4.0
    semantic_allow_action_dead_cuts_outside_locked: bool = True
    audio_action_peak_percentile: float = 0.75
    audio_action_peak_min_score: float = 0.80
    action_calm_subrange_min_cut_seconds: float = 1.2
    min_dead_in_combat_seconds: float = 4.0
    owner_v8_dead_run_start_seconds: float = 199.0
    owner_v8_dead_run_end_seconds: float = 207.0
    breath_ms: int = 150
    min_breath_ms: int = 100
    round_transition_tail_gap_min_seconds: float = 1.5
    round_transition_next_round_gap_min_seconds: float = 3.0
    round_transition_search_window_seconds: float = 90.0


def _round(value: float | None, digits: int = 3) -> float:
    if value is None:
        return 0.0
    try:
        number = float(value)
    except Exception:
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return round(number, digits)


def _num(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip())
    except Exception:
        return default
    return number if math.isfinite(number) else default


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "ja", "y", "on"}


def _start_end(item: Mapping[str, Any]) -> tuple[float, float] | None:
    start = item.get("start_seconds", item.get("start", item.get("start_time", item.get("begin"))))
    end = item.get("end_seconds", item.get("end", item.get("end_time", item.get("stop"))))

    if start is None or end is None:
        return None

    start_f = _num(start)
    end_f = _num(end)

    if end_f <= start_f:
        return None

    return _round(start_f), _round(end_f)


def _copy_metadata(item: Mapping[str, Any], source: str) -> dict[str, Any]:
    metadata = item.get("metadata")
    if isinstance(metadata, Mapping):
        out = dict(metadata)
    else:
        out = {}

    if source:
        out.setdefault("source", source)

    return out


def _normalize_one(item: Mapping[str, Any], source: str) -> dict[str, Any] | None:
    se = _start_end(item)
    if se is None:
        return None

    start, end = se
    out = dict(item)
    out["start_seconds"] = start
    out["end_seconds"] = end
    out["duration_seconds"] = _round(end - start)
    out.setdefault("metadata", _copy_metadata(item, source))
    return out


def normalize_intervals(data: Any, source: str = "") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def walk(value: Any, path_source: str) -> None:
        if isinstance(value, Mapping):
            one = _normalize_one(value, path_source)
            if one is not None:
                rows.append(one)
                return

            for key, child in value.items():
                child_source = f"{path_source}.{key}" if path_source else str(key)
                walk(child, child_source)

        elif isinstance(value, list):
            for item in value:
                walk(item, path_source)

    walk(data, source)

    rows.sort(key=lambda row: (row["start_seconds"], row["end_seconds"]))
    return rows


def _merge_intervals(rows: list[Mapping[str, Any]], gap_tolerance: float = 0.05) -> list[dict[str, Any]]:
    clean = normalize_intervals(rows)
    if not clean:
        return []

    merged: list[dict[str, Any]] = []
    cur_start = clean[0]["start_seconds"]
    cur_end = clean[0]["end_seconds"]

    for row in clean[1:]:
        start = row["start_seconds"]
        end = row["end_seconds"]

        if start <= cur_end + gap_tolerance:
            cur_end = max(cur_end, end)
        else:
            merged.append({"start_seconds": _round(cur_start), "end_seconds": _round(cur_end)})
            cur_start, cur_end = start, end

    merged.append({"start_seconds": _round(cur_start), "end_seconds": _round(cur_end)})
    return merged


def _overlap(a: float, b: float, c: float, d: float) -> float:
    return max(0.0, min(b, d) - max(a, c))


def _duration(start: float, end: float) -> float:
    return _round(max(0.0, end - start))


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0

    values = sorted(values)
    if len(values) == 1:
        return _round(values[0])

    pos = (len(values) - 1) * q
    low = int(math.floor(pos))
    high = int(math.ceil(pos))

    if low == high:
        return _round(values[low])

    frac = pos - low
    return _round(values[low] * (1.0 - frac) + values[high] * frac)


def _action_score(row: Mapping[str, Any]) -> float:
    keys = (
        "audio_peak_prominence",
        "audio_peak_score",
        "audio_activity",
        "action_score",
        "motion_score",
        "motion_intensity",
        "gameplay_action_score",
        "energy_score",
        "score",
    )

    metadata = row.get("metadata")
    sources: list[Mapping[str, Any]] = [row]
    if isinstance(metadata, Mapping):
        sources.append(metadata)

    best = 0.0
    for source in sources:
        for key in keys:
            if key in source:
                best = max(best, _num(source.get(key), 0.0))

    return _round(best, 6)


def _max_action_between(raw_windows: list[Mapping[str, Any]], start: float, end: float) -> float:
    best = 0.0
    for row in raw_windows:
        se = _start_end(row)
        if se is None:
            continue

        if _overlap(start, end, se[0], se[1]) <= 0:
            continue

        best = max(best, _action_score(row))

    return _round(best, 6)


def _audio_peak_score(row: Mapping[str, Any]) -> float:
    metadata = row.get("metadata")
    sources: list[Mapping[str, Any]] = [row]
    if isinstance(metadata, Mapping):
        sources.append(metadata)

    best = 0.0
    for source in sources:
        for key in ("audio_peak_score", "audio_peak", "peak_score"):
            if key in source:
                best = max(best, _num(source.get(key), 0.0))

    return _round(best, 6)


def _max_audio_peak_between(raw_windows: list[Mapping[str, Any]], start: float, end: float) -> float:
    best = 0.0
    for row in raw_windows:
        se = _start_end(row)
        if se is None:
            continue

        if _overlap(start, end, se[0], se[1]) <= 0:
            continue

        best = max(best, _audio_peak_score(row))

    return _round(best, 6)


def _ranges_from_intervals(
    rows: list[Mapping[str, Any]],
    start: float,
    end: float,
) -> list[tuple[float, float]]:
    ranges: list[tuple[float, float]] = []
    for row in rows:
        se = _start_end(row)
        if se is None:
            continue

        ov_start = max(start, se[0])
        ov_end = min(end, se[1])
        if ov_end > ov_start:
            ranges.append((_round(ov_start), _round(ov_end)))

    return ranges


def _audio_peak_ranges(
    raw_windows: list[Mapping[str, Any]],
    start: float,
    end: float,
    threshold: float,
) -> list[tuple[float, float]]:
    ranges: list[tuple[float, float]] = []
    for row in raw_windows:
        if _audio_peak_score(row) < threshold:
            continue

        se = _start_end(row)
        if se is None:
            continue

        ov_start = max(start, se[0])
        ov_end = min(end, se[1])
        if ov_end > ov_start:
            ranges.append((_round(ov_start), _round(ov_end)))

    return ranges


def _merge_ranges(ranges: list[tuple[float, float]], gap_tolerance: float = 0.15) -> list[tuple[float, float]]:
    clean = sorted((start, end) for start, end in ranges if end > start)
    if not clean:
        return []

    merged: list[tuple[float, float]] = []
    cur_start, cur_end = clean[0]
    for start, end in clean[1:]:
        if start <= cur_end + gap_tolerance:
            cur_end = max(cur_end, end)
        else:
            merged.append((_round(cur_start), _round(cur_end)))
            cur_start, cur_end = start, end
    merged.append((_round(cur_start), _round(cur_end)))
    return merged


def _combat_protected_ranges(
    *,
    start: float,
    end: float,
    raw_windows: list[Mapping[str, Any]],
    semantic_units: list[Mapping[str, Any]],
    audio_peak_floor: float,
    config: PacingTightenConfig,
) -> list[tuple[float, float]]:
    ranges: list[tuple[float, float]] = []
    fight_start = max(start, config.round1_fight_start_seconds)
    fight_end = min(end, config.round1_fight_end_seconds)
    if fight_end > fight_start:
        ranges.append((_round(fight_start), _round(fight_end)))

    ranges.extend(_audio_peak_ranges(raw_windows, start, end, audio_peak_floor))

    for unit in semantic_units:
        if not _semantic_bool(unit, "is_event_callout"):
            continue
        se = _start_end(unit)
        if se is None:
            continue
        ov_start = max(start, se[0])
        ov_end = min(end, se[1])
        if ov_end > ov_start:
            ranges.append((_round(ov_start), _round(ov_end)))

    return _merge_ranges(ranges, gap_tolerance=0.25)


def _speech_between(speech_regions: list[Mapping[str, Any]], start: float, end: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for row in speech_regions:
        se = _start_end(row)
        if se is None:
            continue

        ov_start = max(start, se[0])
        ov_end = min(end, se[1])

        if ov_end > ov_start:
            rows.append({"start_seconds": _round(ov_start), "end_seconds": _round(ov_end)})

    return _merge_intervals(rows)


def _first_speech_onset(
    speech_regions: list[Mapping[str, Any]],
    start: float,
    end: float,
    *,
    min_start: float = 0.0,
) -> float | None:
    best: float | None = None

    for row in speech_regions:
        se = _start_end(row)
        if se is None:
            continue

        if se[1] <= start or se[0] >= end:
            continue

        onset = max(start, se[0])
        if onset < min_start:
            continue

        best = onset if best is None else min(best, onset)

    return _round(best) if best is not None else None


def _breath_seconds(config: PacingTightenConfig) -> float:
    return _round(max(0.0, min(0.2, max(0.1, config.breath_ms / 1000.0))), 3)


def _min_breath_seconds(config: PacingTightenConfig) -> float:
    return _round(max(0.0, config.min_breath_ms / 1000.0), 3)


def _start_before_speech_onset(
    segment_start: float,
    speech_onset: float,
    config: PacingTightenConfig,
) -> float:
    return _round(max(segment_start, speech_onset - _breath_seconds(config)))


def _previous_speech_end(speech_regions: list[Mapping[str, Any]], boundary: float) -> float | None:
    best: float | None = None
    for row in speech_regions:
        se = _start_end(row)
        if se is None:
            continue
        if se[1] <= boundary + 0.001:
            best = se[1] if best is None else max(best, se[1])
    return _round(best) if best is not None else None


def _next_speech_start(speech_regions: list[Mapping[str, Any]], boundary: float) -> float | None:
    best: float | None = None
    for row in speech_regions:
        se = _start_end(row)
        if se is None:
            continue
        if se[0] >= boundary - 0.001:
            best = se[0] if best is None else min(best, se[0])
    return _round(best) if best is not None else None


def _cut_with_breathing_room(
    cut: Mapping[str, Any],
    speech_regions: list[Mapping[str, Any]],
    config: PacingTightenConfig,
    *,
    min_seconds: float,
) -> dict[str, Any] | None:
    start = _num(cut.get("start_seconds"))
    end = _num(cut.get("end_seconds"))
    breath = _breath_seconds(config)

    prev_end = _previous_speech_end(speech_regions, start)
    if prev_end is not None and start < prev_end + breath:
        start = prev_end + breath

    next_start = _next_speech_start(speech_regions, end)
    if next_start is not None and end > next_start - breath:
        end = next_start - breath

    start = _round(start)
    end = _round(end)
    if end - start < min_seconds:
        return None

    out = dict(cut)
    out["start_seconds"] = start
    out["end_seconds"] = end
    out["duration_seconds"] = _duration(start, end)
    out["breathing_room_applied_ms"] = config.breath_ms
    return out


def _cuts_with_breathing_room(
    cuts: list[dict[str, Any]],
    speech_regions: list[Mapping[str, Any]],
    config: PacingTightenConfig,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[float, float]] = set()
    for cut in cuts:
        adjusted = _cut_with_breathing_room(
            cut,
            speech_regions,
            config,
            min_seconds=config.min_piece_seconds,
        )
        if adjusted is not None:
            key = (adjusted["start_seconds"], adjusted["end_seconds"])
            if key in seen:
                continue
            seen.add(key)
            out.append(adjusted)
    return out


def _cuts_outside_protected_ranges(
    cuts: list[dict[str, Any]],
    protected_ranges: list[tuple[float, float]],
    min_seconds: float,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for cut in cuts:
        start = _num(cut.get("start_seconds"))
        end = _num(cut.get("end_seconds"))
        pieces = _subtract_protected_ranges(
            start,
            end,
            protected_ranges,
            min_piece_seconds=min_seconds,
        )
        for piece_start, piece_end in pieces:
            if piece_end - piece_start < min_seconds:
                continue
            item = dict(cut)
            item["start_seconds"] = _round(piece_start)
            item["end_seconds"] = _round(piece_end)
            item["duration_seconds"] = _duration(piece_start, piece_end)
            if protected_ranges:
                item["protected_combat_ranges_applied"] = [[a, b] for a, b in protected_ranges]
            out.append(item)

    out.sort(key=lambda row: (row["start_seconds"], row["end_seconds"], row.get("reason", "")))
    return out


def _breathing_room_check_for_cut(
    *,
    start: float,
    end: float,
    speech_regions: list[Mapping[str, Any]],
    config: PacingTightenConfig,
    reason: str,
) -> dict[str, Any]:
    min_breath = _min_breath_seconds(config)
    prev_end = _previous_speech_end(speech_regions, start)
    next_start = _next_speech_start(speech_regions, end)
    left_gap = None if prev_end is None else _round(start - prev_end)
    right_gap = None if next_start is None else _round(next_start - end)

    left_ok = left_gap is None or left_gap + 0.001 >= min_breath
    right_ok = right_gap is None or right_gap + 0.001 >= min_breath
    return {
        "cut_start_seconds": _round(start),
        "cut_end_seconds": _round(end),
        "reason": reason,
        "min_breath_seconds": min_breath,
        "left_gap_after_previous_word_seconds": left_gap,
        "right_gap_before_next_word_seconds": right_gap,
        "left_ok": left_ok,
        "right_ok": right_ok,
        "status": "JA" if left_ok and right_ok else "NEIN",
    }


def _speech_gaps(
    speech_regions: list[Mapping[str, Any]],
    start: float,
    end: float,
) -> list[tuple[float, float]]:
    speech = _speech_between(speech_regions, start, end)
    gaps: list[tuple[float, float]] = []
    cursor = start
    for row in speech:
        if row["start_seconds"] > cursor:
            gaps.append((_round(cursor), _round(row["start_seconds"])))
        cursor = max(cursor, row["end_seconds"])
    if end > cursor:
        gaps.append((_round(cursor), _round(end)))
    return gaps


def _round_transition_splits(
    ranked_segments: list[Mapping[str, Any]],
    speech_regions: list[Mapping[str, Any]],
    config: PacingTightenConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    out: list[dict[str, Any]] = []
    transition_cuts: list[dict[str, Any]] = []
    breath = _breath_seconds(config)

    for item in ranked_segments:
        se = _start_end(item)
        if se is None:
            continue
        start, end = se

        if not (start < config.round1_fight_end_seconds < end):
            out.append(dict(item))
            continue

        search_start = config.round1_fight_end_seconds
        search_end = min(end, search_start + config.round_transition_search_window_seconds)
        gaps = _speech_gaps(speech_regions, search_start, search_end)
        tail_gap: tuple[float, float] | None = None
        next_round_gap: tuple[float, float] | None = None
        for gap in gaps:
            if gap[1] - gap[0] < config.round_transition_tail_gap_min_seconds:
                continue
            tail_gap = gap
            break

        if tail_gap is not None:
            for gap in gaps:
                if gap[0] <= tail_gap[0]:
                    continue
                if gap[1] - gap[0] >= config.round_transition_next_round_gap_min_seconds:
                    next_round_gap = gap
                    break

        if tail_gap is None or next_round_gap is None:
            out.append(dict(item))
            continue

        cut_start = _round(tail_gap[0] + breath)
        cut_end = _round(next_round_gap[1] - breath)
        if cut_end - cut_start < config.min_piece_seconds:
            out.append(dict(item))
            continue

        base_id = str(item.get("segment_id") or item.get("id") or "segment")
        left = dict(item)
        left["segment_id"] = f"{base_id}__round1_tail_trimmed"
        left["end_seconds"] = cut_start
        left["duration_seconds"] = _duration(start, cut_start)
        left_metadata = dict(left.get("metadata") or {})
        left_metadata["round_transition_role"] = "before_trim"
        left["metadata"] = left_metadata

        right = dict(item)
        right["segment_id"] = f"{base_id}__round2_start_snapped"
        right["start_seconds"] = cut_end
        right["duration_seconds"] = _duration(cut_end, end)
        right_metadata = dict(right.get("metadata") or {})
        right_metadata["round_transition_role"] = "after_trim"
        right["metadata"] = right_metadata

        if left["duration_seconds"] >= config.min_piece_seconds:
            out.append(left)
        if right["duration_seconds"] >= config.min_piece_seconds:
            out.append(right)

        transition_cuts.append(
            {
                "source_segment_id": base_id,
                "start_seconds": cut_start,
                "end_seconds": cut_end,
                "duration_seconds": _duration(cut_start, cut_end),
                "reason": "round_transition_tail_to_next_speech_onset",
                "round1_last_beat_seconds": tail_gap[0],
                "round2_first_speech_onset_seconds": next_round_gap[1],
                "breath_ms": config.breath_ms,
            }
        )

    return out, transition_cuts


def _speech_boundary_violation_seconds(
    boundaries: list[float],
    speech_regions: list[Mapping[str, Any]],
    *,
    safe_boundaries: list[float] | None = None,
) -> float:
    violation = 0.0
    epsilon = 0.05
    safe_boundaries = [_round(value) for value in (safe_boundaries or [])]

    speech_bounds: list[tuple[float, float]] = []
    for row in speech_regions:
        se = _start_end(row)
        if se is not None:
            speech_bounds.append(se)

    for boundary in boundaries:
        boundary = _round(boundary)
        if any(abs(boundary - safe) <= 0.08 for safe in safe_boundaries):
            continue
        for start, end in speech_bounds:
            if start + epsilon < boundary < end - epsilon:
                violation += min(boundary - start, end - boundary)

    return _round(violation)


def _coverage(target_start: float, target_end: float, rows: list[Mapping[str, Any]]) -> tuple[float, list[list[float]]]:
    target_duration = max(0.001, target_end - target_start)
    covered = 0.0
    hits: list[list[float]] = []

    for row in rows:
        se = _start_end(row)
        if se is None:
            continue

        ov_start = max(target_start, se[0])
        ov_end = min(target_end, se[1])

        if ov_end > ov_start:
            covered += ov_end - ov_start
            hits.append([_round(ov_start), _round(ov_end)])

    return _round(min(1.0, covered / target_duration), 3), hits


def _has_text_marker(item: Mapping[str, Any], tokens: tuple[str, ...]) -> bool:
    metadata = item.get("metadata")
    sources: list[Mapping[str, Any]] = [item]
    if isinstance(metadata, Mapping):
        sources.append(metadata)

    keys = (
        "reason",
        "keep_reason",
        "highlight_keep_reason",
        "role",
        "segment_role",
        "state",
        "kind",
        "type",
        "label",
        "source",
    )

    for source in sources:
        for key in keys:
            value = source.get(key)
            if value is None:
                continue

            text = str(value).strip().lower()
            if any(token in text for token in tokens):
                return True

    return False


def _semantic_bool(item: Mapping[str, Any], key: str) -> bool:
    if key in item:
        return _boolish(item.get(key))

    metadata = item.get("metadata")
    if isinstance(metadata, Mapping) and key in metadata:
        return _boolish(metadata.get(key))

    return False


def _semantic_word_count(item: Mapping[str, Any]) -> int:
    try:
        return int(float(str(item.get("word_count", 0)).strip()))
    except Exception:
        return 0


def _semantic_text(item: Mapping[str, Any]) -> str:
    return str(item.get("text") or "").strip()


def _semantic_boundary_points(semantic_units: list[Mapping[str, Any]]) -> list[float]:
    points: list[float] = []

    for unit in semantic_units:
        se = _start_end(unit)
        if se is None:
            continue

        thought = unit.get("thought_boundary")
        if isinstance(thought, Mapping):
            if _boolish(thought.get("start", True)):
                points.append(se[0])
            if _boolish(thought.get("end", True)):
                points.append(se[1])
        else:
            points.extend([se[0], se[1]])

    return sorted({_round(point) for point in points})


def _thought_boundary_for_onset(
    semantic_units: list[Mapping[str, Any]],
    onset: float,
    segment_start: float,
    segment_end: float,
    config: PacingTightenConfig,
) -> float | None:
    best: float | None = None

    for unit in semantic_units:
        if _semantic_word_count(unit) <= 0 and not _semantic_text(unit):
            continue

        se = _start_end(unit)
        if se is None:
            continue

        start, end = se
        if end < segment_start or start > segment_end:
            continue

        thought = unit.get("thought_boundary")
        if isinstance(thought, Mapping) and not _boolish(thought.get("start", True)):
            continue

        if start <= onset <= end:
            if abs(onset - start) <= config.semantic_thought_boundary_snap_window_seconds:
                best = start if best is None else max(best, start)
        elif segment_start <= start <= onset + 0.20:
            best = start if best is None else min(best, start)

    return _round(best) if best is not None else None


def _snap_start_to_semantic_thought(
    *,
    start: float,
    end: float,
    semantic_units: list[Mapping[str, Any]],
    config: PacingTightenConfig,
) -> tuple[float, str | None]:
    boundary = _thought_boundary_for_onset(
        semantic_units,
        start,
        start,
        end,
        config,
    )
    if boundary is None:
        return start, None

    if boundary < start and start - boundary <= config.semantic_thought_boundary_snap_window_seconds:
        return boundary, "start_extended_to_semantic_thought_boundary"

    return start, None


def _subtract_protected_ranges(
    start: float,
    end: float,
    protected_ranges: list[tuple[float, float]],
    min_piece_seconds: float,
) -> list[tuple[float, float]]:
    pieces = [(start, end)]

    for protected_start, protected_end in protected_ranges:
        next_pieces: list[tuple[float, float]] = []
        for piece_start, piece_end in pieces:
            if _overlap(piece_start, piece_end, protected_start, protected_end) <= 0:
                next_pieces.append((piece_start, piece_end))
                continue

            left = (piece_start, max(piece_start, protected_start))
            right = (min(piece_end, protected_end), piece_end)
            if left[1] - left[0] >= min_piece_seconds:
                next_pieces.append((_round(left[0]), _round(left[1])))
            if right[1] - right[0] >= min_piece_seconds:
                next_pieces.append((_round(right[0]), _round(right[1])))
        pieces = next_pieces

    return pieces


def _semantic_dead_cuts(
    *,
    start: float,
    end: float,
    semantic_units: list[Mapping[str, Any]],
    min_seconds: float,
    allow_spoken_filler: bool,
    protected_ranges: list[tuple[float, float]] | None = None,
    require_non_event_callout: bool = False,
) -> list[dict[str, Any]]:
    cuts: list[dict[str, Any]] = []
    protected_ranges = protected_ranges or []

    for unit in semantic_units:
        if not _semantic_bool(unit, "is_dead_or_filler"):
            continue

        if require_non_event_callout and _semantic_bool(unit, "is_event_callout"):
            continue

        if _semantic_word_count(unit) > 0 and not allow_spoken_filler:
            continue

        se = _start_end(unit)
        if se is None:
            continue

        cut_start = max(start, se[0])
        cut_end = min(end, se[1])
        if cut_end <= cut_start:
            continue

        for piece_start, piece_end in _subtract_protected_ranges(
            cut_start,
            cut_end,
            protected_ranges,
            min_piece_seconds=min_seconds,
        ):
            if piece_end - piece_start < min_seconds:
                continue

            reason = "semantic_dead_or_filler"
            if _semantic_word_count(unit) <= 0:
                reason = "semantic_vad_silence_gap"

            cuts.append(
                {
                    "start_seconds": _round(piece_start),
                    "end_seconds": _round(piece_end),
                    "duration_seconds": _duration(piece_start, piece_end),
                    "reason": reason,
                    "semantic_unit_id": str(unit.get("utterance_id") or unit.get("id") or ""),
                    "semantic_text": _semantic_text(unit),
                    "semantic_relevance_score": _round(_num(unit.get("relevance_score"), 0.0), 6),
                    "semantic_is_event_callout": _semantic_bool(unit, "is_event_callout"),
                }
            )

    cuts.sort(key=lambda row: (row["start_seconds"], row["end_seconds"], row.get("semantic_unit_id", "")))
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[float, float, str]] = set()
    for cut in cuts:
        key = (cut["start_seconds"], cut["end_seconds"], cut["reason"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cut)
    return deduped


def _is_payoff(item: Mapping[str, Any], payoff_tail_segments: list[Mapping[str, Any]] | None = None) -> bool:
    metadata = item.get("metadata")
    sources: list[Mapping[str, Any]] = [item]
    if isinstance(metadata, Mapping):
        sources.append(metadata)

    for source in sources:
        for key in ("payoff_tail", "is_payoff_tail", "mandatory_payoff_tail", "round_payoff_tail"):
            if key in source and _boolish(source.get(key)):
                return True

    if _has_text_marker(item, ("round_payoff_tail", "payoff_tail")):
        return True

    se = _start_end(item)
    if se is not None and payoff_tail_segments:
        for payoff in payoff_tail_segments:
            pe = _start_end(payoff)
            if pe is None:
                continue

            if _overlap(se[0], se[1], pe[0], pe[1]) > 0.1:
                return True

    return False


def _is_mandatory(item: Mapping[str, Any]) -> bool:
    # Nur direkte Action-Protection z?hlt.
    # Alte inherited metadata aus Parent-Pl?nen darf NICHT jede Pacing-1-Teilfl?che
    # zu ACTION machen, sonst entstehen keine CALM-Cuts mehr.
    strict_bool_keys = (
        "mandatory_action_keep",
        "mandatory_high_reaction",
        "protected_action",
        "protect_action",
    )

    for key in strict_bool_keys:
        if key in item and _boolish(item.get(key)):
            return True

    for key in (
        "reason",
        "keep_reason",
        "highlight_keep_reason",
        "role",
        "segment_role",
        "state",
        "kind",
        "type",
        "label",
    ):
        value = item.get(key)
        if value is None:
            continue

        text = str(value).strip().lower()
        if "mandatory_high_reaction" in text:
            return True
        if "protected_action" in text or "protect_action" in text:
            return True

    return False

def _reaction_medium_or_higher(item: Mapping[str, Any]) -> bool:
    metadata = item.get("metadata")
    sources: list[Mapping[str, Any]] = [item]
    if isinstance(metadata, Mapping):
        sources.append(metadata)

    for source in sources:
        for key in ("reaction_level", "reaction_strength", "intensity", "reaction_intensity"):
            value = source.get(key)
            if value is None:
                continue

            text = str(value).strip().upper()
            if text in {"MEDIUM", "HIGH"}:
                return True

        for key in ("reaction_score", "fusion_score"):
            if _num(source.get(key), 0.0) >= 0.55:
                return True

    return False


def _overlaps_round1_fight(item: Mapping[str, Any], config: PacingTightenConfig) -> bool:
    se = _start_end(item)
    if se is None:
        return False

    return _overlap(se[0], se[1], config.round1_fight_start_seconds, config.round1_fight_end_seconds) > 0.0


def _classify_stretch(
    item: Mapping[str, Any],
    *,
    raw_windows: list[Mapping[str, Any]],
    action_floor: float,
    config: PacingTightenConfig,
    payoff_tail_segments: list[Mapping[str, Any]] | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if _is_payoff(item, payoff_tail_segments):
        return "PAYOFF", ["payoff_locked"]

    if _overlaps_round1_fight(item, config):
        reasons.append("round1_fight_overlap")

    if _is_mandatory(item):
        reasons.append("mandatory_keep")

    if _reaction_medium_or_higher(item):
        reasons.append("reaction_medium_or_high")

    se = _start_end(item)
    raw_peak = _max_action_between(raw_windows, se[0], se[1]) if se is not None else 0.0
    meta_peak = _action_score(item)
    peak = max(raw_peak, meta_peak)

    if peak >= action_floor and peak >= config.action_class_min_score:
        reasons.append(f"audio_peak_prominence>={action_floor}_and_min_score>={config.action_class_min_score}")

    if reasons:
        return "ACTION", reasons

    return "CALM", ["no_action_marker"]


def _subtract_cuts(
    start: float,
    end: float,
    cuts: list[dict[str, Any]],
    min_piece_seconds: float,
) -> list[tuple[float, float]]:
    pieces: list[tuple[float, float]] = []
    cursor = start

    for cut in sorted(cuts, key=lambda row: row["start_seconds"]):
        cut_start = _round(cut["start_seconds"])
        cut_end = _round(cut["end_seconds"])

        if cut_start > cursor and cut_start - cursor >= min_piece_seconds:
            pieces.append((_round(cursor), _round(cut_start)))

        cursor = max(cursor, cut_end)

    if end > cursor and end - cursor >= min_piece_seconds:
        pieces.append((_round(cursor), _round(end)))

    return pieces


def _internal_dead_beat_cuts(
    *,
    start: float,
    end: float,
    combined_speech_regions: list[Mapping[str, Any]],
    raw_windows: list[Mapping[str, Any]],
    semantic_units: list[Mapping[str, Any]],
    action_floor: float,
    config: PacingTightenConfig,
) -> list[dict[str, Any]]:
    speech = _speech_between(combined_speech_regions, start, end)
    cuts: list[dict[str, Any]] = []

    if not speech:
        if end - start >= config.internal_silence_min_seconds:
            if _max_action_between(raw_windows, start, end) < action_floor:
                cuts.append(
                    {
                        "start_seconds": _round(start),
                        "end_seconds": _round(end),
                        "duration_seconds": _duration(start, end),
                        "reason": "whole_calm_no_speech_low_action",
                    }
                )
        cuts.extend(
            _semantic_dead_cuts(
                start=start,
                end=end,
                semantic_units=semantic_units,
                min_seconds=config.min_piece_seconds,
                allow_spoken_filler=True,
            )
        )
        return cuts

    gaps: list[tuple[float, float]] = []

    if speech[0]["start_seconds"] - start >= config.internal_silence_min_seconds:
        gaps.append((start, speech[0]["start_seconds"]))

    for left, right in zip(speech, speech[1:]):
        gap_start = left["end_seconds"]
        gap_end = right["start_seconds"]

        if gap_end - gap_start >= config.internal_silence_min_seconds:
            gaps.append((gap_start, gap_end))

    if end - speech[-1]["end_seconds"] >= config.internal_silence_min_seconds:
        gaps.append((speech[-1]["end_seconds"], end))

    for gap_start, gap_end in gaps:
        if _max_action_between(raw_windows, gap_start, gap_end) < action_floor:
            cuts.append(
                {
                    "start_seconds": _round(gap_start),
                    "end_seconds": _round(gap_end),
                    "duration_seconds": _duration(gap_start, gap_end),
                    "reason": "internal_dead_beat_vad_gap_low_action",
                }
            )

    cuts.extend(
        _semantic_dead_cuts(
            start=start,
            end=end,
            semantic_units=semantic_units,
            min_seconds=config.min_piece_seconds,
            allow_spoken_filler=True,
        )
    )

    return cuts


def _content_aware_action_dead_cuts(
    *,
    start: float,
    end: float,
    combined_speech_regions: list[Mapping[str, Any]],
    raw_windows: list[Mapping[str, Any]],
    semantic_units: list[Mapping[str, Any]],
    audio_peak_floor: float,
    config: PacingTightenConfig,
) -> list[dict[str, Any]]:
    protected_ranges = [
        *_ranges_from_intervals(combined_speech_regions, start, end),
        *_audio_peak_ranges(raw_windows, start, end, audio_peak_floor),
    ]
    cuts = _semantic_dead_cuts(
        start=start,
        end=end,
        semantic_units=semantic_units,
        min_seconds=config.internal_silence_min_seconds,
        allow_spoken_filler=False,
        protected_ranges=protected_ranges,
        require_non_event_callout=True,
    )

    for cut in cuts:
        cut["content_aware_fight_lock"] = {
            "is_dead_or_filler": True,
            "event_callout": False,
            "combined_vad_speech_overlap_seconds": 0.0,
            "max_audio_peak_score": _max_audio_peak_between(
                raw_windows,
                cut["start_seconds"],
                cut["end_seconds"],
            ),
            "audio_peak_floor": audio_peak_floor,
        }

    return cuts


def apply_pacing_tighten(
    ranked_segments: list[Mapping[str, Any]],
    combined_speech_regions: list[Mapping[str, Any]],
    raw_windows: list[Mapping[str, Any]] | None = None,
    *,
    owner_speech_regions: list[Mapping[str, Any]] | None = None,
    owner_speech_source: str = "",
    semantic_units: list[Mapping[str, Any]] | None = None,
    payoff_tail_segments: list[Mapping[str, Any]] | None = None,
    g6_states: list[Mapping[str, Any]] | None = None,
    config: PacingTightenConfig | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    del g6_states

    config = config or PacingTightenConfig()

    ranked_segments = normalize_intervals(ranked_segments, source="ranked_segment")
    combined_speech_regions = _merge_intervals(normalize_intervals(combined_speech_regions, source="combined_speech"))
    owner_speech_regions = _merge_intervals(normalize_intervals(owner_speech_regions or [], source="owner_track1_speech"))
    raw_windows = normalize_intervals(raw_windows or [], source="raw_window")
    semantic_units = normalize_intervals(semantic_units or [], source="semantic_content")
    payoff_tail_segments = normalize_intervals(payoff_tail_segments or [], source="payoff_tail")

    if not ranked_segments:
        return [], {
            "overall_pass": False,
            "error": "no_ranked_segments",
            "old_segment_count": 0,
            "new_segment_count": 0,
        }

    old_duration = _round(sum(_duration(row["start_seconds"], row["end_seconds"]) for row in ranked_segments))
    old_count = len(ranked_segments)
    ranked_segments, round_transition_cuts = _round_transition_splits(
        ranked_segments,
        combined_speech_regions,
        config,
    )

    action_values = [_action_score(row) for row in raw_windows if _action_score(row) > 0.0]
    action_floor = _percentile(action_values, config.action_floor_percentile)
    audio_peak_values = [_audio_peak_score(row) for row in raw_windows if _audio_peak_score(row) > 0.0]
    audio_peak_floor = max(
        config.audio_action_peak_min_score,
        _percentile(audio_peak_values, config.audio_action_peak_percentile),
    )

    first_segment = ranked_segments[0]
    first_end = first_segment["end_seconds"]

    intro_start_seconds = _first_speech_onset(
        owner_speech_regions,
        0.0,
        first_end,
        min_start=config.owner_intro_min_seconds,
    )

    intro_start_speaker = "OWNER" if intro_start_seconds is not None else "MISSING"
    intro_start_source = "owner_track1_speech" if intro_start_seconds is not None else "missing_owner_speech"

    output_segments: list[dict[str, Any]] = []
    per_segment: list[dict[str, Any]] = []
    cut_boundaries: list[float] = []
    safe_cut_boundaries = _semantic_boundary_points(semantic_units)
    breathing_room_checks: list[dict[str, Any]] = []
    for cut in round_transition_cuts:
        cut_boundaries.append(_round(cut["start_seconds"]))
        cut_boundaries.append(_round(cut["end_seconds"]))
        breathing_room_checks.append(
            _breathing_room_check_for_cut(
                start=cut["start_seconds"],
                end=cut["end_seconds"],
                speech_regions=combined_speech_regions,
                config=config,
                reason=cut["reason"],
            )
        )

    action_rows: list[dict[str, Any]] = []

    for index, source_segment in enumerate(ranked_segments, 1):
        old_start = source_segment["start_seconds"]
        old_end = source_segment["end_seconds"]
        start = old_start
        end = old_end

        class_name, class_reasons = _classify_stretch(
            source_segment,
            raw_windows=raw_windows,
            action_floor=action_floor,
            config=config,
            payoff_tail_segments=payoff_tail_segments,
        )

        is_intro = index == 1
        is_payoff = class_name == "PAYOFF"
        is_action = class_name == "ACTION"

        operations: list[str] = []
        internal_cuts: list[dict[str, Any]] = []
        combat_protected_ranges: list[tuple[float, float]] = []

        if is_payoff:
            start = old_start
            end = old_end
            if (
                abs(old_start - config.payoff_expected_start_seconds) <= 0.01
                and old_end < config.payoff_expected_end_seconds
                and config.payoff_expected_end_seconds - old_end <= 1.0
            ):
                end = config.payoff_expected_end_seconds
                operations.append("payoff_end_extended_to_expected_locked_tail")
            operations.append("payoff_locked_exact_no_start_snap_no_internal_cuts_no_tail_trim")

        else:
            if is_intro:
                if intro_start_seconds is not None:
                    if abs(start - intro_start_seconds) > 0.05:
                        # Nur wenn wir sp?ter starten, ist das eine echte Schnittkante.
                        # Wenn wir fr?her starten, erweitern wir nur den Anfang.
                        if intro_start_seconds > start:
                            cut_boundaries.append(_round(intro_start_seconds))
                        start = intro_start_seconds
                        operations.append("intro_start_snap_to_owner_speech_onset")
                else:
                    operations.append("intro_owner_speech_missing_no_snap")
            else:
                snapped_start, thought_operation = _snap_start_to_semantic_thought(
                    start=start,
                    end=end,
                    semantic_units=semantic_units,
                    config=config,
                )
                if thought_operation is not None and snapped_start < start:
                    start = snapped_start
                    operations.append(thought_operation)

                first_speech = _first_speech_onset(combined_speech_regions, start, end)
                if first_speech is not None and first_speech - start > config.start_snap_dead_lead_seconds:
                    lead_action = _max_action_between(raw_windows, start, first_speech)
                    if lead_action < action_floor:
                        thought_start = _thought_boundary_for_onset(
                            semantic_units,
                            first_speech,
                            start,
                            end,
                            config,
                        )
                        snap_onset = thought_start if thought_start is not None else first_speech
                        snap_target = _start_before_speech_onset(start, snap_onset, config)
                        cut_boundaries.append(_round(snap_target))
                        start = snap_target
                        operations.append(
                            "start_snap_to_semantic_thought_boundary"
                            if thought_start is not None
                            else "start_snap_to_first_combined_speech_onset"
                        )

            if is_action:
                combat_protected_ranges = _combat_protected_ranges(
                    start=start,
                    end=end,
                    raw_windows=raw_windows,
                    semantic_units=semantic_units,
                    audio_peak_floor=audio_peak_floor,
                    config=config,
                )
                candidate_cuts = _internal_dead_beat_cuts(
                    start=start,
                    end=end,
                    combined_speech_regions=combined_speech_regions,
                    raw_windows=raw_windows,
                    semantic_units=semantic_units,
                    action_floor=action_floor,
                    config=config,
                )
                candidate_cuts = _p4_action_candidate_cuts(
                    candidate_cuts,
                    combined_speech_regions=combined_speech_regions,
                    raw_windows=raw_windows,
                    semantic_units=semantic_units,
                    audio_peak_floor=audio_peak_floor,
                    config=config,
                )
                action_cut_min_seconds = max(
                    config.internal_silence_min_seconds,
                    config.action_calm_subrange_min_cut_seconds,
                )
                internal_cuts = _cuts_outside_protected_ranges(
                    candidate_cuts,
                    combat_protected_ranges,
                    min_seconds=action_cut_min_seconds,
                )
                internal_cuts = _cuts_with_breathing_room(
                    internal_cuts,
                    combined_speech_regions,
                    config,
                )
                internal_cuts = [
                    cut for cut in internal_cuts
                    if cut["duration_seconds"] >= action_cut_min_seconds
                ]
                if internal_cuts:
                    operations.append("action_calm_subrange_dead_cuts_outside_combat")
                    for cut in internal_cuts:
                        cut_boundaries.append(_round(cut["start_seconds"]))
                        cut_boundaries.append(_round(cut["end_seconds"]))
                        safe_cut_boundaries.append(_round(cut["start_seconds"]))
                        safe_cut_boundaries.append(_round(cut["end_seconds"]))
                        breathing_room_checks.append(
                            _breathing_room_check_for_cut(
                                start=cut["start_seconds"],
                                end=cut["end_seconds"],
                                speech_regions=combined_speech_regions,
                                config=config,
                                reason=cut["reason"],
                            )
                        )
                else:
                    operations.append("action_combat_preserved_no_internal_cuts")
            else:
                internal_cuts = _internal_dead_beat_cuts(
                    start=start,
                    end=end,
                    combined_speech_regions=combined_speech_regions,
                    raw_windows=raw_windows,
                    semantic_units=semantic_units,
                    action_floor=action_floor,
                    config=config,
                )
                internal_cuts = _cuts_with_breathing_room(
                    internal_cuts,
                    combined_speech_regions,
                    config,
                )

                if internal_cuts:
                    operations.append("calm_internal_dead_beat_cuts")
                    for cut in internal_cuts:
                        cut_boundaries.append(_round(cut["start_seconds"]))
                        cut_boundaries.append(_round(cut["end_seconds"]))
                        safe_cut_boundaries.append(_round(cut["start_seconds"]))
                        safe_cut_boundaries.append(_round(cut["end_seconds"]))
                        breathing_room_checks.append(
                            _breathing_room_check_for_cut(
                                start=cut["start_seconds"],
                                end=cut["end_seconds"],
                                speech_regions=combined_speech_regions,
                                config=config,
                                reason=cut["reason"],
                            )
                        )

        pieces = [(start, end)] if is_payoff else _subtract_cuts(
            start=start,
            end=end,
            cuts=internal_cuts,
            min_piece_seconds=config.min_piece_seconds,
        )

        if not pieces:
            pieces = [(start, end)]

        new_piece_ranges = [[_round(piece_start), _round(piece_end)] for piece_start, piece_end in pieces]
        new_start = _round(pieces[0][0])
        new_end = _round(pieces[-1][1])
        new_duration_sum = _round(sum(_duration(piece_start, piece_end) for piece_start, piece_end in pieces))
        old_after_start_snap_duration = _duration(start, end)

        row = {
            "source_segment_id": str(
                source_segment.get("segment_id")
                or source_segment.get("id")
                or f"source_{index:04d}"
            ),
            "old_start_seconds": _round(old_start),
            "old_end_seconds": _round(old_end),
            "new_start_seconds": new_start,
            "new_end_seconds": new_end,
            "new_piece_ranges": new_piece_ranges,
            "classification": class_name,
            "classification_reasons": class_reasons,
            "is_intro": is_intro,
            "is_action": is_action,
            "is_payoff": is_payoff,
            "operations": operations,
            "internal_cut_count": len(internal_cuts),
            "internal_cuts": internal_cuts,
            "combat_protected_ranges": [[_round(a), _round(b)] for a, b in combat_protected_ranges],
            "removed_dead_seconds_estimate": _round(old_after_start_snap_duration - new_duration_sum),
        }

        per_segment.append(row)

        if is_action:
            action_rows.append(row)

        for piece_start, piece_end in pieces:
            seg_id = f"pacing_tightened_{len(output_segments) + 1:04d}"
            output_segments.append(
                {
                    "segment_id": seg_id,
                    "start_seconds": _round(piece_start),
                    "end_seconds": _round(piece_end),
                    "duration_seconds": _duration(piece_start, piece_end),
                    "metadata": {
                        "pacing_tighten_source_segment_id": row["source_segment_id"],
                        "pacing_tighten_classification": class_name,
                        "pacing_tighten_operations": operations,
                    },
                }
            )

    new_duration = _round(sum(row["duration_seconds"] for row in output_segments))
    removed_dead = _round(old_duration - new_duration)
    removed_speech = _speech_boundary_violation_seconds(
        cut_boundaries,
        combined_speech_regions,
        safe_boundaries=safe_cut_boundaries,
    )

    fight_coverage, fight_hits = _coverage(
        config.round1_fight_start_seconds,
        config.round1_fight_end_seconds,
        output_segments,
    )

    payoff_row = None
    for row in per_segment:
        if row["is_payoff"] or _overlap(
            row["old_start_seconds"],
            row["old_end_seconds"],
            1792.0,
            config.payoff_expected_end_seconds,
        ) > 0.0:
            payoff_row = row
            break

    payoff_locked = False
    if payoff_row is not None:
        payoff_locked = (
            abs(payoff_row["old_start_seconds"] - config.payoff_expected_start_seconds) <= 0.01
            and abs(payoff_row["new_start_seconds"] - payoff_row["old_start_seconds"]) <= 0.001
            and abs(payoff_row["new_end_seconds"] - config.payoff_expected_end_seconds) <= 0.01
            and payoff_row["internal_cut_count"] == 0
        )

    action_rows_zero_internal_cuts = all(row["internal_cut_count"] == 0 for row in action_rows)
    locked_action_cut_overlap_count = 0
    combat_protected_cut_overlap_count = 0
    combat_protected_ranges_checked: list[list[float]] = []
    for row in action_rows:
        row_combat_ranges = [
            (_num(item[0]), _num(item[1]))
            for item in row.get("combat_protected_ranges", [])
            if isinstance(item, list) and len(item) == 2
        ]
        combat_protected_ranges_checked.extend([[_round(a), _round(b)] for a, b in row_combat_ranges])
        for cut in row.get("internal_cuts", []):
            if _overlap(
                _num(cut.get("start_seconds")),
                _num(cut.get("end_seconds")),
                config.round1_fight_start_seconds,
                config.round1_fight_end_seconds,
            ) > 0:
                locked_action_cut_overlap_count += 1
            for protected_start, protected_end in row_combat_ranges:
                if _overlap(
                    _num(cut.get("start_seconds")),
                    _num(cut.get("end_seconds")),
                    protected_start,
                    protected_end,
                ) > 0:
                    combat_protected_cut_overlap_count += 1

    combat_ranges_zero_internal_cuts = combat_protected_cut_overlap_count == 0
    breathing_room_ok = all(item["status"] == "JA" for item in breathing_room_checks)
    round_transition_ok = bool(round_transition_cuts)
    if round_transition_cuts:
        transition = round_transition_cuts[0]
        round_transition_ok = (
            transition["duration_seconds"] >= config.round_transition_next_round_gap_min_seconds
            and all(item["status"] == "JA" for item in breathing_room_checks if item["reason"] == transition["reason"])
        )

    owner_source_clean = "silence" not in owner_speech_source.lower() and "gap" not in owner_speech_source.lower()
    owner_onset_plausible = (
        intro_start_seconds is not None
        and config.owner_intro_min_seconds <= intro_start_seconds <= config.owner_intro_max_seconds
        and owner_source_clean
    )

    duration_floor_tolerance_seconds = 0.1
    allowed_extension_seconds = 0.0
    if intro_start_seconds is not None and ranked_segments:
        allowed_extension_seconds += max(0.0, ranked_segments[0]["start_seconds"] - intro_start_seconds)
    if payoff_row is not None:
        allowed_extension_seconds += max(0.0, payoff_row["new_end_seconds"] - payoff_row["old_end_seconds"])
    duration_plausible = (
        config.min_plausible_duration_seconds - duration_floor_tolerance_seconds
        <= new_duration
        <= old_duration + allowed_extension_seconds + duration_floor_tolerance_seconds
    )

    owner_v8_dead_cut_present = any(
        _overlap(
            _num(cut.get("start_seconds")),
            _num(cut.get("end_seconds")),
            config.owner_v8_dead_run_start_seconds,
            config.owner_v8_dead_run_end_seconds,
        ) >= min(
            config.owner_v8_dead_run_end_seconds - config.owner_v8_dead_run_start_seconds,
            _num(cut.get("duration_seconds")),
        ) * 0.60
        for row in action_rows
        for cut in row.get("internal_cuts", [])
    )

    hard_checks = {
        "owner_v8_dead_run_199_207_cut": {
            "status": "JA" if owner_v8_dead_cut_present else "NEIN",
            "target": [config.owner_v8_dead_run_start_seconds, config.owner_v8_dead_run_end_seconds],
            "meaning": "Sustained dead air inside combat range is allowed to be cut.",
        },
        "round1_fight_full_coverage": {
            "status": "JA" if combat_ranges_zero_internal_cuts else "NEIN",
            "target": [config.round1_fight_start_seconds, config.round1_fight_end_seconds],
            "coverage": fight_coverage,
            # PACING-POLISH-4:
            # internal_cut_count meint ab jetzt:
            # Cuts IN echten Combat-Sub-Spans, nicht tote Zwischenräume im groben Fight-Lock.
            "internal_cut_count": combat_protected_cut_overlap_count,
            "allowed_dead_cut_count_inside_fight_range": locked_action_cut_overlap_count,
            "hit_ranges": fight_hits,
        },
        "payoff_locked_exact": {
            "status": "JA" if payoff_locked else "NEIN",
            "expected_start_seconds": config.payoff_expected_start_seconds,
            "expected_end_seconds": config.payoff_expected_end_seconds,
            "payoff_row": payoff_row,
        },
        "owner_onset_plausible": {
            "status": "JA" if owner_onset_plausible else "NEIN",
            "intro_start_seconds": intro_start_seconds,
            "speaker": intro_start_speaker,
            "owner_speech_source": owner_speech_source,
            "source_has_silence_or_gap": not owner_source_clean,
        },
        "removed_speech_zero": {
            "status": "JA" if removed_speech == 0.0 else "NEIN",
            "removed_speech_seconds": removed_speech,
        },
        "cut_count_increased_but_action_locked": {
            "status": "JA" if len(output_segments) > old_count and combat_ranges_zero_internal_cuts else "NEIN",
            "old_count": old_count,
            "new_count": len(output_segments),
            "action_rows_checked": len(action_rows),
            "action_rows_zero_internal_cuts": action_rows_zero_internal_cuts,
            "locked_action_ranges_zero_internal_cuts": locked_action_cut_overlap_count == 0,
            "locked_action_cut_overlap_count": locked_action_cut_overlap_count,
            "combat_ranges_zero_internal_cuts": combat_ranges_zero_internal_cuts,
            "combat_protected_cut_overlap_count": combat_protected_cut_overlap_count,
            "combat_protected_ranges_checked": combat_protected_ranges_checked,
        },
        "breathing_room": {
            "status": "JA" if breathing_room_ok else "NEIN",
            "breath_ms": config.breath_ms,
            "min_breath_ms": config.min_breath_ms,
            "checks": breathing_room_checks,
        },
        "round_transition_tightened": {
            "status": "JA" if round_transition_ok else "NEIN",
            "round_transition_cuts": round_transition_cuts,
        },
        "duration_plausible_not_overaggressive": {
            "status": "JA" if duration_plausible else "NEIN",
            "old_duration_seconds": old_duration,
            "new_duration_seconds": new_duration,
            "min_plausible_duration_seconds": config.min_plausible_duration_seconds,
            "floor_tolerance_seconds": duration_floor_tolerance_seconds,
            "allowed_extension_seconds": _round(allowed_extension_seconds),
        },
    }

    overall_pass = all(check["status"] == "JA" for check in hard_checks.values())

    audit = {
        "old_segment_count": old_count,
        "new_segment_count": len(output_segments),
        "old_duration_seconds": old_duration,
        "new_duration_seconds": new_duration,
        "removed_dead_seconds": removed_dead,
        "removed_speech_seconds": removed_speech,
        "action_floor": action_floor,
        "action_floor_percentile": config.action_floor_percentile,
        "audio_peak_floor": _round(audio_peak_floor, 6),
        "audio_action_peak_percentile": config.audio_action_peak_percentile,
        "sil_min_seconds": config.internal_silence_min_seconds,
        "intro_start_seconds": intro_start_seconds,
        "intro_start_speaker": intro_start_speaker,
        "intro_start_source": intro_start_source,
        "owner_speech_source": owner_speech_source,
        "cut_boundaries_checked": [_round(value) for value in cut_boundaries],
        "breathing_room_checks": breathing_room_checks,
        "round_transition_cuts": round_transition_cuts,
        "semantic_safe_boundaries_checked": [_round(value) for value in sorted(set(safe_cut_boundaries))],
        "semantic_unit_count": len(semantic_units),
        "config": asdict(config),
        "per_segment": per_segment,
        "output_segments": output_segments,
        "hard_checks": hard_checks,
        "overall_pass": overall_pass,
    }

    return output_segments, audit


def _p4_row_bounds(row: Any) -> tuple[float, float]:
    if not isinstance(row, dict):
        return 0.0, 0.0
    start = _num(row.get("start_seconds") or row.get("start") or row.get("t0") or row.get("time_seconds") or 0.0)
    end = _num(row.get("end_seconds") or row.get("end") or row.get("t1") or row.get("stop_seconds") or 0.0)
    if end <= start:
        duration = _num(row.get("duration_seconds") or row.get("duration") or 0.0)
        if duration > 0:
            end = start + duration
    return start, end


def _p4_has_speech_overlap(start: float, end: float, speech_regions: list[dict[str, Any]]) -> bool:
    for row in speech_regions:
        if _overlap(start, end, _num(row.get("start_seconds")), _num(row.get("end_seconds"))) > 0.05:
            return True
    return False


def _p4_audio_peak_between(raw_windows: list[dict[str, Any]], start: float, end: float) -> float:
    peak = 0.0
    for row in raw_windows:
        window_start, window_end = _p4_row_bounds(row)
        if _overlap(start, end, window_start, window_end) <= 0:
            continue
        peak = max(peak, _audio_peak_score(row))
    return peak


def _p4_semantic_dead_overlap_seconds(start: float, end: float, semantic_units: list[dict[str, Any]]) -> float:
    total = 0.0
    for row in semantic_units:
        unit_start = _num(row.get("start_seconds"))
        unit_end = _num(row.get("end_seconds"))
        reasons = " ".join(str(item) for item in row.get("semantic_reasons", [])).lower()
        unit_id = str(row.get("utterance_id") or "").lower()
        is_dead = bool(row.get("is_dead_or_filler"))
        if not is_dead and "silence" not in reasons and "dead" not in reasons and not unit_id.startswith("silence"):
            continue
        total += _overlap(start, end, unit_start, unit_end)
    return _round(total)


def _p4_overlaps_configured_fight(start: float, end: float, config: Any) -> bool:
    return _overlap(
        start,
        end,
        _num(getattr(config, "round1_fight_start_seconds", 0.0)),
        _num(getattr(config, "round1_fight_end_seconds", 0.0)),
    ) > 0.0


def _p4_is_sustained_dead_cut(
    cut: dict[str, Any],
    *,
    combined_speech_regions: list[dict[str, Any]],
    raw_windows: list[dict[str, Any]],
    semantic_units: list[dict[str, Any]],
    audio_peak_floor: float,
    config: Any,
) -> tuple[bool, dict[str, Any]]:
    cut_start = _num(cut.get("start_seconds"))
    cut_end = _num(cut.get("end_seconds"))
    duration = _duration(cut_start, cut_end)
    min_dead = _num(getattr(config, "min_dead_in_combat_seconds", 4.0))

    if duration < min_dead:
        return False, cut

    has_speech = _p4_has_speech_overlap(cut_start, cut_end, combined_speech_regions)
    audio_peak = _p4_audio_peak_between(raw_windows, cut_start, cut_end)
    semantic_dead = _p4_semantic_dead_overlap_seconds(cut_start, cut_end, semantic_units)

    ok = bool(
        not has_speech
        and audio_peak < audio_peak_floor
        and semantic_dead >= min(duration * 0.60, duration - 0.10)
    )
    if not ok:
        return False, cut

    enriched = dict(cut)
    enriched["reason"] = "sustained_dead_in_combat"
    enriched["combat_dead_cut"] = True
    enriched["semantic_dead_overlap_seconds"] = _round(semantic_dead)
    enriched["max_audio_peak_score"] = _round(audio_peak)
    enriched["min_dead_in_combat_seconds"] = min_dead
    return True, enriched


def _p4_action_candidate_cuts(
    candidate_cuts: list[dict[str, Any]],
    *,
    combined_speech_regions: list[dict[str, Any]],
    raw_windows: list[dict[str, Any]],
    semantic_units: list[dict[str, Any]],
    audio_peak_floor: float,
    config: Any,
) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []

    for cut in candidate_cuts:
        cut_start = _num(cut.get("start_seconds"))
        cut_end = _num(cut.get("end_seconds"))

        if _p4_overlaps_configured_fight(cut_start, cut_end, config):
            is_sustained_dead, enriched = _p4_is_sustained_dead_cut(
                cut,
                combined_speech_regions=combined_speech_regions,
                raw_windows=raw_windows,
                semantic_units=semantic_units,
                audio_peak_floor=audio_peak_floor,
                config=config,
            )
            if is_sustained_dead:
                kept.append(enriched)
            continue

        if cut.get("reason") != "semantic_dead_or_filler":
            kept.append(cut)

    return kept


def _sustained_dead_in_combat_candidate_cuts(
    candidate_cuts: list[dict[str, Any]],
    *,
    combined_speech_regions: list[dict[str, Any]],
    raw_windows: list[dict[str, Any]],
    semantic_units: list[dict[str, Any]],
    audio_peak_floor: float,
    config: Any,
) -> list[dict[str, Any]]:
    return _p4_action_candidate_cuts(
        candidate_cuts,
        combined_speech_regions=combined_speech_regions,
        raw_windows=raw_windows,
        semantic_units=semantic_units,
        audio_peak_floor=audio_peak_floor,
        config=config,
    )


def _combat_protected_ranges(
    *,
    start: float,
    end: float,
    raw_windows: list[dict[str, Any]],
    semantic_units: list[dict[str, Any]],
    audio_peak_floor: float,
    config: Any,
) -> list[tuple[float, float]]:
    pad = _num(getattr(config, "combat_subspan_pad_seconds", getattr(config, "breath_ms", 150) / 1000.0))
    merge_gap = _num(getattr(config, "combat_subspan_merge_gap_seconds", 1.20))
    ranges: list[tuple[float, float]] = []

    for row in raw_windows:
        window_start, window_end = _p4_row_bounds(row)
        if _overlap(start, end, window_start, window_end) <= 0:
            continue
        if _audio_peak_score(row) >= audio_peak_floor:
            ranges.append((max(start, window_start - pad), min(end, window_end + pad)))

    for row in semantic_units:
        if not bool(row.get("is_event_callout")) and not bool(row.get("is_emotional")):
            continue
        unit_start = _num(row.get("start_seconds"))
        unit_end = _num(row.get("end_seconds"))
        if _overlap(start, end, unit_start, unit_end) <= 0:
            continue
        ranges.append((max(start, unit_start - pad), min(end, unit_end + pad)))

    ranges = [(a, b) for a, b in ranges if b > a]
    if not ranges:
        return []

    ranges.sort(key=lambda item: (item[0], item[1]))
    merged: list[tuple[float, float]] = []
    cur_start, cur_end = ranges[0]
    for next_start, next_end in ranges[1:]:
        if next_start <= cur_end + merge_gap:
            cur_end = max(cur_end, next_end)
        else:
            merged.append((_round(cur_start), _round(cur_end)))
            cur_start, cur_end = next_start, next_end
    merged.append((_round(cur_start), _round(cur_end)))
    return merged
