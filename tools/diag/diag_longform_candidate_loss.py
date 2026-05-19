from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from core.highlight_selector import HighlightSelector
from core.edit_signal_extractor import EditSignalExtractor
from core.longform_timeline_builder import (
    LONGFORM_PRIMARY_SCORE_FLOOR,
    LongformTimelineBuilder,
    YOUTUBE_MIN_DURATION,
)
from models.analysis_result import AnalysisResult
from models.edit_signal import EditSignal
from models.job import Job
from shared.enums import ChannelType, TargetFormat


JOB_JSON = Path("exports/gaming_main/job_0c140762248f/job.json")
REPORT_TXT = Path("tools/diag/diag_longform_candidate_loss_report.txt")


def _duration(start: float, end: float) -> float:
    return max(0.0, float(end) - float(start))


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "sum": 0.0, "min": 0.0, "median": 0.0, "avg": 0.0, "max": 0.0}
    return {
        "count": len(values),
        "sum": round(sum(values), 3),
        "min": round(min(values), 3),
        "median": round(statistics.median(values), 3),
        "avg": round(sum(values) / len(values), 3),
        "max": round(max(values), 3),
    }


def _buckets(values: list[float]) -> dict[str, int]:
    return {
        "lt_3s": sum(1 for value in values if value < 3.0),
        "3_to_8s": sum(1 for value in values if 3.0 <= value < 8.0),
        "8_to_15s": sum(1 for value in values if 8.0 <= value < 15.0),
        "15_to_30s": sum(1 for value in values if 15.0 <= value < 30.0),
        "gt_30s": sum(1 for value in values if value >= 30.0),
    }


def _overlap_ratio(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    overlap_start = max(start_a, start_b)
    overlap_end = min(end_a, end_b)
    if overlap_end <= overlap_start:
        return 0.0
    overlap = overlap_end - overlap_start
    shorter = max(0.001, min(end_a - start_a, end_b - start_b))
    return overlap / shorter


def _as_edit_signal(raw: dict[str, Any]) -> EditSignal | None:
    start = raw.get("start_time", raw.get("start_seconds", raw.get("start")))
    end = raw.get("end_time", raw.get("end_seconds", raw.get("end")))
    duration = raw.get("duration_seconds", raw.get("duration"))
    center = raw.get("center_seconds", raw.get("time_seconds"))

    if start is None and end is None and center is not None and duration is not None:
        start = float(center) - (float(duration) / 2.0)
        end = float(center) + (float(duration) / 2.0)
    elif start is not None and end is None and duration is not None:
        end = float(start) + float(duration)
    elif start is None and end is not None and duration is not None:
        start = float(end) - float(duration)

    if start is None or end is None:
        return None

    start_f = float(start)
    end_f = float(end)
    if end_f <= start_f:
        return None

    signal_type = raw.get("signal_type") or raw.get("type") or "unknown"
    strength = raw.get("strength", raw.get("signal_score", raw.get("score", 0.0)))

    tags = raw.get("tags")
    if tags is None:
        tags = []
    if not isinstance(tags, list):
        tags = [str(tags)]

    notes = raw.get("notes")
    if notes is None:
        notes = []
    if not isinstance(notes, list):
        notes = [str(notes)]

    return EditSignal(
        signal_id=str(raw.get("signal_id") or raw.get("id") or raw.get("candidate_id") or "diag_signal"),
        job_id=str(raw.get("job_id") or "job_0c140762248f"),
        start_time=start_f,
        end_time=end_f,
        signal_type=str(signal_type),
        strength=float(strength or 0.0),
        confidence=float(raw.get("confidence", 0.0) or 0.0),
        tags=tags,
        source=raw.get("source"),
        notes=notes,
        metadata=raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
    )


def _find_signal_dicts(data: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = data.get("unified_edit_signals")
    if isinstance(candidates, list) and candidates:
        return candidates

    report = data.get("unified_edit_signal_report")
    if isinstance(report, dict):
        signals = report.get("signals")
        if isinstance(signals, list) and signals:
            return signals

    raise RuntimeError("No unified edit signals found in job.json")


def _find_analysis(data: dict[str, Any]) -> AnalysisResult:
    duration = (
        data.get("duration_seconds")
        or data.get("analysis_result", {}).get("duration_seconds")
        or data.get("analysis", {}).get("duration_seconds")
        or 1018.0
    )
    return AnalysisResult(
        job_id=data.get("job_id", "job_0c140762248f"),
        duration_seconds=float(duration),
        file_size_bytes=int(data.get("file_size_bytes") or 0),
        usable_for_shorts=True,
        usable_for_longform=True,
        analysis_confidence=1.0,
        notes=["read-only p2-fix-3c diagnosis"],
    )


def _find_job(data: dict[str, Any]) -> Job:
    job = Job.from_dict(data) if hasattr(Job, "from_dict") else Job(**data)
    job.channel_type = ChannelType.GAMING_MAIN
    job.target_format = TargetFormat.LONGFORM
    return job


def _score_for_longform(
    builder: LongformTimelineBuilder,
    candidate,
    weak_zones,
) -> dict[str, Any]:
    selection_score, notes = builder._score_candidate_for_longform(candidate, weak_zones)
    return {
        "candidate": candidate,
        "selection_score": selection_score,
        "notes": list(notes),
    }


def _simulate_dedupe(
    builder: LongformTimelineBuilder,
    scored_candidates: list[dict[str, Any]],
    reserve_candidates: list[dict[str, Any]],
    *,
    target_duration: float,
    max_segments: int,
    duration_floor: float,
) -> dict[str, Any]:
    selected: list[dict[str, Any]] = []
    selected_duration = 0.0
    reject_counts = Counter()
    reject_seconds = Counter()
    reserve_used = 0
    max_segments_cap_hit = False

    def sort_key(item: dict[str, Any]) -> tuple[float, float, float]:
        candidate = item["candidate"]
        return (-item["selection_score"], candidate.start_time, candidate.end_time)

    def try_add(item: dict[str, Any], pool: str) -> tuple[bool, str, float, float]:
        candidate = item["candidate"]
        original_start = float(candidate.start_time)
        original_end = float(candidate.end_time)
        original_duration = _duration(original_start, original_end)

        if "heavy_weak_zone_penalty" in item["notes"]:
            return False, "heavy_weak_zone_penalty", original_duration, 0.0

        work_start = original_start
        work_end = original_end

        for existing in selected:
            existing_cand = existing["candidate"]
            ratio = _overlap_ratio(
                work_start,
                work_end,
                existing_cand.start_time,
                existing_cand.end_time,
            )
            if ratio >= 0.70:
                return False, "overlap_ge_0_70", original_duration, 0.0

        trimmed_any = False
        for existing in selected:
            existing_cand = existing["candidate"]
            if work_end > existing_cand.start_time and work_start < existing_cand.end_time:
                if work_start < existing_cand.end_time:
                    work_start = float(existing_cand.end_time)
                    trimmed_any = True

                    if work_end <= work_start:
                        return False, "trim_invalid", original_duration, 0.0
                    if work_end - work_start < 3.0:
                        return False, "trim_lt_3s", original_duration, 0.0

        added_duration = _duration(work_start, work_end)
        if added_duration < 3.0:
            return False, "added_duration_lt_3s", original_duration, 0.0

        # Keep the same mutation semantics as current builder, but only inside this script's objects.
        candidate.start_time = work_start
        candidate.end_time = work_end
        selected.append(item)

        if trimmed_any:
            reject_seconds["trimmed_seconds_kept_segment"] += round(original_duration - added_duration, 3)

        return True, "selected", original_duration, added_duration

    for item in sorted(scored_candidates, key=sort_key):
        ok, reason, original_duration, added_duration = try_add(item, "primary")
        if not ok:
            reject_counts[reason] += 1
            reject_seconds[reason] += original_duration
            continue

        selected_duration += added_duration
        floor_reached = selected_duration >= duration_floor
        normal_target_reached = selected_duration >= target_duration * 0.92
        segment_cap_reached = len(selected) >= max_segments
        if segment_cap_reached:
            max_segments_cap_hit = True

        if floor_reached and (normal_target_reached or segment_cap_reached):
            break

    if selected_duration < duration_floor:
        for item in sorted(reserve_candidates, key=sort_key):
            ok, reason, original_duration, added_duration = try_add(item, "reserve")
            if not ok:
                reject_counts[f"reserve_{reason}"] += 1
                reject_seconds[f"reserve_{reason}"] += original_duration
                continue

            selected_duration += added_duration
            reserve_used += 1
            if selected_duration >= duration_floor:
                break

    selected_ids = {id(item) for item in selected}
    unused_primary = [item for item in scored_candidates if id(item) not in selected_ids]
    unused_reserve = [item for item in reserve_candidates if id(item) not in selected_ids]

    return {
        "selected": selected,
        "selected_count": len(selected),
        "selected_duration": round(selected_duration, 3),
        "reject_counts": dict(reject_counts),
        "reject_seconds": {key: round(value, 3) for key, value in reject_seconds.items()},
        "reserve_used": reserve_used,
        "unused_primary_count": len(unused_primary),
        "unused_reserve_count": len(unused_reserve),
        "unused_primary_seconds": round(sum(_duration(i["candidate"].start_time, i["candidate"].end_time) for i in unused_primary), 3),
        "unused_reserve_seconds": round(sum(_duration(i["candidate"].start_time, i["candidate"].end_time) for i in unused_reserve), 3),
        "max_segments_cap_hit": max_segments_cap_hit,
    }


def _coverage_seconds(candidates: list[Any]) -> float:
    ranges = sorted((float(c.start_time), float(c.end_time)) for c in candidates if c.end_time > c.start_time)
    if not ranges:
        return 0.0

    merged: list[list[float]] = []
    for start, end in ranges:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    return round(sum(end - start for start, end in merged), 3)


def main() -> int:
    lines: list[str] = []

    def out(line: str = "") -> None:
        print(line)
        lines.append(line)

    out(f"[DIAG] loading {JOB_JSON}")
    with JOB_JSON.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    job = _find_job(data)
    analysis = _find_analysis(data)
    # Wichtig: Die echte Pipeline nutzt hier NICHT unified_edit_signals,
    # sondern EditSignalExtractor().extract(job, analysis_result).
    # unified_edit_signals sind Review-/Audit-Signale und liefern fuer
    # HighlightSelector nicht die erwarteten audio_peak/audio_activity/
    # motion_peak/motion_activity Seed-Typen.
    raw_path = Path(str(job.raw_video_path))
    if raw_path.exists():
        print("[DIAG] recomputing legacy edit signals via EditSignalExtractor")
        edit_signals = EditSignalExtractor().extract(job, analysis)
        skipped_signal_dicts = 0
        edit_signal_source = "EditSignalExtractor.recomputed"
    else:
        print("[DIAG] raw video missing, falling back to serialized signal-like lists")
        signal_dicts = _find_signal_dicts(data)
        edit_signals = []
        skipped_signal_dicts = 0
        for item in signal_dicts:
            signal = _as_edit_signal(item)
            if signal is None:
                skipped_signal_dicts += 1
                continue
            edit_signals.append(signal)
        edit_signal_source = "serialized_signal_fallback"

    selector = HighlightSelector()
    highlight_result = selector.select(job, analysis, edit_signals)
    highlights = list(highlight_result["highlight_candidates"])
    weak_zones = list(highlight_result["weak_zones"])

    builder = LongformTimelineBuilder()
    scored: list[dict[str, Any]] = []
    reserve: list[dict[str, Any]] = []

    for candidate in highlights:
        item = _score_for_longform(builder, candidate, weak_zones)
        if item["selection_score"] < LONGFORM_PRIMARY_SCORE_FLOOR:
            item["notes"] = list(item["notes"]) + ["duration_floor_reserve"]
            reserve.append(item)
        else:
            scored.append(item)

    target_pool = scored or reserve
    target_duration = builder._build_target_duration(analysis.duration_seconds, target_pool)
    calculated_max = int(target_duration / 10.0)
    max_segments = max(12, min(100, calculated_max))

    raw_durations = [_duration(c.start_time, c.end_time) for c in highlights]
    primary_durations = [_duration(i["candidate"].start_time, i["candidate"].end_time) for i in scored]
    reserve_durations = [_duration(i["candidate"].start_time, i["candidate"].end_time) for i in reserve]

    sim = _simulate_dedupe(
        builder,
        scored,
        reserve,
        target_duration=target_duration,
        max_segments=max_segments,
        duration_floor=YOUTUBE_MIN_DURATION,
    )

    out("=== P2-FIX-3C DIAGNOSIS ===")
    out(f"job_id={job.job_id}")
    out(f"analysis_duration_seconds={analysis.duration_seconds}")
    out(f"edit_signal_source={edit_signal_source}")
    out(f"edit_signals={len(edit_signals)}")
    out(f"skipped_signal_dicts_without_valid_time={skipped_signal_dicts}")
    signal_type_counts = Counter(signal.signal_type for signal in edit_signals)
    out(f"edit_signal_type_counts={dict(signal_type_counts)}")
    out(f"highlight_candidates_before_scoring={len(highlights)}")
    out(f"weak_zones={len(weak_zones)}")
    out(f"primary_candidates={len(scored)}")
    out(f"reserve_candidates={len(reserve)}")
    out(f"target_duration={target_duration:.3f}")
    out(f"max_segments={max_segments}")
    out("")

    out("=== QUESTION 1: CANDIDATE INVENTORY ===")
    out(f"raw_duration_stats={_stats(raw_durations)}")
    out(f"raw_duration_buckets={_buckets(raw_durations)}")
    out(f"raw_sum_with_overlaps={sum(raw_durations):.3f}")
    out(f"raw_unique_coverage_seconds={_coverage_seconds(highlights):.3f}")
    out(f"primary_duration_stats={_stats(primary_durations)}")
    out(f"reserve_duration_stats={_stats(reserve_durations)}")
    out("")

    out("=== QUESTION 2: TRY_ADD LOSSES ===")
    total_candidates = len(scored) + len(reserve)
    out(f"selected_count={sim['selected_count']}")
    out(f"selected_duration={sim['selected_duration']:.3f}")
    out(f"reserve_used={sim['reserve_used']}")
    out(f"unused_primary_count={sim['unused_primary_count']}")
    out(f"unused_reserve_count={sim['unused_reserve_count']}")
    out(f"max_segments_cap_hit={sim['max_segments_cap_hit']}")
    for reason, count in sorted(sim["reject_counts"].items()):
        pct = (count / total_candidates * 100.0) if total_candidates else 0.0
        seconds = sim["reject_seconds"].get(reason, 0.0)
        out(f"reject reason={reason} count={count} pct={pct:.2f}% seconds={seconds:.3f}")
    out("")

    out("=== QUESTION 3: WHERE DID SECONDS GO ===")
    raw_sum = sum(raw_durations)
    selected_duration = float(sim["selected_duration"])
    lost = raw_sum - selected_duration
    out(f"sum_candidate_durations_before_dedup={raw_sum:.3f}")
    out(f"sum_selected_durations_after_dedup={selected_duration:.3f}")
    out(f"lost_seconds_total={lost:.3f}")
    out(f"lost_pct_vs_raw_sum={(lost / raw_sum * 100.0) if raw_sum else 0.0:.2f}%")
    out(f"unused_primary_seconds={sim['unused_primary_seconds']:.3f}")
    out(f"unused_reserve_seconds={sim['unused_reserve_seconds']:.3f}")
    for reason, seconds in sorted(sim["reject_seconds"].items()):
        out(f"lost_by_reason {reason} seconds={seconds:.3f}")
    out("")

    out("=== ROOT CAUSE DECISION ===")
    unique_coverage = _coverage_seconds(highlights)
    heavy_count = sim["reject_counts"].get("heavy_weak_zone_penalty", 0)
    overlap_count = sim["reject_counts"].get("overlap_ge_0_70", 0)
    trim_count = (
        sim["reject_counts"].get("trim_invalid", 0)
        + sim["reject_counts"].get("trim_lt_3s", 0)
        + sim["reject_counts"].get("added_duration_lt_3s", 0)
    )

    if heavy_count > total_candidates * 0.50:
        out("root_cause=Heavy weak-zone penalty ist der Hauptverlust.")
        out(
            "root_cause_detail="
            f"{heavy_count}/{total_candidates} Kandidaten "
            f"({heavy_count / total_candidates * 100.0:.2f}%) "
            "werden wegen heavy_weak_zone_penalty verworfen."
        )
        out("next_fix_area=Weak-zone-Erkennung oder Anwendung der heavy_weak_zone_penalty im Longform-Scoring untersuchen.")
    elif unique_coverage < YOUTUBE_MIN_DURATION:
        out("root_cause=Highlight-Erkennung erzeugt weniger als 480s unique Coverage.")
        out("next_fix_area=Highlight-Erkennung / Kandidaten-Coverage erweitern.")
    elif overlap_count > total_candidates * 0.35:
        out("root_cause=Overlap-Dedup ist zu aggressiv.")
        out("next_fix_area=Overlap-Schwelle oder Kandidaten-Clustering untersuchen.")
    elif trim_count > total_candidates * 0.20:
        out("root_cause=Trim-Stufe macht zu viele Kandidaten unbrauchbar.")
        out("next_fix_area=Trim-/Segment-Erweiterung untersuchen.")
    else:
        out("root_cause=Gemischter Befund; Details siehe Verlusttabelle.")
        out("next_fix_area=Mehrere Verlustquellen gemeinsam untersuchen.")

    REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out(f"[DIAG] report_written={REPORT_TXT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
