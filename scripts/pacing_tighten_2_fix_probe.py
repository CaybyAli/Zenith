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

from core.pacing_tighten import PacingTightenConfig, apply_pacing_tighten, normalize_intervals


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def looks_like_segments(value: Any) -> bool:
    return isinstance(value, list) and value and isinstance(value[0], dict) and (
        any(k in value[0] for k in ("start_seconds", "start", "start_time"))
        and any(k in value[0] for k in ("end_seconds", "end", "end_time"))
    )


def find_segments(raw: Any) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    keys = ("timeline_segments", "segments", "selected_segments", "final_segments", "clips", "timeline")
    if isinstance(raw, dict):
        for key in keys:
            if looks_like_segments(raw.get(key)):
                return raw, key, raw[key]
        for key, value in raw.items():
            if looks_like_segments(value):
                return raw, key, value
        for value in raw.values():
            if isinstance(value, dict):
                try:
                    return find_segments(value)
                except ValueError:
                    pass
    raise ValueError("Keine Segmentliste gefunden")


def extract_lists_by_key(raw: Any, source: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def walk(value: Any, key_path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_key_path = f"{key_path}.{key}".lower()
                if isinstance(child, list):
                    key_lower = str(key).lower()
                    if (
                        ("speech" in key_lower or "owner" in key_lower or "track1" in key_lower or "track_1" in key_lower)
                        and "silence" not in key_lower
                        and "gap" not in key_lower
                    ):
                        rows.extend(normalize_intervals(child, source=f"{source}:{child_key_path}"))
                walk(child, child_key_path)
        elif isinstance(value, list):
            for item in value:
                walk(item, key_path)

    walk(raw, "")
    return rows


def owner_candidate_score(path: Path, rows: list[dict[str, Any]]) -> int:
    text = path.as_posix().lower()

    if "silence" in text or "gap" in text or "dead" in text:
        return -999

    score = 0

    for token in ("owner", "track1", "track_1", "mic_primary", "primary", "speech_1"):
        if token in text:
            score += 20

    for token in ("combined", "friend", "discord", "track2", "track_2"):
        if token in text:
            score -= 30

    plausible = [row for row in rows if 5.0 <= row["start_seconds"] <= 45.0]
    if plausible:
        score += 100

    early_bad = [row for row in rows if row["start_seconds"] < 3.0]
    if early_bad:
        score -= 25

    score += min(len(rows), 50)
    return score


def autodetect_owner_speech() -> tuple[list[dict[str, Any]], str]:
    roots = [
        Path("reports/combined_speech"),
        Path("reports/speech_1_fix_vad"),
        Path("reports/speech_1_transcript"),
        Path("reports/speech_1_transcript_largev3"),
        Path("reports/phase5"),
    ]

    candidates: list[tuple[int, Path, list[dict[str, Any]]]] = []

    for root in roots:
        if not root.exists():
            continue

        for path in root.rglob("*.json"):
            path_text = path.as_posix().lower()

            if "silence" in path_text or "gap" in path_text or "dead" in path_text:
                continue

            try:
                raw = read_json(path)
            except Exception:
                continue

            rows = extract_lists_by_key(raw, path)
            if not rows:
                rows = normalize_intervals(raw, source=str(path))

            rows = [
                row for row in rows
                if row["end_seconds"] > row["start_seconds"]
            ]

            if not rows:
                continue

            plausible = [row for row in rows if 5.0 <= row["start_seconds"] <= 45.0]
            if not plausible:
                continue

            score = owner_candidate_score(path, rows)
            if score > 0:
                candidates.append((score, path, rows))

    candidates.sort(key=lambda item: item[0], reverse=True)

    if not candidates:
        raise RuntimeError(
            "OWNER-SPEECH nicht gefunden. Wichtig: keine silence_gaps-Datei benutzen. "
            "Suche eine echte Track1/Owner-Speech-Regions JSON und starte Probe mit --owner-speech <Pfad>."
        )

    _, path, rows = candidates[0]
    return rows, str(path)


def load_owner_speech(path_value: str | None) -> tuple[list[dict[str, Any]], str]:
    if not path_value:
        return autodetect_owner_speech()

    path = Path(path_value)
    if "silence" in path.as_posix().lower() or "gap" in path.as_posix().lower():
        raise RuntimeError(f"OWNER-SPEECH Quelle abgelehnt, weil silence/gap im Pfad steht: {path}")

    raw = read_json(path)
    rows = extract_lists_by_key(raw, path)
    if not rows:
        rows = normalize_intervals(raw, source=str(path))

    return rows, str(path)


def extract_payoff_tails(raw: Any) -> list[dict[str, Any]]:
    rows = []
    for row in normalize_intervals(raw, source=""):
        text = json.dumps(row, ensure_ascii=False).lower()
        if "payoff_tail" in text or "round_payoff_tail" in text:
            clean = dict(row)
            clean["payoff_tail"] = True
            rows.append(clean)
    return rows


def make_report(report_path: Path, audit: dict[str, Any], output_plan: Path) -> None:
    lines: list[str] = []
    lines.append("PROJECT ZENITH - PACING TIGHTEN 2 FIX REPORT")
    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"- input_old_segment_count={audit['old_segment_count']}")
    lines.append(f"- output_new_segment_count={audit['new_segment_count']}")
    lines.append(f"- old_duration_seconds={audit['old_duration_seconds']}")
    lines.append(f"- new_duration_seconds={audit['new_duration_seconds']}")
    lines.append(f"- removed_dead_seconds={audit['removed_dead_seconds']}")
    lines.append(f"- removed_speech_seconds={audit['removed_speech_seconds']}")
    lines.append(f"- sil_min_seconds={audit['sil_min_seconds']}")
    lines.append(f"- action_floor_percentile={audit['action_floor_percentile']}")
    lines.append(f"- action_floor={audit['action_floor']}")
    lines.append("")
    lines.append("OWNER INTRO START")
    lines.append(f"- intro_start_seconds={audit['intro_start_seconds']}")
    lines.append(f"- intro_start_speaker={audit['intro_start_speaker']}")
    lines.append(f"- owner_speech_source={audit['owner_speech_source']}")
    lines.append("")
    lines.append("HARTE CHECKS")
    for key, value in audit["hard_checks"].items():
        lines.append(f"- {key}={value}")
    lines.append("")
    lines.append("PER-STRECKE")
    for row in audit["per_segment"]:
        lines.append(
            f"- {row['source_segment_id']}: "
            f"alt={row['old_start_seconds']}->{row['old_end_seconds']} "
            f"neu={row['new_start_seconds']}->{row['new_end_seconds']} "
            f"class={row['classification']} reasons={row['classification_reasons']} "
            f"internal_cuts={row['internal_cut_count']} "
            f"removed_dead_est={row['removed_dead_seconds_estimate']} "
            f"ops={row['operations']}"
        )
        for cut in row["internal_cuts"]:
            lines.append(f"  - internal_cut={cut}")
    lines.append("")
    lines.append("OUTPUT SEGMENTS")
    for row in audit["output_segments"]:
        lines.append(
            f"- {row['segment_id']} {row['start_seconds']}->{row['end_seconds']} "
            f"dur={row['duration_seconds']} "
            f"class={row.get('metadata', {}).get('pacing_tighten_classification')}"
        )
    lines.append("")
    lines.append(f"output_plan={output_plan}")
    lines.append(f"overall_pass={audit['overall_pass']}")
    lines.append("STOPP: Kein Commit.")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default="reports/pacing_tighten/pacing_tighten_1_final_editorial_plan.json")
    parser.add_argument("--speech", default="reports/combined_speech/combined_speech_regions.json")
    parser.add_argument("--owner-speech", default=None)
    parser.add_argument("--raw-windows", default="reports/dead_air_1/fortnite_g6_raw_windows_for_dead_air_1.json")
    parser.add_argument("--payoff2", default="reports/payoff_2/payoff_2_g8_timeline_plan_reaction_gated.json")
    parser.add_argument("--out-dir", default="reports/pacing_tighten_2_fix")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    speech_path = Path(args.speech)
    raw_path = Path(args.raw_windows)
    payoff_path = Path(args.payoff2)
    out_dir = Path(args.out_dir)

    for path in (plan_path, speech_path, raw_path):
        if not path.exists():
            print(f"STOPP: Missing input {path}")
            return 2

    try:
        owner_rows, owner_source = load_owner_speech(args.owner_speech)
    except Exception as exc:
        print(f"STOPP: {exc}")
        return 2

    source_plan = read_json(plan_path)
    output_plan = deepcopy(source_plan)

    parent, key, ranked_segments = find_segments(output_plan)
    payoff_tails = extract_payoff_tails(read_json(payoff_path)) if payoff_path.exists() else []

    output_segments, audit = apply_pacing_tighten(
        ranked_segments=ranked_segments,
        combined_speech_regions=read_json(speech_path),
        owner_speech_regions=owner_rows,
        owner_speech_source=owner_source,
        raw_windows=read_json(raw_path),
        payoff_tail_segments=payoff_tails,
        config=PacingTightenConfig(),
    )

    parent[key] = output_segments
    output_plan["pacing_tighten_2_fix_audit_summary"] = {
        k: v for k, v in audit.items()
        if k not in {"output_segments", "per_segment"}
    }
    output_plan["pacing_tighten_2_fix_rows"] = audit["per_segment"]

    out_plan = out_dir / "pacing_tighten_2_fix_final_editorial_plan.json"
    audit_path = out_dir / "pacing_tighten_2_fix_audit.json"
    report_path = out_dir / "pacing_tighten_2_fix_report.txt"

    write_json(out_plan, output_plan)
    write_json(audit_path, audit)
    make_report(report_path, audit, out_plan)

    print("PROJECT ZENITH - PACING TIGHTEN 2 FIX")
    print(f"input_plan={plan_path}")
    print(f"output_plan={out_plan}")
    print(f"report={report_path}")
    print(f"owner_speech_source={owner_source}")
    print(f"intro_start_seconds={audit['intro_start_seconds']}")
    print(f"old_segment_count={audit['old_segment_count']}")
    print(f"new_segment_count={audit['new_segment_count']}")
    print(f"old_duration_seconds={audit['old_duration_seconds']}")
    print(f"new_duration_seconds={audit['new_duration_seconds']}")
    print(f"removed_dead_seconds={audit['removed_dead_seconds']}")
    print(f"removed_speech_seconds={audit['removed_speech_seconds']}")

    for key, value in audit["hard_checks"].items():
        print(f"{key}={value}")

    print(f"overall_pass={audit['overall_pass']}")
    print("STOPP: Kein Commit.")

    return 0 if audit["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
