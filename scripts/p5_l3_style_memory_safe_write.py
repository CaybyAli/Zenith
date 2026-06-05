import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


PHASE = "P5-L3"
MODE = "style_memory_safe_write"
MEMORY_VERSION = "p5_l3_candidate_v1"
OUTPUT_SUBDIR = Path("reports") / "p5_l3_style_memory_safe_write"

INPUT_PATHS = {
    "p5_l2_report": Path("reports") / "p5_l2_analysis_only_dry_run" / "p5_l2_analysis_report.json",
    "gaming_pairs_style_dna": Path("video_configs") / "gaming_pairs_style_dna.json",
    "top_solo_style_dna": Path("video_configs") / "top_solo_style_dna.json",
    "vlog_style_dna": Path("video_configs") / "vlog_style_dna.json",
    "pair_track_truth": Path("video_configs") / "pair_track_truth.json",
}

OUTPUT_NAMES = {
    "candidate": "style_memory_candidate.json",
    "manifest": "style_memory_manifest.json",
    "summary": "style_memory_summary.md",
}

FALSE_SAFETY_FLAGS = {
    "production_files_modified": False,
    "video_configs_modified": False,
    "learning_corpus_modified": False,
    "obsidian_modified_by_script": False,
    "core_modified": False,
    "qwen_used": False,
    "render_used": False,
    "ingest_used": False,
    "music_used": False,
    "autocut_used": False,
    "overnight_started": False,
    "learning_loop_started": False,
    "phase_5_5_used": False,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_repo_relative(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Required input missing: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _resolve_allowed_output_dir(repo_root: Path, output_dir: Path) -> Path:
    repo_root = repo_root.resolve()
    wanted = (repo_root / OUTPUT_SUBDIR).resolve()

    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir

    output_dir = output_dir.resolve()

    if output_dir != wanted:
        raise ValueError(
            "Output dir is not allowed. Expected exactly: "
            f"{OUTPUT_SUBDIR.as_posix()}"
        )

    return output_dir


def _collect_sources(value: Any) -> List[str]:
    sources: List[str] = []

    if isinstance(value, dict):
        source = value.get("source")
        if isinstance(source, str):
            sources.append(source)

        for nested in value.values():
            sources.extend(_collect_sources(nested))

    elif isinstance(value, list):
        for item in value:
            sources.extend(_collect_sources(item))

    return sources


def _count_source_dicts(value: Any) -> int:
    if isinstance(value, dict):
        count = 1 if isinstance(value.get("source"), str) else 0
        for nested in value.values():
            count += _count_source_dicts(nested)
        return count

    if isinstance(value, list):
        return sum(_count_source_dicts(item) for item in value)

    return 0


def _count_entries(value: Any) -> int:
    if isinstance(value, list):
        return len(value)

    if isinstance(value, dict):
        for key in (
            "fingerprint_count",
            "video_count",
            "sample_count",
            "source_count",
            "count",
        ):
            raw_count = value.get(key)
            if isinstance(raw_count, int):
                return raw_count

        for key in ("items", "fingerprints", "sources", "videos", "entries"):
            raw_items = value.get(key)
            if isinstance(raw_items, list):
                return len(raw_items)
            if isinstance(raw_items, dict):
                return len(raw_items)

        source_count = _count_source_dicts(value)
        if source_count:
            return source_count

    return 0


def _count_pair_truth_entries(value: Any) -> int:
    if isinstance(value, list):
        return len(value)

    if not isinstance(value, dict):
        return 0

    for key in ("pairs", "pair_truth", "entries", "truth", "track_truth"):
        raw_items = value.get(key)
        if isinstance(raw_items, list):
            return len(raw_items)
        if isinstance(raw_items, dict):
            return len(raw_items)

    pair_keys = [key for key in value.keys() if str(key).startswith("pair_")]
    if pair_keys:
        return len(pair_keys)

    return 0


def _style_summary(name: str, rel_path: str, data: Any, count: int) -> Dict[str, Any]:
    schema_version: Optional[str] = None
    if isinstance(data, dict) and isinstance(data.get("schema_version"), str):
        schema_version = data["schema_version"]

    sources = _collect_sources(data)

    return {
        "name": name,
        "input_path": rel_path,
        "schema_version": schema_version,
        "count": count,
        "source_examples": sources[:5],
    }


def _find_forbidden_inputs(named_inputs: Dict[str, Any]) -> List[str]:
    found: List[str] = []

    for input_name, payload in named_inputs.items():
        text = json.dumps(payload, ensure_ascii=False).lower()
        if "ali_voice_reference.wav" in text or "ali_voice_reference" in text:
            found.append(f"{input_name}:ali_voice_reference.wav")

    return found


def _build_summary_markdown(manifest: Dict[str, Any], candidate: Dict[str, Any]) -> str:
    counts = manifest["source_counts"]

    lines = [
        "# P5-L3 Style-Memory Safe Write",
        "",
        f"- status: {manifest['status']}",
        f"- phase: {manifest['phase']}",
        f"- mode: {manifest['mode']}",
        f"- memory_version: {candidate['memory_version']}",
        f"- memory_write_target: {manifest['memory_write_target']}",
        f"- writes_only_under: {manifest['writes_only_under']}",
        f"- can_be_used_for_production: {str(candidate['can_be_used_for_production']).lower()}",
        f"- owner_review_required: {str(candidate['owner_review_required']).lower()}",
        "",
        "## Source Counts",
        "",
        f"- pair_fingerprints: {counts['pair_fingerprints']}",
        f"- top_solo_fingerprints: {counts['top_solo_fingerprints']}",
        f"- vlog_fingerprints: {counts['vlog_fingerprints']}",
        f"- pair_truth_entries: {counts['pair_truth_entries']}",
        "",
        "## Safety",
        "",
        "- Kein Render",
        "- Kein Qwen",
        "- Kein Ingest",
        "- Keine Musik",
        "- Kein Overnight",
        "- Kein echter Learning-Loop",
        "- Phase 5.5 nicht benutzt",
        "- Keine Produktionsdateien geändert",
        "",
        "## Outputs",
        "",
    ]

    for output in manifest["outputs_written"]:
        lines.append(f"- {output}")

    if manifest["forbidden_inputs_used"]:
        lines.extend(["", "## Forbidden Inputs", ""])
        for item in manifest["forbidden_inputs_used"]:
            lines.append(f"- {item}")

    if manifest["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in manifest["warnings"]:
            lines.append(f"- {warning}")

    return "\n".join(lines) + "\n"


def build_style_memory_safe_write(repo_root: Path, output_dir: Path) -> Dict[str, Any]:
    repo_root = Path(repo_root).resolve()
    output_dir = _resolve_allowed_output_dir(repo_root, Path(output_dir))

    input_files = {name: repo_root / rel_path for name, rel_path in INPUT_PATHS.items()}
    input_payloads = {name: _read_json(path) for name, path in input_files.items()}

    output_dir.mkdir(parents=True, exist_ok=True)

    pair_count = _count_entries(input_payloads["gaming_pairs_style_dna"])
    top_solo_count = _count_entries(input_payloads["top_solo_style_dna"])
    vlog_count = _count_entries(input_payloads["vlog_style_dna"])
    pair_truth_count = _count_pair_truth_entries(input_payloads["pair_track_truth"])

    source_counts = {
        "pair_fingerprints": pair_count,
        "top_solo_fingerprints": top_solo_count,
        "vlog_fingerprints": vlog_count,
        "pair_truth_entries": pair_truth_count,
    }

    forbidden_inputs_used = _find_forbidden_inputs(input_payloads)
    warnings: List[str] = []
    status = "ok"

    if forbidden_inputs_used:
        status = "error"
        warnings.append("forbidden_ali_voice_reference_detected")

    outputs = {
        "candidate": output_dir / OUTPUT_NAMES["candidate"],
        "manifest": output_dir / OUTPUT_NAMES["manifest"],
        "summary": output_dir / OUTPUT_NAMES["summary"],
    }

    output_rel_paths = [
        _as_repo_relative(outputs["candidate"], repo_root),
        _as_repo_relative(outputs["manifest"], repo_root),
        _as_repo_relative(outputs["summary"], repo_root),
    ]

    input_rel_paths = [
        _as_repo_relative(path, repo_root)
        for path in input_files.values()
    ]

    manifest: Dict[str, Any] = {
        "status": status,
        "phase": PHASE,
        "mode": MODE,
        "memory_write_target": "reports_only_candidate",
        "writes_only_under": OUTPUT_SUBDIR.as_posix(),
        **FALSE_SAFETY_FLAGS,
        "deleted_files": [],
        "inputs_read": input_rel_paths,
        "outputs_written": output_rel_paths,
        "source_counts": source_counts,
        "forbidden_inputs_used": forbidden_inputs_used,
        "warnings": warnings,
        "created_at": _utc_now(),
    }

    candidate: Dict[str, Any] = {
        "source": "P5-L2 report + aggregated style dna",
        "memory_version": MEMORY_VERSION,
        "status": "candidate_only",
        "phase": PHASE,
        "mode": MODE,
        "memory_write_target": "reports_only_candidate",
        "can_be_used_for_production": False,
        "owner_review_required": True,
        "production_files_modified": False,
        "video_configs_modified": False,
        "learning_corpus_modified": False,
        "obsidian_modified_by_script": False,
        "core_modified": False,
        "source_counts": source_counts,
        "style_categories": {
            "gaming_pairs": _style_summary(
                "gaming_pairs",
                _as_repo_relative(input_files["gaming_pairs_style_dna"], repo_root),
                input_payloads["gaming_pairs_style_dna"],
                pair_count,
            ),
            "top_solo": _style_summary(
                "top_solo",
                _as_repo_relative(input_files["top_solo_style_dna"], repo_root),
                input_payloads["top_solo_style_dna"],
                top_solo_count,
            ),
            "vlog": _style_summary(
                "vlog",
                _as_repo_relative(input_files["vlog_style_dna"], repo_root),
                input_payloads["vlog_style_dna"],
                vlog_count,
            ),
        },
        "p5_l2_report": {
            "input_path": _as_repo_relative(input_files["p5_l2_report"], repo_root),
            "status": input_payloads["p5_l2_report"].get("status")
            if isinstance(input_payloads["p5_l2_report"], dict)
            else None,
        },
        "pair_truth": {
            "input_path": _as_repo_relative(input_files["pair_track_truth"], repo_root),
            "entry_count": pair_truth_count,
        },
        "safety_flags": {
            **FALSE_SAFETY_FLAGS,
            "deleted_files": [],
            "forbidden_inputs_used": forbidden_inputs_used,
        },
        "created_at": manifest["created_at"],
    }

    _write_json(outputs["candidate"], candidate)
    _write_json(outputs["manifest"], manifest)
    outputs["summary"].write_text(
        _build_summary_markdown(manifest, candidate),
        encoding="utf-8",
    )

    return manifest


def main(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    parser = argparse.ArgumentParser(description="P5-L3 style memory safe write")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    manifest = build_style_memory_safe_write(
        repo_root=Path(args.repo_root),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return manifest


if __name__ == "__main__":
    main()
