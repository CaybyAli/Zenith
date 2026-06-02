from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ffmpeg_helper import get_ffprobe_path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip().lstrip("\ufeff"))
    except Exception:
        return default
    return number if math.isfinite(number) else default


def ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            get_ffprobe_path(),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    data = json.loads(result.stdout)
    return round(safe_float((data.get("format") or {}).get("duration")), 3)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def segment_range(segment: Mapping[str, Any]) -> tuple[float, float]:
    return (
        safe_float(segment.get("start_seconds", segment.get("start", segment.get("start_time")))),
        safe_float(segment.get("end_seconds", segment.get("end", segment.get("end_time")))),
    )


def range_coverage(plan_path: Path, start_seconds: float, end_seconds: float) -> float:
    plan = read_json(plan_path)
    segments = plan.get("timeline_segments") if isinstance(plan, Mapping) else []
    if not isinstance(segments, list):
        return 0.0
    total = 0.0
    for segment in segments:
        if not isinstance(segment, Mapping):
            continue
        seg_start, seg_end = segment_range(segment)
        total += overlap(start_seconds, end_seconds, seg_start, seg_end)
    return round(total, 3)


def stage_from_report(path: Path, fallback: str) -> str:
    if not path.exists():
        return fallback
    report = read_json(path)
    if isinstance(report, Mapping):
        return str(report.get("stage") or fallback)
    return fallback


def segment_check_from_report(path: Path) -> dict[str, Any]:
    report = read_json(path)
    check = report.get("segment_check") if isinstance(report, Mapping) else {}
    if not isinstance(check, Mapping):
        check = {}
    matched = int(check.get("matched_segments") or 0)
    total = int(check.get("plan_segment_count") or check.get("render_context_segment_count") or 0)
    return {
        "plan_segment_count": total,
        "render_context_segment_count": int(check.get("render_context_segment_count") or 0),
        "matched_segments": matched,
        "deviation_count": int(check.get("deviation_count") or 0),
        "exact_match": bool(check.get("exact_match")),
        "display": f"{matched}/{total} exact" if bool(check.get("exact_match")) else f"{matched}/{total} with deviations",
    }


def build_report(args: argparse.Namespace) -> tuple[list[str], dict[str, Any]]:
    tail_audit = read_json(Path(args.tail_audit))
    xfade_report = read_json(Path(args.xfade_report)) if Path(args.xfade_report).exists() else {}
    segment_check = segment_check_from_report(Path(args.hardcut_report))

    hardcut_duration = ffprobe_duration(Path(args.hardcut_video))
    final_duration = ffprobe_duration(Path(args.final_video))
    v17_events_sha = sha256(Path(args.v17_events))
    events_sha = sha256(Path(args.events))
    byte_identical = v17_events_sha == events_sha

    hardcut_stage = stage_from_report(Path(args.hardcut_report), "hardcut")
    final_stage = stage_from_report(Path(args.xfade_report), "final_xfade")
    tail_clamp_count = int(tail_audit.get("tail_clamp_count") or 0)
    trimmed_seconds = safe_float(tail_audit.get("total_trimmed_seconds", tail_audit.get("trimmed_seconds")))
    removed_speech_seconds = safe_float(tail_audit.get("removed_speech_seconds"))
    boundary_count = int(xfade_report.get("boundary_count") or len(xfade_report.get("boundaries") or []))
    total_overlap_seconds = safe_float(xfade_report.get("total_overlap_seconds"))
    expected_final = safe_float(xfade_report.get("expected_duration_seconds"), final_duration)
    actual_final_reported = safe_float(xfade_report.get("actual_duration_seconds"), final_duration)

    combat_start, combat_end = 142.0, 246.0
    payoff_start, payoff_end = 1756.0, 1810.817
    v17_combat = range_coverage(Path(args.v17_plan), combat_start, combat_end)
    v18_combat = range_coverage(Path(args.plan), combat_start, combat_end)
    v17_payoff = range_coverage(Path(args.v17_plan), payoff_start, payoff_end)
    v18_payoff = range_coverage(Path(args.plan), payoff_start, payoff_end)

    pass_checks = {
        "removed_speech_zero": removed_speech_seconds == 0.0,
        "tail_clamp_count_present": tail_clamp_count > 0,
        "trimmed_seconds_present": trimmed_seconds > 0.0,
        "segment_exact": bool(segment_check["exact_match"]),
        "zoom_events_byte_identical": byte_identical,
        "hardcut_stage": hardcut_stage == "hardcut",
        "final_stage": final_stage == "final_xfade",
        "final_duration_matches_xfade_report": abs(final_duration - actual_final_reported) <= 0.001,
    }
    status = "PASS" if all(pass_checks.values()) else "REVIEW"

    data = {
        "status": status,
        "checks": pass_checks,
        "stage": {"hardcut": hardcut_stage, "final_xfade": final_stage},
        "tail_clamp": {
            "tail_after_speech_seconds": safe_float(tail_audit.get("tail_after_speech_seconds")),
            "tail_clamp_count": tail_clamp_count,
            "trimmed_seconds": round(trimmed_seconds, 3),
            "removed_speech_seconds": round(removed_speech_seconds, 6),
        },
        "zoom_events": {
            "reference_path": args.v17_events,
            "events_path": args.events,
            "reference_sha256": v17_events_sha,
            "events_sha256": events_sha,
            "byte_identical": byte_identical,
        },
        "combat_payoff": {
            "combat_142_246_coverage_v17": v17_combat,
            "combat_142_246_coverage_v18": v18_combat,
            "payoff_1756_1810_817_coverage_v17": v17_payoff,
            "payoff_1756_1810_817_coverage_v18": v18_payoff,
        },
        "render": {
            "hardcut_video": args.hardcut_video,
            "hardcut_duration_seconds": hardcut_duration,
            "final_video": args.final_video,
            "final_duration_seconds": final_duration,
            "xfade_boundary_count": boundary_count,
            "xfade_overlap_seconds": round(total_overlap_seconds, 3),
            "expected_final_duration_seconds": round(expected_final, 3),
            "actual_final_duration_seconds": round(actual_final_reported, 3),
            "segment_check": segment_check,
        },
    }

    lines = [
        "PROJECT ZENITH - ranked_cut_v18 SCRIPT-GENERATED VALIDATION REPORT",
        "",
        f"status={status}",
        f"stage_hardcut={hardcut_stage}",
        f"stage_final_xfade={final_stage}",
        "",
        "TAIL-CLAMP",
        f"tail_after_speech_seconds={data['tail_clamp']['tail_after_speech_seconds']}",
        f"tail_clamp_count={tail_clamp_count}",
        f"trimmed_seconds={data['tail_clamp']['trimmed_seconds']}",
        f"removed_speech_seconds={data['tail_clamp']['removed_speech_seconds']}",
        "",
        "ZOOM EVENTS",
        f"reference_sha256={v17_events_sha}",
        f"events_sha256={events_sha}",
        f"byte_identical={byte_identical}",
        "",
        "SEGMENT CHECK",
        f"segment_check={segment_check['display']}",
        f"plan_segment_count={segment_check['plan_segment_count']}",
        f"render_context_segment_count={segment_check['render_context_segment_count']}",
        f"matched_segments={segment_check['matched_segments']}",
        f"deviation_count={segment_check['deviation_count']}",
        f"exact_match={segment_check['exact_match']}",
        "",
        "COMBAT/PAYOFF",
        f"combat_142_246_coverage_v17={v17_combat}",
        f"combat_142_246_coverage_v18={v18_combat}",
        f"payoff_1756_1810.817_coverage_v17={v17_payoff}",
        f"payoff_1756_1810.817_coverage_v18={v18_payoff}",
        "",
        "RENDER",
        f"hardcut_video={args.hardcut_video}",
        f"hardcut_duration_seconds={hardcut_duration}",
        f"final_video={args.final_video}",
        f"final_duration_seconds={final_duration}",
        f"xfade_boundary_count={boundary_count}",
        f"xfade_overlap_seconds={round(total_overlap_seconds, 3)}",
        f"expected_final_duration_seconds={round(expected_final, 3)}",
        f"actual_final_duration_seconds={round(actual_final_reported, 3)}",
        "",
        "SOURCES",
        f"tail_audit={args.tail_audit}",
        f"hardcut_report={args.hardcut_report}",
        f"xfade_report={args.xfade_report}",
        f"generator={Path(__file__).as_posix()}",
    ]
    return lines, data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default="reports/ranked_render/ranked_cut_v18_editorial_plan.json")
    parser.add_argument("--v17-plan", default="reports/ranked_render/ranked_cut_v17_editorial_plan.json")
    parser.add_argument("--tail-audit", default="reports/ranked_render/ranked_cut_v18_tail_clamp_audit.json")
    parser.add_argument("--v17-events", default="reports/ranked_render/ranked_cut_v17_reaction_size_events.json")
    parser.add_argument("--events", default="reports/ranked_render/ranked_cut_v18_reaction_size_events.json")
    parser.add_argument("--hardcut-video", default="reports/ranked_render/ranked_cut_v18_hardcut.mp4")
    parser.add_argument("--final-video", default="reports/ranked_render/ranked_cut_v18.mp4")
    parser.add_argument("--hardcut-report", default="reports/ranked_render/combined_render_report.json")
    parser.add_argument("--xfade-report", default="reports/ranked_render/ranked_cut_v18_round_xfade_report.json")
    parser.add_argument("--out", default="reports/ranked_render/ranked_cut_v18_validation_report.txt")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    lines, data = build_report(args)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"validation_report={out_path}")
    print(f"status={data['status']}")
    print(f"segment_check={data['render']['segment_check']['display']}")
    print(f"zoom_events_byte_identical={data['zoom_events']['byte_identical']}")
    return 0 if data["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
