from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


REACTION_SIZE_SOURCE = "reaction_adaptive_highlight_gated_size_events_v3"
OWNER_LOUDNESS_SIZE_SOURCE = "owner_loudness_adaptive_size_events_v2"
REACTION_SIGNAL_SIZE_SOURCE = "reaction_signal_highlight_gated_size_events_v1"
SEMANTIC_QUESTION_SIZE_SOURCE = "semantic_question_medium_size_events_v1"
MEANING_GATED_ZOOM_SOURCE = "meaning_gated_facecam_zoom_events_v14"

SIZE_RANK = {
    "tiny": 0,
    "small": 1,
    "medium": 2,
    "large": 3,
}


@dataclass(frozen=True)
class ReactionSizeEventConfig:
    owner_track: str
    friend_track: str | None = None
    game_track: str | None = None
    prominence_percentile: float = 0.25
    prominence_floor: float | None = None
    min_hold_seconds: float = 1.5
    merge_gap_seconds: float = 0.35
    post_hold_seconds: float = 0.15
    include_medium: bool = True
    small_loudness_percentile: float = 0.55
    medium_loudness_percentile: float = 0.75
    large_loudness_percentile: float = 0.90
    min_owner_speech_overlap_seconds: float = 0.10
    reaction_signal_window_seconds: float = 0.5
    target_event_count_min: int = 35
    target_event_count_max: int = 50

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["track_roles"] = {
            "owner": self.owner_track,
            "friend": self.friend_track,
            "game": self.game_track,
        }
        return data


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip())
    except Exception:
        return default
    return number if math.isfinite(number) else default


def _start_end(item: Mapping[str, Any]) -> tuple[float, float] | None:
    start = item.get("start_seconds", item.get("start", item.get("start_time")))
    end = item.get("end_seconds", item.get("end", item.get("end_time")))
    if start is None or end is None:
        return None

    start_f = round(_safe_float(start), 3)
    end_f = round(_safe_float(end), 3)
    if end_f <= start_f:
        return None
    return start_f, end_f


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _overlap_seconds(rows: list[Mapping[str, Any]], start: float, end: float) -> float:
    total = 0.0
    for row in rows:
        se = _start_end(row)
        if se is None:
            continue
        total += _overlap(start, end, se[0], se[1])
    return round(total, 6)


def percentile(values: list[float], pct: float) -> float:
    clean = sorted(value for value in values if math.isfinite(value))
    if not clean:
        return 0.0
    if len(clean) == 1:
        return round(clean[0], 6)

    pct = max(0.0, min(1.0, float(pct)))
    position = (len(clean) - 1) * pct
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return round(clean[lower], 6)
    value = clean[lower] + (clean[upper] - clean[lower]) * (position - lower)
    return round(value, 6)


def _normalise_rows(rows: list[Mapping[str, Any]], *, source: str) -> list[dict[str, Any]]:
    normalised: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        se = _start_end(row)
        if se is None:
            continue
        item = dict(row)
        item["start_seconds"] = se[0]
        item["end_seconds"] = se[1]
        item.setdefault("interval_id", str(row.get("segment_id") or row.get("reaction_id") or f"{source}_{index:05d}"))
        item.setdefault("source", source)
        normalised.append(item)
    return sorted(normalised, key=lambda row: (row["start_seconds"], row["end_seconds"], str(row["interval_id"])))


def _size_for_intensity(intensity: str, config: ReactionSizeEventConfig) -> str | None:
    text = str(intensity or "").strip().upper()
    if text == "HIGH":
        return "large"
    if text == "MEDIUM" and config.include_medium:
        return "medium"
    return None


def _size_for_signal_intensity(intensity: str, config: ReactionSizeEventConfig) -> str | None:
    text = str(intensity or "").strip().upper()
    if text == "HIGH":
        return "large"
    if text == "MEDIUM" and config.include_medium:
        return "medium"
    return None


def _best_prominence_row(
    reaction: Mapping[str, Any],
    prominence_rows: list[Mapping[str, Any]],
) -> dict[str, Any] | None:
    reaction_se = _start_end(reaction)
    if reaction_se is None:
        return None

    best: dict[str, Any] | None = None
    best_overlap = 0.0
    for row in prominence_rows:
        row_se = _start_end(row)
        if row_se is None:
            continue
        overlap = _overlap(reaction_se[0], reaction_se[1], row_se[0], row_se[1])
        if overlap > best_overlap:
            best = dict(row)
            best_overlap = overlap

    return best


def _render_ranges_for_source_interval(
    segments: list[Mapping[str, Any]],
    source_start: float,
    source_end: float,
) -> list[dict[str, Any]]:
    ranges: list[dict[str, Any]] = []
    render_cursor = 0.0

    for index, segment in enumerate(segments, start=1):
        se = _start_end(segment)
        if se is None:
            continue

        seg_start, seg_end = se
        duration = seg_end - seg_start
        overlap_start = max(source_start, seg_start)
        overlap_end = min(source_end, seg_end)

        if overlap_end > overlap_start:
            render_start = render_cursor + (overlap_start - seg_start)
            render_end = render_cursor + (overlap_end - seg_start)
            ranges.append(
                {
                    "segment_index": index,
                    "segment_id": str(segment.get("segment_id") or segment.get("id") or f"segment_{index:04d}"),
                    "source_start_seconds": round(overlap_start, 3),
                    "source_end_seconds": round(overlap_end, 3),
                    "render_start_seconds": round(render_start, 3),
                    "render_end_seconds": round(render_end, 3),
                    "duration_seconds": round(render_end - render_start, 3),
                }
            )

        render_cursor += duration

    return ranges


def _with_render_mapping(event: dict[str, Any], segments: list[Mapping[str, Any]]) -> dict[str, Any]:
    ranges = _render_ranges_for_source_interval(
        segments,
        _safe_float(event.get("source_start_seconds")),
        _safe_float(event.get("source_end_seconds")),
    )
    mapped = dict(event)
    mapped["render_ranges"] = ranges
    if ranges:
        mapped["render_start_seconds"] = ranges[0]["render_start_seconds"]
        mapped["render_end_seconds"] = ranges[-1]["render_end_seconds"]
    else:
        mapped["render_start_seconds"] = None
        mapped["render_end_seconds"] = None
    return mapped


def _merge_events(events: list[dict[str, Any]], config: ReactionSizeEventConfig) -> list[dict[str, Any]]:
    if not events:
        return []

    merged: list[dict[str, Any]] = []
    merge_gap = max(0.0, float(config.merge_gap_seconds))

    for event in sorted(events, key=lambda row: (row["source_start_seconds"], row["source_end_seconds"])):
        if not merged:
            merged.append(dict(event))
            continue

        current = merged[-1]
        if event["source_start_seconds"] > current["source_end_seconds"] + merge_gap:
            merged.append(dict(event))
            continue

        current["source_end_seconds"] = round(max(current["source_end_seconds"], event["source_end_seconds"]), 3)
        current["duration_seconds"] = round(current["source_end_seconds"] - current["source_start_seconds"], 3)
        if SIZE_RANK.get(str(event["size"]), 0) > SIZE_RANK.get(str(current["size"]), 0):
            current["size"] = event["size"]
            current["intensity"] = event["intensity"]
        current["audio_peak_prominence"] = round(
            max(_safe_float(current.get("audio_peak_prominence")), _safe_float(event.get("audio_peak_prominence"))),
            6,
        )
        current.setdefault("contributing_reactions", [])
        current["contributing_reactions"].extend(event.get("contributing_reactions") or [])

    for index, event in enumerate(merged, start=1):
        event["event_id"] = f"reaction_size_{index:04d}"

    return merged


def _merge_same_size_events(events: list[dict[str, Any]], config: ReactionSizeEventConfig) -> list[dict[str, Any]]:
    if not events:
        return []

    merged: list[dict[str, Any]] = []
    merge_gap = max(0.0, float(config.merge_gap_seconds))

    for event in sorted(events, key=lambda row: (row["source_start_seconds"], row["source_end_seconds"], row["size"])):
        if not merged:
            merged.append(dict(event))
            continue

        current = merged[-1]
        if (
            event["size"] == current["size"]
            and event["source_start_seconds"] <= current["source_end_seconds"] + merge_gap
        ):
            current["source_end_seconds"] = round(max(current["source_end_seconds"], event["source_end_seconds"]), 3)
            current["duration_seconds"] = round(current["source_end_seconds"] - current["source_start_seconds"], 3)
            current["max_owner_rms_dbfs"] = round(
                max(_safe_float(current.get("max_owner_rms_dbfs"), -120.0), _safe_float(event.get("max_owner_rms_dbfs"), -120.0)),
                6,
            )
            current["avg_owner_rms_dbfs"] = round(
                max(_safe_float(current.get("avg_owner_rms_dbfs"), -120.0), _safe_float(event.get("avg_owner_rms_dbfs"), -120.0)),
                6,
            )
            current["owner_speech_overlap_seconds"] = round(
                _safe_float(current.get("owner_speech_overlap_seconds")) + _safe_float(event.get("owner_speech_overlap_seconds")),
                6,
            )
            current.setdefault("contributing_windows", [])
            current["contributing_windows"].extend(event.get("contributing_windows") or [])
            continue

        merged.append(dict(event))

    for index, event in enumerate(merged, start=1):
        event["event_id"] = f"owner_loudness_size_{index:04d}"

    return merged


def size_for_owner_loudness(
    rms_dbfs: float,
    thresholds: Mapping[str, float],
) -> str:
    value = _safe_float(rms_dbfs, -120.0)
    if value >= _safe_float(thresholds.get("large_dbfs"), 0.0):
        return "large"
    if value >= _safe_float(thresholds.get("medium_dbfs"), 0.0):
        return "medium"
    if value >= _safe_float(thresholds.get("small_dbfs"), 0.0):
        return "small"
    return "tiny"


def build_owner_loudness_size_event_payload(
    *,
    owner_loudness_windows: list[Mapping[str, Any]],
    render_segments: list[Mapping[str, Any]],
    owner_speech_regions: list[Mapping[str, Any]] | None,
    config: ReactionSizeEventConfig,
    baseline_event_count: int | None = None,
) -> dict[str, Any]:
    if not config.owner_track:
        raise ValueError("ReactionSizeEventConfig.owner_track must be explicit")

    windows = _normalise_rows(owner_loudness_windows, source="owner_loudness_window")
    normalised_segments = _normalise_rows(render_segments, source="render_segment")
    normalised_owner_speech = _normalise_rows(owner_speech_regions or [], source="owner_speech_region")

    min_speech_overlap = max(0.0, float(config.min_owner_speech_overlap_seconds))
    loudness_values: list[float] = []
    classified_windows: list[dict[str, Any]] = []

    for window in windows:
        start, end = _start_end(window) or (0.0, 0.0)
        owner_overlap = _overlap_seconds(normalised_owner_speech, start, end) if normalised_owner_speech else (end - start)
        rms = _safe_float(
            window.get("owner_rms_dbfs", window.get("rms_dbfs", window.get("loudness_dbfs"))),
            -120.0,
        )
        row = dict(window)
        row["owner_speech_overlap_seconds"] = round(owner_overlap, 6)
        row["owner_rms_dbfs"] = round(rms, 6)
        row["track_role"] = "owner"
        row["track"] = config.owner_track
        classified_windows.append(row)

        if owner_overlap >= min_speech_overlap and rms > -119.0:
            loudness_values.append(rms)

    thresholds = {
        "small_percentile": float(config.small_loudness_percentile),
        "medium_percentile": float(config.medium_loudness_percentile),
        "large_percentile": float(config.large_loudness_percentile),
        "small_dbfs": percentile(loudness_values, config.small_loudness_percentile),
        "medium_dbfs": percentile(loudness_values, config.medium_loudness_percentile),
        "large_dbfs": percentile(loudness_values, config.large_loudness_percentile),
    }

    window_size_counts = {"tiny": 0, "small": 0, "medium": 0, "large": 0}
    candidates: list[dict[str, Any]] = []
    min_hold = max(0.0, float(config.min_hold_seconds))
    post_hold = max(0.0, float(config.post_hold_seconds))

    for window in classified_windows:
        start, end = _start_end(window) or (0.0, 0.0)
        owner_overlap = _safe_float(window.get("owner_speech_overlap_seconds"))
        rms = _safe_float(window.get("owner_rms_dbfs"), -120.0)
        size = (
            size_for_owner_loudness(rms, thresholds)
            if owner_overlap >= min_speech_overlap and rms > -119.0
            else "tiny"
        )
        window["size"] = size
        window_size_counts[size] = window_size_counts.get(size, 0) + 1

        if size == "tiny":
            continue

        event_end = max(end + post_hold, start + min_hold)
        if not _render_ranges_for_source_interval(normalised_segments, start, event_end):
            continue

        candidates.append(
            {
                "source_start_seconds": round(start, 3),
                "source_end_seconds": round(event_end, 3),
                "duration_seconds": round(event_end - start, 3),
                "size": size,
                "intensity": size.upper(),
                "track_role": "owner",
                "track": config.owner_track,
                "source": OWNER_LOUDNESS_SIZE_SOURCE,
                "reason": "owner_loudness_adaptive_percentile",
                "owner_speech_overlap_seconds": round(owner_overlap, 6),
                "max_owner_rms_dbfs": round(rms, 6),
                "avg_owner_rms_dbfs": round(rms, 6),
                "thresholds": dict(thresholds),
                "contributing_windows": [
                    {
                        "source_start_seconds": round(start, 3),
                        "source_end_seconds": round(end, 3),
                        "owner_rms_dbfs": round(rms, 6),
                        "owner_speech_overlap_seconds": round(owner_overlap, 6),
                        "size": size,
                    }
                ],
            }
        )

    merged = _merge_same_size_events(candidates, config)
    events = [_with_render_mapping(event, normalised_segments) for event in merged]

    event_size_counts = {"small": 0, "medium": 0, "large": 0}
    for event in events:
        size = str(event.get("size") or "unknown")
        event_size_counts[size] = event_size_counts.get(size, 0) + 1

    event_durations = [_safe_float(event.get("duration_seconds")) for event in events]
    min_hold_pass = all(duration + 1e-6 >= min_hold for duration in event_durations)

    return {
        "source": OWNER_LOUDNESS_SIZE_SOURCE,
        "config": config.to_dict(),
        "track_roles": {
            "owner": config.owner_track,
            "friend": config.friend_track,
            "game": config.game_track,
        },
        "owner_loudness_thresholds": thresholds,
        "owner_loudness_values_count": len(loudness_values),
        "owner_loudness_window_count": len(classified_windows),
        "render_segment_count": len(normalised_segments),
        "baseline_event_count": baseline_event_count,
        "event_count": len(events),
        "size_counts": dict(sorted(window_size_counts.items())),
        "event_size_counts": dict(sorted(event_size_counts.items())),
        "size_switch_count": len(events) * 2,
        "min_hold_pass": min_hold_pass,
        "min_event_duration_seconds": round(min(event_durations), 3) if event_durations else None,
        "events": events,
        "sample_classified_windows": classified_windows[:20],
    }


def build_reaction_size_event_payload(
    *,
    reactions: list[Mapping[str, Any]],
    prominence_rows: list[Mapping[str, Any]],
    render_segments: list[Mapping[str, Any]],
    config: ReactionSizeEventConfig,
) -> dict[str, Any]:
    if not config.owner_track:
        raise ValueError("ReactionSizeEventConfig.owner_track must be explicit")

    normalised_reactions = _normalise_rows(reactions, source="reaction_adaptive")
    normalised_rows = _normalise_rows(prominence_rows, source="highlight_ranking_prominence")
    normalised_segments = _normalise_rows(render_segments, source="render_segment")

    prominence_values = [
        _safe_float(row.get("audio_peak_prominence"))
        for row in normalised_rows
        if "audio_peak_prominence" in row
    ]
    computed_prominence_floor = percentile(prominence_values, config.prominence_percentile)
    prominence_floor = (
        round(_safe_float(config.prominence_floor), 6)
        if config.prominence_floor is not None
        else computed_prominence_floor
    )
    prominence_floor_source = "configured_floor" if config.prominence_floor is not None else "adaptive_percentile"

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    min_hold = max(0.0, float(config.min_hold_seconds))
    post_hold = max(0.0, float(config.post_hold_seconds))

    for reaction in normalised_reactions:
        reaction_start, reaction_end = _start_end(reaction) or (0.0, 0.0)
        intensity = str(reaction.get("intensity") or reaction.get("level") or "").strip().upper()
        size = _size_for_intensity(intensity, config)
        base = {
            "reaction_id": reaction.get("reaction_id"),
            "intensity": intensity,
            "source_start_seconds": reaction_start,
            "source_end_seconds": reaction_end,
            "text": reaction.get("text"),
            "track_role": "owner",
            "track": config.owner_track,
        }

        if size is None:
            rejected.append({**base, "reason": "unsupported_intensity_for_size_event"})
            continue

        prominence_row = _best_prominence_row(reaction, normalised_rows)
        prominence = _safe_float(prominence_row.get("audio_peak_prominence") if prominence_row else None)
        base["audio_peak_prominence"] = round(prominence, 6)
        base["prominence_floor"] = prominence_floor
        if prominence_row is not None:
            base["prominence_row"] = {
                "segment_id": prominence_row.get("segment_id"),
                "start_seconds": prominence_row.get("start_seconds"),
                "end_seconds": prominence_row.get("end_seconds"),
                "audio_peak_prominence": prominence_row.get("audio_peak_prominence"),
            }

        if prominence_row is None:
            rejected.append({**base, "reason": "missing_prominence_row"})
            continue

        if prominence < prominence_floor:
            rejected.append(
                _with_render_mapping(
                    {**base, "size": size, "reason": "prominence_below_floor"},
                    normalised_segments,
                )
            )
            continue

        event_start = reaction_start
        event_end = max(reaction_end + post_hold, event_start + min_hold)
        event = {
            **base,
            "source_start_seconds": round(event_start, 3),
            "source_end_seconds": round(event_end, 3),
            "duration_seconds": round(event_end - event_start, 3),
            "size": size,
            "source": REACTION_SIZE_SOURCE,
            "reason": "highlight_gated_reaction_intensity_prominence",
            "contributing_reactions": [
                {
                    "reaction_id": reaction.get("reaction_id"),
                    "intensity": intensity,
                    "source_start_seconds": reaction_start,
                    "source_end_seconds": reaction_end,
                    "text": reaction.get("text"),
                }
            ],
        }

        if not _render_ranges_for_source_interval(normalised_segments, event_start, event_end):
            rejected.append({**event, "reason": "reaction_not_in_render_timeline"})
            continue

        candidates.append(event)

    merged = _merge_events(candidates, config)
    events = [_with_render_mapping(event, normalised_segments) for event in merged]

    for index, item in enumerate(rejected, start=1):
        item.setdefault("reject_id", f"reaction_size_reject_{index:04d}")

    size_counts: dict[str, int] = {}
    for event in events:
        size = str(event.get("size") or "unknown")
        size_counts[size] = size_counts.get(size, 0) + 1

    event_durations = [
        _safe_float(event.get("duration_seconds"))
        for event in events
    ]
    min_hold_pass = all(duration + 1e-6 >= min_hold for duration in event_durations)

    return {
        "source": REACTION_SIZE_SOURCE,
        "config": config.to_dict(),
        "prominence_floor": prominence_floor,
        "computed_prominence_floor": computed_prominence_floor,
        "prominence_floor_source": prominence_floor_source,
        "prominence_percentile": config.prominence_percentile,
        "prominence_values_count": len(prominence_values),
        "reaction_count": len(normalised_reactions),
        "render_segment_count": len(normalised_segments),
        "event_count": len(events),
        "size_counts": dict(sorted(size_counts.items())),
        "size_switch_count": len(events) * 2,
        "min_hold_pass": min_hold_pass,
        "min_event_duration_seconds": round(min(event_durations), 3) if event_durations else None,
        "events": events,
        "rejected_count": len(rejected),
        "rejected": rejected,
    }


def build_reaction_signal_size_event_payload(
    *,
    reaction_signal_windows: list[Mapping[str, Any]],
    prominence_rows: list[Mapping[str, Any]],
    render_segments: list[Mapping[str, Any]],
    config: ReactionSizeEventConfig,
    question_windows: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if not config.owner_track:
        raise ValueError("ReactionSizeEventConfig.owner_track must be explicit")

    normalised_rows = _normalise_rows(prominence_rows, source="highlight_ranking_prominence")
    normalised_segments = _normalise_rows(render_segments, source="render_segment")

    prominence_values = [
        _safe_float(row.get("audio_peak_prominence"))
        for row in normalised_rows
        if "audio_peak_prominence" in row
    ]
    computed_prominence_floor = percentile(prominence_values, config.prominence_percentile)
    prominence_floor = (
        round(_safe_float(config.prominence_floor), 6)
        if config.prominence_floor is not None
        else computed_prominence_floor
    )
    prominence_floor_source = "configured_floor" if config.prominence_floor is not None else "adaptive_percentile"

    window_seconds = max(0.001, float(config.reaction_signal_window_seconds))
    min_hold = max(0.0, float(config.min_hold_seconds))
    post_hold = max(0.0, float(config.post_hold_seconds))

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for index, window in enumerate(reaction_signal_windows, start=1):
        event_flag = window.get("reaction_event", True)
        if event_flag is False:
            continue

        start = _safe_float(
            window.get("time_seconds", window.get("start_seconds", window.get("start"))),
            -1.0,
        )
        if start < 0.0:
            continue
        end = _safe_float(window.get("end_seconds", window.get("end")), start + window_seconds)
        if end <= start:
            end = start + window_seconds

        raw_intensity = str(
            window.get(
                "reaction_intensity",
                window.get("detected_intensity", window.get("intensity", "")),
            )
        ).strip().upper()
        size = _size_for_signal_intensity(raw_intensity, config)

        base = {
            "reaction_id": str(window.get("reaction_id") or window.get("window_id") or f"reaction_signal_{index:05d}"),
            "intensity": raw_intensity,
            "source_start_seconds": round(start, 3),
            "source_end_seconds": round(end, 3),
            "text": window.get("text"),
            "track_role": "owner",
            "track": config.owner_track,
            "reaction_signal_confidence": round(_safe_float(window.get("confidence")), 6),
        }

        evidence = window.get("evidence")
        if isinstance(evidence, Mapping):
            base["reaction_signal_evidence"] = {
                "mic_audio_rise_db": evidence.get("mic_audio_rise_db"),
                "fusion_score": evidence.get("fusion_score"),
                "facecam_change": evidence.get("facecam_change"),
                "gameplay_rise_db": evidence.get("gameplay_rise_db"),
            }

        if size is None:
            rejected.append({**base, "reason": "unsupported_intensity_for_size_event"})
            continue

        prominence_row = _best_prominence_row(
            {"start_seconds": start, "end_seconds": end},
            normalised_rows,
        )
        prominence = _safe_float(prominence_row.get("audio_peak_prominence") if prominence_row else None)
        base["audio_peak_prominence"] = round(prominence, 6)
        base["prominence_floor"] = prominence_floor
        if prominence_row is not None:
            base["prominence_row"] = {
                "segment_id": prominence_row.get("segment_id"),
                "start_seconds": prominence_row.get("start_seconds"),
                "end_seconds": prominence_row.get("end_seconds"),
                "audio_peak_prominence": prominence_row.get("audio_peak_prominence"),
            }

        if prominence_row is None:
            rejected.append({**base, "size": size, "reason": "missing_prominence_row"})
            continue

        if prominence < prominence_floor:
            rejected.append(
                _with_render_mapping(
                    {**base, "size": size, "reason": "prominence_below_floor"},
                    normalised_segments,
                )
            )
            continue

        event_start = start
        event_end = max(end + post_hold, event_start + min_hold)
        event = {
            **base,
            "source_start_seconds": round(event_start, 3),
            "source_end_seconds": round(event_end, 3),
            "duration_seconds": round(event_end - event_start, 3),
            "size": size,
            "source": REACTION_SIGNAL_SIZE_SOURCE,
            "reason": "highlight_gated_reaction_signal_intensity_prominence",
            "contributing_reactions": [
                {
                    "reaction_id": base["reaction_id"],
                    "intensity": raw_intensity,
                    "source_start_seconds": round(start, 3),
                    "source_end_seconds": round(end, 3),
                    "confidence": base["reaction_signal_confidence"],
                }
            ],
        }

        if not _render_ranges_for_source_interval(normalised_segments, event_start, event_end):
            rejected.append({**event, "reason": "reaction_not_in_render_timeline"})
            continue

        candidates.append(_with_render_mapping(event, normalised_segments))

    for index, question in enumerate(question_windows or [], start=1):
        se = _start_end(question)
        if se is None:
            rejected.append(
                {
                    "reject_id": f"semantic_question_reject_{index:04d}",
                    "reason": "invalid_question_interval",
                    "source": SEMANTIC_QUESTION_SIZE_SOURCE,
                }
            )
            continue

        start, end = se
        event_start = start
        event_end = max(end + post_hold, event_start + min_hold)
        event = {
            "reaction_id": str(question.get("question_id") or question.get("unit_id") or f"semantic_question_{index:04d}"),
            "intensity": "QUESTION",
            "source_start_seconds": round(event_start, 3),
            "source_end_seconds": round(event_end, 3),
            "duration_seconds": round(event_end - event_start, 3),
            "text": question.get("text"),
            "track_role": "owner",
            "track": config.owner_track,
            "size": "medium",
            "source": SEMANTIC_QUESTION_SIZE_SOURCE,
            "reason": "semantic_question_medium_no_large",
            "is_question": True,
            "contributing_reactions": [],
        }

        if not _render_ranges_for_source_interval(normalised_segments, event_start, event_end):
            rejected.append({**event, "reason": "question_not_in_render_timeline"})
            continue

        candidates.append(_with_render_mapping(event, normalised_segments))

    large_intervals = [
        (
            _safe_float(event.get("source_start_seconds")),
            _safe_float(event.get("source_end_seconds")),
            str(event.get("event_id") or event.get("reaction_id") or ""),
        )
        for event in candidates
        if str(event.get("size") or "").lower() == "large"
    ]

    unsuppressed: list[dict[str, Any]] = []
    for event in candidates:
        if str(event.get("size") or "").lower() != "medium":
            unsuppressed.append(event)
            continue

        start = _safe_float(event.get("source_start_seconds"))
        end = _safe_float(event.get("source_end_seconds"))
        suppressor = next(
            (
                large_id
                for large_start, large_end, large_id in large_intervals
                if _overlap(start, end, large_start, large_end) > 0
            ),
            None,
        )
        if suppressor is None:
            unsuppressed.append(event)
            continue

        rejected.append(
            {
                **event,
                "reason": "suppressed_by_large_peak_direct_tiny_return",
                "suppressed_by_large_event": suppressor,
            }
        )

    events = sorted(
        unsuppressed,
        key=lambda row: (row["source_start_seconds"], row["source_end_seconds"], row["size"]),
    )
    for index, event in enumerate(events, start=1):
        event["event_id"] = f"meaning_zoom_{index:04d}"
        event["transition_model"] = "snap_direct"
        event["return_state"] = "tiny"
        event["allowed_states"] = ["tiny", "medium", "large"]
        event["raw_owner_loudness_trigger_enabled"] = False

    for index, item in enumerate(rejected, start=1):
        item.setdefault("reject_id", f"reaction_signal_size_reject_{index:04d}")

    size_counts: dict[str, int] = {}
    for event in events:
        size = str(event.get("size") or "unknown")
        size_counts[size] = size_counts.get(size, 0) + 1

    event_durations = [
        _safe_float(event.get("duration_seconds"))
        for event in events
    ]
    min_hold_pass = all(duration + 1e-6 >= min_hold for duration in event_durations)

    return {
        "source": MEANING_GATED_ZOOM_SOURCE,
        "config": config.to_dict(),
        "prominence_floor": prominence_floor,
        "computed_prominence_floor": computed_prominence_floor,
        "prominence_floor_source": prominence_floor_source,
        "prominence_percentile": config.prominence_percentile,
        "prominence_values_count": len(prominence_values),
        "reaction_signal_window_count": len(reaction_signal_windows),
        "question_window_count": len(question_windows or []),
        "render_segment_count": len(normalised_segments),
        "event_count": len(events),
        "size_counts": dict(sorted(size_counts.items())),
        "size_switch_count": len(events) * 2,
        "allowed_states": ["tiny", "medium", "large"],
        "default_state": "tiny",
        "transition_model": "snap_direct",
        "direct_return_to": "tiny",
        "raw_owner_loudness_trigger_enabled": False,
        "min_hold_pass": min_hold_pass,
        "min_event_duration_seconds": round(min(event_durations), 3) if event_durations else None,
        "events": events,
        "rejected_count": len(rejected),
        "rejected": rejected,
    }


def write_reaction_size_events_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

# v17 pro zoom event generation consolidated from scripts/ranked_cut_v17_pro_zoom_events.py

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.reaction_intensity_signal_builder import (
    ReactionIntensitySignalBuilder,
    parse_crop,
    probe_duration_seconds,
    probe_video_size,
    resolve_video,
    threshold_dict,
)
from models.reaction_signal import ReactionSignalEvidence, ReactionSignalThresholds


PRO_ZOOM_SEMANTIC_QUESTION_SIZE_SOURCE = "semantic_question_medium_size_events_v1"
PRO_ZOOM_REACTION_SIGNAL_SIZE_SOURCE = "reaction_signal_accent_budget_v17"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip().lstrip("\ufeff"))
    except Exception:
        return default
    return number if math.isfinite(number) else default


def overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def percentile(values: list[float], pct: float, *, default: float = 0.0) -> float:
    clean = sorted(value for value in values if math.isfinite(value))
    if not clean:
        return default
    if len(clean) == 1:
        return round(clean[0], 6)
    pct = max(0.0, min(1.0, pct))
    pos = (len(clean) - 1) * pct
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return round(clean[lo], 6)
    weight = pos - lo
    return round(clean[lo] + ((clean[hi] - clean[lo]) * weight), 6)


def norm(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.5
    return clamp01((value - lo) / (hi - lo))


def format_time(seconds: float) -> str:
    minutes = int(seconds // 60)
    rem = seconds - (minutes * 60)
    return f"{minutes:02d}:{rem:06.3f}"


def load_regions(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    rows = data.get("speech_regions") if isinstance(data, Mapping) else data
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        start = safe_float(row.get("start_seconds", row.get("start")))
        end = safe_float(row.get("end_seconds", row.get("end")))
        if end > start:
            out.append({**dict(row), "start_seconds": round(start, 3), "end_seconds": round(end, 3)})
    return sorted(out, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def load_words(path: Path) -> list[dict[str, Any]]:
    rows = read_json(path)
    if isinstance(rows, Mapping):
        rows = rows.get("words") or []
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        start = safe_float(row.get("start_seconds", row.get("start")))
        end = safe_float(row.get("end_seconds", row.get("end")))
        if end > start:
            out.append(
                {
                    **dict(row),
                    "word": str(row.get("word") or row.get("text") or "").strip(),
                    "start_seconds": round(start, 3),
                    "end_seconds": round(end, 3),
                }
            )
    return sorted(out, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def segment_for_source_time(segments: list[Mapping[str, Any]], source_seconds: float) -> tuple[int, Mapping[str, Any], float] | None:
    render_cursor = 0.0
    for index, segment in enumerate(segments, start=1):
        start = safe_float(segment.get("start_seconds"))
        end = safe_float(segment.get("end_seconds"))
        duration = max(0.0, end - start)
        if start <= source_seconds < end:
            return index, segment, render_cursor
        render_cursor += duration
    return None


def render_ranges_for_interval(
    segments: list[Mapping[str, Any]],
    start: float,
    end: float,
) -> list[dict[str, Any]]:
    ranges: list[dict[str, Any]] = []
    render_cursor = 0.0
    for index, segment in enumerate(segments, start=1):
        seg_start = safe_float(segment.get("start_seconds"))
        seg_end = safe_float(segment.get("end_seconds"))
        duration = max(0.0, seg_end - seg_start)
        ov_start = max(start, seg_start)
        ov_end = min(end, seg_end)
        if ov_end > ov_start:
            ranges.append(
                {
                    "segment_index": index,
                    "segment_id": segment.get("segment_id"),
                    "source_start_seconds": round(ov_start, 3),
                    "source_end_seconds": round(ov_end, 3),
                    "render_start_seconds": round(render_cursor + (ov_start - seg_start), 3),
                    "render_end_seconds": round(render_cursor + (ov_end - seg_start), 3),
                    "duration_seconds": round(ov_end - ov_start, 3),
                }
            )
        render_cursor += duration
    return ranges


def plan_duration(segments: list[Mapping[str, Any]]) -> float:
    return round(
        sum(max(0.0, safe_float(segment.get("end_seconds")) - safe_float(segment.get("start_seconds"))) for segment in segments),
        3,
    )


def _profile_crop(profile_path: Path, video_w: int, video_h: int) -> tuple[int, int, int, int]:
    profile = read_json(profile_path)
    raw = profile.get("facecam_crop") if isinstance(profile, Mapping) else None
    if not isinstance(raw, Mapping):
        return (0, 0, max(1, video_w // 2), video_h)
    return parse_crop(
        f"{int(raw.get('x', 0))},{int(raw.get('y', 0))},{int(raw.get('w', max(1, video_w // 2)))},{int(raw.get('h', video_h))}",
        video_w,
        video_h,
    )


def evidence_rows(builder: ReactionIntensitySignalBuilder, features: Mapping[str, Any]) -> list[ReactionSignalEvidence]:
    count = min(
        len(features["mic_rms_db"]),
        len(features["gameplay_rms_db"]),
        len(features["facecam_motion_raw"]),
    )
    return [builder.evidence_at(dict(features), index * builder.window_seconds, tolerance_seconds=0.0) for index in range(count)]


def thresholds_from_percentiles(
    rows: list[ReactionSignalEvidence],
    *,
    event_mic_percentile: float,
    event_fusion_percentile: float,
    high_mic_percentile: float,
) -> ReactionSignalThresholds:
    mic_values = [row.mic_audio_rise_db for row in rows]
    fusion_values = [row.fusion_score for row in rows]
    event_mic = percentile(mic_values, event_mic_percentile / 100.0)
    event_fusion = percentile(fusion_values, event_fusion_percentile / 100.0)
    high_mic = max(percentile(mic_values, high_mic_percentile / 100.0), event_mic + 1.0)
    return ReactionSignalThresholds(
        event_mic_rise_db=round(event_mic, 3),
        event_fusion_score=round(event_fusion, 4),
        medium_mic_rise_db=round(event_mic, 3),
        high_mic_rise_db=round(high_mic, 3),
        facecam_motion_hint=0.60,
        precision_negative_false_positive_count=0,
        high_medium_recall_ratio=0.0,
        any_reaction_recall_ratio=0.0,
    )


def reaction_windows_for_thresholds(
    rows: list[ReactionSignalEvidence],
    thresholds: ReactionSignalThresholds,
    *,
    window_seconds: float,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, evidence in enumerate(rows, start=1):
        is_event = (
            evidence.mic_audio_rise_db >= thresholds.event_mic_rise_db
            and evidence.fusion_score >= thresholds.event_fusion_score
        )
        if not is_event:
            continue
        intensity = "HIGH" if evidence.mic_audio_rise_db >= thresholds.high_mic_rise_db else "MEDIUM"
        out.append(
            {
                "reaction_id": f"v17_adaptive_window_{index:05d}",
                "start_seconds": evidence.time_seconds,
                "end_seconds": round(evidence.time_seconds + window_seconds, 3),
                "time_seconds": evidence.time_seconds,
                "reaction_event": True,
                "reaction_intensity": intensity,
                "confidence": 0.82 if intensity == "HIGH" else 0.66,
                "evidence": evidence.to_dict(),
                "threshold_source": "per_video_adaptive_candidate_thresholds_v17",
            }
        )
    return out


def best_prominence(rows: list[Mapping[str, Any]], start: float, end: float) -> Mapping[str, Any] | None:
    best = None
    best_overlap = 0.0
    for row in rows:
        r_start = safe_float(row.get("start_seconds"))
        r_end = safe_float(row.get("end_seconds"))
        ov = overlap(start, end, r_start, r_end)
        if ov > best_overlap:
            best = row
            best_overlap = ov
    return best


def word_text(words: list[Mapping[str, Any]]) -> str:
    return " ".join(str(word.get("word") or "").strip() for word in words).strip()


def word_span_payload(words: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "first_word": str(words[0].get("word") or ""),
        "last_word": str(words[-1].get("word") or ""),
        "word_count": len(words),
        "word_start_seconds": round(safe_float(words[0].get("start_seconds")), 3),
        "word_end_seconds": round(safe_float(words[-1].get("end_seconds")), 3),
        "text": word_text(words),
    }


def words_inside_segment(words: list[Mapping[str, Any]], segment_start: float, segment_end: float) -> list[Mapping[str, Any]]:
    return [
        word
        for word in words
        if safe_float(word.get("start_seconds")) >= segment_start - 0.001
        and safe_float(word.get("end_seconds")) <= segment_end + 0.001
    ]


def phrase_words_around_anchor(
    *,
    words: list[Mapping[str, Any]],
    anchor_seconds: float,
    segment_start: float,
    segment_end: float,
    max_core_seconds: float,
    max_gap_seconds: float = 0.36,
) -> list[Mapping[str, Any]]:
    local = words_inside_segment(words, segment_start, segment_end)
    if not local:
        return []

    def distance(row: Mapping[str, Any]) -> float:
        start = safe_float(row.get("start_seconds"))
        end = safe_float(row.get("end_seconds"))
        if start <= anchor_seconds <= end:
            return 0.0
        return min(abs(anchor_seconds - start), abs(anchor_seconds - end))

    anchor_index = min(range(len(local)), key=lambda idx: distance(local[idx]))
    if distance(local[anchor_index]) > 1.25:
        return []

    left = anchor_index
    right = anchor_index
    changed = True
    while changed:
        changed = False
        if left > 0:
            prev_word = local[left - 1]
            gap = safe_float(local[left].get("start_seconds")) - safe_float(prev_word.get("end_seconds"))
            core = safe_float(local[right].get("end_seconds")) - safe_float(prev_word.get("start_seconds"))
            if 0 <= gap <= max_gap_seconds and core <= max_core_seconds:
                left -= 1
                changed = True
        if right + 1 < len(local):
            next_word = local[right + 1]
            gap = safe_float(next_word.get("start_seconds")) - safe_float(local[right].get("end_seconds"))
            core = safe_float(next_word.get("end_seconds")) - safe_float(local[left].get("start_seconds"))
            if 0 <= gap <= max_gap_seconds and core <= max_core_seconds:
                right += 1
                changed = True
    phrase = [dict(word) for word in local[left:right + 1]]
    if safe_float(phrase[-1].get("end_seconds")) - safe_float(phrase[0].get("start_seconds")) > max_core_seconds:
        return []
    return phrase


def event_times_from_words(
    *,
    words: list[Mapping[str, Any]],
    segment_start: float,
    segment_end: float,
    lead_seconds: float,
    tail_seconds: float,
    max_zoom_seconds: float,
) -> tuple[float, float] | None:
    if not words:
        return None
    word_start = safe_float(words[0].get("start_seconds"))
    word_end = safe_float(words[-1].get("end_seconds"))
    if word_start < segment_start - 0.001 or word_end > segment_end + 0.001:
        return None
    start = max(segment_start, word_start - lead_seconds)
    end = min(segment_end, word_end + tail_seconds)
    if end - start > max_zoom_seconds:
        return None
    if end <= start:
        return None
    return round(start, 3), round(end, 3)


def question_phrase_words(
    *,
    question: Mapping[str, Any],
    words: list[Mapping[str, Any]],
    max_question_words: int,
    max_question_core_seconds: float,
) -> list[Mapping[str, Any]]:
    q_start = safe_float(question.get("start_seconds"))
    q_end = safe_float(question.get("end_seconds"))
    local = [
        word
        for word in words
        if overlap(safe_float(word.get("start_seconds")), safe_float(word.get("end_seconds")), q_start, q_end) > 0
    ]
    if not local:
        return []
    question_indices = [idx for idx, word in enumerate(local) if "?" in str(word.get("word") or "")]
    if not question_indices:
        return []
    q_idx = question_indices[0]
    left = q_idx
    while left > 0 and q_idx - left < max_question_words - 1:
        prev = str(local[left - 1].get("word") or "")
        gap = safe_float(local[left].get("start_seconds")) - safe_float(local[left - 1].get("end_seconds"))
        core = safe_float(local[q_idx].get("end_seconds")) - safe_float(local[left - 1].get("start_seconds"))
        if gap > 0.45 or core > max_question_core_seconds:
            break
        left -= 1
        if prev.endswith((".", "!", "?")):
            break
    phrase = [dict(word) for word in local[left:q_idx + 1]]
    if len(phrase) > max_question_words:
        phrase = phrase[-max_question_words:]
    if safe_float(phrase[-1].get("end_seconds")) - safe_float(phrase[0].get("start_seconds")) > max_question_core_seconds:
        return []
    return phrase


def build_raw_candidates(
    *,
    reaction_windows: list[Mapping[str, Any]],
    questions: list[Mapping[str, Any]],
    prominence_rows: list[Mapping[str, Any]],
    render_segments: list[Mapping[str, Any]],
    words: list[Mapping[str, Any]],
    prominence_floor: float,
    lead_seconds: float,
    tail_seconds: float,
    max_zoom_seconds: float,
    max_core_seconds: float,
    max_question_words: int,
    max_question_core_seconds: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for window in reaction_windows:
        trigger_start = safe_float(window.get("start_seconds", window.get("time_seconds")))
        trigger_end = safe_float(window.get("end_seconds"), trigger_start + 0.5)
        located = segment_for_source_time(render_segments, trigger_start)
        if located is None:
            rejected.append({**dict(window), "reason": "trigger_outside_plan"})
            continue
        segment_index, segment, _ = located
        segment_start = safe_float(segment.get("start_seconds"))
        segment_end = safe_float(segment.get("end_seconds"))
        phrase = phrase_words_around_anchor(
            words=words,
            anchor_seconds=trigger_start,
            segment_start=segment_start,
            segment_end=segment_end,
            max_core_seconds=max_core_seconds,
        )
        if not phrase:
            rejected.append({**dict(window), "reason": "no_owner_word_anchor"})
            continue

        prominence = best_prominence(prominence_rows, trigger_start, trigger_end)
        prominence_value = safe_float(prominence.get("audio_peak_prominence") if prominence else None)
        if prominence is None or prominence_value < prominence_floor:
            rejected.append(
                {
                    **dict(window),
                    "reason": "prominence_below_floor",
                    "audio_peak_prominence": round(prominence_value, 6),
                    "prominence_floor": prominence_floor,
                }
            )
            continue

        times = event_times_from_words(
            words=phrase,
            segment_start=segment_start,
            segment_end=segment_end,
            lead_seconds=lead_seconds,
            tail_seconds=tail_seconds,
            max_zoom_seconds=max_zoom_seconds,
        )
        if times is None:
            rejected.append({**dict(window), "reason": "invalid_word_timed_span"})
            continue
        start, end = times
        ranges = render_ranges_for_interval(render_segments, start, end)
        if len(ranges) != 1:
            rejected.append({**dict(window), "reason": "would_cross_cut"})
            continue
        evidence = window.get("evidence") if isinstance(window.get("evidence"), Mapping) else {}
        span = word_span_payload(phrase)
        text = span["text"]
        candidates.append(
            {
                "candidate_id": f"reaction_{len(candidates) + 1:05d}",
                "reaction_id": str(window.get("reaction_id") or window.get("window_id")),
                "candidate_type": "reaction",
                "source": PRO_ZOOM_REACTION_SIGNAL_SIZE_SOURCE,
                "source_start_seconds": start,
                "source_end_seconds": end,
                "duration_seconds": round(end - start, 3),
                "trigger_start_seconds": trigger_start,
                "trigger_end_seconds": trigger_end,
                "render_ranges": ranges,
                "render_start_seconds": ranges[0]["render_start_seconds"],
                "render_end_seconds": ranges[0]["render_end_seconds"],
                "segment_index": segment_index,
                "segment_id": segment.get("segment_id"),
                "word_span": span,
                "text": text,
                "audio_peak_prominence": round(prominence_value, 6),
                "mic_peak_over_baseline_db": safe_float(evidence.get("mic_peak_over_baseline_db")),
                "mic_audio_rise_db": safe_float(evidence.get("mic_audio_rise_db")),
                "fusion_score": safe_float(evidence.get("fusion_score")),
                "reaction_signal_evidence": dict(evidence),
                "mandatory_busfahrer": "busfahrer" in text.lower(),
                "reason": "reaction_score_candidate_word_timed",
            }
        )

    for question in questions:
        q_start = safe_float(question.get("start_seconds"))
        located = segment_for_source_time(render_segments, q_start)
        if located is None:
            rejected.append({**dict(question), "reason": "question_outside_plan"})
            continue
        segment_index, segment, _ = located
        segment_start = safe_float(segment.get("start_seconds"))
        segment_end = safe_float(segment.get("end_seconds"))
        phrase = question_phrase_words(
            question=question,
            words=words,
            max_question_words=max_question_words,
            max_question_core_seconds=max_question_core_seconds,
        )
        if not phrase:
            rejected.append({**dict(question), "reason": "question_not_short_clear"})
            continue
        text = word_text(phrase)
        if "?" not in text:
            rejected.append({**dict(question), "reason": "question_mark_not_in_phrase"})
            continue
        times = event_times_from_words(
            words=phrase,
            segment_start=segment_start,
            segment_end=segment_end,
            lead_seconds=lead_seconds,
            tail_seconds=tail_seconds,
            max_zoom_seconds=max_zoom_seconds,
        )
        if times is None:
            rejected.append({**dict(question), "reason": "invalid_question_word_span"})
            continue
        start, end = times
        ranges = render_ranges_for_interval(render_segments, start, end)
        if len(ranges) != 1:
            rejected.append({**dict(question), "reason": "question_would_cross_cut"})
            continue
        span = word_span_payload(phrase)
        shortness = 1.0 - min(1.0, max(0, span["word_count"] - 2) / max(1, max_question_words - 2))
        candidates.append(
            {
                "candidate_id": f"question_{len(candidates) + 1:05d}",
                "reaction_id": str(question.get("question_id") or question.get("unit_index")),
                "candidate_type": "question",
                "source": PRO_ZOOM_SEMANTIC_QUESTION_SIZE_SOURCE,
                "source_start_seconds": start,
                "source_end_seconds": end,
                "duration_seconds": round(end - start, 3),
                "trigger_start_seconds": q_start,
                "trigger_end_seconds": safe_float(question.get("end_seconds")),
                "render_ranges": ranges,
                "render_start_seconds": ranges[0]["render_start_seconds"],
                "render_end_seconds": ranges[0]["render_end_seconds"],
                "segment_index": segment_index,
                "segment_id": segment.get("segment_id"),
                "word_span": span,
                "text": text,
                "audio_peak_prominence": 0.0,
                "mic_peak_over_baseline_db": 0.0,
                "mic_audio_rise_db": 0.0,
                "fusion_score": 0.0,
                "question_shortness": round(shortness, 6),
                "question_relevance_score": safe_float(question.get("relevance_score")),
                "is_question": True,
                "mandatory_busfahrer": False,
                "reason": "short_clear_question_candidate_word_timed",
            }
        )

    return candidates, rejected


def score_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reaction_candidates = [row for row in candidates if row["candidate_type"] == "reaction"]
    mic_values = [safe_float(row.get("mic_peak_over_baseline_db")) for row in reaction_candidates]
    fusion_values = [safe_float(row.get("fusion_score")) for row in reaction_candidates]
    mic_lo = percentile(mic_values, 0.10, default=0.0)
    mic_hi = percentile(mic_values, 0.90, default=1.0)
    fusion_lo = percentile(fusion_values, 0.10, default=0.0)
    fusion_hi = percentile(fusion_values, 0.90, default=1.0)

    scored: list[dict[str, Any]] = []
    for row in candidates:
        item = dict(row)
        if row["candidate_type"] == "question":
            shortness = safe_float(row.get("question_shortness"))
            relevance = safe_float(row.get("question_relevance_score"))
            early_bonus = 0.08 if safe_float(row.get("source_start_seconds")) < 45.0 else 0.0
            score = 0.58 + (0.16 * shortness) + (0.08 * relevance) + early_bonus
            item["score_components"] = {
                "question_shortness": round(shortness, 6),
                "question_relevance": round(relevance, 6),
                "early_question_bonus": early_bonus,
            }
        else:
            prom = safe_float(row.get("audio_peak_prominence"))
            mic = safe_float(row.get("mic_peak_over_baseline_db"))
            fusion = safe_float(row.get("fusion_score"))
            mic_n = norm(mic, mic_lo, mic_hi)
            fusion_n = norm(fusion, fusion_lo, fusion_hi)
            bus_bonus = 0.35 if row.get("mandatory_busfahrer") else 0.0
            score = (0.50 * prom) + (0.28 * mic_n) + (0.22 * fusion_n) + bus_bonus
            item["score_components"] = {
                "prominence": round(prom, 6),
                "mic_peak_norm": round(mic_n, 6),
                "fusion_norm": round(fusion_n, 6),
                "busfahrer_bonus": bus_bonus,
            }
        item["score"] = round(score, 6)
        scored.append(item)
    return scored


def dedupe_candidates(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dedup: dict[tuple[Any, ...], dict[str, Any]] = {}
    rejected: list[dict[str, Any]] = []
    for row in candidates:
        key = (
            row.get("candidate_type"),
            row.get("segment_index"),
            round(safe_float(row.get("source_start_seconds")), 2),
            round(safe_float(row.get("source_end_seconds")), 2),
            row.get("text") if row.get("candidate_type") == "question" else "",
        )
        current = dedup.get(key)
        if current is None or safe_float(row.get("score")) > safe_float(current.get("score")):
            if current is not None:
                rejected.append({**current, "reason": "dedupe_lower_score"})
            dedup[key] = row
        else:
            rejected.append({**row, "reason": "dedupe_lower_score"})
    return list(dedup.values()), rejected


def select_budgeted_events(
    candidates: list[dict[str, Any]],
    *,
    render_duration_seconds: float,
    zooms_per_minute: float,
    min_event_count: int,
    max_event_count: int,
    min_gap_seconds: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    budget = int(round((render_duration_seconds / 60.0) * zooms_per_minute))
    budget = max(min_event_count, min(max_event_count, budget))
    ordered = sorted(
        candidates,
        key=lambda item: (
            -safe_float(item.get("score")),
            safe_float(item.get("render_start_seconds")),
            safe_float(item.get("duration_seconds")),
        ),
    )
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for item in ordered:
        if len(selected) >= budget:
            rejected.append({**item, "reason": "budget"})
            continue
        start = safe_float(item.get("render_start_seconds"))
        end = safe_float(item.get("render_end_seconds"))
        conflict = None
        for chosen in selected:
            chosen_start = safe_float(chosen.get("render_start_seconds"))
            chosen_end = safe_float(chosen.get("render_end_seconds"))
            if abs(start - chosen_start) < min_gap_seconds or overlap(start, end, chosen_start, chosen_end) > 0:
                conflict = chosen
                break
        if conflict is not None:
            rejected.append(
                {
                    **item,
                    "reason": "min_gap",
                    "conflict_candidate_id": conflict.get("candidate_id"),
                    "conflict_render_start_seconds": conflict.get("render_start_seconds"),
                }
            )
            continue
        selected.append(item)

    return selected, rejected, {
        "zoom_budget": budget,
        "zooms_per_minute": zooms_per_minute,
        "min_event_count": min_event_count,
        "max_event_count": max_event_count,
        "min_gap_seconds": min_gap_seconds,
    }


def assign_sizes(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(selected, key=lambda item: -safe_float(item.get("score")))
    rank_by_id = {id(item): index for index, item in enumerate(ranked, start=1)}
    reactions = [row for row in selected if row.get("candidate_type") == "reaction"]
    prom_values = [safe_float(row.get("audio_peak_prominence")) for row in reactions]
    mic_values = [safe_float(row.get("mic_peak_over_baseline_db")) for row in reactions]
    prom_floor = percentile(prom_values, 0.72, default=1.0)
    mic_floor = percentile(mic_values, 0.60, default=999.0)
    large_quota = max(3, min(7, int(round(len(selected) * 0.25))))
    out: list[dict[str, Any]] = []
    large_count = 0
    for item in ranked:
        row = dict(item)
        rank = rank_by_id[id(item)]
        row["rank"] = rank
        is_bus = bool(row.get("mandatory_busfahrer"))
        is_top_peak = (
            row.get("candidate_type") == "reaction"
            and rank <= large_quota
            and safe_float(row.get("audio_peak_prominence")) >= prom_floor
            and safe_float(row.get("mic_peak_over_baseline_db")) >= mic_floor
        )
        if row.get("candidate_type") == "question":
            row["size"] = "medium"
            row["size_reason"] = "question_always_medium"
        elif is_bus or (is_top_peak and large_count < large_quota):
            row["size"] = "large"
            row["size_reason"] = "mandatory_busfahrer_peak" if is_bus else "top_peak_prominence_and_mic"
            large_count += 1
        else:
            row["size"] = "medium"
            row["size_reason"] = "accent_reaction_medium"
        out.append(row)
    out.sort(key=lambda item: safe_float(item.get("render_start_seconds")))
    for index, row in enumerate(out, start=1):
        row["event_id"] = f"v17_zoom_{index:04d}"
        row["transition_model"] = "snap_direct"
        row["return_state"] = "tiny"
        row["allowed_states"] = ["tiny", "medium", "large"]
        row["max_duration_pass"] = safe_float(row.get("duration_seconds")) <= 3.501
        row["word_timing_pass"] = (
            abs(
                safe_float(row.get("source_start_seconds"))
                - safe_float((row.get("word_span") or {}).get("word_start_seconds"))
            )
            <= 0.001
            and safe_float(row.get("source_end_seconds")) >= safe_float((row.get("word_span") or {}).get("word_end_seconds")) + 0.149
            and safe_float(row.get("source_end_seconds")) <= safe_float((row.get("word_span") or {}).get("word_end_seconds")) + 0.201
        )
    return out


def size_time_distribution(events: list[Mapping[str, Any]], render_segments: list[Mapping[str, Any]]) -> dict[str, Any]:
    total = plan_duration(render_segments)
    endpoints = {0.0, total}
    for event in events:
        endpoints.add(max(0.0, min(total, safe_float(event.get("render_start_seconds")))))
        endpoints.add(max(0.0, min(total, safe_float(event.get("render_end_seconds")))))
    points = sorted(endpoints)
    seconds = {"tiny": 0.0, "medium": 0.0, "large": 0.0}
    for start, end in zip(points, points[1:]):
        if end <= start:
            continue
        mid = (start + end) / 2.0
        active = [
            event
            for event in events
            if safe_float(event.get("render_start_seconds")) <= mid < safe_float(event.get("render_end_seconds"))
        ]
        if any(event.get("size") == "large" for event in active):
            seconds["large"] += end - start
        elif any(event.get("size") == "medium" for event in active):
            seconds["medium"] += end - start
        else:
            seconds["tiny"] += end - start
    return {
        "total_seconds": round(total, 3),
        "seconds": {key: round(value, 3) for key, value in seconds.items()},
        "percent": {key: round((value / total) * 100.0, 3) if total else 0.0 for key, value in seconds.items()},
        "target_percent": "info_only_accent_model_no_hard_percent_band",
    }


def build_pro_zoom_payload(
    *,
    reaction_windows: list[Mapping[str, Any]],
    questions: list[Mapping[str, Any]],
    prominence_rows: list[Mapping[str, Any]],
    render_segments: list[Mapping[str, Any]],
    words: list[Mapping[str, Any]],
    prominence_floor: float,
    zooms_per_minute: float = 2.0,
    min_gap_seconds: float = 8.0,
    min_event_count: int = 15,
    max_event_count: int = 30,
    lead_seconds: float = 0.0,
    tail_seconds: float = 0.15,
    max_zoom_seconds: float = 3.5,
    max_core_seconds: float = 3.30,
    max_question_words: int = 9,
    max_question_core_seconds: float = 3.0,
) -> dict[str, Any]:
    raw_candidates, rejected = build_raw_candidates(
        reaction_windows=reaction_windows,
        questions=questions,
        prominence_rows=prominence_rows,
        render_segments=render_segments,
        words=words,
        prominence_floor=prominence_floor,
        lead_seconds=lead_seconds,
        tail_seconds=tail_seconds,
        max_zoom_seconds=max_zoom_seconds,
        max_core_seconds=max_core_seconds,
        max_question_words=max_question_words,
        max_question_core_seconds=max_question_core_seconds,
    )
    scored = score_candidates(raw_candidates)
    deduped, dedupe_rejected = dedupe_candidates(scored)
    selected, selection_rejected, budget_cfg = select_budgeted_events(
        deduped,
        render_duration_seconds=plan_duration(render_segments),
        zooms_per_minute=zooms_per_minute,
        min_event_count=min_event_count,
        max_event_count=max_event_count,
        min_gap_seconds=min_gap_seconds,
    )
    events = assign_sizes(selected)
    distribution = size_time_distribution(events, render_segments)
    size_counts = Counter(str(event.get("size")) for event in events)
    rejected_all = rejected + dedupe_rejected + selection_rejected
    rejected_counts = Counter(str(row.get("reason")) for row in rejected_all)
    effective_zpm = round((len(events) / max(0.001, plan_duration(render_segments))) * 60.0, 3)
    return {
        "source": "pro_zoom_accent_budget_word_timed_v17",
        "size_event_mode": "pro_zoom_accent_budget_word_timed_v17",
        "allowed_states": ["tiny", "medium", "large"],
        "default_state": "tiny",
        "transition_model": "snap_direct",
        "direct_return_to": "tiny",
        "raw_owner_loudness_trigger_enabled": False,
        "prominence_floor": prominence_floor,
        "config": {
            **budget_cfg,
            "lead_seconds": lead_seconds,
            "tail_seconds": tail_seconds,
            "max_zoom_seconds": max_zoom_seconds,
            "max_core_seconds": max_core_seconds,
            "max_question_words": max_question_words,
            "max_question_core_seconds": max_question_core_seconds,
            "min_hold_seconds": 0.0,
            "accent_model": True,
        },
        "candidate_count": len(raw_candidates),
        "deduped_candidate_count": len(deduped),
        "event_count": len(events),
        "effective_zooms_per_minute": effective_zpm,
        "size_counts": dict(sorted(size_counts.items())),
        "time_distribution": distribution,
        "events": events,
        "metrics_table": build_metrics_table(events),
        "rejected_count": len(rejected_all),
        "rejected_counts": dict(sorted(rejected_counts.items())),
        "rejected": rejected_all[:800],
    }


def build_metrics_table(events: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        span = event.get("word_span") if isinstance(event.get("word_span"), Mapping) else {}
        rows.append(
            {
                "rank": event.get("rank"),
                "event_id": event.get("event_id"),
                "render_start_seconds": event.get("render_start_seconds"),
                "render_end_seconds": event.get("render_end_seconds"),
                "render_time": f"{format_time(safe_float(event.get('render_start_seconds')))}-{format_time(safe_float(event.get('render_end_seconds')))}",
                "size": event.get("size"),
                "word_start_seconds": span.get("word_start_seconds"),
                "word_end_seconds": span.get("word_end_seconds"),
                "word_span": f"{span.get('first_word')} ... {span.get('last_word')}",
                "text": span.get("text"),
                "prominence": event.get("audio_peak_prominence"),
                "mic_peak_over_baseline_db": event.get("mic_peak_over_baseline_db"),
                "fusion_score": event.get("fusion_score"),
                "score": event.get("score"),
                "source": event.get("source"),
                "size_reason": event.get("size_reason"),
            }
        )
    return rows


def build_zoom_timing_table(events: list[Mapping[str, Any]], *, expected_tail_seconds: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        span = event.get("word_span") if isinstance(event.get("word_span"), Mapping) else {}
        word_start = safe_float(span.get("word_start_seconds"))
        word_end = safe_float(span.get("word_end_seconds"))
        zoom_start = safe_float(event.get("source_start_seconds"))
        zoom_end = safe_float(event.get("source_end_seconds"))
        start_delta = round(zoom_start - word_start, 3)
        end_delta = round(zoom_end - word_end, 3)
        text = str(span.get("text") or event.get("text") or "")
        rows.append(
            {
                "event_id": event.get("event_id"),
                "rank": event.get("rank"),
                "size": event.get("size"),
                "source": event.get("source"),
                "render_start_seconds": event.get("render_start_seconds"),
                "render_end_seconds": event.get("render_end_seconds"),
                "source_start_seconds": zoom_start,
                "source_end_seconds": zoom_end,
                "first_word": span.get("first_word"),
                "last_word": span.get("last_word"),
                "first_word_start_seconds": word_start,
                "last_word_end_seconds": word_end,
                "zoom_start_minus_first_word_start_seconds": start_delta,
                "zoom_end_minus_last_word_end_seconds": end_delta,
                "expected_tail_seconds": expected_tail_seconds,
                "timing_status": (
                    "PASS"
                    if abs(start_delta) <= 0.001 and abs(end_delta - expected_tail_seconds) <= 0.051
                    else "REVIEW"
                ),
                "possible_partial_utterance": bool(text and not text.rstrip().endswith((".", "!", "?", ","))),
                "text": text,
            }
        )
    return rows


def write_zoom_timing_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "event_id",
        "rank",
        "size",
        "source",
        "render_start_seconds",
        "render_end_seconds",
        "source_start_seconds",
        "source_end_seconds",
        "first_word",
        "last_word",
        "first_word_start_seconds",
        "last_word_end_seconds",
        "zoom_start_minus_first_word_start_seconds",
        "zoom_end_minus_last_word_end_seconds",
        "expected_tail_seconds",
        "timing_status",
        "possible_partial_utterance",
        "text",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def write_metrics_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "rank",
        "event_id",
        "render_time",
        "size",
        "word_start_seconds",
        "word_end_seconds",
        "word_span",
        "prominence",
        "mic_peak_over_baseline_db",
        "fusion_score",
        "score",
        "source",
        "size_reason",
        "text",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def write_text_report(path: Path, report: Mapping[str, Any]) -> None:
    payload = report["payload"]
    dist = payload["time_distribution"]
    lines = [
        "PROJECT ZENITH - ranked_cut_v17 PRO-ZOOM ACCENT BUDGET + TIMING",
        "",
        f"plan={report['plan']}",
        "threshold_basis=per_video_adaptive_candidate_thresholds_v17",
        f"selected_thresholds={report['selected_thresholds']}",
        f"event_count={payload['event_count']}",
        f"effective_zooms_per_minute={payload['effective_zooms_per_minute']}",
        f"size_counts={payload['size_counts']}",
        f"time_distribution_percent_info_only={dist['percent']}",
        f"rejected_counts={payload['rejected_counts']}",
        "",
        "TARGET CHECKS",
        f"busfahrer_large={report['busfahrer_large']}",
        f"question_medium={report['question_medium']}",
        f"no_zoom_crosses_cut={report['no_zoom_crosses_cut']}",
        f"min_gap_seconds_ok={report['min_gap_seconds_ok']}",
        f"word_timing_ok={report['word_timing_ok']}",
        f"timing_csv={report['timing_csv']}",
        "",
        "METRICS TABLE",
    ]
    for row in payload["metrics_table"]:
        lines.append(
            f"- rank={row['rank']} {row['render_time']} size={row['size']} "
            f"words={row['word_span']} prom={row['prominence']} "
            f"mic_peak_over={row['mic_peak_over_baseline_db']} fusion={row['fusion_score']} "
            f"score={row['score']}"
        )
    lines.extend(["", "ZOOM TIMING TABLE"])
    for row in report.get("zoom_timing_table") or []:
        lines.append(
            f"- {row['event_id']} start_delta={row['zoom_start_minus_first_word_start_seconds']} "
            f"end_delta={row['zoom_end_minus_last_word_end_seconds']} status={row['timing_status']} "
            f"partial_utterance={row['possible_partial_utterance']} text={row['text']}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def min_render_start_gap(events: list[Mapping[str, Any]]) -> float | None:
    starts = sorted(safe_float(event.get("render_start_seconds")) for event in events)
    if len(starts) < 2:
        return None
    return round(min(b - a for a, b in zip(starts, starts[1:])), 3)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default=r"D:\Zenith\inbox\gaming_main\Fortnite Full Video.mp4")
    parser.add_argument("--plan", default="reports/ranked_render/ranked_cut_v17_editorial_plan.json")
    parser.add_argument("--profile", default="profiles/gaming_main.json")
    parser.add_argument("--words", default="reports/speech_1_transcript_largev3/fortnite_words.json")
    parser.add_argument("--semantic-content-analysis", default="reports/semantic_content_layer/semantic_content_analysis.json")
    parser.add_argument("--reaction-prominence-rows", default="reports/highlight_ranking_reaction_wiring/highlight_ranking_reaction_wiring_rows.json")
    parser.add_argument("--mic-track", type=int, default=1)
    parser.add_argument("--gameplay-track", type=int, default=3)
    parser.add_argument("--prominence-floor", type=float, default=0.50)
    parser.add_argument("--zooms-per-minute", type=float, default=2.0)
    parser.add_argument("--min-gap-seconds", type=float, default=8.0)
    parser.add_argument("--feature-cache", default="reports/ranked_render/reaction_signal_v15/pro_zoom_feature_cache.json")
    parser.add_argument("--out-events", default="reports/ranked_render/ranked_cut_v17_reaction_size_events.json")
    parser.add_argument("--out-windows", default="reports/ranked_render/reaction_signal_v17/reaction_signal_windows.jsonl")
    parser.add_argument("--report-json", default="reports/ranked_render/reaction_signal_v17/pro_zoom_report.json")
    parser.add_argument("--report-txt", default="reports/ranked_render/reaction_signal_v17/pro_zoom_report.txt")
    parser.add_argument("--metrics-csv", default="reports/ranked_render/ranked_cut_v17_zoom_metrics.csv")
    parser.add_argument("--timing-csv", default="reports/ranked_render/ranked_cut_v17_zoom_timing.csv")
    args = parser.parse_args()

    plan = read_json(Path(args.plan))
    render_segments = plan.get("timeline_segments") or []
    words = load_words(Path(args.words))
    prominence_rows = read_json(Path(args.reaction_prominence_rows))
    if isinstance(prominence_rows, Mapping):
        prominence_rows = prominence_rows.get("rows") or prominence_rows.get("segments") or []
    from core.render.final_render_pipeline import _extract_semantic_question_windows

    questions = _extract_semantic_question_windows(
        semantic_analysis_path=Path(args.semantic_content_analysis),
        plan=plan,
    )

    video = resolve_video(args.video)
    duration = probe_duration_seconds(video)
    video_w, video_h = probe_video_size(video)
    crop = _profile_crop(Path(args.profile), video_w, video_h)
    builder = ReactionIntensitySignalBuilder(
        video=video,
        mic_track=args.mic_track,
        gameplay_track=args.gameplay_track,
        facecam_crop=crop,
    )

    feature_cache = Path(args.feature_cache)
    if feature_cache.exists():
        features = read_json(feature_cache)
        print(f"[PRO-ZOOM v17] loaded per-video evidence cache: {feature_cache}")
    else:
        print("[PRO-ZOOM v17] extracting per-video evidence...")
        features = builder.extract_video_features()
        write_json(feature_cache, features)
    evidence = evidence_rows(builder, features)
    thresholds = thresholds_from_percentiles(
        evidence,
        event_mic_percentile=55.0,
        event_fusion_percentile=45.0,
        high_mic_percentile=92.0,
    )
    windows = reaction_windows_for_thresholds(
        evidence,
        thresholds,
        window_seconds=builder.window_seconds,
    )
    payload = build_pro_zoom_payload(
        reaction_windows=windows,
        questions=questions,
        prominence_rows=list(prominence_rows or []),
        render_segments=render_segments,
        words=words,
        prominence_floor=args.prominence_floor,
        zooms_per_minute=args.zooms_per_minute,
        min_gap_seconds=args.min_gap_seconds,
    )
    payload["adaptive_thresholds"] = threshold_dict(thresholds)
    payload["adaptive_percentiles"] = {
        "event_mic_percentile": 55.0,
        "event_fusion_percentile": 45.0,
        "high_mic_percentile": 92.0,
    }
    payload["threshold_basis"] = "per_video_adaptive_candidate_thresholds_v17"
    payload["source_video"] = str(video)
    payload["plan_path"] = args.plan
    payload["word_timestamp_source"] = args.words
    payload["semantic_content_analysis_source"] = args.semantic_content_analysis

    events = payload.get("events") or []
    zoom_timing_table = build_zoom_timing_table(events, expected_tail_seconds=0.15)
    bus_large = any(
        event.get("size") == "large"
        and "busfahrer" in str((event.get("word_span") or {}).get("text", "")).lower()
        for event in events
    )
    question_medium = any(
        event.get("size") == "medium"
        and event.get("source") == PRO_ZOOM_SEMANTIC_QUESTION_SIZE_SOURCE
        for event in events
    )
    no_cross_cut = all(len(event.get("render_ranges") or []) == 1 for event in events)
    min_gap = min_render_start_gap(events)
    min_gap_ok = min_gap is None or min_gap >= args.min_gap_seconds - 0.001
    word_timing_ok = all(bool(event.get("word_timing_pass")) for event in events)

    windows_path = Path(args.out_windows)
    windows_path.parent.mkdir(parents=True, exist_ok=True)
    with windows_path.open("w", encoding="utf-8") as handle:
        for row in windows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    write_json(Path(args.out_events), payload)
    write_metrics_csv(Path(args.metrics_csv), payload["metrics_table"])
    write_zoom_timing_csv(Path(args.timing_csv), zoom_timing_table)

    report = {
        "video": str(video),
        "video_duration_seconds": round(duration, 3),
        "plan": args.plan,
        "features_baselines": features.get("baselines") if isinstance(features, Mapping) else None,
        "selected_thresholds": threshold_dict(thresholds),
        "payload": payload,
        "windows_jsonl": str(windows_path),
        "metrics_csv": args.metrics_csv,
        "timing_csv": args.timing_csv,
        "zoom_timing_table": zoom_timing_table,
        "busfahrer_large": bool(bus_large),
        "question_medium": bool(question_medium),
        "no_zoom_crosses_cut": bool(no_cross_cut),
        "min_gap_seconds_ok": bool(min_gap_ok),
        "min_render_start_gap_seconds": min_gap,
        "word_timing_ok": bool(word_timing_ok),
    }
    write_json(Path(args.report_json), report)
    write_text_report(Path(args.report_txt), report)

    print(f"events={args.out_events}")
    print(f"report={args.report_txt}")
    print(f"metrics_csv={args.metrics_csv}")
    print(f"event_count={payload['event_count']} effective_zpm={payload['effective_zooms_per_minute']} size_counts={payload['size_counts']}")
    print(f"distribution_info_only={payload['time_distribution']['percent']}")
    print(f"busfahrer_large={bus_large} question_medium={question_medium} min_gap={min_gap} word_timing_ok={word_timing_ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
