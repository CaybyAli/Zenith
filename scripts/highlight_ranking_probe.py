from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.highlight_ranking import (
    HighlightRankingConfig,
    normalize_intervals,
    rank_highlight_segments,
)
from core.video_config import normalize_protected_ranges, read_video_config


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _find_segment_container(plan: Any) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    candidate_keys = (
        "timeline_segments",
        "segments",
        "selected_segments",
        "final_segments",
        "clips",
        "timeline",
    )

    def looks_like_segments(value: Any) -> bool:
        if not isinstance(value, list) or not value:
            return False

        first = value[0]
        if not isinstance(first, dict):
            return False

        has_start = any(key in first for key in ("start_seconds", "start", "start_time"))
        has_end = any(key in first for key in ("end_seconds", "end", "end_time"))

        return has_start and has_end

    if isinstance(plan, dict):
        for key in candidate_keys:
            value = plan.get(key)
            if looks_like_segments(value):
                return plan, key, value

        for key, value in plan.items():
            if looks_like_segments(value):
                return plan, key, value

        for value in plan.values():
            if isinstance(value, dict):
                try:
                    return _find_segment_container(value)
                except ValueError:
                    pass

    raise ValueError("No segment list found in plan JSON")


def _write_report(
    report_path: Path,
    audit: dict[str, Any],
    *,
    output_plan_path: Path,
    pytest_output_path: Path,
) -> None:
    lines: list[str] = []

    lines.append("PROJECT ZENITH - HIGHLIGHT RANKING + BUDGET REPORT")
    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"- session_seconds={audit['session_seconds']}")
    lines.append(f"- target_seconds={audit['target_seconds']}")
    lines.append(f"- max_allowed_seconds={audit['max_allowed_seconds']}")
    lines.append(f"- input_segment_count={audit['input_segment_count']}")
    lines.append(f"- kept_segment_count={audit['kept_segment_count']}")
    lines.append(f"- dropped_segment_count={audit['dropped_segment_count']}")
    lines.append(f"- input_duration_seconds={audit['input_duration_seconds']}")
    lines.append(f"- final_duration_seconds={audit['final_duration_seconds']}")
    lines.append("")
    lines.append("CONFIG")
    for key, value in audit["config"].items():
        lines.append(f"- {key}={value}")
    lines.append("")
    lines.append("GLOBAL AUDIO")
    for key, value in audit["global_audio"].items():
        lines.append(f"- {key}={value}")
    lines.append("")
    lines.append("HARTE CHECKS")
    hard = audit["hard_checks"]
    lines.append(f"- final_duration <= target+10%: {hard['duration_within_budget_plus_10_percent']}")
    lines.append(f"- final_duration >= 480s: {hard['duration_at_least_480_seconds']}")
    lines.append(f"- combat_range_kept: {hard['combat_range_kept']}")
    lines.append(f"- payoff_range_kept: {hard['payoff_range_kept']}")
    lines.append(f"- no_mid_segment_cut: {hard['no_mid_segment_cut']}")
    lines.append("")
    lines.append("LATE LOBBY STATUS")
    for item in hard["late_lobby_status"]:
        lines.append(
            f"- {item['name']} target={item['target']} "
            f"matched={item.get('matched_segment')} kept={item.get('kept')} "
            f"status={item.get('status')} score={item.get('importance_score')} "
            f"rank={item.get('rank')} reason={item.get('keep_reason')}"
        )

    lines.append("")
    lines.append("RANKING TABLE")
    lines.append(
        "rank | kept | reason | range | dur | reaction | audio_prom | speech_eng | importance | selection"
    )

    for row in sorted(audit["ranked_rows"], key=lambda item: (item.get("rank") or 9999, item["start_seconds"])):
        lines.append(
            f"{row['rank']} | "
            f"{'JA' if row['kept'] else 'NEIN'} | "
            f"{row['keep_reason']} | "
            f"{row['start_seconds']}->{row['end_seconds']} | "
            f"{row['duration_seconds']} | "
            f"{row['reaction_max']} | "
            f"{row['audio_peak_prominence']} | "
            f"{row['speech_engagement']} | "
            f"{row['importance_score']} | "
            f"{row['selection_score']}"
        )

    lines.append("")
    lines.append("OUTPUT SEGMENTS")
    for segment in audit["output_segments"]:
        lines.append(
            f"- {segment['segment_id']} {segment['start_seconds']}->{segment['end_seconds']} "
            f"dur={segment['duration_seconds']}"
        )

    lines.append("")
    lines.append("PYTEST OUTPUT")
    if pytest_output_path.exists():
        lines.append(pytest_output_path.read_text(encoding="utf-8", errors="replace"))
    else:
        lines.append("MISSING_PYTEST_OUTPUT")

    lines.append("")
    lines.append("OUTPUT")
    lines.append(f"- output_plan={output_plan_path}")
    lines.append(f"- report={report_path}")
    lines.append("")
    lines.append("STOPP: Kein Commit.")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default="reports/content_gap_protector_fix/content_gap_protector_fix_final_editorial_plan.json")
    parser.add_argument("--raw-windows", default="reports/dead_air_1/fortnite_g6_raw_windows_for_dead_air_1.json")
    parser.add_argument("--speech", default="reports/combined_speech/combined_speech_regions.json")
    parser.add_argument("--reactions", default="reports/reaction_adaptive/reaction_adaptive_fortnite_reactions.json")
    parser.add_argument("--out-dir", default="reports/highlight_ranking")
    parser.add_argument("--pytest-output", default="reports/highlight_ranking/pytest_highlight_ranking.txt")
    parser.add_argument("--video-config", default="video_configs/fortnite_v18_legacy_fixture.json")
    parser.add_argument("--target-seconds", type=float, default=None)
    args = parser.parse_args(argv)

    plan_path = Path(args.plan)
    raw_path = Path(args.raw_windows)
    speech_path = Path(args.speech)
    reactions_path = Path(args.reactions)
    out_dir = Path(args.out_dir)
    pytest_output_path = Path(args.pytest_output)
    out_dir.mkdir(parents=True, exist_ok=True)

    required = [plan_path, raw_path, speech_path, reactions_path]
    missing = [str(path) for path in required if not path.exists()]

    if missing:
        print("STOPP: Missing required inputs")
        for path in missing:
            print(f"MISSING: {path}")
        return 2

    source_plan = _read_json(plan_path)
    output_plan = deepcopy(source_plan)

    _, _, source_segments = _find_segment_container(source_plan)
    output_parent, output_key, _ = _find_segment_container(output_plan)

    raw_windows = normalize_intervals(_read_json(raw_path), source="raw_action_window")
    speech_regions = normalize_intervals(_read_json(speech_path), source="combined_speech")
    reactions = normalize_intervals(_read_json(reactions_path), source="reaction")
    protected_ranges = normalize_protected_ranges(read_video_config(args.video_config))

    output_segments, audit = rank_highlight_segments(
        content_segments=source_segments,
        raw_windows=raw_windows,
        reactions=reactions,
        combined_speech_regions=speech_regions,
        target_seconds=args.target_seconds,
        config=HighlightRankingConfig(protected_ranges=protected_ranges),
    )

    output_parent[output_key] = output_segments
    output_plan["highlight_ranking_audit"] = {
        key: value
        for key, value in audit.items()
        if key not in {"ranked_rows", "output_segments"}
    }
    output_plan["highlight_ranking_rows"] = audit["ranked_rows"]

    duration_contract = output_plan.get("duration_contract")
    if not isinstance(duration_contract, dict):
        duration_contract = {}
    duration_contract["highlight_ranking_output_duration_seconds"] = audit["final_duration_seconds"]
    duration_contract["highlight_ranking_target_seconds"] = audit["target_seconds"]
    output_plan["duration_contract"] = duration_contract

    output_plan_path = out_dir / "highlight_ranking_final_editorial_plan.json"
    report_path = out_dir / "highlight_ranking_report.txt"
    audit_path = out_dir / "highlight_ranking_audit.json"
    ranked_rows_path = out_dir / "highlight_ranking_rows.json"

    _write_json(output_plan_path, output_plan)
    _write_json(audit_path, audit)
    _write_json(ranked_rows_path, audit["ranked_rows"])
    _write_report(
        report_path,
        audit,
        output_plan_path=output_plan_path,
        pytest_output_path=pytest_output_path,
    )

    hard = audit["hard_checks"]
    late_statuses = hard["late_lobby_status"]
    late_dropped_count = len([item for item in late_statuses if item.get("status") == "NEIN"])

    overall_pass = (
        hard["duration_within_budget_plus_10_percent"] == "JA"
        and hard["duration_at_least_480_seconds"] == "JA"
        and hard["combat_range_kept"]["status"] == "JA"
        and hard["payoff_range_kept"]["status"] == "JA"
        and hard["no_mid_segment_cut"] == "JA"
    )

    print("PROJECT ZENITH - HIGHLIGHT RANKING + BUDGET")
    print(f"output_plan={output_plan_path}")
    print(f"report={report_path}")
    print(f"audit={audit_path}")
    print(f"session_seconds={audit['session_seconds']}")
    print(f"target_seconds={audit['target_seconds']}")
    print(f"max_allowed_seconds={audit['max_allowed_seconds']}")
    print(f"input_duration_seconds={audit['input_duration_seconds']}")
    print(f"final_duration_seconds={audit['final_duration_seconds']}")
    print(f"kept_segment_count={audit['kept_segment_count']}")
    print(f"dropped_segment_count={audit['dropped_segment_count']}")
    print(f"combat_range_kept={hard['combat_range_kept']['status']}")
    print(f"payoff_range_kept={hard['payoff_range_kept']['status']}")
    print(f"late_lobby_dropped_count={late_dropped_count}/{len(late_statuses)}")
    print(f"no_mid_segment_cut={hard['no_mid_segment_cut']}")
    print(f"overall_pass={overall_pass}")

    return 0 if overall_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
