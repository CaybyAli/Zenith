from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PHASE = "P5-L2"
MODE = "analysis_only_dry_run"
DEFAULT_OUTPUT_DIR = Path("reports") / "p5_l2_analysis_only_dry_run"

STYLE_DNA_FILES = {
    "gaming_pairs": Path("video_configs") / "gaming_pairs_style_dna.json",
    "top_solo": Path("video_configs") / "top_solo_style_dna.json",
    "vlogs": Path("video_configs") / "vlog_style_dna.json",
}

PAIR_TRUTH_PATH = Path("video_configs") / "pair_track_truth.json"

FINGERPRINT_ROOTS = {
    "pairs": Path("learning_corpus") / "pairs",
    "top_solo": Path("learning_corpus") / "top_solo",
    "vlogs": Path("learning_corpus") / "vlogs",
}

FORBIDDEN_ALI_SOURCE_NAME = "ali_voice_reference.wav"


def _safe_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def validate_output_dir(repo_root: Path | str, output_dir: Path | str) -> Path:
    root = Path(repo_root).resolve()
    raw = Path(output_dir)
    out = raw if raw.is_absolute() else root / raw
    out = out.resolve()

    try:
        rel = out.relative_to(root)
    except ValueError as exc:
        raise ValueError("output-dir must be inside repo-root") from exc

    if rel.as_posix() != DEFAULT_OUTPUT_DIR.as_posix():
        raise ValueError("output-dir must be exactly reports/p5_l2_analysis_only_dry_run")

    return out


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _json_key_count(value: Any) -> int:
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, list):
        return len(value)
    return 0


def _find_style_fingerprints(repo_root: Path, category: str) -> list[Path]:
    root = repo_root / FINGERPRINT_ROOTS[category]
    if not root.exists():
        return []
    return sorted(root.glob("*/style_fingerprint.json"))


def _make_base_report() -> dict[str, Any]:
    return {
        "status": "ok",
        "phase": PHASE,
        "mode": MODE,
        "qwen_used": False,
        "render_used": False,
        "ingest_used": False,
        "music_used": False,
        "autocut_used": False,
        "learning_loop_started": False,
        "phase_5_5_used": False,
        "deleted_files": [],
        "writes_only_under": DEFAULT_OUTPUT_DIR.as_posix(),
        "inputs_read": [],
        "counts": {
            "pair_fingerprints": 0,
            "top_solo_fingerprints": 0,
            "vlog_fingerprints": 0,
            "pair_truth_entries": 0,
        },
        "style_dna_files": {},
        "pair_truth_validation": {},
        "forbidden_inputs_used": [],
        "warnings": [],
    }


def _record_input(report: dict[str, Any], path: Path, repo_root: Path) -> None:
    rel = _safe_relative(path, repo_root)
    if rel not in report["inputs_read"]:
        report["inputs_read"].append(rel)


def _scan_for_forbidden_input(report: dict[str, Any]) -> None:
    existing_hits = list(report.get("forbidden_inputs_used", []))
    input_hits = [
        value
        for value in report["inputs_read"]
        if FORBIDDEN_ALI_SOURCE_NAME.lower() in value.lower()
    ]
    hits = existing_hits + input_hits
    report["forbidden_inputs_used"] = sorted(set(hits))
    if hits:
        report["status"] = "error"
        if "Forbidden Ali reference input was detected." not in report["warnings"]:
            report["warnings"].append("Forbidden Ali reference input was detected.")


def _load_style_dna_files(repo_root: Path, report: dict[str, Any]) -> None:
    for name, rel_path in STYLE_DNA_FILES.items():
        path = repo_root / rel_path
        entry: dict[str, Any] = {
            "path": rel_path.as_posix(),
            "exists": path.exists(),
            "top_level_type": None,
            "top_level_count": 0,
            "keys": [],
        }

        if not path.exists():
            report["status"] = "error"
            report["warnings"].append(f"Missing style DNA file: {rel_path.as_posix()}")
            report["style_dna_files"][name] = entry
            continue

        data = _read_json(path)
        _record_input(report, path, repo_root)

        entry["top_level_type"] = type(data).__name__
        entry["top_level_count"] = _json_key_count(data)
        if isinstance(data, dict):
            entry["keys"] = sorted(str(key) for key in data.keys())

        report["style_dna_files"][name] = entry


def _load_pair_truth(repo_root: Path, report: dict[str, Any]) -> None:
    path = repo_root / PAIR_TRUTH_PATH
    validation: dict[str, Any] = {
        "path": PAIR_TRUTH_PATH.as_posix(),
        "exists": path.exists(),
        "schema_shape": None,
        "entry_count": 0,
        "ali_sources": {},
        "invalid_ali_sources": [],
        "uses_forbidden_ali_reference": False,
    }

    if not path.exists():
        report["status"] = "error"
        report["warnings"].append("Missing pair_track_truth.json.")
        report["pair_truth_validation"] = validation
        return

    data = _read_json(path)
    _record_input(report, path, repo_root)

    if not isinstance(data, dict):
        report["status"] = "error"
        report["warnings"].append("pair_track_truth.json is not a JSON object.")
        report["pair_truth_validation"] = validation
        return

    if isinstance(data.get("pairs"), dict):
        pair_entries = data["pairs"]
        validation["schema_shape"] = "metadata_with_pairs"
    else:
        pair_entries = data
        validation["schema_shape"] = "flat_pair_map"

    validation["entry_count"] = len(pair_entries)
    report["counts"]["pair_truth_entries"] = len(pair_entries)

    for pair_id, entry in sorted(pair_entries.items()):
        ali_source = None
        if isinstance(entry, dict):
            ali_source = entry.get("ali_source")

        validation["ali_sources"][str(pair_id)] = ali_source

        if ali_source not in {"a0", "a1", "a2", "a3"}:
            validation["invalid_ali_sources"].append(
                {"pair_id": str(pair_id), "ali_source": ali_source}
            )

        if isinstance(ali_source, str) and FORBIDDEN_ALI_SOURCE_NAME.lower() in ali_source.lower():
            validation["uses_forbidden_ali_reference"] = True
            report["forbidden_inputs_used"].append(f"{pair_id}:{ali_source}")

    if validation["invalid_ali_sources"]:
        report["status"] = "error"
        report["warnings"].append("Invalid ali_source values found in pair truth.")

    if validation["uses_forbidden_ali_reference"]:
        report["status"] = "error"
        report["warnings"].append("Forbidden Ali reference was used as ali_source.")

    report["pair_truth_validation"] = validation

def _load_fingerprint_counts(repo_root: Path, report: dict[str, Any]) -> None:
    pair_fps = _find_style_fingerprints(repo_root, "pairs")
    solo_fps = _find_style_fingerprints(repo_root, "top_solo")
    vlog_fps = _find_style_fingerprints(repo_root, "vlogs")

    report["counts"]["pair_fingerprints"] = len(pair_fps)
    report["counts"]["top_solo_fingerprints"] = len(solo_fps)
    report["counts"]["vlog_fingerprints"] = len(vlog_fps)

    for path in pair_fps + solo_fps + vlog_fps:
        _record_input(report, path, repo_root)


def build_report(repo_root: Path | str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    report = _make_base_report()

    _load_style_dna_files(root, report)
    _load_pair_truth(root, report)
    _load_fingerprint_counts(root, report)
    _scan_for_forbidden_input(report)

    report["inputs_read"] = sorted(report["inputs_read"])
    return report


def _summary_lines(report: dict[str, Any]) -> list[str]:
    safety_flags = [
        "qwen_used",
        "render_used",
        "ingest_used",
        "music_used",
        "autocut_used",
        "learning_loop_started",
        "phase_5_5_used",
    ]

    lines = [
        "# P5-L2 Analysis-only Dry-run Summary",
        "",
        f"- Status: {report['status']}",
        f"- Phase: {report['phase']}",
        f"- Mode: {report['mode']}",
        "",
        "## Counts",
        "",
        f"- Pair fingerprints: {report['counts']['pair_fingerprints']}",
        f"- Top solo fingerprints: {report['counts']['top_solo_fingerprints']}",
        f"- Vlog fingerprints: {report['counts']['vlog_fingerprints']}",
        f"- Pair truth entries: {report['counts']['pair_truth_entries']}",
        "",
        "## Safety Flags",
        "",
    ]

    for key in safety_flags:
        lines.append(f"- {key}: {report[key]}")

    lines.extend(
        [
            f"- deleted_files: {report['deleted_files']}",
            "",
            "## Inputs Read",
            "",
        ]
    )

    for item in report["inputs_read"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Warnings",
            "",
        ]
    )

    if report["warnings"]:
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Safety Statement",
            "",
            "- No Qwen was used.",
            "- No visual output process was used.",
            "- No ingest was used.",
            "- No loop was started.",
        ]
    )

    return lines


def write_report(
    report: dict[str, Any],
    output_dir: Path | str,
    repo_root: Path | str,
) -> tuple[Path, Path]:
    out_dir = validate_output_dir(repo_root, output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "p5_l2_analysis_report.json"
    md_path = out_dir / "p5_l2_analysis_summary.md"

    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text("\n".join(_summary_lines(report)) + "\n", encoding="utf-8")

    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="P5-L2 analysis-only dry-run.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR.as_posix(),
    )
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--write-report", action="store_true")

    args = parser.parse_args()

    report = build_report(args.repo_root)

    if not args.no_write or args.write_report:
        json_path, md_path = write_report(report, args.output_dir, args.repo_root)
        print(f"report_json={json_path}")
        print(f"summary_md={md_path}")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))

    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
