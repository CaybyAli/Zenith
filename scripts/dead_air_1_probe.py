from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.dead_air_trim import (
    apply_dead_air_trim,
    derive_silence_gaps_from_speech_segments,
    normalize_g6_action_windows,
    normalize_silence_gaps,
    normalize_speech_segments,
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _media_duration_from_speech_report(path: Path) -> float | None:
    if not path.exists():
        return None
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if line.startswith("media_duration_seconds="):
            return float(line.split("=", 1)[1].strip())
    return None


def _latest_payoff_2_plan() -> Path:
    preferred = Path("reports/payoff_2/payoff_2_g8_timeline_plan_reaction_gated.json")
    if preferred.exists():
        return preferred

    candidates = sorted(
        Path("reports").glob("**/*payoff_2*g8*plan*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No PAYOFF-2 plan found.")
    return candidates[0]


def _load_or_build_g6_raw_windows(
    *,
    g6_json_path: Path,
    video_path: Path,
    out_dir: Path,
) -> tuple[list[dict[str, Any]], Path, str]:
    if g6_json_path.exists():
        data = _read_json(g6_json_path)
        windows = normalize_g6_action_windows(data)
        has_raw = isinstance(data, Mapping) and isinstance(data.get("raw_windows"), list) and bool(data["raw_windows"])
        if has_raw and windows:
            return windows, g6_json_path, "loaded_existing_g6_raw_windows"

    # Fallback: build raw windows locally for DEAD-AIR-1.
    from core.play_segment_boundary_detector import PlaySegmentBoundaryDetector

    detector = PlaySegmentBoundaryDetector(window_seconds=2.0, visual_sample_seconds=1.0)
    result = detector.detect(video_path, max_duration_seconds=None, include_raw_windows=True)

    raw_path = out_dir / "fortnite_g6_raw_windows_for_dead_air_1.json"
    detector.write_json(result, raw_path, include_raw_windows=True)

    windows = normalize_g6_action_windows(_read_json(raw_path))
    return windows, raw_path, "rebuilt_g6_raw_windows_for_dead_air_1"


def _load_silence_or_derive(
    *,
    silence_gaps_path: Path,
    speech_segments: list[Mapping[str, Any]],
    media_duration_seconds: float,
) -> tuple[list[dict[str, Any]], str]:
    if silence_gaps_path.exists():
        gaps = normalize_silence_gaps(_read_json(silence_gaps_path))
        if gaps:
            return gaps, "loaded_speech_1_silence_gaps"

    return derive_silence_gaps_from_speech_segments(
        speech_segments,
        media_duration_seconds=media_duration_seconds,
    ), "derived_from_speech_segments"


def _pick_first(evaluations: list[Mapping[str, Any]], reason: str) -> Mapping[str, Any] | None:
    for item in evaluations:
        if item.get("reason") == reason:
            return item
    return None


def _write_report(
    *,
    report_path: Path,
    source_plan_path: Path,
    output_plan_path: Path,
    g6_source_path: Path,
    g6_source_mode: str,
    silence_source_mode: str,
    speech_segments_path: Path,
    silence_gaps_path: Path,
    result_plan: dict[str, Any],
) -> None:
    audit = result_plan.get("dead_air_1_audit") or {}
    contract = result_plan.get("dead_air_1_contract") or {}
    floor = audit.get("adaptive_action_floor") or {}
    trims = list(result_plan.get("dead_air_1_trimmed_gaps") or [])
    evaluations = list(audit.get("evaluations") or [])

    high_action_counter = _pick_first(evaluations, "action_above_adaptive_floor")
    short_counter = _pick_first(evaluations, "below_min_dead_gap_seconds")
    speech_counter = _pick_first(evaluations, "speech_overlap_safety_block")

    lines: list[str] = []
    lines.append("PROJECT ZENITH - DEAD-AIR-1 REPORT")
    lines.append("")
    lines.append(f"source_plan={source_plan_path}")
    lines.append(f"output_plan={output_plan_path}")
    lines.append(f"speech_segments={speech_segments_path}")
    lines.append(f"silence_gaps={silence_gaps_path}")
    lines.append(f"silence_source_mode={silence_source_mode}")
    lines.append(f"g6_source={g6_source_path}")
    lines.append(f"g6_source_mode={g6_source_mode}")
    lines.append("")
    lines.append("PARAMETER")
    lines.append(f"- min_dead_gap_seconds={audit.get('min_dead_gap_seconds')}")
    lines.append(f"- edge_buffer_seconds={audit.get('edge_buffer_seconds')}")
    lines.append(f"- action_floor_percentile={audit.get('action_floor_percentile')}")
    lines.append("")
    lines.append("ADAPTIVE ACTION FLOOR")
    for key, value in floor.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("DURATION")
    lines.append(f"- original_planned_output_duration_seconds={contract.get('original_planned_output_duration_seconds')}")
    lines.append(f"- new_planned_output_duration_seconds={contract.get('new_planned_output_duration_seconds')}")
    lines.append(f"- total_trimmed_seconds={contract.get('total_trimmed_seconds')}")
    lines.append("")
    lines.append("ANTI-OVERCUT")
    lines.append(f"- anti_overcut_fail_count={audit.get('anti_overcut_fail_count')}")
    lines.append(f"- removed_speech_seconds={audit.get('removed_speech_seconds')}")
    lines.append(f"- removed_high_action_seconds={audit.get('removed_high_action_seconds')}")
    lines.append("")
    lines.append("TRIMMED DEAD-AIR GAPS")
    lines.append(f"- trim_count={len(trims)}")
    if not trims:
        lines.append("- none")
    for trim in trims[:10]:
        lines.append(
            f"- {trim.get('trim_id')} block={trim.get('block_id')} segment={trim.get('segment_id')} "
            f"trim={trim.get('trim_start_seconds')}->{trim.get('trim_end_seconds')} "
            f"duration={trim.get('duration_seconds')} "
            f"avg_action={trim.get('avg_action_score')} "
            f"max_action={trim.get('max_action_score')} "
            f"threshold={trim.get('action_floor_threshold')}"
        )
    lines.append("")
    lines.append("COUNTERCHECKS")
    if high_action_counter:
        lines.append(
            "- silent_but_high_action_not_trimmed="
            f"{high_action_counter.get('gap_start_seconds')}->{high_action_counter.get('gap_end_seconds')} "
            f"max_action={high_action_counter.get('max_action_score')} "
            f"threshold={high_action_counter.get('action_floor_threshold')} "
            f"reason={high_action_counter.get('reason')}"
        )
    else:
        lines.append("- silent_but_high_action_not_trimmed=NOT_FOUND_IN_REAL_INPUT")

    if short_counter:
        lines.append(
            "- short_pause_not_trimmed="
            f"{short_counter.get('gap_start_seconds')}->{short_counter.get('gap_end_seconds')} "
            f"duration={short_counter.get('gap_duration_seconds')} "
            f"min={short_counter.get('min_dead_gap_seconds')} "
            f"reason={short_counter.get('reason')}"
        )
    else:
        lines.append("- short_pause_not_trimmed=NOT_FOUND_IN_REAL_INPUT")

    if speech_counter:
        lines.append(
            "- speech_overlap_not_trimmed="
            f"{speech_counter.get('gap_start_seconds')}->{speech_counter.get('gap_end_seconds')} "
            f"reason={speech_counter.get('reason')}"
        )
    else:
        lines.append("- speech_overlap_not_trimmed=NOT_FOUND_IN_REAL_INPUT_SYNTHETIC_TEST_COVERS_THIS")
    lines.append("")
    lines.append("OUTPUTS")
    lines.append(str(output_plan_path))
    lines.append(str(report_path))
    lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default=None)
    parser.add_argument("--video", default=r"D:\Zenith\inbox\gaming_main\Fortnite Full Video.mp4")
    parser.add_argument("--speech-segments", default="reports/speech_1_transcript/fortnite_speech_segments.json")
    parser.add_argument("--silence-gaps", default="reports/speech_1_transcript/fortnite_silence_gaps.json")
    parser.add_argument("--speech-report", default="reports/speech_1_transcript/speech_1_report.txt")
    parser.add_argument("--g6-json", default="reports/g6_2_play_segment_detector/fortnite_g6_2_segments.json")
    parser.add_argument("--out-dir", default="reports/dead_air_1")
    parser.add_argument("--min-dead-gap-seconds", type=float, default=1.5)
    parser.add_argument("--edge-buffer-seconds", type=float, default=0.2)
    parser.add_argument("--action-floor-percentile", type=float, default=25.0)
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    plan_path = Path(args.plan) if args.plan else _latest_payoff_2_plan()
    video_path = Path(args.video)
    speech_segments_path = Path(args.speech_segments)
    silence_gaps_path = Path(args.silence_gaps)
    speech_report_path = Path(args.speech_report)
    g6_json_path = Path(args.g6_json)

    if not plan_path.exists():
        raise FileNotFoundError(f"plan not found: {plan_path}")
    if not speech_segments_path.exists():
        raise FileNotFoundError(f"speech_segments not found: {speech_segments_path}")
    if not video_path.exists():
        raise FileNotFoundError(f"video not found: {video_path}")

    plan = _read_json(plan_path)
    speech_segments = normalize_speech_segments(_read_json(speech_segments_path))

    media_duration = _media_duration_from_speech_report(speech_report_path)
    if media_duration is None:
        media_duration = max(
            [float(item.get("end_seconds") or 0.0) for item in speech_segments]
            + [float(item.get("end_seconds") or 0.0) for item in plan.get("timeline_segments") or [] if isinstance(item, Mapping)]
            + [0.0]
        )

    silence_gaps, silence_source_mode = _load_silence_or_derive(
        silence_gaps_path=silence_gaps_path,
        speech_segments=speech_segments,
        media_duration_seconds=float(media_duration),
    )

    g6_windows, g6_source_path, g6_source_mode = _load_or_build_g6_raw_windows(
        g6_json_path=g6_json_path,
        video_path=video_path,
        out_dir=out_dir,
    )

    result_plan = apply_dead_air_trim(
        plan,
        silence_gaps,
        g6_windows,
        speech_segments=speech_segments,
        min_dead_gap_seconds=args.min_dead_gap_seconds,
        edge_buffer_seconds=args.edge_buffer_seconds,
        action_floor_percentile=args.action_floor_percentile,
    )

    output_plan_path = out_dir / "dead_air_1_g8_payoff_2_plan_trimmed.json"
    report_path = out_dir / "dead_air_1_report.txt"

    _write_json(output_plan_path, result_plan)

    _write_report(
        report_path=report_path,
        source_plan_path=plan_path,
        output_plan_path=output_plan_path,
        g6_source_path=g6_source_path,
        g6_source_mode=g6_source_mode,
        silence_source_mode=silence_source_mode,
        speech_segments_path=speech_segments_path,
        silence_gaps_path=silence_gaps_path,
        result_plan=result_plan,
    )

    audit = result_plan.get("dead_air_1_audit") or {}
    contract = result_plan.get("dead_air_1_contract") or {}
    floor = audit.get("adaptive_action_floor") or {}

    print("PROJECT ZENITH - DEAD-AIR-1")
    print(f"source_plan={plan_path}")
    print(f"output_plan={output_plan_path}")
    print(f"report={report_path}")
    print(f"g6_source={g6_source_path}")
    print(f"g6_source_mode={g6_source_mode}")
    print(f"silence_source_mode={silence_source_mode}")
    print(f"action_floor_threshold={floor.get('threshold')}")
    print(f"trim_count={audit.get('trim_count')}")
    print(f"total_trimmed_seconds={audit.get('total_trimmed_seconds')}")
    print(f"new_planned_output_duration_seconds={contract.get('new_planned_output_duration_seconds')}")
    print(f"anti_overcut_fail_count={audit.get('anti_overcut_fail_count')}")

    for trim in (result_plan.get("dead_air_1_trimmed_gaps") or [])[:10]:
        print(
            f"{trim.get('trim_id')} "
            f"{trim.get('trim_start_seconds')}->{trim.get('trim_end_seconds')} "
            f"duration={trim.get('duration_seconds')} "
            f"max_action={trim.get('max_action_score')} "
            f"threshold={trim.get('action_floor_threshold')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
