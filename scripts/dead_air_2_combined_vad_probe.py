from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.dead_air_trim import (
    DEAD_AIR_2_SOURCE,
    dead_air_2_apply_trims_to_segments,
    dead_air_2_normalize_action_windows,
    dead_air_2_normalize_intervals,
    dead_air_2_select_trims,
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return round(max(0.0, min(end_a, end_b) - max(start_a, start_b)), 6)


def _interval_overlap_total(interval: Mapping[str, Any], trims: list[Mapping[str, Any]]) -> float:
    start = _safe_float(interval.get("start_seconds"))
    end = _safe_float(interval.get("end_seconds"))
    total = 0.0

    for trim in trims:
        total += _overlap(
            start,
            end,
            _safe_float(trim.get("start_seconds")),
            _safe_float(trim.get("end_seconds")),
        )

    return round(total, 6)


def _find_segment_container(plan: Any) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    candidate_keys = (
        "segments",
        "timeline_segments",
        "timeline",
        "selected_segments",
        "final_segments",
        "clips",
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


def _parse_dead_air_1_baseline(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "dead_air_1_report_found": False,
            "dead_air_1_trim_count": None,
            "dead_air_1_total_trimmed_seconds": None,
        }

    text = path.read_text(encoding="utf-8", errors="replace")

    def extract(name: str) -> float | None:
        match = re.search(rf"{re.escape(name)}=([0-9.]+)", text)
        if match:
            return float(match.group(1))
        match = re.search(rf"-\s*{re.escape(name)}=([0-9.]+)", text)
        if match:
            return float(match.group(1))
        return None

    return {
        "dead_air_1_report_found": True,
        "dead_air_1_trim_count": extract("trim_count"),
        "dead_air_1_total_trimmed_seconds": extract("total_trimmed_seconds"),
    }


def _write_report(
    *,
    report_path: Path,
    source_plan: Path,
    output_plan: Path,
    combined_silence_path: Path,
    combined_speech_path: Path,
    friend_examples_path: Path,
    g6_windows_path: Path,
    baseline: dict[str, Any],
    selection: dict[str, Any],
    new_duration_seconds: float,
    friend_safety_checks: list[dict[str, Any]],
) -> None:
    audit = selection["audit"]
    trims = selection["trims"]

    lines: list[str] = []
    lines.append("PROJECT ZENITH - DEAD-AIR-2 COMBINED VAD REPORT")
    lines.append("")
    lines.append(f"source_plan={source_plan}")
    lines.append(f"output_plan={output_plan}")
    lines.append(f"combined_silence_gaps={combined_silence_path}")
    lines.append(f"combined_speech_regions={combined_speech_path}")
    lines.append(f"friend_only_examples={friend_examples_path}")
    lines.append(f"g6_windows={g6_windows_path}")
    lines.append("")
    lines.append("SOURCE")
    lines.append(f"- source={DEAD_AIR_2_SOURCE}")
    lines.append("- silence_source=combined_silence_gaps_owner_plus_friend")
    lines.append("- word_derived_silence_used=False")
    lines.append("")
    lines.append("BASELINE DEAD-AIR-1")
    for key, value in baseline.items():
        lines.append(f"- {key}={value}")
    lines.append("")
    lines.append("DEAD-AIR-2 SUMMARY")
    lines.append(f"- trim_count={audit.get('trim_count')}")
    lines.append(f"- total_trimmed_seconds={audit.get('total_trimmed_seconds')}")
    lines.append(f"- new_planned_output_duration_seconds={new_duration_seconds}")
    lines.append(f"- action_floor_threshold={audit.get('action_floor_threshold')}")
    lines.append(f"- action_floor_percentile={audit.get('action_floor_percentile')}")
    lines.append(f"- min_dead_gap_seconds={audit.get('min_dead_gap_seconds')}")
    lines.append(f"- edge_buffer_seconds={audit.get('edge_buffer_seconds')}")
    lines.append("")
    lines.append("SAFETY")
    lines.append(f"- removed_speech_seconds={audit.get('removed_speech_seconds')}")
    lines.append(f"- removed_friend_only_speech_seconds={audit.get('removed_friend_only_speech_seconds')}")
    lines.append(f"- anti_overcut_fail_count={audit.get('anti_overcut_fail_count')}")
    lines.append("")
    lines.append("KERN-SICHERHEIT: FRIEND-ONLY REGIONS NOT TRIMMED")
    for check in friend_safety_checks:
        lines.append(
            f"- {check.get('status')} friend_only={check.get('start_seconds')}->{check.get('end_seconds')} "
            f"duration={check.get('duration_seconds')} trim_overlap={check.get('trim_overlap_seconds')}"
        )
    lines.append("")
    lines.append("TRIMS")
    if not trims:
        lines.append("- none")
    for index, trim in enumerate(trims[:30], start=1):
        lines.append(
            f"{index}. segment={trim.get('segment_id')} "
            f"trim={trim.get('start_seconds')}->{trim.get('end_seconds')} "
            f"duration={trim.get('duration_seconds')} "
            f"max_action={trim.get('max_action')} "
            f"floor={trim.get('action_floor')}"
        )
    lines.append("")
    lines.append("VERDICT")
    friend_fail_count = sum(1 for item in friend_safety_checks if item.get("status") != "PASS")
    hard_fail = (
        friend_fail_count > 0
        or float(audit.get("removed_speech_seconds") or 0.0) > 0.001
        or float(audit.get("removed_friend_only_speech_seconds") or 0.0) > 0.001
        or int(audit.get("anti_overcut_fail_count") or 0) != 0
    )
    lines.append(f"- friend_only_safety_fail_count={friend_fail_count}")
    lines.append(f"- overall_status={'FAIL' if hard_fail else 'PASS'}")
    if hard_fail:
        lines.append("- NO_GO_REASON=safety validation failed")
    else:
        lines.append("- GO_REASON=combined VAD dead-air trims do not remove Owner/Friend speech and anti-overcut remains clean")
    lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default="reports/payoff_2/payoff_2_g8_timeline_plan_reaction_gated.json")
    parser.add_argument("--combined-silence", default="reports/combined_speech/combined_silence_gaps.json")
    parser.add_argument("--combined-speech", default="reports/combined_speech/combined_speech_regions.json")
    parser.add_argument("--friend-examples", default="reports/combined_speech/friend_speaks_owner_silent_examples.json")
    parser.add_argument("--g6-windows", default="reports/dead_air_1/fortnite_g6_raw_windows_for_dead_air_1.json")
    parser.add_argument("--dead-air-1-report", default="reports/dead_air_1/dead_air_1_report.txt")
    parser.add_argument("--out-dir", default="reports/dead_air_2")
    parser.add_argument("--min-dead-gap-seconds", type=float, default=1.5)
    parser.add_argument("--edge-buffer-seconds", type=float, default=0.2)
    parser.add_argument("--action-floor-percentile", type=float, default=25.0)
    args = parser.parse_args(argv)

    plan_path = Path(args.plan)
    combined_silence_path = Path(args.combined_silence)
    combined_speech_path = Path(args.combined_speech)
    friend_examples_path = Path(args.friend_examples)
    g6_windows_path = Path(args.g6_windows)
    dead_air_1_report_path = Path(args.dead_air_1_report)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for required in (plan_path, combined_silence_path, combined_speech_path, friend_examples_path, g6_windows_path):
        if not required.exists():
            raise FileNotFoundError(f"required input missing: {required}")

    source_plan = _read_json(plan_path)
    plan_for_output = deepcopy(source_plan)
    source_parent, source_key, source_segments = _find_segment_container(source_plan)
    output_parent, output_key, _output_segments_ref = _find_segment_container(plan_for_output)

    combined_silence_gaps = dead_air_2_normalize_intervals(
        _read_json(combined_silence_path),
        list_keys=("silence_gaps", "items"),
        id_prefix="combined_silence",
        source="combined_both_owner_and_friend_silent",
    )

    combined_speech_regions = dead_air_2_normalize_intervals(
        _read_json(combined_speech_path),
        list_keys=("speech_regions", "items"),
        id_prefix="combined_speech",
        source="combined_owner_or_friend_speech",
    )

    friend_only_regions = dead_air_2_normalize_intervals(
        _read_json(friend_examples_path),
        list_keys=("examples", "items"),
        id_prefix="friend_only",
        source="friend_speaks_owner_silent",
    )

    action_windows = dead_air_2_normalize_action_windows(_read_json(g6_windows_path))

    selection = dead_air_2_select_trims(
        plan_segments=source_segments,
        combined_silence_gaps=combined_silence_gaps,
        action_windows=action_windows,
        combined_speech_regions=combined_speech_regions,
        friend_only_regions=friend_only_regions,
        min_dead_gap_seconds=args.min_dead_gap_seconds,
        edge_buffer_seconds=args.edge_buffer_seconds,
        action_floor_percentile=args.action_floor_percentile,
    )

    new_segments, new_duration = dead_air_2_apply_trims_to_segments(
        plan_segments=source_segments,
        trims=selection["trims"],
    )

    output_parent[output_key] = new_segments

    plan_for_output["dead_air_2_audit"] = selection["audit"]
    plan_for_output["dead_air_2_trims"] = selection["trims"]
    plan_for_output["dead_air_2_rejected_candidates"] = selection["rejected"]

    duration_contract = plan_for_output.get("duration_contract")
    if not isinstance(duration_contract, dict):
        duration_contract = {}
    duration_contract["dead_air_2_planned_output_duration_seconds"] = new_duration
    duration_contract["dead_air_2_total_trimmed_seconds"] = selection["audit"]["total_trimmed_seconds"]
    plan_for_output["duration_contract"] = duration_contract

    output_plan_path = out_dir / "dead_air_2_g8_payoff_2_plan_combined_vad_trimmed.json"
    report_path = out_dir / "dead_air_2_report.txt"

    friend_safety_checks: list[dict[str, Any]] = []
    for item in friend_only_regions:
        overlap = _interval_overlap_total(item, selection["trims"])
        friend_safety_checks.append({
            "start_seconds": item["start_seconds"],
            "end_seconds": item["end_seconds"],
            "duration_seconds": item["duration_seconds"],
            "trim_overlap_seconds": overlap,
            "status": "PASS" if overlap <= 0.001 else "FAIL",
        })

    baseline = _parse_dead_air_1_baseline(dead_air_1_report_path)

    _write_json(output_plan_path, plan_for_output)
    _write_json(out_dir / "dead_air_2_trims.json", selection["trims"])
    _write_json(out_dir / "dead_air_2_friend_only_safety_checks.json", friend_safety_checks)

    _write_report(
        report_path=report_path,
        source_plan=plan_path,
        output_plan=output_plan_path,
        combined_silence_path=combined_silence_path,
        combined_speech_path=combined_speech_path,
        friend_examples_path=friend_examples_path,
        g6_windows_path=g6_windows_path,
        baseline=baseline,
        selection=selection,
        new_duration_seconds=new_duration,
        friend_safety_checks=friend_safety_checks,
    )

    audit = selection["audit"]
    friend_fail_count = sum(1 for item in friend_safety_checks if item["status"] != "PASS")
    overall = "PASS" if friend_fail_count == 0 and audit["removed_speech_seconds"] <= 0.001 and audit["anti_overcut_fail_count"] == 0 else "FAIL"

    print("PROJECT ZENITH - DEAD-AIR-2 COMBINED VAD")
    print(f"source_plan={plan_path}")
    print(f"output_plan={output_plan_path}")
    print(f"report={report_path}")
    print(f"trim_count={audit['trim_count']}")
    print(f"total_trimmed_seconds={audit['total_trimmed_seconds']}")
    print(f"new_planned_output_duration_seconds={new_duration}")
    print(f"removed_speech_seconds={audit['removed_speech_seconds']}")
    print(f"removed_friend_only_speech_seconds={audit['removed_friend_only_speech_seconds']}")
    print(f"friend_only_safety_fail_count={friend_fail_count}")
    print(f"anti_overcut_fail_count={audit['anti_overcut_fail_count']}")
    print(f"overall_status={overall}")

    for item in friend_safety_checks[:5]:
        print(
            f"FRIEND_ONLY_CHECK {item['status']} "
            f"{item['start_seconds']}->{item['end_seconds']} "
            f"trim_overlap={item['trim_overlap_seconds']}"
        )

    return 0 if overall == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
