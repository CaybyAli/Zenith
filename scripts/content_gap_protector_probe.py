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

from core.content_gap_protector import (
    ContentGapProtectorConfig,
    normalize_intervals,
    protect_content_gaps,
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


def _short_state(row: dict[str, Any]) -> str:
    states = row.get("g6_states") or []
    values = sorted(set(str(item.get("state") or "") for item in states))

    if not values:
        return "NO_G6_STATE"

    text = " / ".join(values)

    if len(text) > 130:
        return text[:127] + "..."

    return text


def _write_report(report_path: Path, audit: dict[str, Any], *, output_plan_path: Path, pytest_output_path: Path | None) -> None:
    lines: list[str] = []

    lines.append("PROJECT ZENITH - CONTENT-GAP-PROTECTOR-FIX REPORT")
    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"- old_plan_duration_seconds={audit['old_plan_duration_seconds']}")
    lines.append(f"- new_plan_duration_seconds={audit['new_plan_duration_seconds']}")
    lines.append(f"- duration_delta_seconds={audit['duration_delta_seconds']}")
    lines.append(f"- gap_count={audit['gap_count']}")
    lines.append(f"- content_gap_count={audit['content_gap_count']}")
    lines.append(f"- dead_gap_count={audit['dead_gap_count']}")
    lines.append(f"- re_included_gap_count={audit['reincluded_gap_count']}")
    lines.append(f"- old_kept_speech_seconds={audit['old_kept_speech_seconds']}")
    lines.append(f"- new_kept_speech_seconds={audit['new_kept_speech_seconds']}")
    lines.append(f"- kept_speech_not_lost={audit['kept_speech_not_lost']}")
    lines.append(f"- anti_overcut_fail_count={audit['anti_overcut_fail_count']}")
    lines.append("")
    lines.append("CONFIG")
    for key, value in audit["config"].items():
        lines.append(f"- {key}={value}")
    lines.append("")
    lines.append("METRIC DISCOVERY")
    lines.append(f"- audio_keys={audit['metric_discovery']['audio_keys']}")
    lines.append(f"- audio_floor_key={audit['metric_discovery']['audio_floor_key']}")
    lines.append(f"- audio_floor={audit['metric_discovery']['audio_floor']}")
    lines.append(f"- motion_keys_report_only={audit['metric_discovery']['motion_keys_report_only']}")
    lines.append(f"- motion_primary_allowed={audit['metric_discovery']['motion_primary_allowed']}")
    lines.append("")
    lines.append("HARTE PRUEFUNG")
    hard = audit["hard_checks"]
    lines.append(
        "- combat_content_gaps_reincluded="
        f"{hard['combat_content_gaps_reincluded']['status']} "
        f"{hard['combat_content_gaps_reincluded']}"
    )
    lines.append(
        "- within_round_gap_120_133_6_content="
        f"{hard['within_round_gap_120_133_6_content']['status']} "
        f"{hard['within_round_gap_120_133_6_content']}"
    )
    lines.append(
        "- late_round_dead_lobbies_remain_dead_trimmed="
        f"{hard['late_round_dead_lobbies_remain_dead_trimmed']['status']} "
        f"late_lobby_gap_count={hard['late_round_dead_lobbies_remain_dead_trimmed']['late_lobby_gap_count']} "
        f"late_dead_lobby_reincluded_count={hard['late_round_dead_lobbies_remain_dead_trimmed']['late_dead_lobby_reincluded_count']}"
    )
    lines.append(f"- anti_overcut_zero={hard['anti_overcut_zero']}")
    lines.append(f"- no_kept_speech_lost={hard['no_kept_speech_lost']}")
    lines.append(f"- duration_under_previous_bad_29min={hard['duration_under_previous_bad_29min']}")
    lines.append("")
    lines.append("LATE LOBBY GAP LIST")
    for row in hard["late_round_dead_lobbies_remain_dead_trimmed"]["late_lobby_rows"]:
        lines.append(
            f"- {row['gap_id']} {row['start_seconds']}->{row['end_seconds']} "
            f"audio={row['audio_max']}/{row['audio_floor']} "
            f"speech_share={row['speech_share']} longest={row['longest_speech_run_seconds']} "
            f"class={row['classification']}"
        )
    lines.append("")
    lines.append("GAP TABLE")
    lines.append(
        "gap | range | dur | g6_state | audio_max/floor/action | "
        "speech_s/share/longest | motion_max(report_only) | reaction | class | action"
    )

    for row in audit["gap_rows"]:
        lines.append(
            f"{row['gap_id']} | "
            f"{row['start_seconds']}->{row['end_seconds']} | "
            f"{row['duration_seconds']} | "
            f"{_short_state(row)} | "
            f"{row['audio_max']}/{row['audio_floor']}/{row['audio_action']} | "
            f"{row['speech_seconds']}/{row['speech_share']}/{row['longest_speech_run_seconds']} | "
            f"{row['motion_max']} | "
            f"{row['reaction_level']} | "
            f"{row['classification']} | "
            f"{row['action']}"
        )

    lines.append("")
    lines.append("NEW SEGMENTS")
    for segment in audit["new_segments"]:
        lines.append(
            f"- {segment['segment_id']} {segment['start_seconds']}->{segment['end_seconds']} "
            f"dur={segment['duration_seconds']} state={segment['state']}"
        )

    lines.append("")
    lines.append("PYTEST OUTPUT")
    if pytest_output_path and pytest_output_path.exists():
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
    parser.add_argument("--plan", default="reports/word_snap_2_fix/word_snap_2_fix_final_editorial_plan.json")
    parser.add_argument("--g6-states", default="reports/g6_2_play_segment_detector/fortnite_g6_2_segments.json")
    parser.add_argument("--raw-windows", default="reports/dead_air_1/fortnite_g6_raw_windows_for_dead_air_1.json")
    parser.add_argument("--speech", default="reports/combined_speech/combined_speech_regions.json")
    parser.add_argument("--reactions", default="reports/reaction_adaptive/reaction_adaptive_fortnite_reactions.json")
    parser.add_argument("--out-dir", default="reports/content_gap_protector_fix")
    parser.add_argument("--pytest-output", default="reports/content_gap_protector_fix/pytest_content_gap_protector_fix.txt")
    parser.add_argument("--video-config", default="video_configs/fortnite_v18_legacy_fixture.json")
    parser.add_argument("--speech-run-min-seconds", type=float, default=4.0)
    parser.add_argument("--speech-share-min", type=float, default=0.50)
    parser.add_argument("--min-dead-gap-seconds", type=float, default=1.5)
    parser.add_argument("--audio-floor-percentile", type=float, default=0.70)
    parser.add_argument("--reaction-medium-score", type=float, default=0.50)
    args = parser.parse_args(argv)

    plan_path = Path(args.plan)
    g6_path = Path(args.g6_states)
    raw_path = Path(args.raw_windows)
    speech_path = Path(args.speech)
    reactions_path = Path(args.reactions)
    out_dir = Path(args.out_dir)
    pytest_output_path = Path(args.pytest_output)
    out_dir.mkdir(parents=True, exist_ok=True)

    required = [plan_path, g6_path, raw_path, speech_path, reactions_path]
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
    g6_states = normalize_intervals(_read_json(g6_path), source="g6_state")
    protected_ranges = normalize_protected_ranges(read_video_config(args.video_config))

    new_segments, audit = protect_content_gaps(
        kept_segments=source_segments,
        raw_windows=raw_windows,
        combined_speech_regions=speech_regions,
        reactions=reactions,
        g6_states=g6_states,
        protected_ranges=protected_ranges,
        config=ContentGapProtectorConfig(
            speech_run_min_seconds=args.speech_run_min_seconds,
            speech_share_min=args.speech_share_min,
            min_dead_gap_seconds=args.min_dead_gap_seconds,
            audio_floor_percentile=args.audio_floor_percentile,
            reaction_medium_score=args.reaction_medium_score,
        ),
    )

    output_parent[output_key] = new_segments
    output_plan["content_gap_protector_fix_audit"] = {
        key: value
        for key, value in audit.items()
        if key not in {"gap_rows", "new_segments"}
    }
    output_plan["content_gap_protector_fix_gap_rows"] = audit["gap_rows"]

    duration_contract = output_plan.get("duration_contract")
    if not isinstance(duration_contract, dict):
        duration_contract = {}
    duration_contract["content_gap_protector_fix_planned_output_duration_seconds"] = audit["new_plan_duration_seconds"]
    duration_contract["content_gap_protector_fix_duration_delta_seconds"] = audit["duration_delta_seconds"]
    output_plan["duration_contract"] = duration_contract

    output_plan_path = out_dir / "content_gap_protector_fix_final_editorial_plan.json"
    report_path = out_dir / "content_gap_protector_fix_report.txt"
    audit_path = out_dir / "content_gap_protector_fix_audit.json"
    gap_table_path = out_dir / "content_gap_protector_fix_gap_table.json"

    _write_json(output_plan_path, output_plan)
    _write_json(audit_path, audit)
    _write_json(gap_table_path, audit["gap_rows"])
    _write_report(
        report_path,
        audit,
        output_plan_path=output_plan_path,
        pytest_output_path=pytest_output_path,
    )

    hard = audit["hard_checks"]
    overall_pass = (
        hard["combat_content_gaps_reincluded"]["status"] == "JA"
        and hard["within_round_gap_120_133_6_content"]["status"] == "JA"
        and hard["anti_overcut_zero"] == "JA"
        and hard["no_kept_speech_lost"] == "JA"
        and hard["duration_under_previous_bad_29min"] == "JA"
        and len(audit["metric_discovery"]["audio_keys"]) > 0
    )

    print("PROJECT ZENITH - CONTENT-GAP-PROTECTOR-FIX")
    print(f"output_plan={output_plan_path}")
    print(f"report={report_path}")
    print(f"audit={audit_path}")
    print(f"audio_keys={audit['metric_discovery']['audio_keys']}")
    print(f"audio_floor_key={audit['metric_discovery']['audio_floor_key']}")
    print(f"audio_floor={audit['metric_discovery']['audio_floor']}")
    print(f"gap_count={audit['gap_count']}")
    print(f"content_gap_count={audit['content_gap_count']}")
    print(f"dead_gap_count={audit['dead_gap_count']}")
    print(f"re_included_gap_count={audit['reincluded_gap_count']}")
    print(f"old_plan_duration_seconds={audit['old_plan_duration_seconds']}")
    print(f"new_plan_duration_seconds={audit['new_plan_duration_seconds']}")
    print(f"duration_delta_seconds={audit['duration_delta_seconds']}")
    print(f"old_kept_speech_seconds={audit['old_kept_speech_seconds']}")
    print(f"new_kept_speech_seconds={audit['new_kept_speech_seconds']}")
    print(f"kept_speech_not_lost={audit['kept_speech_not_lost']}")
    print(f"anti_overcut_fail_count={audit['anti_overcut_fail_count']}")
    print(f"combat_content_gaps_reincluded={hard['combat_content_gaps_reincluded']['status']}")
    print(f"gap_120_133_6={hard['within_round_gap_120_133_6_content']['status']}")
    print(f"late_round_dead_lobbies_remain_dead_trimmed={hard['late_round_dead_lobbies_remain_dead_trimmed']['status']}")
    print(f"late_dead_lobby_reincluded_count={hard['late_round_dead_lobbies_remain_dead_trimmed']['late_dead_lobby_reincluded_count']}")
    print(f"duration_under_previous_bad_29min={hard['duration_under_previous_bad_29min']}")
    print(f"overall_pass={overall_pass}")

    return 0 if overall_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
