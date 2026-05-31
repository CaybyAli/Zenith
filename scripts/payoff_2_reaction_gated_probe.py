from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.payoff_reaction_tail import (
    apply_round_payoff_tails_with_reaction_gate,
    normalize_reaction_events,
    normalize_speech_segments,
    normalize_words,
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _latest_g8_plan() -> Path:
    candidates = sorted(
        Path("reports/g8_assembly").glob("*_g8_timeline_plan.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No G8 timeline plan found in reports/g8_assembly/*_g8_timeline_plan.json")
    return candidates[0]


def _media_duration_from_speech_report(path: Path) -> float | None:
    if not path.exists():
        return None
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if line.startswith("media_duration_seconds="):
            return float(line.split("=", 1)[1].strip())
    return None


def _load_previous_payoff1_seconds(path: Path) -> float | None:
    if not path.exists():
        return None
    try:
        data = _read_json(path)
    except Exception:
        return None
    contract = data.get("payoff_tail_contract") if isinstance(data, Mapping) else None
    if isinstance(contract, Mapping) and contract.get("added_tail_seconds") is not None:
        return float(contract["added_tail_seconds"])
    return None


def _find_death_tail(payoff_tails: list[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    for tail in payoff_tails:
        if abs(float(tail.get("start_seconds") or 0.0) - 1792.0) <= 5.0:
            return tail
    return payoff_tails[-1] if payoff_tails else None


def _write_report(
    *,
    report_path: Path,
    source_plan_path: Path,
    output_plan_path: Path,
    speech_segments_path: Path,
    reactions_path: Path,
    previous_payoff1_seconds: float | None,
    plan: dict[str, Any],
) -> None:
    audit = plan.get("payoff_tail_audit") or {}
    contract = plan.get("payoff_tail_contract") or {}
    original_anti = plan.get("anti_overcut_audit") or {}
    evaluations = list(audit.get("evaluations") or [])
    payoff_tails = list(plan.get("payoff_tails") or [])
    death_tail = _find_death_tail(payoff_tails)

    lines: list[str] = []
    lines.append("PROJECT ZENITH - PAYOFF-2 REACTION-GATED REPORT")
    lines.append("")
    lines.append(f"source_g8_plan={source_plan_path}")
    lines.append(f"output_plan={output_plan_path}")
    lines.append(f"speech_segments={speech_segments_path}")
    lines.append(f"reaction_events={reactions_path}")
    lines.append(f"engine={audit.get('engine')}")
    lines.append(f"tail_max_seconds={audit.get('tail_max_seconds')}")
    lines.append(f"reaction_min_intensity={audit.get('reaction_min_intensity')}")
    lines.append("")
    lines.append("DURATION")
    lines.append(f"payoff_1_added_tail_seconds_before={previous_payoff1_seconds if previous_payoff1_seconds is not None else 'unknown'}")
    lines.append(f"payoff_2_added_tail_seconds_after={contract.get('added_tail_seconds')}")
    lines.append(f"original_planned_output_duration_seconds={contract.get('original_planned_output_duration_seconds')}")
    lines.append(f"new_planned_output_duration_seconds={contract.get('new_planned_output_duration_seconds')}")
    lines.append("")
    lines.append("ANTI-OVERCUT")
    lines.append(f"original_g8_anti_overcut_fail_count={original_anti.get('fail_count')}")
    lines.append(f"payoff_2_anti_overcut_fail_count={audit.get('anti_overcut_fail_count')}")
    lines.append(f"removed_active_play_seconds={audit.get('removed_active_play_seconds')}")
    lines.append("")
    lines.append("PER-BLOCK REACTION GATE TABLE")
    lines.append("block_id | block_end | window | best_reaction | fusion | mic_rise | tail_added | reason")
    lines.append("---|---:|---:|---|---:|---:|---|---")
    for item in evaluations:
        lines.append(
            f"{item.get('block_id')} | "
            f"{item.get('original_block_end_seconds')} | "
            f"{item.get('tail_window_start_seconds')}->{item.get('tail_window_end_seconds')} | "
            f"{item.get('best_reaction_intensity')} | "
            f"{item.get('best_reaction_fusion_score')} | "
            f"{item.get('best_reaction_mic_audio_rise_db')} | "
            f"{item.get('tail_added')} | "
            f"{item.get('reason')}"
        )
    lines.append("")
    lines.append("PAYOFF TAILS")
    if not payoff_tails:
        lines.append("- none")
    for tail in payoff_tails:
        meta = tail.get("metadata") or {}
        reaction = meta.get("best_reaction") or {}
        lines.append(
            "- "
            f"block_id={tail.get('block_id')} "
            f"start={tail.get('start_seconds')} "
            f"end={tail.get('end_seconds')} "
            f"duration={tail.get('duration_seconds')} "
            f"segment_role={tail.get('segment_role')} "
            f"reaction={str(reaction.get('intensity') or '').upper()} "
            f"fusion={reaction.get('fusion_score')} "
            f"mic_rise={reaction.get('mic_audio_rise_db')}"
        )
        text = str(meta.get("speech_text") or "").strip()
        if text:
            lines.append(f"  speech_text={text}")
    lines.append("")
    lines.append("VALIDATION - DEATH PAYOFF")
    if death_tail is None:
        lines.append("- NOT_FOUND")
    else:
        meta = death_tail.get("metadata") or {}
        reaction = meta.get("best_reaction") or {}
        lines.append(f"- block_id={death_tail.get('block_id')}")
        lines.append(f"- start={death_tail.get('start_seconds')}")
        lines.append(f"- end={death_tail.get('end_seconds')}")
        lines.append(f"- duration={death_tail.get('duration_seconds')}")
        lines.append(f"- reaction_intensity={str(reaction.get('intensity') or '').upper()}")
        lines.append(f"- reaction_fusion={reaction.get('fusion_score')}")
        lines.append(f"- reaction_mic_rise={reaction.get('mic_audio_rise_db')}")
        lines.append(f"- text={str(meta.get('speech_text') or '').strip()}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"tail_count={audit.get('tail_count')}")
    lines.append(f"added_tail_seconds={audit.get('added_tail_seconds')}")
    lines.append(f"new_total_duration={contract.get('new_planned_output_duration_seconds')}")
    lines.append(f"anti_overcut_fail_count={audit.get('anti_overcut_fail_count')}")
    lines.append("")
    lines.append("OUTPUTS")
    lines.append(str(output_plan_path))
    lines.append(str(report_path))
    lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--g8-plan", default=None)
    parser.add_argument("--speech-segments", default="reports/speech_1_transcript/fortnite_speech_segments.json")
    parser.add_argument("--words-json", default="reports/speech_1_transcript/fortnite_words.json")
    parser.add_argument("--speech-report", default="reports/speech_1_transcript/speech_1_report.txt")
    parser.add_argument("--reaction-events", default="reports/reaction_adaptive/reaction_adaptive_fortnite_reactions.json")
    parser.add_argument("--previous-payoff1-plan", default="reports/payoff_1/payoff_1_g8_timeline_plan_with_payoff_tails.json")
    parser.add_argument("--out-dir", default="reports/payoff_2")
    parser.add_argument("--tail-max-seconds", type=float, default=20.0)
    parser.add_argument("--reaction-min-intensity", default="medium")
    parser.add_argument("--media-duration-seconds", type=float, default=None)
    args = parser.parse_args(argv)

    g8_plan_path = Path(args.g8_plan) if args.g8_plan else _latest_g8_plan()
    speech_segments_path = Path(args.speech_segments)
    words_path = Path(args.words_json)
    speech_report_path = Path(args.speech_report)
    reactions_path = Path(args.reaction_events)
    previous_payoff1_path = Path(args.previous_payoff1_plan)
    out_dir = Path(args.out_dir)

    if not g8_plan_path.exists():
        raise FileNotFoundError(f"G8 plan not found: {g8_plan_path}")
    if not speech_segments_path.exists():
        raise FileNotFoundError(f"speech_segments not found: {speech_segments_path}")
    if not reactions_path.exists():
        raise FileNotFoundError(f"reaction events not found: {reactions_path}")

    plan = _read_json(g8_plan_path)
    words = normalize_words(_read_json(words_path)) if words_path.exists() else []
    speech_segments = normalize_speech_segments(_read_json(speech_segments_path), words=words)
    reaction_events = normalize_reaction_events(_read_json(reactions_path))

    media_duration = args.media_duration_seconds
    if media_duration is None:
        media_duration = _media_duration_from_speech_report(speech_report_path)
    if media_duration is None:
        media_duration = max(
            [float(item.get("end_seconds") or 0.0) for item in speech_segments]
            + [float(item.get("end_seconds") or 0.0) for item in plan.get("timeline_segments") or [] if isinstance(item, Mapping)]
            + [0.0]
        )

    new_plan = apply_round_payoff_tails_with_reaction_gate(
        plan,
        speech_segments,
        reaction_events,
        media_duration_seconds=float(media_duration),
        tail_max_seconds=args.tail_max_seconds,
        reaction_min_intensity=args.reaction_min_intensity,
    )

    output_plan_path = out_dir / "payoff_2_g8_timeline_plan_reaction_gated.json"
    report_path = out_dir / "payoff_2_report.txt"

    _write_json(output_plan_path, new_plan)

    _write_report(
        report_path=report_path,
        source_plan_path=g8_plan_path,
        output_plan_path=output_plan_path,
        speech_segments_path=speech_segments_path,
        reactions_path=reactions_path,
        previous_payoff1_seconds=_load_previous_payoff1_seconds(previous_payoff1_path),
        plan=new_plan,
    )

    audit = new_plan.get("payoff_tail_audit") or {}
    contract = new_plan.get("payoff_tail_contract") or {}

    print("PROJECT ZENITH - PAYOFF-2 REACTION-GATED")
    print(f"g8_plan={g8_plan_path}")
    print(f"reaction_events={reactions_path}")
    print(f"output_plan={output_plan_path}")
    print(f"report={report_path}")
    print(f"tail_count={audit.get('tail_count')}")
    print(f"added_tail_seconds={audit.get('added_tail_seconds')}")
    print(f"new_planned_output_duration_seconds={contract.get('new_planned_output_duration_seconds')}")
    print(f"payoff_2_anti_overcut_fail_count={audit.get('anti_overcut_fail_count')}")

    for item in audit.get("evaluations") or []:
        print(
            f"{item.get('block_id')} end={item.get('original_block_end_seconds')} "
            f"reaction={item.get('best_reaction_intensity')} "
            f"fusion={item.get('best_reaction_fusion_score')} "
            f"mic={item.get('best_reaction_mic_audio_rise_db')} "
            f"tail_added={item.get('tail_added')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
