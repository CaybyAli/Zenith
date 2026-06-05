from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PHASE = "P5-L5"
MODE = "overnight_dry_run"
ALLOWED_OUTPUT_REL = Path("reports") / "p5_l5_overnight_dry_run"

OPTIONAL_REPORTS = [
    Path("reports") / "p5_l2_analysis_only_dry_run" / "p5_l2_analysis_report.json",
    Path("reports") / "p5_l3_style_memory_safe_write" / "style_memory_candidate.json",
    Path("reports") / "p5_l3_style_memory_safe_write" / "style_memory_manifest.json",
    Path("reports") / "p5_l4_qwen_analysis_only_evaluator" / "qwen_analysis_manifest.json",
    Path("reports") / "p5_l4_qwen_analysis_only_evaluator" / "qwen_analysis_report.json",
]

FINGERPRINT_SOURCES = [
    ("pair", Path("learning_corpus") / "pairs"),
    ("top_solo", Path("learning_corpus") / "top_solo"),
    ("vlog", Path("learning_corpus") / "vlogs"),
]

FORBIDDEN_INPUT_MARKERS = [
    "ali_voice_reference.wav",
    "phase5.5",
    "phase 5.5",
    "phase_5_5",
    "music_reference",
    "music_audio_path",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve_output_dir(repo_root: Path, output_dir: str | Path) -> Path:
    raw = Path(output_dir)
    candidate = raw if raw.is_absolute() else repo_root / raw
    resolved = candidate.resolve()
    allowed = (repo_root / ALLOWED_OUTPUT_REL).resolve()
    if resolved != allowed:
        raise ValueError(
            "output_dir_must_be_reports_p5_l5_overnight_dry_run"
        )
    return resolved


def _read_json(path: Path, repo_root: Path, inputs_read: list[str], warnings: list[str]) -> Any:
    inputs_read.append(_rel(path, repo_root))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        warnings.append(f"invalid_json: {_rel(path, repo_root)}")
        return None


def _string_values(payload: Any) -> list[str]:
    values: list[str] = []
    if isinstance(payload, str):
        values.append(payload)
    elif isinstance(payload, dict):
        for value in payload.values():
            values.extend(_string_values(value))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(_string_values(value))
    return values


def _detect_forbidden_input(path: Path, payload: Any, repo_root: Path) -> list[str]:
    hits: list[str] = []
    text_values = [_rel(path, repo_root), *_string_values(payload)]
    lowered_values = [value.lower() for value in text_values]
    for marker in FORBIDDEN_INPUT_MARKERS:
        marker_lower = marker.lower()
        if any(marker_lower in value for value in lowered_values):
            hits.append(marker)
    return sorted(set(hits))


def _collect_optional_reports(
    repo_root: Path,
    inputs_read: list[str],
    warnings: list[str],
) -> None:
    for rel_path in OPTIONAL_REPORTS:
        path = repo_root / rel_path
        if not path.exists():
            warnings.append(f"missing_optional_report: {rel_path.as_posix()}")
            continue
        _read_json(path, repo_root, inputs_read, warnings)


def _collect_planned_items(
    repo_root: Path,
    max_items: int,
    inputs_read: list[str],
    warnings: list[str],
    forbidden_inputs_used: list[str],
) -> list[dict[str, Any]]:
    planned_items: list[dict[str, Any]] = []

    for category, base_rel in FINGERPRINT_SOURCES:
        if len(planned_items) >= max_items:
            break

        base = repo_root / base_rel
        if not base.exists():
            warnings.append(f"missing_fingerprint_folder: {base_rel.as_posix()}")
            continue

        for path in sorted(base.glob("*/style_fingerprint.json")):
            if len(planned_items) >= max_items:
                break

            payload = _read_json(path, repo_root, inputs_read, warnings)
            hits = _detect_forbidden_input(path, payload, repo_root)
            for hit in hits:
                forbidden_inputs_used.append(f"{_rel(path, repo_root)}::{hit}")

            planned_items.append(
                {
                    "item_id": path.parent.name,
                    "category": category,
                    "source": _rel(path, repo_root),
                    "action": "analysis_planning_only",
                    "video_file_opened": False,
                    "audio_file_opened": False,
                    "qwen_action": False,
                    "render_action": False,
                    "ingest_action": False,
                    "music_action": False,
                    "phase_5_5_action": False,
                }
            )

    return planned_items


def _base_manifest(max_items: int) -> dict[str, Any]:
    return {
        "status": "ok",
        "phase": PHASE,
        "mode": MODE,
        "dry_run_only": True,
        "real_overnight_started": False,
        "overnight_started": False,
        "bounded_run": True,
        "max_items": max_items,
        "items_planned": 0,
        "items_processed": 0,
        "stop_file_supported": True,
        "stop_file_detected": False,
        "timeout_guard_enabled": True,
        "qwen_used": False,
        "qwen_autocut_used": False,
        "render_used": False,
        "ingest_used": False,
        "music_used": False,
        "autocut_used": False,
        "learning_loop_started": False,
        "phase_5_5_used": False,
        "external_network_used": False,
        "api_key_used": False,
        "production_files_modified": False,
        "video_configs_modified": False,
        "learning_corpus_modified": False,
        "obsidian_modified_by_script": False,
        "core_modified": False,
        "deleted_files": [],
        "writes_only_under": ALLOWED_OUTPUT_REL.as_posix(),
        "inputs_read": [],
        "outputs_written": [],
        "planned_items": [],
        "processed_items": [],
        "warnings": [],
        "forbidden_inputs_used": [],
    }


def _build_plan(max_items: int, planned_items: list[dict[str, Any]], status: str) -> dict[str, Any]:
    return {
        "status": status,
        "phase": PHASE,
        "mode": MODE,
        "dry_run_only": True,
        "max_items": max_items,
        "items_planned": len(planned_items),
        "planned_items": planned_items,
        "rules": {
            "analysis_planning_only": True,
            "no_video_file_opened": True,
            "no_audio_file_opened": True,
            "no_qwen_action": True,
            "no_qwen_autocut": True,
            "no_render": True,
            "no_ingest": True,
            "no_music": True,
            "no_phase_5_5": True,
            "no_real_overnight": True,
            "no_real_learning_loop": True,
        },
    }


def _build_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# P5-L5 Overnight Dry-run Summary",
        "",
        f"- status: {manifest['status']}",
        f"- phase: {manifest['phase']}",
        f"- mode: {manifest['mode']}",
        f"- dry_run_only: {manifest['dry_run_only']}",
        f"- real_overnight_started: {manifest['real_overnight_started']}",
        f"- overnight_started: {manifest['overnight_started']}",
        f"- bounded_run: {manifest['bounded_run']}",
        f"- max_items: {manifest['max_items']}",
        f"- items_planned: {manifest['items_planned']}",
        f"- items_processed: {manifest['items_processed']}",
        f"- stop_file_supported: {manifest['stop_file_supported']}",
        f"- stop_file_detected: {manifest['stop_file_detected']}",
        f"- qwen_used: {manifest['qwen_used']}",
        f"- qwen_autocut_used: {manifest['qwen_autocut_used']}",
        f"- render_used: {manifest['render_used']}",
        f"- ingest_used: {manifest['ingest_used']}",
        f"- music_used: {manifest['music_used']}",
        f"- autocut_used: {manifest['autocut_used']}",
        f"- learning_loop_started: {manifest['learning_loop_started']}",
        f"- phase_5_5_used: {manifest['phase_5_5_used']}",
        f"- external_network_used: {manifest['external_network_used']}",
        f"- api_key_used: {manifest['api_key_used']}",
        f"- deleted_files: {manifest['deleted_files']}",
        f"- warnings: {manifest['warnings']}",
        f"- forbidden_inputs_used: {manifest['forbidden_inputs_used']}",
        "",
        "Safety: no render, no ingest, no qwen autocut, no music, no real overnight loop.",
    ]
    return "\n".join(lines) + "\n"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_outputs(
    output_dir: Path,
    plan: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Path]:
    plan_path = output_dir / "overnight_dry_run_plan.json"
    manifest_path = output_dir / "overnight_dry_run_manifest.json"
    summary_path = output_dir / "overnight_dry_run_summary.md"

    _write_json(plan_path, plan)
    _write_json(manifest_path, manifest)
    summary_path.write_text(_build_summary(manifest), encoding="utf-8")

    return {
        "plan": plan_path,
        "manifest": manifest_path,
        "summary": summary_path,
    }


def run_overnight_dry_run(
    repo_root: str | Path,
    output_dir: str | Path = ALLOWED_OUTPUT_REL,
    max_items: int = 5,
) -> dict[str, Any]:
    if max_items > 10:
        raise ValueError("max_items_must_be_10_or_less")
    if max_items < 0:
        raise ValueError("max_items_must_not_be_negative")

    repo = Path(repo_root).resolve()
    out = _resolve_output_dir(repo, output_dir)
    out.mkdir(parents=True, exist_ok=True)

    manifest = _base_manifest(max_items)
    outputs_rel = [
        (ALLOWED_OUTPUT_REL / "overnight_dry_run_plan.json").as_posix(),
        (ALLOWED_OUTPUT_REL / "overnight_dry_run_manifest.json").as_posix(),
        (ALLOWED_OUTPUT_REL / "overnight_dry_run_summary.md").as_posix(),
    ]
    manifest["outputs_written"] = outputs_rel

    stop_file = out / "STOP"
    if stop_file.exists():
        manifest["status"] = "stopped_by_stop_file"
        manifest["stop_file_detected"] = True
        plan = _build_plan(max_items, [], "stopped_by_stop_file")
        paths = _write_outputs(out, plan, manifest)
        return {"manifest": manifest, "plan": plan, "paths": paths}

    warnings: list[str] = []
    inputs_read: list[str] = []
    forbidden_inputs_used: list[str] = []

    _collect_optional_reports(repo, inputs_read, warnings)
    planned_items = _collect_planned_items(
        repo,
        min(max_items, 5),
        inputs_read,
        warnings,
        forbidden_inputs_used,
    )

    processed_items = [
        {
            "item_id": item["item_id"],
            "category": item["category"],
            "source": item["source"],
            "status": "dry_run_record_only",
        }
        for item in planned_items
    ]

    status = "ok"
    if forbidden_inputs_used:
        status = "blocked_for_forbidden_input"

    manifest.update(
        {
            "status": status,
            "items_planned": len(planned_items),
            "items_processed": len(processed_items),
            "inputs_read": sorted(set(inputs_read)),
            "planned_items": planned_items,
            "processed_items": processed_items,
            "warnings": warnings,
            "forbidden_inputs_used": sorted(set(forbidden_inputs_used)),
        }
    )

    plan = _build_plan(max_items, planned_items, status)
    paths = _write_outputs(out, plan, manifest)
    return {"manifest": manifest, "plan": plan, "paths": paths}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="P5-L5 bounded overnight dry-run")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument(
        "--output-dir",
        default=ALLOWED_OUTPUT_REL.as_posix(),
    )
    parser.add_argument("--max-items", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = run_overnight_dry_run(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        max_items=args.max_items,
    )
    print(json.dumps(result["manifest"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
