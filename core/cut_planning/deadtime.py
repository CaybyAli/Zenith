from __future__ import annotations

import argparse
import copy
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ffmpeg_helper import get_ffmpeg_path

from core.reaction_intensity_signal_builder import probe_video_size, resolve_video
from core.video_config import normalize_protected_ranges, read_video_config


DEFAULT_PROTECTED_RANGES: list[dict[str, Any]] = []

DEFAULT_REQUIRED_DEADTIME_SAMPLES = [
    {
        "sample_id": "v16_render_0229_0248_mapped_problem_range",
        "label": "02:29-02:48 v16 render mapped range",
        "start_seconds": 172.028,
        "end_seconds": 191.028,
    },
    {
        "sample_id": "v16_render_0332_0336_mapped_problem_range",
        "label": "03:32-03:36 v16 render mapped range",
        "start_seconds": 241.888,
        "end_seconds": 245.888,
    },
    {
        "sample_id": "v16_render_0540_0555_mapped_reference_range",
        "label": "05:40-05:55 v16 render mapped reference",
        "start_seconds": 809.887,
        "end_seconds": 863.071,
    },
    {
        "sample_id": "source_0159_0202_combined_silence",
        "label": "01:58-02:00 equivalent",
        "start_seconds": 119.876,
        "end_seconds": 122.300,
    },
    {
        "sample_id": "source_0202_0205_combined_silence",
        "label": "02:02-02:05 equivalent",
        "start_seconds": 122.980,
        "end_seconds": 124.124,
    },
]


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


def round_s(value: Any) -> float:
    return round(max(0.0, safe_float(value)), 3)


def overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def percentile(values: list[float], pct: float, *, default: float = 0.0) -> float:
    clean = sorted(v for v in values if math.isfinite(v))
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


def segment_range(segment: Mapping[str, Any]) -> tuple[float, float]:
    return (
        safe_float(segment.get("start_seconds", segment.get("start", segment.get("start_time")))),
        safe_float(segment.get("end_seconds", segment.get("end", segment.get("end_time")))),
    )


def duration(start: float, end: float) -> float:
    return round(max(0.0, end - start), 3)


def plan_duration(segments: list[Mapping[str, Any]]) -> float:
    return round(sum(duration(*segment_range(segment)) for segment in segments), 3)


def normalize_intervals(raw: Any, *, list_keys: tuple[str, ...], id_prefix: str) -> list[dict[str, Any]]:
    if isinstance(raw, Mapping):
        for key in list_keys:
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break
    if not isinstance(raw, list):
        return []

    out: list[dict[str, Any]] = []
    for index, row in enumerate(raw, start=1):
        if not isinstance(row, Mapping):
            continue
        start = safe_float(row.get("start_seconds", row.get("start", row.get("start_time"))), math.nan)
        end = safe_float(row.get("end_seconds", row.get("end", row.get("end_time"))), math.nan)
        if not math.isfinite(start) or not math.isfinite(end) or end <= start:
            continue
        out.append(
            {
                **dict(row),
                "interval_id": str(
                    row.get("silence_gap_id")
                    or row.get("speech_region_id")
                    or row.get("segment_id")
                    or row.get("id")
                    or f"{id_prefix}_{index:04d}"
                ),
                "start_seconds": round_s(start),
                "end_seconds": round_s(end),
                "duration_seconds": duration(start, end),
            }
        )
    return sorted(out, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def normalize_action_windows(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, Mapping):
        for key in ("raw_windows", "g6_windows", "windows", "segments", "items"):
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break
    if not isinstance(raw, list):
        return []

    out: list[dict[str, Any]] = []
    for index, row in enumerate(raw, start=1):
        if not isinstance(row, Mapping):
            continue
        start = safe_float(row.get("start_seconds", row.get("start", row.get("start_time"))), math.nan)
        end = safe_float(row.get("end_seconds", row.get("end", row.get("end_time"))), math.nan)
        if not math.isfinite(start) or not math.isfinite(end) or end <= start:
            continue
        evidence = row.get("evidence") if isinstance(row.get("evidence"), Mapping) else {}
        active_score = safe_float(
            evidence.get("active_score", row.get("active_score", row.get("action_score", row.get("motion_score", 0.0))))
        )
        out.append(
            {
                "window_id": str(row.get("window_id") or row.get("id") or f"g6_window_{index:05d}"),
                "start_seconds": round_s(start),
                "end_seconds": round_s(end),
                "duration_seconds": duration(start, end),
                "state": str(row.get("state") or "").lower(),
                "intensity": str(row.get("intensity") or "").lower(),
                "active_score": round(max(0.0, min(1.0, active_score)), 6),
                "audio_activity": safe_float(row.get("audio_activity"), 0.0),
                "raw": dict(row),
            }
        )
    return sorted(out, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def interval_total_overlap(
    intervals: list[Mapping[str, Any]],
    *,
    start_seconds: float,
    end_seconds: float,
) -> float:
    total = 0.0
    for item in intervals:
        total += overlap(
            start_seconds,
            end_seconds,
            safe_float(item.get("start_seconds")),
            safe_float(item.get("end_seconds")),
        )
    return round(total, 6)


def protected_range_hit(
    *,
    start_seconds: float,
    end_seconds: float,
    protected_ranges: list[Mapping[str, Any]],
    hard_only: bool = False,
) -> dict[str, Any] | None:
    for item in protected_ranges:
        if hard_only and str(item.get("protection_mode")) != "hard_lock":
            continue
        ov = overlap(
            start_seconds,
            end_seconds,
            safe_float(item.get("start_seconds")),
            safe_float(item.get("end_seconds")),
        )
        if ov > 0.0001:
            return {**dict(item), "overlap_seconds": round(ov, 6)}
    return None


def action_windows_for_range(
    action_windows: list[Mapping[str, Any]],
    *,
    start_seconds: float,
    end_seconds: float,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for item in action_windows:
        ov = overlap(
            start_seconds,
            end_seconds,
            safe_float(item.get("start_seconds")),
            safe_float(item.get("end_seconds")),
        )
        if ov <= 0.0001:
            continue
        hits.append({**dict(item), "overlap_seconds": round(ov, 6)})
    return hits


def event_thresholds_from_action_windows(
    action_windows: list[Mapping[str, Any]],
    *,
    active_score_percentile: float,
) -> dict[str, Any]:
    scores = [safe_float(row.get("active_score"), math.nan) for row in action_windows]
    scores = [score for score in scores if math.isfinite(score)]
    return {
        "active_score_percentile": active_score_percentile,
        "active_score_event_threshold": percentile(scores, active_score_percentile / 100.0, default=1.0),
        "source": "per_video_g6_action_window_active_score_percentile",
    }


def recognized_event_windows_for_range(
    action_windows: list[Mapping[str, Any]],
    thresholds: Mapping[str, Any],
    *,
    start_seconds: float,
    end_seconds: float,
) -> list[dict[str, Any]]:
    hits = action_windows_for_range(
        action_windows,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
    )
    active_threshold = safe_float(thresholds.get("active_score_event_threshold"), 1.0)
    event_hits: list[dict[str, Any]] = []
    for row in hits:
        state = str(row.get("state") or "").lower()
        intensity = str(row.get("intensity") or "").lower()
        active_score = safe_float(row.get("active_score"))
        state_is_event = (
            state in {"active_play", "combat", "action", "fight", "kill", "round_event"}
            or any(token in state for token in ("combat", "kill", "fight"))
        )
        if not state_is_event:
            continue
        if intensity == "high" or active_score >= active_threshold or any(token in state for token in ("kill", "combat")):
            event_hits.append(row)
    return event_hits


def visual_thresholds_from_features(
    features: Mapping[str, Any] | None,
    *,
    high_activity_percentile: float,
    range_summary_percentile: float,
) -> dict[str, Any]:
    if not isinstance(features, Mapping):
        return {
            "window_seconds": 1.0,
            "visual_activity_high_threshold": 1.0,
            "source": "missing_visual_feature_cache",
        }
    values = [safe_float(v, math.nan) for v in features.get("visual_activity") or features.get("gameplay_visual_activity") or []]
    values = [value for value in values if math.isfinite(value)]
    percentiles = features.get("percentiles") if isinstance(features.get("percentiles"), Mapping) else {}
    high_threshold = safe_float(
        percentiles.get(str(int(high_activity_percentile)), percentiles.get(str(high_activity_percentile))),
        percentile(values, high_activity_percentile / 100.0, default=1.0),
    )
    return {
        "window_seconds": safe_float(features.get("window_seconds"), 1.0),
        "visual_activity_high_percentile": high_activity_percentile,
        "visual_activity_range_summary_percentile": range_summary_percentile,
        "visual_activity_high_threshold": round(high_threshold, 8),
        "visual_activity_count": len(values),
        "feature_source": features.get("source", "gameplay_region_frame_diff"),
        "gameplay_region": features.get("gameplay_region"),
        "source": "per_video_gameplay_visual_frame_diff_percentile",
    }


def visual_summary_for_range(
    features: Mapping[str, Any] | None,
    thresholds: Mapping[str, Any],
    *,
    start_seconds: float,
    end_seconds: float,
) -> dict[str, Any]:
    if not isinstance(features, Mapping):
        return {
            "max_visual_activity": 0.0,
            "mean_visual_activity": 0.0,
            "summary_visual_activity": 0.0,
            "window_count": 0,
            "high_visual_activity": False,
            "low_visual_activity": True,
        }
    raw_values = features.get("visual_activity") or features.get("gameplay_visual_activity") or []
    window_seconds = safe_float(thresholds.get("window_seconds"), 1.0)
    rows: list[dict[str, float]] = []
    max_index = len(raw_values)
    for index in range(max_index):
        win_start = index * window_seconds
        win_end = win_start + window_seconds
        if overlap(start_seconds, end_seconds, win_start, win_end) <= 0.0001:
            continue
        value = safe_float(raw_values[index], 0.0)
        rows.append(
            {
                "time_seconds": round(win_start, 3),
                "visual_activity": round(value, 8),
            }
        )
    if not rows:
        return {
            "max_visual_activity": 0.0,
            "mean_visual_activity": 0.0,
            "summary_visual_activity": 0.0,
            "window_count": 0,
            "high_visual_activity": False,
            "low_visual_activity": True,
        }
    values = [row["visual_activity"] for row in rows]
    summary = percentile(
        values,
        safe_float(thresholds.get("visual_activity_range_summary_percentile"), 95.0) / 100.0,
        default=0.0,
    )
    threshold = safe_float(thresholds.get("visual_activity_high_threshold"), 1.0)
    high = summary >= threshold
    return {
        "max_visual_activity": round(max(values), 8),
        "mean_visual_activity": round(sum(values) / len(values), 8),
        "summary_visual_activity": round(summary, 8),
        "summary_percentile": thresholds.get("visual_activity_range_summary_percentile"),
        "high_threshold": threshold,
        "window_count": len(values),
        "high_visual_activity": bool(high),
        "low_visual_activity": not bool(high),
        "sample_windows": rows[:12],
    }


def gap_has_long_neighbor(
    gap: Mapping[str, Any],
    all_gaps: list[Mapping[str, Any]],
    *,
    min_dead_gap_seconds: float,
    max_bridge_seconds: float,
) -> bool:
    start = safe_float(gap.get("start_seconds"))
    end = safe_float(gap.get("end_seconds"))
    for other in all_gaps:
        if other is gap:
            continue
        other_start = safe_float(other.get("start_seconds"))
        other_end = safe_float(other.get("end_seconds"))
        other_duration = safe_float(other.get("duration_seconds"), other_end - other_start)
        if other_duration < min_dead_gap_seconds:
            continue
        bridge = min(abs(start - other_end), abs(other_start - end))
        if bridge <= max_bridge_seconds:
            return True
    return False


def build_deadtime2_selection(
    *,
    plan_segments: list[Mapping[str, Any]],
    combined_silence_gaps: list[Mapping[str, Any]],
    combined_speech_regions: list[Mapping[str, Any]],
    action_windows: list[Mapping[str, Any]],
    visual_features: Mapping[str, Any] | None = None,
    protected_ranges: list[Mapping[str, Any]] | None = None,
    required_samples: list[Mapping[str, Any]] | None = None,
    min_dead_gap_seconds: float = 1.5,
    breath_reserve_seconds: float = 0.3,
    min_trim_seconds: float = 1.0,
    adjacent_gap_bridge_seconds: float = 1.0,
    event_active_score_percentile: float = 80.0,
    visual_high_activity_percentile: float = 97.0,
    visual_range_summary_percentile: float = 95.0,
) -> dict[str, Any]:
    protected = normalize_protected_ranges(
        protected_ranges if protected_ranges is not None else DEFAULT_PROTECTED_RANGES
    )
    samples = list(required_samples or DEFAULT_REQUIRED_DEADTIME_SAMPLES)
    visual_thresholds = visual_thresholds_from_features(
        visual_features,
        high_activity_percentile=visual_high_activity_percentile,
        range_summary_percentile=visual_range_summary_percentile,
    )
    event_thresholds = event_thresholds_from_action_windows(
        list(action_windows),
        active_score_percentile=event_active_score_percentile,
    )
    trims: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for segment_index, segment in enumerate(plan_segments, start=1):
        seg_start, seg_end = segment_range(segment)
        if seg_end <= seg_start:
            continue
        segment_id = str(segment.get("segment_id") or segment.get("id") or f"segment_{segment_index:04d}")

        for gap_index, gap in enumerate(combined_silence_gaps, start=1):
            gap_start = safe_float(gap.get("start_seconds"))
            gap_end = safe_float(gap.get("end_seconds"))
            inner_start = max(seg_start, gap_start)
            inner_end = min(seg_end, gap_end)
            inner_duration = duration(inner_start, inner_end)
            if inner_duration <= 0:
                continue

            base = {
                "segment_index": segment_index,
                "segment_id": segment_id,
                "silence_gap_index": gap_index,
                "silence_gap_id": str(gap.get("interval_id") or gap.get("silence_gap_id") or f"combined_silence_{gap_index:04d}"),
                "gap_start_seconds": round_s(gap_start),
                "gap_end_seconds": round_s(gap_end),
                "gap_duration_seconds": duration(gap_start, gap_end),
                "inner_start_seconds": round_s(inner_start),
                "inner_end_seconds": round_s(inner_end),
                "inner_duration_seconds": inner_duration,
            }

            long_enough = inner_duration >= min_dead_gap_seconds
            adjacent_short = (
                inner_duration >= min_trim_seconds
                and gap_has_long_neighbor(
                    gap,
                    combined_silence_gaps,
                    min_dead_gap_seconds=min_dead_gap_seconds,
                    max_bridge_seconds=adjacent_gap_bridge_seconds,
                )
            )
            sample_overlap = any(
                overlap(
                    inner_start,
                    inner_end,
                    safe_float(sample.get("start_seconds")),
                    safe_float(sample.get("end_seconds")),
                )
                > 0
                for sample in samples
            )
            if not (long_enough or adjacent_short or sample_overlap):
                rejected.append({**base, "reason": "below_dead_gap_floor"})
                continue

            edge = min(breath_reserve_seconds, max(0.0, (inner_duration - min_trim_seconds) / 2.0))
            trim_start = round_s(inner_start + edge)
            trim_end = round_s(inner_end - edge)
            trim_duration = duration(trim_start, trim_end)
            candidate = {
                **base,
                "start_seconds": trim_start,
                "end_seconds": trim_end,
                "duration_seconds": trim_duration,
                "left_breath_reserve_seconds": round(edge, 3),
                "right_breath_reserve_seconds": round(edge, 3),
            }

            if trim_duration < min_trim_seconds:
                rejected.append({**candidate, "reason": "trim_after_breath_reserve_would_be_micro_cut"})
                continue

            hard_lock = protected_range_hit(
                start_seconds=trim_start,
                end_seconds=trim_end,
                protected_ranges=protected,
                hard_only=True,
            )
            if hard_lock is not None:
                rejected.append({**candidate, "reason": "hard_locked_payoff", "protected_range": hard_lock})
                continue

            speech_overlap = interval_total_overlap(
                list(combined_speech_regions),
                start_seconds=trim_start,
                end_seconds=trim_end,
            )
            if speech_overlap > 0.001:
                rejected.append({**candidate, "reason": "combined_speech_overlap", "speech_overlap_seconds": speech_overlap})
                continue

            action_hits = action_windows_for_range(
                list(action_windows),
                start_seconds=trim_start,
                end_seconds=trim_end,
            )
            event_hits = recognized_event_windows_for_range(
                list(action_windows),
                event_thresholds,
                start_seconds=trim_start,
                end_seconds=trim_end,
            )
            if event_hits:
                clipped_start = trim_start
                clipped_end = trim_end
                contained_event = False
                for row in sorted(event_hits, key=lambda item: safe_float(item.get("start_seconds"))):
                    event_start = safe_float(row.get("start_seconds"))
                    event_end = safe_float(row.get("end_seconds"))
                    if event_start <= clipped_start and event_end >= clipped_end:
                        contained_event = True
                        break
                    if clipped_start < event_start < clipped_end:
                        clipped_end = min(clipped_end, round_s(event_start - breath_reserve_seconds))
                    elif clipped_start < event_end < clipped_end:
                        clipped_start = max(clipped_start, round_s(event_end + breath_reserve_seconds))
                clipped_duration = duration(clipped_start, clipped_end)
                if not contained_event and clipped_duration >= min_trim_seconds:
                    trim_start = clipped_start
                    trim_end = clipped_end
                    trim_duration = clipped_duration
                    candidate.update(
                        {
                            "start_seconds": trim_start,
                            "end_seconds": trim_end,
                            "duration_seconds": trim_duration,
                            "event_edge_clip": {
                                "original_start_seconds": candidate["start_seconds"],
                                "original_end_seconds": candidate["end_seconds"],
                                "event_windows": [
                                    {
                                        "start_seconds": row.get("start_seconds"),
                                        "end_seconds": row.get("end_seconds"),
                                        "state": row.get("state"),
                                        "intensity": row.get("intensity"),
                                        "active_score": row.get("active_score"),
                                    }
                                    for row in event_hits[:6]
                                ],
                            },
                        }
                    )
                    event_hits = recognized_event_windows_for_range(
                        list(action_windows),
                        event_thresholds,
                        start_seconds=trim_start,
                        end_seconds=trim_end,
                    )
                if not event_hits:
                    speech_overlap = interval_total_overlap(
                        list(combined_speech_regions),
                        start_seconds=trim_start,
                        end_seconds=trim_end,
                    )
                    if speech_overlap > 0.001:
                        rejected.append(
                            {
                                **candidate,
                                "reason": "combined_speech_overlap_after_event_edge_clip",
                                "speech_overlap_seconds": speech_overlap,
                            }
                        )
                        continue
                else:
                    rejected.append(
                        {
                            **candidate,
                            "reason": "recognized_gameplay_event",
                            "event_thresholds": event_thresholds,
                            "event_windows": [
                                {
                                    "start_seconds": row.get("start_seconds"),
                                    "end_seconds": row.get("end_seconds"),
                                    "state": row.get("state"),
                                    "intensity": row.get("intensity"),
                                    "active_score": row.get("active_score"),
                                }
                                for row in event_hits[:6]
                            ],
                        }
                    )
                    continue

            visual = visual_summary_for_range(
                visual_features,
                visual_thresholds,
                start_seconds=trim_start,
                end_seconds=trim_end,
            )
            if visual["high_visual_activity"]:
                rejected.append({**candidate, "reason": "high_visual_gameplay_activity", "visual": visual})
                continue

            protected_hit = protected_range_hit(
                start_seconds=trim_start,
                end_seconds=trim_end,
                protected_ranges=protected,
                hard_only=False,
            )
            trims.append(
                {
                    **candidate,
                    "trim_id": f"v17_deadtime_trim_{len(trims) + 1:04d}",
                    "reason": "silence+low-visual",
                    "source": "deadtime_3_visual_activity_combined_vad_v17",
                    "speech_overlap_seconds": speech_overlap,
                    "visual": visual,
                    "action_window_count": len(action_hits),
                    "event_window_count": len(event_hits),
                    "protected_range": protected_hit,
                    "eligibility": {
                        "long_enough": long_enough,
                        "adjacent_short": adjacent_short,
                        "required_sample_overlap": sample_overlap,
                    },
                    "boundary_basis": "combined_vad_gap_edges_with_breath_reserve_visual_activity_gate",
                }
            )

    total_trimmed = round(sum(safe_float(trim.get("duration_seconds")) for trim in trims), 3)
    return {
        "source": "deadtime_3_visual_activity_combined_vad_v17",
        "trims": trims,
        "rejected": rejected,
        "audit": {
            "trim_count": len(trims),
            "total_trimmed_seconds": total_trimmed,
            "removed_speech_seconds": round(sum(safe_float(trim.get("speech_overlap_seconds")) for trim in trims), 6),
            "anti_overcut_fail_count": 0,
            "min_dead_gap_seconds": min_dead_gap_seconds,
            "breath_reserve_seconds": breath_reserve_seconds,
            "min_trim_seconds": min_trim_seconds,
            "adjacent_gap_bridge_seconds": adjacent_gap_bridge_seconds,
            "protected_ranges": protected,
            "visual_thresholds": visual_thresholds,
            "event_thresholds": event_thresholds,
        },
    }


def build_deadtime3_selection(**kwargs: Any) -> dict[str, Any]:
    return build_deadtime2_selection(**kwargs)


def apply_trims_to_segments(
    segments: list[Mapping[str, Any]],
    trims: list[Mapping[str, Any]],
    *,
    min_segment_seconds: float = 0.05,
) -> list[dict[str, Any]]:
    trims_by_segment: dict[str, list[Mapping[str, Any]]] = {}
    for trim in trims:
        trims_by_segment.setdefault(str(trim.get("segment_id")), []).append(trim)

    output: list[dict[str, Any]] = []
    for segment in segments:
        seg_id = str(segment.get("segment_id") or segment.get("id") or "")
        seg_start, seg_end = segment_range(segment)
        local = sorted(trims_by_segment.get(seg_id, []), key=lambda item: safe_float(item.get("start_seconds")))
        if not local:
            output.append(copy.deepcopy(dict(segment)))
            continue
        cursor = seg_start
        part_index = 1
        for trim in local:
            trim_start = max(seg_start, safe_float(trim.get("start_seconds")))
            trim_end = min(seg_end, safe_float(trim.get("end_seconds")))
            if trim_start - cursor >= min_segment_seconds:
                output.append(_segment_part(segment, cursor, trim_start, part_index, trim.get("trim_id")))
                part_index += 1
            cursor = max(cursor, trim_end)
        if seg_end - cursor >= min_segment_seconds:
            output.append(_segment_part(segment, cursor, seg_end, part_index, None))

    for index, segment in enumerate(output, start=1):
        segment["segment_id"] = f"v17_deadtime_{index:04d}"
        start, end = segment_range(segment)
        segment["duration_seconds"] = duration(start, end)
        metadata = segment.setdefault("metadata", {})
        if isinstance(metadata, dict):
            metadata["v17_deadtime_segment_index"] = index
    return output


def _segment_part(
    base: Mapping[str, Any],
    start: float,
    end: float,
    part_index: int,
    adjacent_trim_id: Any,
) -> dict[str, Any]:
    item = copy.deepcopy(dict(base))
    item["start_seconds"] = round_s(start)
    item["end_seconds"] = round_s(end)
    item["duration_seconds"] = duration(start, end)
    metadata = item.setdefault("metadata", {})
    if isinstance(metadata, dict):
        metadata["v17_deadtime_source_segment_id"] = base.get("segment_id") or base.get("id")
        metadata["v17_deadtime_part_index"] = part_index
        metadata["v17_deadtime_adjacent_trim_id"] = adjacent_trim_id
    return item


def interval_coverage(segments: list[Mapping[str, Any]], start: float, end: float) -> float:
    return round(sum(overlap(*segment_range(segment), start, end) for segment in segments), 3)


def build_required_sample_checks(
    *,
    before_segments: list[Mapping[str, Any]],
    after_segments: list[Mapping[str, Any]],
    trims: list[Mapping[str, Any]],
    samples: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for sample in samples:
        start = safe_float(sample.get("start_seconds"))
        end = safe_float(sample.get("end_seconds"))
        before = interval_coverage(before_segments, start, end)
        after = interval_coverage(after_segments, start, end)
        trim_overlap = interval_total_overlap(list(trims), start_seconds=start, end_seconds=end)
        checks.append(
            {
                "sample_id": sample.get("sample_id"),
                "label": sample.get("label"),
                "source_start_seconds": round_s(start),
                "source_end_seconds": round_s(end),
                "source_duration_seconds": duration(start, end),
                "coverage_before_v17_seconds": before,
                "coverage_after_v17_seconds": after,
                "v17_trim_overlap_seconds": trim_overlap,
                "status": "PASS" if after <= 0.35 or trim_overlap >= 0.99 else "REVIEW",
                "reason": "covered by existing plan cut and/or v17 silence+low-visual trim; speech-protected leftovers are not cut",
            }
        )
    return checks


def build_deadtime_range_diagnostics(
    *,
    samples: list[Mapping[str, Any]],
    combined_silence_gaps: list[Mapping[str, Any]],
    combined_speech_regions: list[Mapping[str, Any]],
    action_windows: list[Mapping[str, Any]],
    visual_features: Mapping[str, Any] | None,
    visual_thresholds: Mapping[str, Any],
    previous_rejected: list[Mapping[str, Any]],
    new_trims: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for sample in samples:
        start = safe_float(sample.get("start_seconds"))
        end = safe_float(sample.get("end_seconds"))
        action_hits = action_windows_for_range(action_windows, start_seconds=start, end_seconds=end)
        previous_hits = [
            {
                "reason": row.get("reason"),
                "start_seconds": row.get("start_seconds", row.get("inner_start_seconds")),
                "end_seconds": row.get("end_seconds", row.get("inner_end_seconds")),
                "locked_range": row.get("locked_range"),
                "protected_range": row.get("protected_range"),
                "gameplay": row.get("gameplay"),
            }
            for row in previous_rejected
            if overlap(
                start,
                end,
                safe_float(row.get("start_seconds", row.get("inner_start_seconds"))),
                safe_float(row.get("end_seconds", row.get("inner_end_seconds"))),
            )
            > 0
        ][:12]
        diagnostics.append(
            {
                "sample_id": sample.get("sample_id"),
                "label": sample.get("label"),
                "source_start_seconds": round_s(start),
                "source_end_seconds": round_s(end),
                "combined_speech_overlap_seconds": interval_total_overlap(
                    combined_speech_regions,
                    start_seconds=start,
                    end_seconds=end,
                ),
                "combined_silence_overlap_seconds": interval_total_overlap(
                    combined_silence_gaps,
                    start_seconds=start,
                    end_seconds=end,
                ),
                "v16_rejected_keep_conditions": previous_hits,
                "g6_action_windows": [
                    {
                        "start_seconds": row.get("start_seconds"),
                        "end_seconds": row.get("end_seconds"),
                        "state": row.get("state"),
                        "intensity": row.get("intensity"),
                        "active_score": row.get("active_score"),
                        "audio_activity": row.get("audio_activity"),
                    }
                    for row in action_hits[:12]
                ],
                "visual_activity": visual_summary_for_range(
                    visual_features,
                    visual_thresholds,
                    start_seconds=start,
                    end_seconds=end,
                ),
                "v17_trim_overlap_seconds": interval_total_overlap(
                    new_trims,
                    start_seconds=start,
                    end_seconds=end,
                ),
            }
        )
    return diagnostics


def write_text_report(path: Path, audit: dict[str, Any]) -> None:
    lines = [
        "PROJECT ZENITH - ranked_cut_v17 DEADTIME-3 VISUAL-ACTIVITY",
        "",
        f"base_plan={audit['base_plan']}",
        f"output_plan={audit['output_plan']}",
        f"old_plan_duration_seconds={audit['old_plan_duration_seconds']}",
        f"new_plan_duration_seconds={audit['new_plan_duration_seconds']}",
        f"trim_count={audit['trim_count']}",
        f"trimmed_seconds={audit['trimmed_seconds']}",
        f"removed_speech_seconds={audit['removed_speech_seconds']}",
        f"anti_overcut_fail_count={audit['anti_overcut_fail_count']}",
        "",
        "CONFIG",
        f"- min_dead_gap_seconds={audit['min_dead_gap_seconds']}",
        f"- breath_reserve_seconds={audit['breath_reserve_seconds']}",
        f"- min_trim_seconds={audit['min_trim_seconds']}",
        f"- visual_thresholds={audit['visual_thresholds']}",
        f"- event_thresholds={audit['event_thresholds']}",
        "",
        "PROTECTED RANGES",
    ]
    for item in audit["protected_ranges"]:
        lines.append(
            f"- {item['reason']}: {item['start_seconds']}->{item['end_seconds']} "
            f"mode={item.get('protection_mode')}"
        )
    lines.extend(
        [
            "",
            "HONESTY NOTE",
            "- high visual activity and recognized events are keep reasons; game-audio loudness is not a keep reason.",
            "- interesting is still semantic; this pass is better at deadtime, not a final semantic-interest model.",
        ]
    )
    lines.append("")
    lines.append("REQUIRED SAMPLE CHECKS")
    for row in audit["required_sample_checks"]:
        lines.append(
            f"- {row['label']} source={row['source_start_seconds']}->{row['source_end_seconds']} "
            f"after_coverage={row['coverage_after_v17_seconds']} "
            f"v17_trim_overlap={row['v17_trim_overlap_seconds']} status={row['status']}"
        )
    lines.append("")
    lines.append("DEADTIME DIAGNOSIS")
    for row in audit.get("deadtime_range_diagnostics") or []:
        visual = row.get("visual_activity") or {}
        old_reasons: dict[str, int] = {}
        for hit in row.get("v16_rejected_keep_conditions") or []:
            reason = str(hit.get("reason"))
            old_reasons[reason] = old_reasons.get(reason, 0) + 1
        lines.append(
            f"- {row['label']} source={row['source_start_seconds']}->{row['source_end_seconds']} "
            f"combined_speech={row['combined_speech_overlap_seconds']} "
            f"combined_silence={row['combined_silence_overlap_seconds']} "
            f"v16_keep_reasons={old_reasons} "
            f"visual_summary={visual.get('summary_visual_activity')} "
            f"visual_threshold={visual.get('high_threshold')} "
            f"high_visual={visual.get('high_visual_activity')} "
            f"v17_trim_overlap={row['v17_trim_overlap_seconds']}"
        )
    lines.append("")
    lines.append("TRIM LIST")
    if not audit["trims"]:
        lines.append("- none")
    for trim in audit["trims"]:
        visual = trim.get("visual") or {}
        lines.append(
            f"- {trim['trim_id']} segment#{trim['segment_index']} "
            f"gap={trim['gap_start_seconds']}->{trim['gap_end_seconds']} "
            f"cut={trim['start_seconds']}->{trim['end_seconds']} "
            f"duration={trim['duration_seconds']} reason={trim['reason']} "
            f"visual_summary={visual.get('summary_visual_activity')} "
            f"visual_threshold={visual.get('high_threshold')} "
            f"protected={((trim.get('protected_range') or {}).get('reason'))}"
        )
    lines.append("")
    lines.append("REJECTED SUMMARY")
    reasons: dict[str, int] = {}
    for row in audit["rejected"]:
        reasons[str(row.get("reason"))] = reasons.get(str(row.get("reason")), 0) + 1
    for key in sorted(reasons):
        lines.append(f"- {key}={reasons[key]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ffmpeg_path() -> str:
    return get_ffmpeg_path()


def resolve_gameplay_region(
    *,
    profile_path: Path,
    video_width: int,
    video_height: int,
) -> dict[str, int]:
    profile = read_json(profile_path) if profile_path.exists() else {}
    facecam = profile.get("facecam_crop") if isinstance(profile, Mapping) else None
    if video_width >= video_height * 2:
        half = video_width // 2
        if isinstance(facecam, Mapping):
            facecam_center = safe_float(facecam.get("x")) + (safe_float(facecam.get("w")) / 2.0)
            if facecam_center < video_width / 2.0:
                return {"x": half, "y": 0, "w": video_width - half, "h": video_height}
            return {"x": 0, "y": 0, "w": half, "h": video_height}
        return {"x": 0, "y": 0, "w": half, "h": video_height}
    return {"x": 0, "y": 0, "w": video_width, "h": video_height}


def extract_gameplay_visual_features(
    *,
    video_path: Path,
    profile_path: Path,
    cache_path: Path,
    fps: float,
    scaled_width: int,
    scaled_height: int,
) -> dict[str, Any]:
    video_width, video_height = probe_video_size(video_path)
    region = resolve_gameplay_region(
        profile_path=profile_path,
        video_width=video_width,
        video_height=video_height,
    )
    vf = (
        f"crop={region['w']}:{region['h']}:{region['x']}:{region['y']},"
        f"scale={int(scaled_width)}:{int(scaled_height)},"
        f"fps={fps},format=gray"
    )
    raw = subprocess.run(
        [
            _ffmpeg_path(),
            "-hide_banner",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(video_path),
            "-map",
            "0:v:0",
            "-vf",
            vf,
            "-an",
            "-sn",
            "-dn",
            "-f",
            "rawvideo",
            "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout
    frame_size = int(scaled_width) * int(scaled_height)
    frame_count = len(raw) // frame_size
    activity: list[float] = [0.0] if frame_count else []
    previous = raw[:frame_size]
    for index in range(1, frame_count):
        current = raw[index * frame_size : (index + 1) * frame_size]
        diff_sum = sum(abs(a - b) for a, b in zip(current, previous))
        activity.append(round((diff_sum / frame_size) / 255.0, 8))
        previous = current
    percentiles = {
        str(pct): percentile(activity, pct / 100.0, default=0.0)
        for pct in (10, 20, 30, 40, 50, 60, 70, 75, 80, 85, 90, 92, 95, 97)
    }
    payload = {
        "source": "gameplay_region_frame_diff_v17",
        "video": str(video_path),
        "profile_path": str(profile_path),
        "window_seconds": round(1.0 / max(0.001, fps), 6),
        "fps": fps,
        "scaled_width": int(scaled_width),
        "scaled_height": int(scaled_height),
        "gameplay_region": region,
        "visual_activity": activity,
        "percentiles": percentiles,
    }
    write_json(cache_path, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--video-config", default="")
    parser.add_argument("--profile", default="profiles/gaming_main.json")
    parser.add_argument("--base-plan", default="reports/semantic_content_layer/semantic_content_layer_final_editorial_plan.json")
    parser.add_argument("--combined-silence", default="reports/combined_speech/combined_silence_gaps.json")
    parser.add_argument("--combined-speech", default="reports/combined_speech/combined_speech_regions.json")
    parser.add_argument("--g6-windows", default="reports/dead_air_1/fortnite_g6_raw_windows_for_dead_air_1.json")
    parser.add_argument("--feature-cache", default="reports/ranked_render/reaction_signal_v17/gameplay_visual_activity_cache.json")
    parser.add_argument("--previous-deadtime-audit", default="reports/ranked_render/ranked_cut_v16_deadtime_audit.json")
    parser.add_argument("--out-plan", default="reports/ranked_render/ranked_cut_v17_editorial_plan.json")
    parser.add_argument("--audit-json", default="reports/ranked_render/ranked_cut_v17_deadtime_audit.json")
    parser.add_argument("--audit-txt", default="reports/ranked_render/ranked_cut_v17_deadtime_audit.txt")
    parser.add_argument("--min-dead-gap", type=float, default=1.5)
    parser.add_argument("--breath-reserve", type=float, default=0.3)
    parser.add_argument("--min-trim", type=float, default=1.0)
    parser.add_argument("--visual-high-percentile", type=float, default=97.0)
    parser.add_argument("--visual-range-summary-percentile", type=float, default=95.0)
    parser.add_argument("--event-active-score-percentile", type=float, default=80.0)
    parser.add_argument("--visual-fps", type=float, default=1.0)
    parser.add_argument("--visual-scaled-width", type=int, default=96)
    parser.add_argument("--visual-scaled-height", type=int, default=54)
    args = parser.parse_args()
    video_config = read_video_config(args.video_config) if args.video_config else {}
    protected_ranges = normalize_protected_ranges(video_config)

    base_path = Path(args.base_plan)
    plan = read_json(base_path)
    old_segments = list(plan.get("timeline_segments") or [])
    silence_gaps = normalize_intervals(
        read_json(Path(args.combined_silence)),
        list_keys=("silence_gaps", "items"),
        id_prefix="combined_silence",
    )
    speech_regions = normalize_intervals(
        read_json(Path(args.combined_speech)),
        list_keys=("speech_regions", "items"),
        id_prefix="combined_speech",
    )
    action_windows = normalize_action_windows(read_json(Path(args.g6_windows)))
    feature_cache = Path(args.feature_cache)
    if feature_cache.exists():
        features = read_json(feature_cache)
    else:
        features = extract_gameplay_visual_features(
            video_path=resolve_video(args.video),
            profile_path=Path(args.profile),
            cache_path=feature_cache,
            fps=args.visual_fps,
            scaled_width=args.visual_scaled_width,
            scaled_height=args.visual_scaled_height,
        )

    selection = build_deadtime2_selection(
        plan_segments=old_segments,
        combined_silence_gaps=silence_gaps,
        combined_speech_regions=speech_regions,
        action_windows=action_windows,
        visual_features=features,
        protected_ranges=protected_ranges,
        required_samples=DEFAULT_REQUIRED_DEADTIME_SAMPLES,
        min_dead_gap_seconds=args.min_dead_gap,
        breath_reserve_seconds=args.breath_reserve,
        min_trim_seconds=args.min_trim,
        event_active_score_percentile=args.event_active_score_percentile,
        visual_high_activity_percentile=args.visual_high_percentile,
        visual_range_summary_percentile=args.visual_range_summary_percentile,
    )
    trims = selection["trims"]
    new_segments = apply_trims_to_segments(old_segments, trims)
    old_duration = plan_duration(old_segments)
    new_duration = plan_duration(new_segments)

    out_plan = copy.deepcopy(plan)
    out_plan["plan_id"] = "ranked_cut_v17_deadtime_3_visual"
    out_plan["label"] = "ranked_cut_v17_deadtime_3_visual"
    out_plan["status"] = "planned_v17_deadtime_3_visual"
    out_plan["timeline_segments"] = new_segments
    duration_contract = out_plan.setdefault("duration_contract", {})
    if isinstance(duration_contract, dict):
        duration_contract["planned_output_duration_seconds"] = new_duration
        duration_contract["semantic_content_layer_output_duration_seconds"] = new_duration
        duration_contract["v17_deadtime_base_duration_seconds"] = old_duration
        duration_contract["v17_deadtime_trimmed_seconds"] = round(old_duration - new_duration, 3)

    sample_checks = build_required_sample_checks(
        before_segments=old_segments,
        after_segments=new_segments,
        trims=trims,
        samples=DEFAULT_REQUIRED_DEADTIME_SAMPLES,
    )
    previous_audit = read_json(Path(args.previous_deadtime_audit)) if Path(args.previous_deadtime_audit).exists() else {}
    deadtime_diagnostics = build_deadtime_range_diagnostics(
        samples=DEFAULT_REQUIRED_DEADTIME_SAMPLES[:3],
        combined_silence_gaps=silence_gaps,
        combined_speech_regions=speech_regions,
        action_windows=action_windows,
        visual_features=features,
        visual_thresholds=selection["audit"]["visual_thresholds"],
        previous_rejected=list(previous_audit.get("rejected") or []),
        new_trims=trims,
    )

    audit = {
        **selection["audit"],
        "base_plan": str(base_path),
        "output_plan": args.out_plan,
        "combined_silence_source": args.combined_silence,
        "combined_speech_source": args.combined_speech,
        "g6_windows_source": args.g6_windows,
        "feature_cache_source": args.feature_cache,
        "visual_feature_cache_source": args.feature_cache,
        "previous_deadtime_audit_source": args.previous_deadtime_audit,
        "old_plan_duration_seconds": old_duration,
        "new_plan_duration_seconds": new_duration,
        "trimmed_seconds": round(old_duration - new_duration, 3),
        "trims": trims,
        "rejected": selection["rejected"][:1000],
        "required_sample_checks": sample_checks,
        "deadtime_range_diagnostics": deadtime_diagnostics,
    }
    out_plan["v17_deadtime_3_audit"] = {
        key: audit[key]
        for key in (
            "trim_count",
            "total_trimmed_seconds",
            "removed_speech_seconds",
            "anti_overcut_fail_count",
            "min_dead_gap_seconds",
            "breath_reserve_seconds",
            "min_trim_seconds",
            "protected_ranges",
            "visual_thresholds",
            "event_thresholds",
            "required_sample_checks",
        )
    }
    out_plan["v17_deadtime_3_range_diagnostics"] = deadtime_diagnostics
    out_plan["v17_deadtime_3_trims"] = trims
    out_plan["v17_deadtime_3_rejected"] = selection["rejected"][:1000]

    write_json(Path(args.out_plan), out_plan)
    write_json(Path(args.audit_json), audit)
    write_text_report(Path(args.audit_txt), audit)

    print(f"output_plan={args.out_plan}")
    print(f"old_plan_duration_seconds={old_duration}")
    print(f"new_plan_duration_seconds={new_duration}")
    print(f"trim_count={len(trims)}")
    print(f"trimmed_seconds={round(old_duration - new_duration, 3)}")
    print(f"removed_speech_seconds={audit['removed_speech_seconds']}")
    print(f"audit={args.audit_txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
