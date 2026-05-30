
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.g8_block_assembly import G8BlockAssemblyPlanner


DEFAULT_OUTPUT_DIR = ROOT / "reports" / "g8_assembly"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_play_segments_from_json(path: Path) -> list[dict[str, Any]]:
    data = _read_json(path)
    if isinstance(data.get("segments"), list):
        return list(data["segments"])
    if isinstance(data.get("play_segments"), list):
        return list(data["play_segments"])
    if isinstance(data.get("g6"), dict) and isinstance(data["g6"].get("segments"), list):
        return list(data["g6"]["segments"])
    raise RuntimeError(f"No G6 play segments found in {path}")


def _load_optional_spans(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    data = _read_json(path)
    for key in (
        "spans",
        "segments",
        "windows",
        "decisions",
        "g7a_spans",
        "trim_spans",
        "active_play_decisions",
    ):
        value = data.get(key)
        if isinstance(value, list):
            return list(value)
    if isinstance(data.get("report"), dict):
        for key in ("spans", "segments", "windows", "decisions"):
            value = data["report"].get(key)
            if isinstance(value, list):
                return list(value)
    return []


def _detect_g6(video_path: Path, output_path: Path, max_duration_seconds: float | None) -> list[dict[str, Any]]:
    from core.play_segment_boundary_detector import PlaySegmentBoundaryDetector

    detector = PlaySegmentBoundaryDetector(window_seconds=2.0, visual_sample_seconds=1.0)
    result = detector.detect(
        video_path,
        max_duration_seconds=max_duration_seconds,
        include_raw_windows=False,
    )
    detector.write_json(result, output_path, include_raw_windows=False)
    return result.to_dict(include_raw_windows=False)["segments"]


def _write_markdown_report(
    *,
    report_path: Path,
    label: str,
    plan_path: Path,
    plan: dict[str, Any],
    g6_source: str,
    g7a_source: str,
    highlights_source: str,
) -> None:
    duration = plan["duration_contract"]
    audit = plan["anti_overcut_audit"]
    old_new = plan["old_vs_new"]
    minimum_filter = plan.get("minimum_standalone_block_filter", {})
    selected_blocks = plan["selected_blocks"]

    lines: list[str] = []
    lines.append("# G8 Assembly Report")
    lines.append("")
    lines.append(f"- label: `{label}`")
    lines.append(f"- plan_json: `{plan_path}`")
    lines.append(f"- engine: `{plan['engine']}`")
    lines.append(f"- status: `{plan['status']}`")
    lines.append(f"- g6_source: `{g6_source}`")
    lines.append(f"- g7a_source: `{g7a_source}`")
    lines.append(f"- highlights_source: `{highlights_source}`")
    lines.append("")
    lines.append("## Duration")
    lines.append(f"- available_keep_active_budget_seconds: {duration['available_keep_active_budget_seconds']}")
    lines.append(f"- selected_keep_active_budget_seconds: {duration['selected_keep_active_budget_seconds']}")
    lines.append(f"- target_duration_seconds: {duration['target_duration_seconds']}")
    lines.append(f"- planned_output_duration_seconds: {duration['planned_output_duration_seconds']}")
    lines.append(f"- youtube_floor_seconds: {duration['youtube_floor_seconds']}")
    lines.append(f"- ceiling_seconds: {duration['ceiling_seconds']}")
    lines.append("")
    lines.append("## Old vs New")
    lines.append(f"- old_performance_cap_seconds: {old_new['old_performance_cap_seconds']}")
    lines.append(f"- old_performance_stop_92_seconds: {old_new['old_performance_stop_92_seconds']}")
    lines.append(f"- new_planned_output_duration_seconds: {old_new['new_planned_output_duration_seconds']}")
    lines.append(f"- performance_cap_removed_for_longform: {old_new['performance_cap_removed_for_longform']}")
    lines.append("")
    lines.append("## Anti-Overcut Audit")
    lines.append(f"- fail_count: {audit['fail_count']}")
    lines.append(f"- tolerance_seconds: {audit['tolerance_seconds']}")
    lines.append("")
    lines.append("## G8.1 Minimum Standalone Block Filter")
    if minimum_filter:
        lines.append(f"- enabled: {minimum_filter.get('enabled')}")
        lines.append(f"- min_standalone_block_seconds: {minimum_filter.get('min_standalone_block_seconds')}")
        lines.append(f"- before_block_count: {minimum_filter.get('before_block_count')}")
        lines.append(f"- after_block_count: {minimum_filter.get('after_block_count')}")
        lines.append(f"- before_available_keep_active_budget_seconds: {minimum_filter.get('before_available_keep_active_budget_seconds')}")
        lines.append(f"- after_available_keep_active_budget_seconds: {minimum_filter.get('after_available_keep_active_budget_seconds')}")
        lines.append(f"- budget_delta_seconds: {minimum_filter.get('budget_delta_seconds')}")
        lines.append(f"- discarded_count: {minimum_filter.get('discarded_count')}")
        lines.append(f"- expanded_count: {minimum_filter.get('expanded_count')}")
        lines.append(f"- after_budget_below_720: {minimum_filter.get('after_budget_below_720')}")
        lines.append("")
        lines.append("### Before Blocks")
        lines.append("| block_id | start | end | keep_budget | quality |")
        lines.append("|---|---:|---:|---:|---:|")
        for block in minimum_filter.get("before_blocks", []):
            lines.append(
                f"| {block.get('block_id')} | {block.get('start_seconds')} | {block.get('end_seconds')} | {block.get('keep_active_budget_seconds')} | {block.get('quality_score')} |"
            )
        lines.append("")
        lines.append("### After Blocks")
        lines.append("| block_id | start | end | keep_budget | quality |")
        lines.append("|---|---:|---:|---:|---:|")
        for block in minimum_filter.get("after_blocks", []):
            lines.append(
                f"| {block.get('block_id')} | {block.get('start_seconds')} | {block.get('end_seconds')} | {block.get('keep_active_budget_seconds')} | {block.get('quality_score')} |"
            )
        lines.append("")
        lines.append("### Filter Actions")
        lines.append("| block_id | action | reason | keep_budget |")
        lines.append("|---|---|---|---:|")
        for action in minimum_filter.get("actions", []):
            lines.append(
                f"| {action.get('block_id')} | {action.get('action')} | {action.get('reason')} | {action.get('keep_active_budget_seconds', action.get('after_keep_active_budget_seconds', ''))} |"
            )
    else:
        lines.append("- filter_report: missing")
    lines.append("")
    lines.append("## Selected Blocks")
    lines.append("| rank | block_id | start | end | keep_budget | quality | source |")
    lines.append("|---:|---|---:|---:|---:|---:|---|")
    for block in selected_blocks:
        lines.append(
            "| "
            f"{block.get('rank')} | "
            f"{block['block_id']} | "
            f"{block['start_seconds']} | "
            f"{block['end_seconds']} | "
            f"{block['keep_active_budget_seconds']} | "
            f"{block['quality_score']} | "
            f"{block['quality_source']} |"
        )
    lines.append("")
    lines.append("## Timeline Segments")
    lines.append("| segment_id | block_id | start | end | duration | state | source |")
    lines.append("|---|---|---:|---:|---:|---|---|")
    for item in plan["timeline_segments"]:
        lines.append(
            "| "
            f"{item['segment_id']} | "
            f"{item['block_id']} | "
            f"{item['start_seconds']} | "
            f"{item['end_seconds']} | "
            f"{item['duration_seconds']} | "
            f"{item['state']} | "
            f"{item['source']} |"
        )
    lines.append("")
    lines.append("## Notes")
    for note in plan.get("notes", []):
        lines.append(f"- {note}")
    lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--video", default=None, help="Optional real video path. Used when --g6-json is missing.")
    parser.add_argument("--g6-json", default=None, help="Existing G6 play segment JSON.")
    parser.add_argument("--g7a-json", default=None, help="Optional G7a decision/trim JSON.")
    parser.add_argument("--highlights-json", default=None, help="Optional highlight/quality JSON.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--bridge-seconds", type=float, default=8.0)
    parser.add_argument("--min-standalone-block-seconds", type=float, default=12.0)
    parser.add_argument("--max-duration-seconds", type=float, default=None)
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    label = str(args.label)
    g6_path = Path(args.g6_json) if args.g6_json else output_dir / f"{label}_g6_segments.json"

    if g6_path.exists():
        play_segments = _load_play_segments_from_json(g6_path)
        g6_source = str(g6_path)
    else:
        if not args.video:
            raise RuntimeError("Provide --g6-json or --video")
        video_path = Path(args.video)
        if not video_path.exists():
            raise FileNotFoundError(str(video_path))
        play_segments = _detect_g6(video_path, g6_path, args.max_duration_seconds)
        g6_source = f"detected:{video_path}"

    g7a_path = Path(args.g7a_json) if args.g7a_json else None
    g7a_spans = _load_optional_spans(g7a_path)
    g7a_source = str(g7a_path) if g7a_path and g7a_path.exists() else "none"

    highlights_path = Path(args.highlights_json) if args.highlights_json else None
    highlights = _load_optional_spans(highlights_path)
    highlights_source = str(highlights_path) if highlights_path and highlights_path.exists() else "g6_confidence_intensity_fallback"

    planner = G8BlockAssemblyPlanner(
        bridge_seconds=args.bridge_seconds,
        min_standalone_block_seconds=args.min_standalone_block_seconds,
    )
    plan = planner.build_plan(
        label=label,
        play_segments=play_segments,
        g7a_spans=g7a_spans,
        highlights=highlights,
    )
    plan_dict = plan.to_dict()

    plan_path = output_dir / f"{label}_g8_timeline_plan.json"
    _write_json(plan_path, plan_dict)

    report_path = output_dir / "g8_assembly_report.md"
    _write_markdown_report(
        report_path=report_path,
        label=label,
        plan_path=plan_path,
        plan=plan_dict,
        g6_source=g6_source,
        g7a_source=g7a_source,
        highlights_source=highlights_source,
    )

    print(f"[G8] label={label}")
    print(f"[G8] plan={plan_path}")
    print(f"[G8] report={report_path}")
    print(f"[G8] status={plan.status}")
    print(f"[G8] anti_overcut_fail_count={plan.anti_overcut_fail_count}")
    print(f"[G8] available_keep_active_budget={plan.available_keep_active_budget_seconds:.3f}s")
    print(f"[G8] planned_output_duration={plan.planned_output_duration_seconds:.3f}s")
    print(f"[G8] old_performance_stop_92={plan.old_performance_stop_92_seconds:.3f}s")
    print(f"[G8] performance_cap_removed_for_longform={plan.performance_cap_removed_for_longform}")
    minimum_filter = plan_dict.get("minimum_standalone_block_filter", {})
    if minimum_filter:
        print(f"[G8.1] min_standalone_block_seconds={minimum_filter.get('min_standalone_block_seconds')}")
        print(f"[G8.1] before_block_count={minimum_filter.get('before_block_count')}")
        print(f"[G8.1] after_block_count={minimum_filter.get('after_block_count')}")
        print(f"[G8.1] discarded_count={minimum_filter.get('discarded_count')}")
        print(f"[G8.1] expanded_count={minimum_filter.get('expanded_count')}")
        print(f"[G8.1] after_budget_below_720={minimum_filter.get('after_budget_below_720')}")
    return 0 if plan.anti_overcut_fail_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

