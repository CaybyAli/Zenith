from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping


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


def duration(start: float, end: float) -> float:
    return round(max(0.0, end - start), 3)


def overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def segment_range(segment: Mapping[str, Any]) -> tuple[float, float]:
    return (
        safe_float(segment.get("start_seconds", segment.get("start", segment.get("start_time")))),
        safe_float(segment.get("end_seconds", segment.get("end", segment.get("end_time")))),
    )


def plan_duration(segments: list[Mapping[str, Any]]) -> float:
    return round(sum(duration(*segment_range(segment)) for segment in segments), 3)


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
            safe_float(item.get("start_seconds", item.get("start", item.get("start_time")))),
            safe_float(item.get("end_seconds", item.get("end", item.get("end_time")))),
        )
    return round(total, 6)


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
                    row.get("speech_region_id")
                    or row.get("silence_gap_id")
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


def normalize_words(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, Mapping):
        for key in ("words", "items", "segments"):
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
                "word_index": index,
                "word": str(row.get("word") or row.get("text") or ""),
                "start_seconds": round_s(start),
                "end_seconds": round_s(end),
                "duration_seconds": duration(start, end),
            }
        )
    return sorted(out, key=lambda item: (item["start_seconds"], item["end_seconds"], item["word_index"]))


def protected_range_hit(
    *,
    start_seconds: float,
    end_seconds: float,
    protected_ranges: list[Mapping[str, Any]],
) -> dict[str, Any] | None:
    for item in protected_ranges:
        item_start = safe_float(item.get("start_seconds"))
        item_end = safe_float(item.get("end_seconds"))
        ov = overlap(start_seconds, end_seconds, item_start, item_end)
        if ov > 0.0001:
            return {**dict(item), "overlap_seconds": round(ov, 6)}
    return None


def timeline_maps(segments: list[Mapping[str, Any]]) -> list[dict[str, float | str]]:
    render_cursor = 0.0
    out: list[dict[str, float | str]] = []
    for segment in segments:
        start, end = segment_range(segment)
        dur = duration(start, end)
        out.append(
            {
                "segment_id": str(segment.get("segment_id") or segment.get("id") or ""),
                "source_start_seconds": start,
                "source_end_seconds": end,
                "render_start_seconds": round(render_cursor, 3),
                "render_end_seconds": round(render_cursor + dur, 3),
            }
        )
        render_cursor += dur
    return out


def source_to_render(source_seconds: float, maps: list[Mapping[str, Any]]) -> float | None:
    for row in maps:
        source_start = safe_float(row.get("source_start_seconds"))
        source_end = safe_float(row.get("source_end_seconds"))
        if source_start - 0.0001 <= source_seconds <= source_end + 0.0001:
            return round(safe_float(row.get("render_start_seconds")) + (source_seconds - source_start), 3)
    return None


def last_speech_region_for_segment(
    segment: Mapping[str, Any],
    speech_regions: list[Mapping[str, Any]],
) -> dict[str, Any] | None:
    seg_start, seg_end = segment_range(segment)
    hits = [
        dict(row)
        for row in speech_regions
        if overlap(
            seg_start,
            seg_end,
            safe_float(row.get("start_seconds")),
            safe_float(row.get("end_seconds")),
        )
        > 0.0001
    ]
    if not hits:
        return None
    return max(hits, key=lambda item: (safe_float(item.get("end_seconds")), safe_float(item.get("start_seconds"))))


def words_for_range(
    words: list[Mapping[str, Any]],
    *,
    start_seconds: float,
    end_seconds: float,
) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in words
        if overlap(
            start_seconds,
            end_seconds,
            safe_float(row.get("start_seconds")),
            safe_float(row.get("end_seconds")),
        )
        > 0.0001
    ]


def build_tail_clamps(
    *,
    plan_segments: list[Mapping[str, Any]],
    combined_speech_regions: list[Mapping[str, Any]],
    words: list[Mapping[str, Any]],
    protected_ranges: list[Mapping[str, Any]],
    tail_after_speech_seconds: float = 0.15,
    min_tail_trim_seconds: float = 0.075,
    min_segment_seconds: float = 0.4,
) -> dict[str, Any]:
    speech_regions = normalize_intervals(
        combined_speech_regions,
        list_keys=("speech_regions", "items"),
        id_prefix="combined_speech",
    )
    word_rows = normalize_words(words)
    protected = normalize_intervals(
        protected_ranges,
        list_keys=("protected_ranges", "items"),
        id_prefix="protected",
    )

    clamps: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for segment_index, segment in enumerate(plan_segments, start=1):
        seg_start, seg_end = segment_range(segment)
        segment_id = str(segment.get("segment_id") or segment.get("id") or f"segment_{segment_index:04d}")
        if seg_end - seg_start < min_segment_seconds:
            rejected.append(
                {
                    "segment_index": segment_index,
                    "segment_id": segment_id,
                    "reason": "segment_below_min_duration",
                    "start_seconds": round_s(seg_start),
                    "end_seconds": round_s(seg_end),
                }
            )
            continue

        last_speech = last_speech_region_for_segment(segment, speech_regions)
        if last_speech is None:
            rejected.append(
                {
                    "segment_index": segment_index,
                    "segment_id": segment_id,
                    "reason": "no_combined_speech_in_segment",
                    "start_seconds": round_s(seg_start),
                    "end_seconds": round_s(seg_end),
                }
            )
            continue

        speech_start = max(seg_start, safe_float(last_speech.get("start_seconds")))
        speech_end = min(seg_end, safe_float(last_speech.get("end_seconds")))
        if speech_end >= seg_end - tail_after_speech_seconds:
            rejected.append(
                {
                    "segment_index": segment_index,
                    "segment_id": segment_id,
                    "reason": "tail_already_at_or_below_target",
                    "segment_end_seconds": round_s(seg_end),
                    "combined_speech_end_seconds": round_s(speech_end),
                    "tail_after_combined_vad_seconds": round(seg_end - speech_end, 3),
                }
            )
            continue

        clamp_start = round_s(speech_end + tail_after_speech_seconds)
        clamp_end = round_s(seg_end)
        trim_seconds = duration(clamp_start, clamp_end)
        if trim_seconds < min_tail_trim_seconds:
            rejected.append(
                {
                    "segment_index": segment_index,
                    "segment_id": segment_id,
                    "reason": "tail_trim_below_min_meaningful_delta",
                    "start_seconds": clamp_start,
                    "end_seconds": clamp_end,
                    "duration_seconds": trim_seconds,
                }
            )
            continue

        if clamp_start - seg_start < min_segment_seconds:
            rejected.append(
                {
                    "segment_index": segment_index,
                    "segment_id": segment_id,
                    "reason": "remaining_segment_below_min_duration",
                    "start_seconds": round_s(seg_start),
                    "new_end_seconds": clamp_start,
                    "remaining_duration_seconds": duration(seg_start, clamp_start),
                }
            )
            continue

        protected_hit = protected_range_hit(
            start_seconds=clamp_start,
            end_seconds=clamp_end,
            protected_ranges=protected,
        )
        if protected_hit:
            rejected.append(
                {
                    "segment_index": segment_index,
                    "segment_id": segment_id,
                    "reason": "locked_combat_or_payoff_range",
                    "start_seconds": clamp_start,
                    "end_seconds": clamp_end,
                    "duration_seconds": trim_seconds,
                    "protected_range": protected_hit,
                }
            )
            continue

        speech_overlap = interval_total_overlap(speech_regions, start_seconds=clamp_start, end_seconds=clamp_end)
        if speech_overlap > 0.0001:
            rejected.append(
                {
                    "segment_index": segment_index,
                    "segment_id": segment_id,
                    "reason": "combined_speech_overlap_guard",
                    "start_seconds": clamp_start,
                    "end_seconds": clamp_end,
                    "speech_overlap_seconds": speech_overlap,
                }
            )
            continue

        tail_words = words_for_range(word_rows, start_seconds=speech_start, end_seconds=seg_end)
        reliable_tail_words = [
            row
            for row in tail_words
            if safe_float(row.get("end_seconds")) <= speech_end + 0.25
        ]
        terminal_word = (
            max(reliable_tail_words, key=lambda item: safe_float(item.get("end_seconds")))
            if reliable_tail_words
            else None
        )
        word_overlap_after_cut = interval_total_overlap(
            reliable_tail_words,
            start_seconds=clamp_start,
            end_seconds=clamp_end,
        )
        clamps.append(
            {
                "trim_id": f"v18_tail_clamp_{len(clamps) + 1:04d}",
                "segment_index": segment_index,
                "segment_id": segment_id,
                "start_seconds": clamp_start,
                "end_seconds": clamp_end,
                "duration_seconds": trim_seconds,
                "reason": "tail_after_speech_clamp",
                "source": "deadtime_4_tail_clamp_combined_vad_v18",
                "tail_after_speech_seconds": round(tail_after_speech_seconds, 3),
                "combined_speech_region_id": last_speech.get("speech_region_id") or last_speech.get("interval_id"),
                "combined_speech_start_seconds": round_s(speech_start),
                "combined_speech_end_seconds": round_s(speech_end),
                "tail_before_clamp_seconds": round(seg_end - speech_end, 3),
                "tail_after_clamp_seconds": round(clamp_start - speech_end, 3),
                "combined_speech_overlap_seconds": speech_overlap,
                "terminal_owner_word": terminal_word.get("word") if terminal_word else None,
                "terminal_owner_word_end_seconds": (
                    round_s(terminal_word.get("end_seconds")) if terminal_word else None
                ),
                "owner_word_overlap_after_cut_seconds": word_overlap_after_cut,
                "word_boundary_note": (
                    "combined_vad_boundary_used; reliable_owner_word_clear"
                    if terminal_word
                    else "combined_vad_boundary_used_no_reliable_owner_word_in_tail"
                ),
                "follow_speech_before_segment_cut": False,
            }
        )

    total_trimmed = round(sum(safe_float(row.get("duration_seconds")) for row in clamps), 3)
    removed_speech = round(
        sum(
            interval_total_overlap(
                speech_regions,
                start_seconds=safe_float(row.get("start_seconds")),
                end_seconds=safe_float(row.get("end_seconds")),
            )
            for row in clamps
        ),
        6,
    )
    return {
        "clamps": clamps,
        "rejected": rejected,
        "audit": {
            "tail_after_speech_seconds": round(tail_after_speech_seconds, 3),
            "min_tail_trim_seconds": round(min_tail_trim_seconds, 3),
            "tail_clamp_count": len(clamps),
            "total_trimmed_seconds": total_trimmed,
            "removed_speech_seconds": removed_speech,
            "protected_ranges": protected,
            "game_agnostic_note": "tail_after_speech_seconds is a global style value; no game-specific thresholds are introduced",
        },
    }


def apply_tail_clamps_to_segments(
    plan_segments: list[Mapping[str, Any]],
    clamps: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    clamps_by_segment = {str(row.get("segment_id")): row for row in clamps}
    out: list[dict[str, Any]] = []
    for index, segment in enumerate(plan_segments, start=1):
        item = copy.deepcopy(dict(segment))
        segment_id = str(item.get("segment_id") or item.get("id") or f"segment_{index:04d}")
        clamp = clamps_by_segment.get(segment_id)
        if clamp:
            item["end_seconds"] = round_s(clamp.get("start_seconds"))
            start, end = segment_range(item)
            item["duration_seconds"] = duration(start, end)
            metadata = item.setdefault("metadata", {})
            if isinstance(metadata, dict):
                metadata["v18_tail_clamp_source_segment_id"] = segment_id
                metadata["v18_tail_clamp_trim_id"] = clamp.get("trim_id")
                metadata["v18_tail_clamp_removed_seconds"] = clamp.get("duration_seconds")
        item["segment_id"] = f"v18_tail_{len(out) + 1:04d}"
        metadata = item.setdefault("metadata", {})
        if isinstance(metadata, dict):
            metadata["v18_tail_clamp_segment_index"] = len(out) + 1
        out.append(item)
    return out


def add_render_proof_to_clamps(
    clamps: list[Mapping[str, Any]],
    before_segments: list[Mapping[str, Any]],
    after_segments: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    before_maps = timeline_maps(before_segments)
    after_maps = timeline_maps(after_segments)
    out: list[dict[str, Any]] = []
    for row in clamps:
        start = safe_float(row.get("start_seconds"))
        end = safe_float(row.get("end_seconds"))
        speech_end = safe_float(row.get("combined_speech_end_seconds"))
        item = copy.deepcopy(dict(row))
        item["v17_render_speech_end_seconds"] = source_to_render(speech_end, before_maps)
        item["v17_render_old_cut_seconds"] = source_to_render(end, before_maps)
        item["v18_render_speech_end_seconds"] = source_to_render(speech_end, after_maps)
        item["v18_render_new_cut_seconds"] = source_to_render(start, after_maps)
        item["v17_render_tail_before_clamp_seconds"] = (
            round(item["v17_render_old_cut_seconds"] - item["v17_render_speech_end_seconds"], 3)
            if item["v17_render_old_cut_seconds"] is not None and item["v17_render_speech_end_seconds"] is not None
            else None
        )
        item["v18_render_tail_after_clamp_seconds"] = (
            round(item["v18_render_new_cut_seconds"] - item["v18_render_speech_end_seconds"], 3)
            if item["v18_render_new_cut_seconds"] is not None and item["v18_render_speech_end_seconds"] is not None
            else None
        )
        item["render_tail_after_clamp_seconds"] = item["v18_render_tail_after_clamp_seconds"]
        out.append(item)
    return out


def copy_file_byte_identical(source: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = source.read_bytes()
    destination.write_bytes(payload)
    src_hash = hashlib.sha256(payload).hexdigest()
    dst_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
    return {
        "source": str(source),
        "destination": str(destination),
        "sha256": src_hash,
        "byte_identical": src_hash == dst_hash,
        "bytes": len(payload),
    }


def write_tail_report(path: Path, audit: Mapping[str, Any]) -> None:
    lines = [
        "PROJECT ZENITH - ranked_cut_v18 DEADTIME-4 TAIL-CLAMP",
        "",
        f"base_plan={audit['base_plan']}",
        f"output_plan={audit['output_plan']}",
        f"old_plan_duration_seconds={audit['old_plan_duration_seconds']}",
        f"new_plan_duration_seconds={audit['new_plan_duration_seconds']}",
        f"tail_after_speech_seconds={audit['tail_after_speech_seconds']}",
        f"tail_clamp_count={audit['tail_clamp_count']}",
        f"trimmed_seconds={audit['total_trimmed_seconds']}",
        f"removed_speech_seconds={audit['removed_speech_seconds']}",
        f"zoom_events_byte_identical_to_v17={audit.get('zoom_events_copy', {}).get('byte_identical')}",
        "",
        "SCOPE",
        "- additive pacing only: v17 visual deadtime logic, combat/payoff handling, round xfade, and zoom model stay unchanged.",
        "- Tail target 0.15s is a global style value, not a game-specific threshold.",
        "",
        "PROTECTED RANGES",
    ]
    for row in audit.get("protected_ranges") or []:
        lines.append(
            f"- {row.get('reason')}: {row.get('start_seconds')}->{row.get('end_seconds')} "
            f"mode={row.get('protection_mode')}"
        )
    lines.extend(["", "TAIL EXAMPLES"])
    for row in (audit.get("tail_examples") or [])[:12]:
        lines.append(
            f"- {row['trim_id']} source={row['combined_speech_end_seconds']}->{row['start_seconds']} "
            f"old_cut={row['end_seconds']} tail_before={row['tail_before_clamp_seconds']} "
            f"tail_after={row['tail_after_clamp_seconds']} "
            f"render_old_cut={row.get('v17_render_old_cut_seconds')} "
            f"render_new_cut={row.get('v18_render_new_cut_seconds')} "
            f"word={row.get('terminal_owner_word')} word_overlap_after_cut={row.get('owner_word_overlap_after_cut_seconds')}"
        )
    lines.extend(["", "00:09-00:11 EQUIVALENT DIAGNOSIS"])
    for row in audit.get("render_0009_0011_equivalent") or []:
        lines.append(
            f"- {row['label']} render={row['render_start_seconds']}->{row['render_end_seconds']} "
            f"source={row['source_start_seconds']}->{row['source_end_seconds']} "
            f"combined_speech_overlap={row['combined_speech_overlap_seconds']} "
            f"status={row['status']} reason={row['reason']}"
        )
    lines.extend(["", "TAIL CLAMP LIST"])
    if not audit.get("clamps"):
        lines.append("- none")
    for row in audit.get("clamps") or []:
        lines.append(
            f"- {row['trim_id']} segment#{row['segment_index']} {row['segment_id']} "
            f"trim={row['start_seconds']}->{row['end_seconds']} dur={row['duration_seconds']} "
            f"tail={row['tail_before_clamp_seconds']}->{row['tail_after_clamp_seconds']} "
            f"speech_overlap={row['combined_speech_overlap_seconds']}"
        )
    lines.extend(["", "REJECTED SUMMARY"])
    reasons: dict[str, int] = {}
    for row in audit.get("rejected") or []:
        reason = str(row.get("reason"))
        reasons[reason] = reasons.get(reason, 0) + 1
    for key in sorted(reasons):
        lines.append(f"- {key}={reasons[key]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def diagnose_render_range(
    *,
    label: str,
    render_start: float,
    render_end: float,
    segments: list[Mapping[str, Any]],
    speech_regions: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    render_cursor = 0.0
    for segment in segments:
        seg_start, seg_end = segment_range(segment)
        seg_dur = duration(seg_start, seg_end)
        overlap_start = max(render_start, render_cursor)
        overlap_end = min(render_end, render_cursor + seg_dur)
        if overlap_end > overlap_start:
            source_start = seg_start + (overlap_start - render_cursor)
            source_end = seg_start + (overlap_end - render_cursor)
            speech_overlap = interval_total_overlap(
                speech_regions,
                start_seconds=source_start,
                end_seconds=source_end,
            )
            out.append(
                {
                    "label": label,
                    "render_start_seconds": round_s(overlap_start),
                    "render_end_seconds": round_s(overlap_end),
                    "source_start_seconds": round_s(source_start),
                    "source_end_seconds": round_s(source_end),
                    "combined_speech_overlap_seconds": speech_overlap,
                    "status": "not_tail_clamp_candidate" if speech_overlap > 0.001 else "tail_silence_candidate",
                    "reason": (
                        "combined_vad_reports_owner_or_friend_speech"
                        if speech_overlap > 0.001
                        else "no_combined_vad_speech_in_render_window"
                    ),
                }
            )
        render_cursor += seg_dur
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-plan", default="reports/ranked_render/ranked_cut_v17_editorial_plan.json")
    parser.add_argument("--combined-speech", default="reports/combined_speech/combined_speech_regions.json")
    parser.add_argument("--words", default="reports/speech_1_transcript_largev3/fortnite_words.json")
    parser.add_argument("--v17-deadtime-audit", default="reports/ranked_render/ranked_cut_v17_deadtime_audit.json")
    parser.add_argument("--v17-events", default="reports/ranked_render/ranked_cut_v17_reaction_size_events.json")
    parser.add_argument("--out-plan", default="reports/ranked_render/ranked_cut_v18_editorial_plan.json")
    parser.add_argument("--audit-json", default="reports/ranked_render/ranked_cut_v18_tail_clamp_audit.json")
    parser.add_argument("--audit-txt", default="reports/ranked_render/ranked_cut_v18_tail_clamp_audit.txt")
    parser.add_argument("--tail-list-json", default="reports/ranked_render/ranked_cut_v18_tail_examples.json")
    parser.add_argument("--events-out", default="reports/ranked_render/ranked_cut_v18_reaction_size_events.json")
    parser.add_argument("--tail-after-speech-seconds", type=float, default=0.15)
    parser.add_argument("--min-tail-trim-seconds", type=float, default=0.075)
    args = parser.parse_args()

    plan_path = Path(args.base_plan)
    plan = read_json(plan_path)
    segments = list(plan.get("timeline_segments") or [])
    if not segments:
        raise RuntimeError(f"plan has no timeline_segments: {plan_path}")
    speech_regions = normalize_intervals(
        read_json(Path(args.combined_speech)),
        list_keys=("speech_regions", "items"),
        id_prefix="combined_speech",
    )
    words = normalize_words(read_json(Path(args.words)))
    v17_audit = read_json(Path(args.v17_deadtime_audit)) if Path(args.v17_deadtime_audit).exists() else {}
    protected_ranges = list(v17_audit.get("protected_ranges") or [])

    selection = build_tail_clamps(
        plan_segments=segments,
        combined_speech_regions=speech_regions,
        words=words,
        protected_ranges=protected_ranges,
        tail_after_speech_seconds=args.tail_after_speech_seconds,
        min_tail_trim_seconds=args.min_tail_trim_seconds,
    )
    new_segments = apply_tail_clamps_to_segments(segments, selection["clamps"])
    clamps_with_render = add_render_proof_to_clamps(selection["clamps"], segments, new_segments)
    tail_examples = sorted(
        clamps_with_render,
        key=lambda row: (-safe_float(row.get("duration_seconds")), safe_float(row.get("start_seconds"))),
    )

    old_duration = plan_duration(segments)
    new_duration = plan_duration(new_segments)
    out_plan = copy.deepcopy(plan)
    out_plan["plan_id"] = "ranked_cut_v18_deadtime_4_tail_clamp"
    out_plan["label"] = "ranked_cut_v18_deadtime_4_tail_clamp"
    out_plan["status"] = "planned_v18_deadtime_4_tail_clamp"
    out_plan["timeline_segments"] = new_segments
    duration_contract = out_plan.setdefault("duration_contract", {})
    if isinstance(duration_contract, dict):
        duration_contract["planned_output_duration_seconds"] = new_duration
        duration_contract["v18_tail_clamp_base_duration_seconds"] = old_duration
        duration_contract["v18_tail_clamp_trimmed_seconds"] = round(old_duration - new_duration, 3)
    out_plan["v18_tail_clamp_audit"] = {
        "tail_after_speech_seconds": round(args.tail_after_speech_seconds, 3),
        "tail_clamp_count": len(clamps_with_render),
        "total_trimmed_seconds": round(old_duration - new_duration, 3),
        "removed_speech_seconds": selection["audit"]["removed_speech_seconds"],
        "zoom_model_unchanged": True,
        "events_json_expected_byte_identical_to_v17": True,
    }
    out_plan["v18_tail_clamps"] = clamps_with_render

    zoom_copy = copy_file_byte_identical(Path(args.v17_events), Path(args.events_out))
    render_diag = diagnose_render_range(
        label="00:09-00:11 v17 render window",
        render_start=9.0,
        render_end=11.0,
        segments=segments,
        speech_regions=speech_regions,
    )
    audit = {
        **selection["audit"],
        "base_plan": str(plan_path),
        "output_plan": args.out_plan,
        "combined_speech_source": args.combined_speech,
        "words_source": args.words,
        "v17_deadtime_audit_source": args.v17_deadtime_audit,
        "old_plan_duration_seconds": old_duration,
        "new_plan_duration_seconds": new_duration,
        "total_trimmed_seconds": round(old_duration - new_duration, 3),
        "clamps": clamps_with_render,
        "tail_examples": tail_examples,
        "tail_example_count": len(tail_examples),
        "rejected": selection["rejected"],
        "zoom_events_copy": zoom_copy,
        "render_0009_0011_equivalent": render_diag,
    }

    write_json(Path(args.out_plan), out_plan)
    write_json(Path(args.audit_json), audit)
    write_json(Path(args.tail_list_json), tail_examples)
    write_tail_report(Path(args.audit_txt), audit)

    print(f"output_plan={args.out_plan}")
    print(f"old_plan_duration_seconds={old_duration}")
    print(f"new_plan_duration_seconds={new_duration}")
    print(f"tail_clamp_count={len(clamps_with_render)}")
    print(f"trimmed_seconds={round(old_duration - new_duration, 3)}")
    print(f"removed_speech_seconds={selection['audit']['removed_speech_seconds']}")
    print(f"zoom_events_byte_identical_to_v17={zoom_copy['byte_identical']}")
    print(f"audit={args.audit_txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
