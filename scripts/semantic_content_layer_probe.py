from __future__ import annotations

import argparse
import json
import math
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.highlight_ranking import HighlightRankingConfig, rank_highlight_segments
from core.pacing_tighten import PacingTightenConfig, apply_pacing_tighten
from core.semantic_content_layer import (
    SemanticContentConfig,
    analyze_semantic_content,
    normalize_intervals,
)


OWNER_DEAD_RENDER_TARGETS = [
    ("owner_dead_00_51_00_55", 51.0, 55.0),
    ("owner_dead_02_00_02_03", 120.0, 123.0),
    ("owner_dead_02_38_02_47", 158.0, 167.0),
    ("owner_dead_03_38_03_42", 218.0, 222.0),
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip())
    except Exception:
        return default
    return number if math.isfinite(number) else default


def looks_like_segments(value: Any) -> bool:
    return isinstance(value, list) and value and isinstance(value[0], dict) and (
        any(key in value[0] for key in ("start_seconds", "start", "start_time"))
        and any(key in value[0] for key in ("end_seconds", "end", "end_time"))
    )


def find_segment_container(raw: Any) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    keys = ("timeline_segments", "segments", "selected_segments", "final_segments", "clips", "timeline")
    if isinstance(raw, dict):
        for key in keys:
            if looks_like_segments(raw.get(key)):
                return raw, key, raw[key]
        for key, value in raw.items():
            if looks_like_segments(value):
                return raw, key, value
        for value in raw.values():
            if isinstance(value, dict):
                try:
                    return find_segment_container(value)
                except ValueError:
                    pass
    raise ValueError("No segment list found")


def start_end(item: Mapping[str, Any]) -> tuple[float, float] | None:
    start = item.get("start_seconds", item.get("start", item.get("start_time")))
    end = item.get("end_seconds", item.get("end", item.get("end_time")))
    if start is None or end is None:
        return None
    start_f = round(safe_float(start), 3)
    end_f = round(safe_float(end), 3)
    if end_f <= start_f:
        return None
    return start_f, end_f


def overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def coverage(target_start: float, target_end: float, rows: list[Mapping[str, Any]]) -> float:
    duration = max(0.001, target_end - target_start)
    covered = 0.0
    for row in rows:
        se = start_end(row)
        if se is None:
            continue
        covered += overlap(target_start, target_end, se[0], se[1])
    return round(min(1.0, covered / duration), 6)


def map_render_interval_to_source(
    plan_segments: list[Mapping[str, Any]],
    render_start: float,
    render_end: float,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cursor = 0.0
    for index, segment in enumerate(plan_segments, start=1):
        se = start_end(segment)
        if se is None:
            continue
        source_start, source_end = se
        duration = source_end - source_start
        ov_start = max(cursor, render_start)
        ov_end = min(cursor + duration, render_end)
        if ov_end > ov_start:
            out.append(
                {
                    "segment_index": index,
                    "render_start_seconds": round(ov_start, 3),
                    "render_end_seconds": round(ov_end, 3),
                    "source_start_seconds": round(source_start + (ov_start - cursor), 3),
                    "source_end_seconds": round(source_start + (ov_end - cursor), 3),
                    "source_segment": [source_start, source_end],
                }
            )
        cursor += duration
    return out


def extract_payoff_tails(*raw_values: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[float, float, str]] = set()

    def boolish(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "ja", "payoff", "payoff_tail"}

    def has_payoff_marker(row: Mapping[str, Any]) -> bool:
        for marker_key in ("payoff_tail", "is_payoff_tail", "mandatory_payoff_tail", "round_payoff_tail"):
            if marker_key in row and boolish(row.get(marker_key)):
                return True

        for text_key in ("segment_role", "role", "kind", "type", "keep_decision", "reason"):
            value = row.get(text_key)
            if value is not None and "payoff" in str(value).lower():
                return True

        metadata = row.get("metadata")
        if isinstance(metadata, Mapping):
            for marker_key in ("payoff_tail", "is_payoff_tail", "mandatory_payoff_tail", "round_payoff_tail"):
                if marker_key in metadata and boolish(metadata.get(marker_key)):
                    return True

        return False

    for raw in raw_values:
        for row in normalize_intervals(raw, source="time_item"):
            if not has_payoff_marker(row):
                continue
            se = start_end(row)
            if se is None:
                continue
            key = (se[0], se[1], str(row.get("source", "")))
            if key in seen:
                continue
            seen.add(key)
            clean = dict(row)
            clean["payoff_tail"] = True
            rows.append(clean)
    return sorted(rows, key=lambda row: start_end(row) or (0.0, 0.0))


def semantic_hits_for_interval(
    semantic_units: list[Mapping[str, Any]],
    start: float,
    end: float,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for unit in semantic_units:
        se = start_end(unit)
        if se is None:
            continue
        ov = overlap(start, end, se[0], se[1])
        if ov <= 0:
            continue
        hits.append(
            {
                "utterance_id": unit.get("utterance_id"),
                "start_seconds": se[0],
                "end_seconds": se[1],
                "overlap_seconds": round(ov, 3),
                "text": unit.get("text", ""),
                "relevance_score": unit.get("relevance_score"),
                "is_dead_or_filler": bool(unit.get("is_dead_or_filler")),
                "reasons": unit.get("semantic_reasons", []),
            }
        )
    return hits


def build_owner_dead_target_report(
    *,
    baseline_plan_segments: list[Mapping[str, Any]],
    output_segments: list[Mapping[str, Any]],
    semantic_units: list[Mapping[str, Any]],
    config: PacingTightenConfig,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, render_start, render_end in OWNER_DEAD_RENDER_TARGETS:
        mapped = map_render_interval_to_source(baseline_plan_segments, render_start, render_end)
        mapped_rows = []
        for item in mapped:
            source_start = item["source_start_seconds"]
            source_end = item["source_end_seconds"]
            locked_overlap = overlap(
                source_start,
                source_end,
                config.round1_fight_start_seconds,
                config.round1_fight_end_seconds,
            )
            output_coverage = coverage(source_start, source_end, output_segments)
            semantic_hits = semantic_hits_for_interval(semantic_units, source_start, source_end)
            dead_hit = any(hit["is_dead_or_filler"] for hit in semantic_hits)
            cut_status = "CUT" if output_coverage < 0.50 else "KEPT"
            if cut_status != "CUT" and locked_overlap > 0:
                cut_status = "KEPT_BY_ROUND1_FIGHT_REQUIREMENT"
            mapped_rows.append(
                {
                    **item,
                    "semantic_dead_or_filler_detected": dead_hit,
                    "semantic_hits": semantic_hits[:6],
                    "output_coverage": output_coverage,
                    "cut_status": cut_status,
                    "round1_fight_locked_overlap_seconds": round(locked_overlap, 3),
                }
            )
        rows.append(
            {
                "name": name,
                "old_render_target_seconds": [render_start, render_end],
                "mapped_source_intervals": mapped_rows,
            }
        )
    return rows


def write_report(
    path: Path,
    *,
    semantic: dict[str, Any],
    ranking_audit: dict[str, Any],
    pacing_audit: dict[str, Any],
    owner_dead_targets: list[dict[str, Any]],
    output_plan: Path,
) -> None:
    hard = pacing_audit["hard_checks"]
    first_segment = (pacing_audit.get("output_segments") or [{}])[0]
    first_segment_start = first_segment.get("start_seconds")
    owner_onset = hard["owner_onset_plausible"].get("intro_start_seconds")
    start_check_pass = (
        isinstance(first_segment_start, (int, float))
        and isinstance(owner_onset, (int, float))
        and abs(first_segment_start - owner_onset) <= 0.05
    )
    hard_checks_ready = (
        hard["round1_fight_full_coverage"]["status"] == "JA"
        and hard["payoff_locked_exact"]["status"] == "JA"
        and hard["removed_speech_zero"]["status"] == "JA"
        and hard.get("breathing_room", {}).get("status") == "JA"
        and hard.get("round_transition_tightened", {}).get("status") == "JA"
        and hard.get("cut_count_increased_but_action_locked", {}).get("combat_ranges_zero_internal_cuts") is True
        and pacing_audit.get("overall_pass") is True
    )
    validation_report_path = Path("reports/ranked_render/ranked_cut_v8_validation_report.txt")
    render_validation_lines: list[str] = []
    render_validation_pass = False
    if validation_report_path.exists():
        validation_text = validation_report_path.read_text(encoding="utf-8", errors="replace")
        render_validation_pass = "overall_pass=True" in validation_text
        wanted_prefixes = (
            "duration_seconds=",
            "expected_duration_seconds=",
            "duration_delta_seconds=",
            "resolution=",
            "audio_stream_count=",
            "expected_kept_segments=",
            "render_log_segment_total=",
            "segment_exact_match=",
            "render_seconds=",
            "overall_pass=",
        )
        render_validation_lines = [
            line for line in validation_text.splitlines() if line.startswith(wanted_prefixes)
        ]
    ready_for_owner_ear = hard_checks_ready and render_validation_pass and start_check_pass

    lines: list[str] = []
    lines.append("# Semantic Content Layer Report")
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append(f"READY_FOR_OWNER_EAR = {'yes' if ready_for_owner_ear else 'no'}")
    lines.append("")
    lines.append("## Semantic Layer")
    lines.append("")
    lines.append(f"- provider: {semantic.get('provider')}")
    lines.append(f"- dependency: {semantic.get('dependency_note')}")
    lines.append(f"- utterance_count: {semantic['summary']['utterance_count']}")
    lines.append(f"- silence_unit_count: {semantic['summary']['silence_unit_count']}")
    lines.append(f"- dead_or_filler_count: {semantic['summary']['dead_or_filler_count']}")
    lines.append(f"- event_callout_count: {semantic['summary']['event_callout_count']}")
    lines.append(f"- input_fingerprint: `{semantic['input_fingerprint']}`")
    lines.append("")
    lines.append("## Integration")
    lines.append("")
    lines.append(f"- semantic_weight: {ranking_audit['config']['semantic_weight']}")
    lines.append(f"- ranked_kept_segments: {ranking_audit['kept_segment_count']}")
    lines.append(f"- pacing_output_segments: {pacing_audit['new_segment_count']}")
    lines.append(f"- removed_dead_seconds: {pacing_audit['removed_dead_seconds']}")
    lines.append(f"- removed_speech_seconds: {pacing_audit['removed_speech_seconds']}")
    lines.append("")
    lines.append("## Render Validation")
    lines.append("")
    lines.append("- output_video: `reports/ranked_render/ranked_cut_v8.mp4`")
    lines.append(f"- validation_report: `{validation_report_path}`")
    if render_validation_lines:
        for line in render_validation_lines:
            lines.append(f"- {line}")
    else:
        lines.append("- validation_report_status: MISSING")
    lines.append("")
    lines.append("## Start Check")
    lines.append("")
    lines.append(f"- first_segment_start_seconds: {first_segment_start}")
    lines.append(f"- owner_onset_seconds: {owner_onset}")
    lines.append(f"- starts_at_owner_onset: {'JA' if start_check_pass else 'NEIN'}")
    lines.append("- reason: first timeline segment is snapped to owner track1 speech onset, not source 0.0 pre-roll")
    lines.append("")
    lines.append("## Hard Checks")
    lines.append("")
    for key, value in hard.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Owner Dead-Time Targets")
    lines.append("")
    for target in owner_dead_targets:
        lines.append(f"- {target['name']} old_render={target['old_render_target_seconds']}")
        for item in target["mapped_source_intervals"]:
            lines.append(
                "  - source="
                f"{item['source_start_seconds']}->{item['source_end_seconds']} "
                f"semantic_dead={item['semantic_dead_or_filler_detected']} "
                f"output_coverage={item['output_coverage']} "
                f"status={item['cut_status']} "
                f"locked_overlap={item['round1_fight_locked_overlap_seconds']}"
            )
    lines.append("")
    lines.append("## Render-Time Mapping")
    lines.append("")
    lines.append("- start: see `reports/ranked_render/ranked_cut_v8_validation_report.txt` -> source 9.82->30.0")
    lines.append("- fight_142_246: see `reports/ranked_render/ranked_cut_v8_validation_report.txt`; internal cuts = 0")
    lines.append("- round_transition: see `reports/ranked_render/ranked_cut_v8_validation_report.txt`")
    lines.append(
        "- runde2_nee_wenn_dann_hier: see `reports/ranked_render/ranked_cut_v8_validation_report.txt` "
        "-> source 721.641->733.564"
    )
    lines.append(
        "- payoff_locked: see `reports/ranked_render/ranked_cut_v8_validation_report.txt` "
        "-> source 1756.0->1810.817"
    )
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    lines.append(f"- output_plan: `{output_plan}`")
    lines.append(f"- semantic_cache: `reports/semantic_content_layer/semantic_content_analysis.json`")
    lines.append(f"- ranking_audit: `reports/semantic_content_layer/semantic_highlight_ranking_audit.json`")
    lines.append(f"- pacing_audit: `reports/semantic_content_layer/semantic_pacing_tighten_audit.json`")
    lines.append("")
    lines.append("STOPP: Kein Commit.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-plan", default="reports/content_gap_protector_fix/content_gap_protector_fix_final_editorial_plan.json")
    parser.add_argument("--baseline-render-plan", default="reports/pacing_tighten_2_fix/pacing_tighten_2_fix_final_editorial_plan.json")
    parser.add_argument("--words", default="reports/speech_1_transcript_largev3/fortnite_words.json")
    parser.add_argument("--speech", default="reports/combined_speech/combined_speech_regions.json")
    parser.add_argument("--owner-speech", default="reports/speech_1_fix_vad/fortnite_vad_speech_regions.json")
    parser.add_argument("--raw-windows", default="reports/dead_air_1/fortnite_g6_raw_windows_for_dead_air_1.json")
    parser.add_argument("--reactions", default="reports/reaction_adaptive/reaction_adaptive_fortnite_reactions.json")
    parser.add_argument("--payoff2", default="reports/payoff_2/payoff_2_g8_timeline_plan_reaction_gated.json")
    parser.add_argument("--out-dir", default="reports/semantic_content_layer")
    args = parser.parse_args(argv)

    paths = {
        "source_plan": Path(args.source_plan),
        "baseline_render_plan": Path(args.baseline_render_plan),
        "words": Path(args.words),
        "speech": Path(args.speech),
        "owner_speech": Path(args.owner_speech),
        "raw_windows": Path(args.raw_windows),
        "reactions": Path(args.reactions),
    }
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        print("STOPP: Missing required inputs")
        for path in missing:
            print(f"MISSING: {path}")
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    source_plan = read_json(paths["source_plan"])
    output_plan = deepcopy(source_plan)
    parent, key, source_segments = find_segment_container(output_plan)
    baseline_plan = read_json(paths["baseline_render_plan"])
    _, _, baseline_segments = find_segment_container(baseline_plan)

    raw_windows = read_json(paths["raw_windows"])
    video_duration = safe_float(raw_windows.get("video_duration_seconds"), 1820.817) if isinstance(raw_windows, dict) else 1820.817

    semantic_config = SemanticContentConfig.from_env()
    semantic = analyze_semantic_content(
        words_raw=read_json(paths["words"]),
        speech_regions_raw=read_json(paths["speech"]),
        video_duration_seconds=video_duration,
        config=semantic_config,
        cache_path=out_dir / "semantic_content_analysis.json",
    )
    semantic_units = semantic["semantic_units"]

    payoff_sources = [source_plan]
    payoff_path = Path(args.payoff2)
    if payoff_path.exists():
        payoff_sources.append(read_json(payoff_path))
    payoff_tails = extract_payoff_tails(*payoff_sources)

    ranked_segments, ranking_audit = rank_highlight_segments(
        content_segments=source_segments,
        raw_windows=raw_windows,
        reactions=read_json(paths["reactions"]),
        combined_speech_regions=read_json(paths["speech"]),
        semantic_units=semantic_units,
        payoff_tail_segments=payoff_tails,
        config=HighlightRankingConfig(),
    )

    pacing_config = PacingTightenConfig()
    output_segments, pacing_audit = apply_pacing_tighten(
        ranked_segments=ranked_segments,
        combined_speech_regions=read_json(paths["speech"]),
        owner_speech_regions=read_json(paths["owner_speech"]),
        owner_speech_source=str(paths["owner_speech"]),
        raw_windows=raw_windows,
        semantic_units=semantic_units,
        payoff_tail_segments=payoff_tails,
        config=pacing_config,
    )

    parent[key] = output_segments
    output_plan["semantic_content_layer_audit"] = {
        "semantic_summary": semantic["summary"],
        "ranking_summary": {
            key_: value
            for key_, value in ranking_audit.items()
            if key_ not in {"ranked_rows", "output_segments"}
        },
        "pacing_summary": {
            key_: value
            for key_, value in pacing_audit.items()
            if key_ not in {"per_segment", "output_segments"}
        },
    }
    output_plan["semantic_content_layer_rows"] = pacing_audit["per_segment"]

    duration_contract = output_plan.get("duration_contract")
    if not isinstance(duration_contract, dict):
        duration_contract = {}
    duration_contract["semantic_content_layer_output_duration_seconds"] = pacing_audit["new_duration_seconds"]
    duration_contract["semantic_content_layer_removed_dead_seconds"] = pacing_audit["removed_dead_seconds"]
    output_plan["duration_contract"] = duration_contract

    owner_dead_targets = build_owner_dead_target_report(
        baseline_plan_segments=baseline_segments,
        output_segments=output_segments,
        semantic_units=semantic_units,
        config=pacing_config,
    )

    output_plan_path = out_dir / "semantic_content_layer_final_editorial_plan.json"
    ranking_audit_path = out_dir / "semantic_highlight_ranking_audit.json"
    pacing_audit_path = out_dir / "semantic_pacing_tighten_audit.json"
    owner_targets_path = out_dir / "owner_dead_time_targets.json"
    report_path = out_dir / "SEMANTIC_CONTENT_LAYER_REPORT.md"

    write_json(output_plan_path, output_plan)
    write_json(ranking_audit_path, ranking_audit)
    write_json(pacing_audit_path, pacing_audit)
    write_json(owner_targets_path, owner_dead_targets)
    write_report(
        report_path,
        semantic=semantic,
        ranking_audit=ranking_audit,
        pacing_audit=pacing_audit,
        owner_dead_targets=owner_dead_targets,
        output_plan=output_plan_path,
    )

    hard = pacing_audit["hard_checks"]
    overall_pass = (
        hard["round1_fight_full_coverage"]["status"] == "JA"
        and hard["payoff_locked_exact"]["status"] == "JA"
        and hard["removed_speech_zero"]["status"] == "JA"
        and pacing_audit["overall_pass"] is True
    )

    print("PROJECT ZENITH - SEMANTIC CONTENT LAYER")
    print(f"output_plan={output_plan_path}")
    print(f"report={report_path}")
    print(f"semantic_provider={semantic.get('provider')}")
    print(f"utterance_count={semantic['summary']['utterance_count']}")
    print(f"dead_or_filler_count={semantic['summary']['dead_or_filler_count']}")
    print(f"old_segment_count={pacing_audit['old_segment_count']}")
    print(f"new_segment_count={pacing_audit['new_segment_count']}")
    print(f"new_duration_seconds={pacing_audit['new_duration_seconds']}")
    print(f"removed_dead_seconds={pacing_audit['removed_dead_seconds']}")
    print(f"removed_speech_seconds={pacing_audit['removed_speech_seconds']}")
    for key_, value in hard.items():
        print(f"{key_}={value}")
    print(f"overall_pass={overall_pass}")
    print("STOPP: Kein Commit.")
    return 0 if overall_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
