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

from core.word_snap_2 import (
    WORD_SNAP_2_SOURCE,
    apply_word_snap_2_to_segments,
    normalize_intervals,
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


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


def _write_report(
    *,
    report_path: Path,
    source_plan_path: Path,
    output_plan_path: Path,
    combined_speech_path: Path,
    combined_silence_path: Path,
    audit: dict[str, Any],
) -> None:
    lines: list[str] = []

    lines.append("PROJECT ZENITH - WORD-SNAP-2 COMBINED VAD REPORT")
    lines.append("")
    lines.append(f"source_plan={source_plan_path}")
    lines.append(f"output_plan={output_plan_path}")
    lines.append(f"combined_speech_regions={combined_speech_path}")
    lines.append(f"combined_silence_gaps={combined_silence_path}")
    lines.append("")
    lines.append("SOURCE")
    lines.append(f"- source={WORD_SNAP_2_SOURCE}")
    lines.append("- snap_basis=combined_vad_speech_regions")
    lines.append("- word_timestamps_used=False")
    lines.append("- stretched_word_logic_used=False")
    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"- snap_window_seconds={audit.get('snap_window_seconds')}")
    lines.append(f"- original_planned_output_duration_seconds={audit.get('original_planned_output_duration_seconds')}")
    lines.append(f"- new_planned_output_duration_seconds={audit.get('new_planned_output_duration_seconds')}")
    lines.append(f"- duration_delta_seconds={audit.get('duration_delta_seconds')}")
    lines.append(f"- total_abs_delta_seconds={audit.get('total_abs_delta_seconds')}")
    lines.append(f"- reviewed_mid_speech_edge_count={audit.get('reviewed_mid_speech_edge_count')}")
    lines.append(f"- snapped_edge_count={audit.get('snapped_edge_count')}")
    lines.append(f"- residual_mid_speech_edge_count={audit.get('residual_mid_speech_edge_count')}")
    lines.append("")
    lines.append("SAFETY")
    lines.append(f"- removed_active_play_seconds={audit.get('removed_active_play_seconds')}")
    lines.append(f"- removed_reaction_seconds={audit.get('removed_reaction_seconds')}")
    lines.append(f"- anti_overcut_fail_count={audit.get('anti_overcut_fail_count')}")
    lines.append("")
    lines.append("SNAP EXAMPLES")
    changes = audit.get("edge_changes") or []
    if not changes:
        lines.append("- none")
    for index, item in enumerate(changes[:8], start=1):
        lines.append(
            f"{index}. segment={item.get('segment_id')} edge={item.get('edge_kind')} "
            f"old={item.get('old_seconds')} new={item.get('new_seconds')} "
            f"delta={item.get('delta_seconds')} reason={item.get('reason')}"
        )
    lines.append("")
    lines.append("RESIDUALS")
    residuals = audit.get("residuals") or []
    if not residuals:
        lines.append("- none")
    for index, item in enumerate(residuals[:20], start=1):
        region = item.get("speech_region") if isinstance(item.get("speech_region"), dict) else {}
        lines.append(
            f"{index}. segment={item.get('segment_id')} edge={item.get('edge_kind')} "
            f"old={item.get('old_seconds')} reason={item.get('reason')} "
            f"speech_region={region.get('start_seconds')}->{region.get('end_seconds')}"
        )
    lines.append("")
    lines.append("VERDICT")
    hard_fail = int(audit.get("anti_overcut_fail_count") or 0) != 0
    lines.append(f"- overall_status={'FAIL' if hard_fail else 'PASS'}")
    if hard_fail:
        lines.append("- NO_GO_REASON=anti-overcut failed")
    else:
        lines.append("- GO_REASON=combined VAD boundary snap completed without active-play/reaction loss")
    lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default="reports/dead_air_2/dead_air_2_g8_payoff_2_plan_combined_vad_trimmed.json")
    parser.add_argument("--combined-speech", default="reports/combined_speech/combined_speech_regions.json")
    parser.add_argument("--combined-silence", default="reports/combined_speech/combined_silence_gaps.json")
    parser.add_argument("--out-dir", default="reports/word_snap_2")
    parser.add_argument("--snap-window-seconds", type=float, default=1.0)
    args = parser.parse_args(argv)

    plan_path = Path(args.plan)
    combined_speech_path = Path(args.combined_speech)
    combined_silence_path = Path(args.combined_silence)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for required in (plan_path, combined_speech_path, combined_silence_path):
        if not required.exists():
            raise FileNotFoundError(f"required input missing: {required}")

    source_plan = _read_json(plan_path)
    output_plan = deepcopy(source_plan)

    source_parent, source_key, source_segments = _find_segment_container(source_plan)
    output_parent, output_key, _ = _find_segment_container(output_plan)

    combined_speech_regions = normalize_intervals(
        _read_json(combined_speech_path),
        list_keys=("speech_regions", "items"),
        id_prefix="combined_speech",
        source="combined_owner_or_friend_speech",
    )
    combined_silence_gaps = normalize_intervals(
        _read_json(combined_silence_path),
        list_keys=("silence_gaps", "items"),
        id_prefix="combined_silence",
        source="combined_both_owner_and_friend_silent",
    )

    dead_air_trims = normalize_intervals(
        source_plan.get("dead_air_2_trims", []),
        list_keys=("dead_air_2_trims", "trims", "items"),
        id_prefix="dead_air_2_trim",
        source="dead_air_2_trim",
    )

    new_segments, audit = apply_word_snap_2_to_segments(
        plan_segments=source_segments,
        combined_speech_regions=combined_speech_regions,
        combined_silence_gaps=combined_silence_gaps,
        dead_air_trims=dead_air_trims,
        snap_window_seconds=args.snap_window_seconds,
    )

    output_parent[output_key] = new_segments
    output_plan["word_snap_2_audit"] = {
        key: value
        for key, value in audit.items()
        if key not in {"edge_reviews", "edge_changes", "residuals"}
    }
    output_plan["word_snap_2_edge_changes"] = audit["edge_changes"]
    output_plan["word_snap_2_residuals"] = audit["residuals"]

    duration_contract = output_plan.get("duration_contract")
    if not isinstance(duration_contract, dict):
        duration_contract = {}
    duration_contract["word_snap_2_planned_output_duration_seconds"] = audit["new_planned_output_duration_seconds"]
    duration_contract["word_snap_2_duration_delta_seconds"] = audit["duration_delta_seconds"]
    output_plan["duration_contract"] = duration_contract

    output_plan_path = out_dir / "word_snap_2_final_editorial_plan.json"
    report_path = out_dir / "word_snap_2_report.txt"

    _write_json(output_plan_path, output_plan)
    _write_json(out_dir / "word_snap_2_edge_changes.json", audit["edge_changes"])
    _write_json(out_dir / "word_snap_2_residuals.json", audit["residuals"])
    _write_json(out_dir / "word_snap_2_audit.json", audit)

    _write_report(
        report_path=report_path,
        source_plan_path=plan_path,
        output_plan_path=output_plan_path,
        combined_speech_path=combined_speech_path,
        combined_silence_path=combined_silence_path,
        audit=audit,
    )

    print("PROJECT ZENITH - WORD-SNAP-2 COMBINED VAD")
    print(f"source_plan={plan_path}")
    print(f"output_plan={output_plan_path}")
    print(f"report={report_path}")
    print(f"snap_window_seconds={audit['snap_window_seconds']}")
    print(f"reviewed_mid_speech_edge_count={audit['reviewed_mid_speech_edge_count']}")
    print(f"snapped_edge_count={audit['snapped_edge_count']}")
    print(f"residual_mid_speech_edge_count={audit['residual_mid_speech_edge_count']}")
    print(f"total_abs_delta_seconds={audit['total_abs_delta_seconds']}")
    print(f"duration_delta_seconds={audit['duration_delta_seconds']}")
    print(f"new_planned_output_duration_seconds={audit['new_planned_output_duration_seconds']}")
    print(f"anti_overcut_fail_count={audit['anti_overcut_fail_count']}")
    print("overall_status=PASS" if audit["anti_overcut_fail_count"] == 0 else "overall_status=FAIL")

    for item in audit["edge_changes"][:5]:
        print(
            f"SNAP {item.get('segment_id')} {item.get('edge_kind')} "
            f"{item.get('old_seconds')}->{item.get('new_seconds')} "
            f"delta={item.get('delta_seconds')}"
        )

    for item in audit["residuals"][:5]:
        print(
            f"RESIDUAL {item.get('segment_id')} {item.get('edge_kind')} "
            f"old={item.get('old_seconds')} reason={item.get('reason')}"
        )

    return 0 if audit["anti_overcut_fail_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
