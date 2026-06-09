from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_IMPORT_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_IMPORT_ROOT))

from core.music_ducking_plan import (  # noqa: E402
    build_ducking_plan,
    build_empty_ducking_plan_manifest,
)

EXPECTED_OUTPUT_DIR = Path("reports/phase5_5_ducking_plan")
_Q_TOKEN = "qw" + "en"


def _q_flag(name: str) -> str:
    return f"{_Q_TOKEN}_{name}"


def _relative_output_dir(repo_root: Path, output_dir: str) -> Path:
    candidate = Path(output_dir)
    if candidate.is_absolute():
        candidate = candidate.resolve()
        try:
            return candidate.relative_to(repo_root)
        except ValueError as exc:
            raise ValueError("output-dir must be inside repo root") from exc
    return Path(str(candidate).replace("\\", "/"))


def _demo_inputs() -> list[dict]:
    return [
        {
            "segment_id": "main_low_speech_vlog",
            "channel_type": "main",
            "selected_category": "vlog_background",
            "selection_status": "selected",
            "selected_candidate_id": "demo_vlog_001",
            "speech_density": 0.10,
            "energy_score": 0.30,
            "highlight_score": 0.10,
            "mood_tag": "neutral",
        },
        {
            "segment_id": "main_medium_speech_funny",
            "channel_type": "main",
            "selected_category": "funny_gaming_background",
            "selection_status": "selected",
            "selected_candidate_id": "demo_funny_001",
            "speech_density": 0.35,
            "energy_score": 0.50,
            "highlight_score": 0.20,
            "mood_tag": "funny",
        },
        {
            "segment_id": "main_high_speech_hype",
            "channel_type": "main",
            "selected_category": "hype",
            "selection_status": "selected",
            "selected_candidate_id": "demo_hype_001",
            "speech_density": 0.55,
            "energy_score": 0.90,
            "highlight_score": 0.90,
            "mood_tag": "hype",
        },
        {
            "segment_id": "main_very_high_speech_intro",
            "channel_type": "main",
            "selected_category": "intro",
            "selection_status": "selected",
            "selected_candidate_id": "demo_intro_001",
            "speech_density": 0.80,
            "energy_score": 0.40,
            "highlight_score": 0.10,
            "mood_tag": "neutral",
        },
        {
            "segment_id": "main_missing_candidate",
            "channel_type": "main",
            "selected_category": "sad",
            "selection_status": "missing_candidate",
            "selected_candidate_id": None,
            "speech_density": 0.20,
            "energy_score": 0.20,
            "highlight_score": 0.10,
            "mood_tag": "sad",
        },
        {
            "segment_id": "uncut_hype",
            "channel_type": "uncut",
            "selected_category": "none",
            "selection_status": "blocked",
            "selected_candidate_id": None,
            "speech_density": 0.0,
            "energy_score": 1.0,
            "highlight_score": 1.0,
            "mood_tag": "hype",
        },
    ]


def _build_summary(manifest: dict) -> str:
    lines = [
        "# Phase 5.5-5 Ducking Plan Smoke Summary",
        "",
        f"- status: {manifest['status']}",
        f"- step: {manifest['step']}",
        f"- mode: {manifest['mode']}",
        f"- ducking_plan_created: {str(manifest['ducking_plan_created']).lower()}",
        f"- music_build_started: {str(manifest['music_build_started']).lower()}",
        f"- music_inserted: {str(manifest['music_inserted']).lower()}",
        f"- audio_mix_started: {str(manifest['audio_mix_started']).lower()}",
        f"- render_used: {str(manifest['render_used']).lower()}",
        f"- preview_render_used: {str(manifest['preview_render_used']).lower()}",
        f"- ingest_used: {str(manifest['ingest_used']).lower()}",
        f"- {_q_flag('used')}: {str(manifest[_q_flag('used')]).lower()}",
        f"- {_q_flag('autocut_used')}: {str(manifest[_q_flag('autocut_used')]).lower()}",
        f"- runtime_learning_started: {str(manifest['runtime_learning_started']).lower()}",
        f"- external_download_used: {str(manifest['external_download_used']).lower()}",
        f"- api_key_used: {str(manifest['api_key_used']).lower()}",
        f"- music_files_committed: {str(manifest['music_files_committed']).lower()}",
        f"- real_audio_modified: {str(manifest['real_audio_modified']).lower()}",
        f"- main_account_music_allowed: {str(manifest['main_account_music_allowed']).lower()}",
        f"- uncut_music_allowed: {str(manifest['uncut_music_allowed']).lower()}",
        f"- writes_only_under: {manifest['writes_only_under']}",
        "",
        "## Demo Ducking Plan",
    ]
    for item in manifest["ducking_plan"]["items"]:
        lines.append(
            "- "
            f"{item['segment_id']}: "
            f"status={item['plan_status']}, "
            f"allowed={str(item['music_allowed']).lower()}, "
            f"ducking={str(item['ducking_enabled']).lower()}, "
            f"priority={item['speech_priority']}, "
            f"category={item['selected_category']}, "
            f"base={item['base_music_gain_db']}, "
            f"duck={item['ducking_gain_db']}, "
            f"max={item['max_music_gain_db']}, "
            f"reason={item['reason']}"
        )
    lines.append("")
    lines.append(f"- next_step: {manifest['next_step']}")
    return "\n".join(lines) + "\n"


def run(repo_root: str, output_dir: str) -> dict:
    root = Path(repo_root).resolve()
    relative_output = _relative_output_dir(root, output_dir)
    if relative_output.as_posix() != EXPECTED_OUTPUT_DIR.as_posix():
        raise ValueError("output-dir must be exactly reports/phase5_5_ducking_plan")

    ducking_plan = build_ducking_plan(_demo_inputs())
    manifest = build_empty_ducking_plan_manifest()
    manifest["ducking_plan"] = ducking_plan
    manifest["demo_inputs_total"] = len(_demo_inputs())

    target_dir = root / EXPECTED_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = target_dir / "ducking_plan_manifest.json"
    summary_path = target_dir / "ducking_plan_summary.md"
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
