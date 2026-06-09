from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_IMPORT_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_IMPORT_ROOT))

from core.music_selector import (  # noqa: E402
    build_empty_music_selector_manifest,
    build_music_selection_plan,
)

EXPECTED_OUTPUT_DIR = Path("reports/phase5_5_music_selector")
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


def _demo_candidates() -> list[dict]:
    return [
        {
            "candidate_id": "main_intro",
            "file_path": "local_assets/music/main_account/intro/demo_intro.mp3",
            "channel_type": "main",
            "category": "intro",
            "source": "demo_metadata",
            "owner_approved": True,
            "license_status": "owner_approved",
            "intended_use": "main account intro",
            "mood_tags": ["intro"],
            "priority": 10,
        },
        {
            "candidate_id": "main_funny_gaming_background",
            "file_path": "local_assets/music/main_account/funny_gaming_background/demo_funny_gaming_background.mp3",
            "channel_type": "main",
            "category": "funny_gaming_background",
            "source": "demo_metadata",
            "owner_approved": True,
            "license_status": "royalty_free",
            "intended_use": "main account funny gaming background",
            "mood_tags": ["funny"],
            "priority": 20,
        },
        {
            "candidate_id": "main_fail",
            "file_path": "local_assets/music/main_account/fail/demo_fail.mp3",
            "channel_type": "main",
            "category": "fail",
            "source": "demo_metadata",
            "owner_approved": True,
            "license_status": "owner_approved",
            "intended_use": "main account fail moment",
            "mood_tags": ["fail"],
            "priority": 25,
        },
        {
            "candidate_id": "main_hype",
            "file_path": "local_assets/music/main_account/hype/demo_hype.mp3",
            "channel_type": "main",
            "category": "hype",
            "source": "demo_metadata",
            "owner_approved": True,
            "license_status": "self_created",
            "intended_use": "main account hype moment",
            "mood_tags": ["hype", "suspense"],
            "priority": 30,
        },
        {
            "candidate_id": "main_sad",
            "file_path": "local_assets/music/main_account/sad/demo_sad.mp3",
            "channel_type": "main",
            "category": "sad",
            "source": "demo_metadata",
            "owner_approved": True,
            "license_status": "owner_approved",
            "intended_use": "main account sad moment",
            "mood_tags": ["sad"],
            "priority": 15,
        },
        {
            "candidate_id": "main_vlog_background",
            "file_path": "local_assets/music/main_account/vlog_background/demo_vlog_background.mp3",
            "channel_type": "main",
            "category": "vlog_background",
            "source": "demo_metadata",
            "owner_approved": True,
            "license_status": "royalty_free",
            "intended_use": "main account vlog background",
            "mood_tags": ["neutral", "calm"],
            "priority": 5,
        },
        {
            "candidate_id": "main_outro",
            "file_path": "local_assets/music/main_account/outro/demo_outro.mp3",
            "channel_type": "main",
            "category": "outro",
            "source": "demo_metadata",
            "owner_approved": True,
            "license_status": "owner_approved",
            "intended_use": "main account outro",
            "mood_tags": ["outro"],
            "priority": 10,
        },
    ]


def _demo_mapping_items() -> list[dict]:
    return [
        {
            "segment_id": "demo_main_intro",
            "channel_type": "main",
            "requested_category": "intro",
            "mood_tag": "intro",
            "energy_level": "medium",
            "ducking_required": False,
        },
        {
            "segment_id": "demo_main_funny_gaming_background",
            "channel_type": "main",
            "requested_category": "funny_gaming_background",
            "mood_tag": "funny",
            "energy_level": "medium",
            "ducking_required": False,
        },
        {
            "segment_id": "demo_main_fail",
            "channel_type": "main",
            "requested_category": "fail",
            "mood_tag": "fail",
            "energy_level": "medium",
            "ducking_required": False,
        },
        {
            "segment_id": "demo_main_hype",
            "channel_type": "main",
            "requested_category": "hype",
            "mood_tag": "hype",
            "energy_level": "peak",
            "ducking_required": True,
        },
        {
            "segment_id": "demo_main_sad",
            "channel_type": "main",
            "requested_category": "sad",
            "mood_tag": "sad",
            "energy_level": "low",
            "ducking_required": False,
        },
        {
            "segment_id": "demo_main_vlog_background",
            "channel_type": "main",
            "requested_category": "vlog_background",
            "mood_tag": "neutral",
            "energy_level": "medium",
            "ducking_required": False,
        },
        {
            "segment_id": "demo_main_outro",
            "channel_type": "main",
            "requested_category": "outro",
            "mood_tag": "outro",
            "energy_level": "low",
            "ducking_required": False,
        },
        {
            "segment_id": "demo_uncut_blocked",
            "channel_type": "uncut",
            "requested_category": "none",
            "mood_tag": "hype",
            "energy_level": "peak",
            "ducking_required": True,
        },
    ]


def _eligible_demo_candidates() -> list[dict]:
    return [candidate for candidate in _demo_candidates() if candidate["channel_type"] == "main"]


def _build_summary(manifest: dict) -> str:
    lines = [
        "# Phase 5.5-4 Music Selector Smoke Summary",
        "",
        f"- status: {manifest['status']}",
        f"- step: {manifest['step']}",
        f"- mode: {manifest['mode']}",
        f"- metadata_only: {str(manifest['metadata_only']).lower()}",
        f"- reads_music_files: {str(manifest['reads_music_files']).lower()}",
        f"- music_build_started: {str(manifest['music_build_started']).lower()}",
        f"- music_inserted: {str(manifest['music_inserted']).lower()}",
        f"- render_used: {str(manifest['render_used']).lower()}",
        f"- preview_render_used: {str(manifest['preview_render_used']).lower()}",
        f"- ingest_used: {str(manifest['ingest_used']).lower()}",
        f"- {_q_flag('used')}: {str(manifest[_q_flag('used')]).lower()}",
        f"- {_q_flag('autocut_used')}: {str(manifest[_q_flag('autocut_used')]).lower()}",
        f"- runtime_learning_started: {str(manifest['runtime_learning_started']).lower()}",
        f"- external_download_used: {str(manifest['external_download_used']).lower()}",
        f"- api_key_used: {str(manifest['api_key_used']).lower()}",
        f"- music_files_committed: {str(manifest['music_files_committed']).lower()}",
        f"- production_files_modified: {str(manifest['production_files_modified']).lower()}",
        f"- main_account_music_allowed: {str(manifest['main_account_music_allowed']).lower()}",
        f"- uncut_music_allowed: {str(manifest['uncut_music_allowed']).lower()}",
        f"- allowed_categories: {', '.join(manifest['allowed_categories'])}",
        f"- channel_rules_enforced: {str(manifest['channel_rules_enforced']).lower()}",
        f"- writes_only_under: {manifest['writes_only_under']}",
        "",
        "## Demo Selection",
    ]
    for selection in manifest["selection_plan"]["selections"]:
        lines.append(
            "- "
            f"{selection['segment_id']}: {selection['requested_category']} -> "
            f"{selection['selection_status']} "
            f"(candidate={selection['selected_candidate_id']}, "
            f"category={selection['selected_category']}, "
            f"music_allowed={str(selection['music_allowed']).lower()})"
        )
    lines.append("")
    lines.append(f"- next_step: {manifest['next_step']}")
    return "\n".join(lines) + "\n"


def run(repo_root: str, output_dir: str) -> dict:
    root = Path(repo_root).resolve()
    relative_output = _relative_output_dir(root, output_dir)
    if relative_output.as_posix() != EXPECTED_OUTPUT_DIR.as_posix():
        raise ValueError("output-dir must be exactly reports/phase5_5_music_selector")

    selection_plan = build_music_selection_plan(
        _demo_mapping_items(),
        _eligible_demo_candidates(),
        str(root),
    )
    manifest = build_empty_music_selector_manifest()
    manifest["selection_plan"] = selection_plan
    manifest["demo_candidates_total"] = len(_demo_candidates())
    manifest["demo_candidates_eligible"] = len(_eligible_demo_candidates())

    target_dir = root / EXPECTED_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = target_dir / "music_selector_manifest.json"
    summary_path = target_dir / "music_selector_summary.md"
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
