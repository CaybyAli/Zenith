from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_IMPORT_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_IMPORT_ROOT))

from core.music_preview_gate import (  # noqa: E402
    build_preview_gate_manifest,
    evaluate_music_preview_gate,
)

EXPECTED_OUTPUT_DIR = Path("reports/phase5_5_music_preview_gate")
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


def _base_gate_input() -> dict:
    return {
        "channel_type": "main",
        "owner_preview_go": True,
        "phase_5_done": True,
        "p5_l_closed": True,
        "music_library_verified": True,
        "selector_ready": True,
        "ducking_plan_ready": True,
        "uncut_music_allowed": False,
        "music_files_tracked": False,
        "music_files_staged": False,
        "render_requested": False,
        "audio_mix_requested": False,
        _q_flag("requested"): False,
        "runtime_learning_requested": False,
        "external_download_requested": False,
        "api_key_present": False,
    }


def _demo_inputs() -> dict[str, dict]:
    main_without_owner_go = _base_gate_input()
    main_without_owner_go["owner_preview_go"] = False

    main_with_owner_go_but_render_requested = _base_gate_input()
    main_with_owner_go_but_render_requested["render_requested"] = True

    main_clean_gate = _base_gate_input()

    uncut_gate = _base_gate_input()
    uncut_gate["channel_type"] = "uncut"

    return {
        "main_without_owner_go": main_without_owner_go,
        "main_with_owner_go_but_render_requested": main_with_owner_go_but_render_requested,
        "main_clean_gate": main_clean_gate,
        "uncut_gate": uncut_gate,
    }


def _build_summary(manifest: dict) -> str:
    lines = [
        "# Phase 5.5-6 Controlled Music Preview Gate Smoke Summary",
        "",
        f"- status: {manifest['status']}",
        f"- step: {manifest['step']}",
        f"- mode: {manifest['mode']}",
        f"- gate_created: {str(manifest['gate_created']).lower()}",
        f"- owner_preview_go_required: {str(manifest['owner_preview_go_required']).lower()}",
        f"- music_library_verified: {str(manifest['music_library_verified']).lower()}",
        f"- selector_ready: {str(manifest['selector_ready']).lower()}",
        f"- ducking_plan_ready: {str(manifest['ducking_plan_ready']).lower()}",
        f"- music_build_started: {str(manifest['music_build_started']).lower()}",
        f"- music_inserted: {str(manifest['music_inserted']).lower()}",
        f"- audio_mix_started: {str(manifest['audio_mix_started']).lower()}",
        f"- real_audio_modified: {str(manifest['real_audio_modified']).lower()}",
        f"- render_used: {str(manifest['render_used']).lower()}",
        f"- preview_render_used: {str(manifest['preview_render_used']).lower()}",
        f"- ingest_used: {str(manifest['ingest_used']).lower()}",
        f"- {_q_flag('used')}: {str(manifest[_q_flag('used')]).lower()}",
        f"- {_q_flag('autocut_used')}: {str(manifest[_q_flag('autocut_used')]).lower()}",
        f"- runtime_learning_started: {str(manifest['runtime_learning_started']).lower()}",
        f"- external_download_used: {str(manifest['external_download_used']).lower()}",
        f"- api_key_used: {str(manifest['api_key_used']).lower()}",
        f"- music_files_committed: {str(manifest['music_files_committed']).lower()}",
        f"- main_account_music_allowed: {str(manifest['main_account_music_allowed']).lower()}",
        f"- uncut_music_allowed: {str(manifest['uncut_music_allowed']).lower()}",
        f"- writes_only_under: {manifest['writes_only_under']}",
        "",
        "## Demo Decisions",
    ]
    for decision in manifest["preview_gate_decisions"]:
        flags = decision["safety_flags"]
        lines.append(
            "- "
            f"{flags['demo_name']}: "
            f"status={decision['gate_status']}, "
            f"preview_allowed={str(decision['preview_allowed']).lower()}, "
            f"channel={flags['channel_type']}, "
            f"reason={decision['reason']}, "
            f"music_build_started={str(flags['music_build_started']).lower()}, "
            f"render_used={str(flags['render_used']).lower()}"
        )
    lines.append("")
    lines.append(f"- next_step: {manifest['next_step']}")
    return "\n".join(lines) + "\n"


def run(repo_root: str, output_dir: str) -> dict:
    root = Path(repo_root).resolve()
    relative_output = _relative_output_dir(root, output_dir)
    if relative_output.as_posix() != EXPECTED_OUTPUT_DIR.as_posix():
        raise ValueError("output-dir must be exactly reports/phase5_5_music_preview_gate")

    decisions = []
    for demo_name, gate_input in _demo_inputs().items():
        decision = evaluate_music_preview_gate(gate_input)
        decision.safety_flags["demo_name"] = demo_name
        decisions.append(decision)

    manifest = build_preview_gate_manifest(decisions)
    manifest["demo_inputs_total"] = len(decisions)

    target_dir = root / EXPECTED_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = target_dir / "music_preview_gate_manifest.json"
    summary_path = target_dir / "music_preview_gate_summary.md"
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
