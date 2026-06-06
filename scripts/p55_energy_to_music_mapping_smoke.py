from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_IMPORT_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_IMPORT_ROOT))

from core.music_energy_mapping import (  # noqa: E402
    build_empty_energy_mapping_manifest,
    build_music_mapping_plan,
)

EXPECTED_OUTPUT_DIR = Path("reports/phase5_5_energy_to_music_mapping")


def _relative_output_dir(repo_root: Path, output_dir: str) -> Path:
    candidate = Path(output_dir)
    if candidate.is_absolute():
        candidate = candidate.resolve()
        try:
            return candidate.relative_to(repo_root)
        except ValueError as exc:
            raise ValueError("output-dir must be inside repo root") from exc
    return Path(str(candidate).replace("\\", "/"))


def _demo_segments() -> list[dict]:
    return [
        {
            "segment_id": "demo_intro",
            "start_sec": 0.0,
            "end_sec": 8.0,
            "segment_role": "intro",
            "energy_score": 0.40,
            "highlight_score": 0.10,
            "speech_density": 0.10,
            "mood_tag": "neutral",
            "channel_type": "main",
        },
        {
            "segment_id": "demo_calm_gameplay",
            "start_sec": 8.0,
            "end_sec": 35.0,
            "segment_role": "gameplay",
            "energy_score": 0.25,
            "highlight_score": 0.10,
            "speech_density": 0.20,
            "mood_tag": "calm",
            "channel_type": "main",
        },
        {
            "segment_id": "demo_hype_highlight",
            "start_sec": 35.0,
            "end_sec": 52.0,
            "segment_role": "highlight",
            "energy_score": 0.92,
            "highlight_score": 0.95,
            "speech_density": 0.50,
            "mood_tag": "hype",
            "channel_type": "main",
        },
        {
            "segment_id": "demo_outro",
            "start_sec": 52.0,
            "end_sec": 60.0,
            "segment_role": "outro",
            "energy_score": 0.30,
            "highlight_score": 0.10,
            "speech_density": 0.10,
            "mood_tag": "victory",
            "channel_type": "main",
        },
        {
            "segment_id": "demo_main_funny_gameplay",
            "start_sec": 60.0,
            "end_sec": 75.0,
            "segment_role": "gameplay",
            "energy_score": 0.45,
            "highlight_score": 0.20,
            "speech_density": 0.20,
            "mood_tag": "funny",
            "channel_type": "main",
        },
        {
            "segment_id": "demo_main_suspense_gameplay",
            "start_sec": 75.0,
            "end_sec": 90.0,
            "segment_role": "gameplay",
            "energy_score": 0.55,
            "highlight_score": 0.30,
            "speech_density": 0.15,
            "mood_tag": "suspense",
            "channel_type": "main",
        },
        {
            "segment_id": "demo_main_emotional",
            "start_sec": 90.0,
            "end_sec": 105.0,
            "segment_role": "gameplay",
            "energy_score": 0.35,
            "highlight_score": 0.20,
            "speech_density": 0.25,
            "mood_tag": "emotional",
            "channel_type": "main",
        },
        {
            "segment_id": "demo_uncut_highlight",
            "start_sec": 105.0,
            "end_sec": 120.0,
            "segment_role": "highlight",
            "energy_score": 1.0,
            "highlight_score": 1.0,
            "speech_density": 0.50,
            "mood_tag": "hype",
            "channel_type": "uncut",
        },
    ]


def _build_summary(manifest: dict) -> str:
    lines = [
        "# Phase 5.5-3 Energy-to-Music Mapping Smoke Summary",
        "",
        f"- status: {manifest['status']}",
        f"- mode: {manifest['mode']}",
        f"- music_build_started: {str(manifest['music_build_started']).lower()}",
        f"- music_inserted: {str(manifest['music_inserted']).lower()}",
        f"- render_used: {str(manifest['render_used']).lower()}",
        f"- preview_render_used: {str(manifest['preview_render_used']).lower()}",
        f"- ingest_used: {str(manifest['ingest_used']).lower()}",
        f"- runtime_learning_started: {str(manifest['runtime_learning_started']).lower()}",
        f"- external_download_used: {str(manifest['external_download_used']).lower()}",
        f"- api_key_used: {str(manifest['api_key_used']).lower()}",
        f"- music_files_committed: {str(manifest['music_files_committed']).lower()}",
        f"- main_account_music_allowed: {str(manifest['main_account_music_allowed']).lower()}",
        f"- uncut_music_allowed: {str(manifest['uncut_music_allowed']).lower()}",
        f"- channel_rules_enforced: {str(manifest['channel_rules_enforced']).lower()}",
        f"- writes_only_under: {manifest['writes_only_under']}",
        "",
        "## Demo Mapping",
    ]
    for segment in manifest["mapping_plan"]["segments"]:
        lines.append(
            "- "
            f"{segment['segment_id']}: {segment['segment_role']} -> "
            f"{segment['music_category']} "
            f"(music_allowed={str(segment['music_allowed']).lower()}, "
            f"energy_level={segment['energy_level']}, "
            f"ducking_required={str(segment['ducking_required']).lower()})"
        )
    lines.append("")
    lines.append(f"- next_step: {manifest['next_step']}")
    return "\n".join(lines) + "\n"


def run(repo_root: str, output_dir: str) -> dict:
    root = Path(repo_root).resolve()
    relative_output = _relative_output_dir(root, output_dir)
    if relative_output.as_posix() != EXPECTED_OUTPUT_DIR.as_posix():
        raise ValueError("output-dir must be exactly reports/phase5_5_energy_to_music_mapping")

    mapping_plan = build_music_mapping_plan(_demo_segments())
    manifest = build_empty_energy_mapping_manifest()
    manifest["mapping_plan"] = mapping_plan

    target_dir = root / EXPECTED_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = target_dir / "energy_to_music_mapping_manifest.json"
    summary_path = target_dir / "energy_to_music_mapping_summary.md"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path.write_text(_build_summary(manifest), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        run(args.repo_root, args.output_dir)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
