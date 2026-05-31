from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.g8_block_assembly import G8BlockAssemblyPlanner


OLD_PLAN_PATH = Path("reports/g8_assembly/fortnite_bridge20_g8_1_g8_timeline_plan.json")
G6_PATH = Path("reports/g6_2_play_segment_detector/fortnite_g6_2_segments.json")
OUT_DIR = Path("reports/g8_2_round_end")
NEW_PLAN_PATH = Path("reports/g8_assembly/fortnite_bridge20_g8_2_state_aware_g8_timeline_plan.json")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_segments(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    if isinstance(data, list):
        return data
    for key in ("segments", "play_segments", "g6_segments"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, list):
            return value
    if isinstance(data, dict) and isinstance(data.get("g6"), dict):
        value = data["g6"].get("segments")
        if isinstance(value, list):
            return value
    raise RuntimeError(f"No segments found in {path}")


def f(value: Any) -> float:
    return float(value)


def selected_blocks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        list(plan.get("selected_blocks") or []),
        key=lambda block: (f(block.get("start_seconds", 0)), f(block.get("end_seconds", 0))),
    )


def timeline_segments(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        list(plan.get("timeline_segments") or []),
        key=lambda seg: (f(seg.get("start_seconds", 0)), f(seg.get("end_seconds", 0))),
    )


def fmt_block(block: dict[str, Any] | None) -> str:
    if block is None:
        return "NONE"
    return (
        f"{block.get('block_id')} "
        f"{block.get('start_seconds')}->{block.get('end_seconds')} "
        f"budget={block.get('keep_active_budget_seconds')}"
    )


def block_covering(blocks: list[dict[str, Any]], start: float, end: float) -> dict[str, Any] | None:
    for block in blocks:
        if f(block["start_seconds"]) <= start and f(block["end_seconds"]) >= end:
            return block
    return None


def block_starting_near(blocks: list[dict[str, Any]], start: float, tolerance: float = 4.0) -> dict[str, Any] | None:
    for block in blocks:
        if abs(f(block["start_seconds"]) - start) <= tolerance:
            return block
    return None


def g6_rows_in_gap(g6_segments: list[dict[str, Any]], lo: float, hi: float) -> list[dict[str, Any]]:
    return [
        s for s in g6_segments
        if f(s["end_seconds"]) > lo and f(s["start_seconds"]) < hi
    ]


def intro_lobby_seconds(rows: list[dict[str, Any]], lo: float, hi: float) -> float:
    ranges = []
    for row in rows:
        if row.get("state") != "intro_menu_lobby":
            continue
        start = max(lo, f(row["start_seconds"]))
        end = min(hi, f(row["end_seconds"]))
        if end > start:
            ranges.append((start, end))
    ranges.sort()
    merged = []
    for start, end in ranges:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return round(sum(end - start for start, end in merged), 3)


def state_lines(rows: list[dict[str, Any]]) -> list[str]:
    out = []
    for s in rows:
        out.append(
            f"{s['start_seconds']}->{s['end_seconds']} "
            f"state={s.get('state')} "
            f"dur={round(f(s['end_seconds']) - f(s['start_seconds']), 3)}"
        )
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    NEW_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)

    old_plan = read_json(OLD_PLAN_PATH)
    g6_segments = load_segments(G6_PATH)

    planner = G8BlockAssemblyPlanner(
        bridge_seconds=20.0,
        min_standalone_block_seconds=12.0,
        round_gap_seconds=45.0,
        lobby_min_seconds=5.0,
    )
    new_plan = planner.build_plan(
        label="fortnite_bridge20_g8_2_state_aware",
        play_segments=g6_segments,
        g7a_spans=[],
        highlights=[],
    )
    new_plan_dict = new_plan.to_dict()

    NEW_PLAN_PATH.write_text(
        json.dumps(new_plan_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    old_blocks = selected_blocks(old_plan)
    new_blocks = selected_blocks(new_plan_dict)
    old_timeline = timeline_segments(old_plan)
    new_timeline = timeline_segments(new_plan_dict)

    block_001 = block_covering(new_blocks, 16.0, 172.0)
    block_001_segments = [
        seg for seg in new_timeline
        if block_001 is not None and seg.get("block_id") == block_001.get("block_id")
    ]

    tail_166_172_kept = any(
        f(seg["start_seconds"]) == 166.0 and f(seg["end_seconds"]) == 172.0
        for seg in new_timeline
    )
    lull_142_166_trimmed = not any(
        f(seg["start_seconds"]) < 166.0 and f(seg["end_seconds"]) > 142.0
        and not (f(seg["end_seconds"]) <= 142.0 or f(seg["start_seconds"]) >= 166.0)
        for seg in new_timeline
    )

    gap_checks = []
    for name, lo, hi, expected_stable_lobby in [
        ("block_001_lull_142_166", 142.0, 166.0, False),
        ("late_boundary_1198_1230", 1198.0, 1230.0, True),
        ("late_boundary_1468_1518", 1468.0, 1518.0, True),
        ("late_boundary_1622_1652", 1622.0, 1652.0, True),
    ]:
        rows = g6_rows_in_gap(g6_segments, lo, hi)
        lobby_seconds = intro_lobby_seconds(rows, lo, hi)
        has_stable_lobby = lobby_seconds >= 5.0
        gap_checks.append({
            "name": name,
            "range": [lo, hi],
            "lobby_seconds": lobby_seconds,
            "has_stable_lobby": has_stable_lobby,
            "expected_stable_lobby": expected_stable_lobby,
            "pass": has_stable_lobby == expected_stable_lobby,
            "states": state_lines(rows),
        })

    late_expected_ranges = [
        ("round_A", 968.0, 1198.0),
        ("round_B", 1226.0, 1498.0),
        ("round_C", 1512.0, 1622.0),
        ("round_D", 1648.0, 1792.0),
    ]
    late_round_checks = []
    for name, start, end in late_expected_ranges:
        block = block_covering(new_blocks, start, end)
        late_round_checks.append({
            "name": name,
            "expected_active_range": [start, end],
            "covering_block": block,
            "pass": block is not None,
        })

    bad_504_merge = any(
        f(block["start_seconds"]) <= 968.0 and f(block["end_seconds"]) >= 1792.0
        for block in new_blocks
    )

    duration = new_plan_dict["duration_contract"]
    anti = new_plan_dict["anti_overcut_audit"]
    minimum = new_plan_dict.get("minimum_standalone_block_filter", {})

    overall_pass = bool(
        block_001 is not None
        and f(block_001["end_seconds"]) >= 172.0
        and tail_166_172_kept
        and lull_142_166_trimmed
        and not bad_504_merge
        and all(item["pass"] for item in gap_checks)
        and all(item["pass"] for item in late_round_checks)
        and anti["fail_count"] == 0
        and duration["planned_output_duration_seconds"] >= duration["youtube_floor_seconds"]
    )

    report = {
        "stage": "g8_2_state_aware_round_end_fix",
        "old_plan_path": str(OLD_PLAN_PATH),
        "new_plan_path": str(NEW_PLAN_PATH),
        "g6_path": str(G6_PATH),
        "round_gap_seconds": new_plan_dict.get("round_gap_seconds"),
        "lobby_min_seconds": new_plan_dict.get("lobby_min_seconds"),
        "bridge_seconds": new_plan_dict.get("bridge_seconds"),
        "old_selected_block_count": len(old_blocks),
        "new_selected_block_count": len(new_blocks),
        "old_timeline_segment_count": len(old_timeline),
        "new_timeline_segment_count": len(new_timeline),
        "old_planned_output_duration_seconds": old_plan["duration_contract"]["planned_output_duration_seconds"],
        "new_planned_output_duration_seconds": duration["planned_output_duration_seconds"],
        "youtube_floor_seconds": duration["youtube_floor_seconds"],
        "new_duration_meets_youtube_floor": duration["planned_output_duration_seconds"] >= duration["youtube_floor_seconds"],
        "anti_overcut_fail_count": anti["fail_count"],
        "anti_overcut_pass": anti["fail_count"] == 0,
        "minimum_filter_discarded_count": minimum.get("discarded_count"),
        "block_001": block_001,
        "block_001_segments": block_001_segments,
        "block_001_extended_to_172": bool(block_001 is not None and f(block_001["end_seconds"]) >= 172.0),
        "tail_166_172_kept": tail_166_172_kept,
        "lull_142_166_trimmed_from_timeline": lull_142_166_trimmed,
        "gap_checks": gap_checks,
        "late_round_checks": late_round_checks,
        "bad_504_merge_present": bad_504_merge,
        "overall_pass": overall_pass,
    }

    report_json = OUT_DIR / "g8_2_state_aware_round_end_report.json"
    report_txt = OUT_DIR / "g8_2_state_aware_round_end_report.txt"
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("PROJECT ZENITH - G8.2-FIX STATE-AWARE ROUND-END REPORT")
    lines.append("")
    lines.append(f"old_plan_path: {report['old_plan_path']}")
    lines.append(f"new_plan_path: {report['new_plan_path']}")
    lines.append(f"g6_path: {report['g6_path']}")
    lines.append(f"round_gap_seconds: {report['round_gap_seconds']}")
    lines.append(f"lobby_min_seconds: {report['lobby_min_seconds']}")
    lines.append(f"bridge_seconds: {report['bridge_seconds']}")
    lines.append("")
    lines.append("Block_001:")
    lines.append(f"- new: {fmt_block(block_001)}")
    lines.append(f"- block_001_extended_to_172: {report['block_001_extended_to_172']}")
    lines.append(f"- tail_166_172_kept: {report['tail_166_172_kept']}")
    lines.append(f"- lull_142_166_trimmed_from_timeline: {report['lull_142_166_trimmed_from_timeline']}")
    lines.append("")
    lines.append("New Block_001 timeline segments:")
    for seg in block_001_segments:
        lines.append(
            f"- {seg['segment_id']} {seg['start_seconds']}->{seg['end_seconds']} "
            f"dur={seg['duration_seconds']} block={seg['block_id']}"
        )
    lines.append("")
    lines.append("Gap state checks:")
    for item in gap_checks:
        lines.append(
            f"- {item['name']} range={item['range']} "
            f"lobby_seconds={item['lobby_seconds']} "
            f"has_stable_lobby={item['has_stable_lobby']} "
            f"expected={item['expected_stable_lobby']} pass={item['pass']}"
        )
        for state in item["states"]:
            lines.append(f"  * {state}")
    lines.append("")
    lines.append("Late round separation checks:")
    for item in late_round_checks:
        lines.append(
            f"- {item['name']} expected={item['expected_active_range']} "
            f"covering_block={fmt_block(item['covering_block'])} pass={item['pass']}"
        )
    lines.append(f"- bad_504_merge_present: {report['bad_504_merge_present']}")
    lines.append("")
    lines.append("Summary:")
    lines.append(f"- old_selected_block_count: {report['old_selected_block_count']}")
    lines.append(f"- new_selected_block_count: {report['new_selected_block_count']}")
    lines.append(f"- old_timeline_segment_count: {report['old_timeline_segment_count']}")
    lines.append(f"- new_timeline_segment_count: {report['new_timeline_segment_count']}")
    lines.append(f"- old_planned_output_duration_seconds: {report['old_planned_output_duration_seconds']}")
    lines.append(f"- new_planned_output_duration_seconds: {report['new_planned_output_duration_seconds']}")
    lines.append(f"- new_duration_meets_youtube_floor: {report['new_duration_meets_youtube_floor']}")
    lines.append(f"- anti_overcut_fail_count: {report['anti_overcut_fail_count']}")
    lines.append(f"- minimum_filter_discarded_count: {report['minimum_filter_discarded_count']}")
    lines.append(f"- overall_pass: {report['overall_pass']}")
    report_txt.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("")
    print(f"WROTE_REPORT_JSON: {report_json}")
    print(f"WROTE_REPORT_TXT: {report_txt}")
    print(f"WROTE_NEW_PLAN: {NEW_PLAN_PATH}")

    return 0 if overall_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
