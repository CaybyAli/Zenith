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
    WORD_SNAP_2_FIX_SOURCE,
    apply_word_snap_2_fix_to_residuals,
    normalize_intervals,
    normalize_speech_1_words,
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
    words_path: Path,
    residuals_path: Path,
    audit: dict[str, Any],
) -> None:
    lines: list[str] = []

    lines.append("PROJECT ZENITH - WORD-SNAP-2-FIX INNER WORD BOUNDARY REPORT")
    lines.append("")
    lines.append(f"source_plan={source_plan_path}")
    lines.append(f"output_plan={output_plan_path}")
    lines.append(f"speech_1_words={words_path}")
    lines.append(f"word_snap_2_residuals={residuals_path}")
    lines.append("")
    lines.append("SOURCE")
    lines.append(f"- source={WORD_SNAP_2_FIX_SOURCE}")
    lines.append("- primary_vad_snap_unchanged=True")
    lines.append("- fallback_only_for=continuous_speech_no_pause_boundary_inside_snap_window")
    lines.append("- stretched_words_excluded=True")
    lines.append("")
    lines.append("PARAMETERS")
    lines.append(f"- snap_window_seconds={audit.get('snap_window_seconds')}")
    lines.append(f"- max_word_seconds={audit.get('max_word_seconds')}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"- input_residual_count={audit.get('input_residual_count')}")
    lines.append(f"- continuous_speech_residual_count={audit.get('continuous_speech_residual_count')}")
    lines.append(f"- word_boundary_snapped_count={audit.get('word_boundary_snapped_count')}")
    lines.append(f"- real_residual_count={audit.get('real_residual_count')}")
    lines.append(f"- skipped_residual_count={audit.get('skipped_residual_count')}")
    lines.append(f"- stretched_word_snap_target_count={audit.get('stretched_word_snap_target_count')}")
    lines.append(f"- original_planned_output_duration_seconds={audit.get('original_planned_output_duration_seconds')}")
    lines.append(f"- new_planned_output_duration_seconds={audit.get('new_planned_output_duration_seconds')}")
    lines.append(f"- duration_delta_seconds={audit.get('duration_delta_seconds')}")
    lines.append(f"- total_abs_delta_seconds={audit.get('total_abs_delta_seconds')}")
    lines.append("")
    lines.append("SAFETY")
    lines.append(f"- removed_active_play_seconds={audit.get('removed_active_play_seconds')}")
    lines.append(f"- removed_reaction_seconds={audit.get('removed_reaction_seconds')}")
    lines.append(f"- anti_overcut_fail_count={audit.get('anti_overcut_fail_count')}")
    lines.append("")
    lines.append("WORD BOUNDARY SNAP EXAMPLES")
    fixes = audit.get("word_boundary_fixes") or []
    if not fixes:
        lines.append("- none")
    for index, item in enumerate(fixes[:8], start=1):
        word = item.get("selected_word") if isinstance(item.get("selected_word"), dict) else {}
        lines.append(
            f"{index}. segment={item.get('segment_id')} edge={item.get('edge_kind')} "
            f"old={item.get('old_seconds')} new={item.get('new_seconds')} "
            f"delta={item.get('delta_seconds')} "
            f"boundary={item.get('boundary_kind')} "
            f"word={word.get('word')} "
            f"word_range={word.get('start_seconds')}->{word.get('end_seconds')} "
            f"word_duration={word.get('duration_seconds')}"
        )
    lines.append("")
    lines.append("REAL RESIDUALS")
    real_residuals = audit.get("real_residuals") or []
    if not real_residuals:
        lines.append("- none")
    for index, item in enumerate(real_residuals[:20], start=1):
        lines.append(
            f"{index}. segment={item.get('segment_id')} edge={item.get('edge_kind')} "
            f"old={item.get('old_seconds')} reason={item.get('reason')}"
        )
    lines.append("")
    lines.append("VERDICT")
    hard_fail = (
        int(audit.get("anti_overcut_fail_count") or 0) != 0
        or int(audit.get("stretched_word_snap_target_count") or 0) != 0
    )
    lines.append(f"- overall_status={'FAIL' if hard_fail else 'PASS'}")
    if hard_fail:
        lines.append("- NO_GO_REASON=anti-overcut failed or stretched word was used as snap target")
    else:
        lines.append("- GO_REASON=continuous-speech residuals were reduced using reliable inner word boundaries")
    lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default="reports/word_snap_2/word_snap_2_final_editorial_plan.json")
    parser.add_argument("--residuals", default="reports/word_snap_2/word_snap_2_residuals.json")
    parser.add_argument("--words", default="reports/speech_1_transcript/fortnite_words.json")
    parser.add_argument("--out-dir", default="reports/word_snap_2_fix")
    parser.add_argument("--snap-window-seconds", type=float, default=1.0)
    parser.add_argument("--max-word-seconds", type=float, default=1.2)
    args = parser.parse_args(argv)

    plan_path = Path(args.plan)
    residuals_path = Path(args.residuals)
    words_path = Path(args.words)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for required in (plan_path, residuals_path, words_path):
        if not required.exists():
            raise FileNotFoundError(f"required input missing: {required}")

    source_plan = _read_json(plan_path)
    output_plan = deepcopy(source_plan)

    source_parent, source_key, source_segments = _find_segment_container(source_plan)
    output_parent, output_key, _ = _find_segment_container(output_plan)

    residuals = _read_json(residuals_path)
    if isinstance(residuals, dict) and isinstance(residuals.get("residuals"), list):
        residuals = residuals["residuals"]

    words = normalize_speech_1_words(
        _read_json(words_path),
        max_word_seconds=args.max_word_seconds,
    )

    dead_air_trims = normalize_intervals(
        source_plan.get("dead_air_2_trims", []),
        list_keys=("dead_air_2_trims", "trims", "items"),
        id_prefix="dead_air_2_trim",
        source="dead_air_2_trim",
    )

    new_segments, audit = apply_word_snap_2_fix_to_residuals(
        plan_segments=source_segments,
        residuals=residuals,
        speech_1_words=words,
        dead_air_trims=dead_air_trims,
        snap_window_seconds=args.snap_window_seconds,
        max_word_seconds=args.max_word_seconds,
    )

    output_parent[output_key] = new_segments
    output_plan["word_snap_2_fix_audit"] = {
        key: value
        for key, value in audit.items()
        if key not in {"word_boundary_fixes", "real_residuals", "skipped"}
    }
    output_plan["word_snap_2_fix_word_boundary_fixes"] = audit["word_boundary_fixes"]
    output_plan["word_snap_2_fix_real_residuals"] = audit["real_residuals"]

    duration_contract = output_plan.get("duration_contract")
    if not isinstance(duration_contract, dict):
        duration_contract = {}
    duration_contract["word_snap_2_fix_planned_output_duration_seconds"] = audit["new_planned_output_duration_seconds"]
    duration_contract["word_snap_2_fix_duration_delta_seconds"] = audit["duration_delta_seconds"]
    output_plan["duration_contract"] = duration_contract

    output_plan_path = out_dir / "word_snap_2_fix_final_editorial_plan.json"
    report_path = out_dir / "word_snap_2_fix_report.txt"

    _write_json(output_plan_path, output_plan)
    _write_json(out_dir / "word_snap_2_fix_word_boundary_fixes.json", audit["word_boundary_fixes"])
    _write_json(out_dir / "word_snap_2_fix_real_residuals.json", audit["real_residuals"])
    _write_json(out_dir / "word_snap_2_fix_audit.json", audit)

    _write_report(
        report_path=report_path,
        source_plan_path=plan_path,
        output_plan_path=output_plan_path,
        words_path=words_path,
        residuals_path=residuals_path,
        audit=audit,
    )

    overall = "PASS" if audit["anti_overcut_fail_count"] == 0 and audit["stretched_word_snap_target_count"] == 0 else "FAIL"

    print("PROJECT ZENITH - WORD-SNAP-2-FIX INNER WORD BOUNDARY")
    print(f"source_plan={plan_path}")
    print(f"output_plan={output_plan_path}")
    print(f"report={report_path}")
    print(f"snap_window_seconds={audit['snap_window_seconds']}")
    print(f"max_word_seconds={audit['max_word_seconds']}")
    print(f"input_residual_count={audit['input_residual_count']}")
    print(f"continuous_speech_residual_count={audit['continuous_speech_residual_count']}")
    print(f"word_boundary_snapped_count={audit['word_boundary_snapped_count']}")
    print(f"real_residual_count={audit['real_residual_count']}")
    print(f"stretched_word_snap_target_count={audit['stretched_word_snap_target_count']}")
    print(f"total_abs_delta_seconds={audit['total_abs_delta_seconds']}")
    print(f"duration_delta_seconds={audit['duration_delta_seconds']}")
    print(f"new_planned_output_duration_seconds={audit['new_planned_output_duration_seconds']}")
    print(f"anti_overcut_fail_count={audit['anti_overcut_fail_count']}")
    print(f"overall_status={overall}")

    for item in audit["word_boundary_fixes"][:5]:
        word = item.get("selected_word") if isinstance(item.get("selected_word"), dict) else {}
        print(
            f"WORD_FIX {item.get('segment_id')} {item.get('edge_kind')} "
            f"{item.get('old_seconds')}->{item.get('new_seconds')} "
            f"delta={item.get('delta_seconds')} "
            f"word={word.get('word')} "
            f"word_duration={word.get('duration_seconds')}"
        )

    for item in audit["real_residuals"][:5]:
        print(
            f"REAL_RESIDUAL {item.get('segment_id')} {item.get('edge_kind')} "
            f"old={item.get('old_seconds')} reason={item.get('reason')}"
        )

    return 0 if overall == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
