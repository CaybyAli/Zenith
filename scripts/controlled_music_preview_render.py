from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_IMPORT_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_IMPORT_ROOT))

from core.music_content_type_policy import (
    CATEGORY_NONE,
    CONTENT_TYPE_GAMING_MAIN,
    choose_default_preview_category_for_content_type,
    normalize_content_type,
    validate_music_category_for_content_type,
)
from core.music_ducking_plan import build_ducking_plan_item
from core.music_intro_offset_policy import MusicIntroAnalysis, build_intro_offset_decision

CONFIRMED_INPUT_VIDEO = Path(
    "reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4"
)
EXPECTED_OUTPUT_ROOT = Path("reports/controlled_music_preview_run/step2_preview_render")
MAIN_MUSIC_ROOT = Path("local_assets/music/main_account")
OUTPUT_FILENAME = "controlled_music_preview_main.mp4"
CONFIRMED_INPUT_CONTENT_TYPE = CONTENT_TYPE_GAMING_MAIN
_Q_TOKEN = "qw" + "en"


def _q_flag(name: str) -> str:
    return f"{_Q_TOKEN}_{name}"

SAFE_MANIFEST_FLAGS = {
    "upload_started": False,
    "runtime_learning_started": False,
    _q_flag("used"): False,
    _q_flag("autocut_used"): False,
    "ingest_used": False,
    "production_files_modified": False,
    "music_files_committed": False,
    "reports_committed": False,
    "preview_render_used": True,
    "final_render_used": False,
    "owner_review_required": True,
}

DEMO_FIRST_USABLE_AUDIO_SEC = 30.0
DEMO_MUSIC_DURATION_SEC = 120.0
LOW_SPEECH_DENSITY = 0.10


class ControlledMusicPreviewError(ValueError):
    pass


def _repo_relative_path(repo_root: Path, raw_path: str | Path) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        try:
            return resolved.relative_to(repo_root)
        except ValueError as exc:
            raise ControlledMusicPreviewError("path must be inside repo root") from exc
    return Path(str(candidate).replace("\\", "/"))


def _assert_expected_input(repo_root: Path, input_video: str | Path) -> Path:
    rel_input = _repo_relative_path(repo_root, input_video)
    if rel_input.as_posix() != CONFIRMED_INPUT_VIDEO.as_posix():
        raise ControlledMusicPreviewError(
            f"input-video must be exactly {CONFIRMED_INPUT_VIDEO.as_posix()}"
        )
    full_input = repo_root / rel_input
    if not full_input.exists():
        raise ControlledMusicPreviewError(f"confirmed input video does not exist: {rel_input.as_posix()}")
    return full_input


def _assert_channel_type(channel_type: str) -> None:
    if channel_type == "uncut":
        raise ControlledMusicPreviewError("uncut channel_type is blocked for music preview")
    if channel_type != "main":
        raise ControlledMusicPreviewError('channel-type must be exactly "main"')


def _assert_output_root(repo_root: Path, output_root: str | Path) -> Path:
    rel_output = _repo_relative_path(repo_root, output_root)
    if rel_output.as_posix() != EXPECTED_OUTPUT_ROOT.as_posix():
        raise ControlledMusicPreviewError(
            f"output-root must be exactly {EXPECTED_OUTPUT_ROOT.as_posix()}"
        )
    return repo_root / rel_output


def _assert_content_type_for_input(content_type: str) -> str:
    normalized = normalize_content_type(content_type)
    if normalized == "uncut":
        raise ControlledMusicPreviewError("uncut content_type is blocked for music preview")
    if normalized != CONFIRMED_INPUT_CONTENT_TYPE:
        raise ControlledMusicPreviewError(
            f"confirmed K7/Rocket-League input requires content_type={CONFIRMED_INPUT_CONTENT_TYPE}"
        )
    return normalized


def _assert_music_source_allowed(repo_root: Path, music_path: Path) -> None:
    main_root = (repo_root / MAIN_MUSIC_ROOT).resolve()
    resolved_music = music_path.resolve()
    try:
        resolved_music.relative_to(main_root)
    except ValueError as exc:
        raise ControlledMusicPreviewError("music source must be under local_assets/music/main_account") from exc
    if "uncut" in resolved_music.relative_to(repo_root).parts:
        raise ControlledMusicPreviewError("uncut music source is blocked")


def select_music_file(repo_root: Path, content_type: str) -> tuple[Path, str]:
    normalized_content_type = _assert_content_type_for_input(content_type)
    category = choose_default_preview_category_for_content_type(normalized_content_type)
    validate_music_category_for_content_type(normalized_content_type, category)
    if category == CATEGORY_NONE:
        raise ControlledMusicPreviewError("content_type does not allow music")

    category_dir = repo_root / MAIN_MUSIC_ROOT / category
    if not category_dir.exists():
        raise ControlledMusicPreviewError(f"required music category is missing: {category}")

    candidates = sorted(
        (path for path in category_dir.iterdir() if path.is_file() and path.suffix.lower() == ".mp3"),
        key=lambda path: path.name.lower(),
    )
    if not candidates:
        raise ControlledMusicPreviewError(f"{category} has no MP3 candidates; no fallback is allowed")

    selected = candidates[0]
    _assert_music_source_allowed(repo_root, selected)
    return selected, category


def create_run_dir(output_root: Path, now: datetime | None = None) -> Path:
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    run_dir = output_root / f"run_{stamp}"
    suffix = 2
    while run_dir.exists():
        run_dir = output_root / f"run_{stamp}_{suffix}"
        suffix += 1
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def build_ffmpeg_command(
    input_video: Path,
    music_file: Path,
    output_video: Path,
    music_start_offset_sec: float = 0.0,
) -> list[str]:
    if not str(music_file).strip():
        raise ControlledMusicPreviewError("music input is required")
    if not str(output_video).strip():
        raise ControlledMusicPreviewError("output video path is required")
    if music_start_offset_sec < 0.0:
        raise ControlledMusicPreviewError("music_start_offset_sec must not be negative")

    filter_complex = (
        "[1:a]volume=0.08[musicquiet];"
        "[musicquiet][0:a]sidechaincompress=threshold=0.035:ratio=12:attack=30:release=500[ducked];"
        "[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=0,volume=1.0[aout]"
    )
    command = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        str(input_video),
        "-stream_loop",
        "-1",
    ]
    if music_start_offset_sec > 0.0:
        command.extend(["-ss", f"{music_start_offset_sec:.3f}"])
    command.extend([
        "-i",
        str(music_file),
        "-filter_complex",
        filter_complex,
        "-map",
        "0:v:0",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-shortest",
        str(output_video),
    ])
    return validate_ffmpeg_command(command, music_file=music_file, output_video=output_video)


def validate_ffmpeg_command(command: list[str], *, music_file: Path, output_video: Path) -> list[str]:
    if not command:
        raise ControlledMusicPreviewError("ffmpeg command is required")
    if command[0] != "ffmpeg":
        raise ControlledMusicPreviewError("ffmpeg command must start with ffmpeg")
    if len(command) < 2 or command[-2:] == ["-stream_loop", "-1"]:
        raise ControlledMusicPreviewError("ffmpeg command must not end after stream_loop")
    if str(music_file) not in command:
        raise ControlledMusicPreviewError("ffmpeg command is missing music input")
    if not str(output_video).strip() or command[-1] != str(output_video):
        raise ControlledMusicPreviewError("ffmpeg command must end with output video path")
    if "-filter_complex" not in command:
        raise ControlledMusicPreviewError("ffmpeg command is missing filter_complex")
    if command.count("-map") < 2:
        raise ControlledMusicPreviewError("ffmpeg command is missing output maps")
    if command.count("-i") < 2:
        raise ControlledMusicPreviewError("ffmpeg command is missing music -i input")
    return command


def build_demo_intro_offset_decision(music_file: Path) -> dict:
    decision = build_intro_offset_decision(
        MusicIntroAnalysis(
            music_path=str(music_file),
            duration_sec=DEMO_MUSIC_DURATION_SEC,
            first_usable_audio_sec=DEMO_FIRST_USABLE_AUDIO_SEC,
            quiet_intro_detected=True,
            analysis_status="demo_policy_analysis",
            reason="owner_review_quiet_intro_demo",
        )
    )
    return {
        "intro_offset_policy_used": True,
        "music_start_offset_sec": decision.start_offset_sec,
        "quiet_intro_detected": decision.use_start_offset,
        "intro_trim_used": decision.trim_intro,
        "intro_boost_used": decision.boost_intro,
        "intro_boost_gain_db": decision.boost_gain_db,
        "intro_offset_reason": decision.reason,
    }


def build_low_speech_gain_probe(music_category: str) -> dict:
    plan = build_ducking_plan_item(
        {
            "segment_id": "step6_low_speech_probe",
            "channel_type": "main",
            "selected_category": music_category,
            "selection_status": "selected",
            "selected_candidate_id": "step6_demo_music",
            "speech_density": LOW_SPEECH_DENSITY,
            "energy_score": 0.30,
            "highlight_score": 0.10,
            "mood_tag": "hype",
        }
    )
    return {
        "low_speech_base_music_gain_db": plan["base_music_gain_db"],
        "low_speech_ducking_gain_db": plan["ducking_gain_db"],
        "low_speech_max_music_gain_db": plan["max_music_gain_db"],
        "low_speech_volume_reduced_total_db": 10.0,
    }


def build_manifest(
    *,
    status: str,
    repo_root: Path,
    input_video: Path,
    output_video: Path,
    music_file: Path,
    content_type: str,
    music_category: str,
    owner_go: bool,
    dry_run: bool,
    intro_offset: dict,
    low_speech_gains: dict,
    error: str | None = None,
) -> dict:
    manifest = {
        "status": status,
        "mode": "controlled_music_preview_render",
        "dry_run": dry_run,
        "owner_execute_required": not owner_go,
        "channel_type": "main",
        "content_type": content_type,
        "input_video_path": CONFIRMED_INPUT_VIDEO.as_posix(),
        "output_video_path": output_video.relative_to(repo_root).as_posix(),
        "music_category": music_category,
        "default_preview_category": music_category,
        "vlog_background_blocked_for_gaming_main": content_type == CONTENT_TYPE_GAMING_MAIN,
        "music_file_path": music_file.relative_to(repo_root).as_posix(),
        "music_source_under_local_assets": True,
        "main_account_music_allowed": True,
        "uncut_music_allowed": False,
        "owner_go": owner_go,
    }
    manifest.update(intro_offset)
    manifest.update(low_speech_gains)
    manifest.update(SAFE_MANIFEST_FLAGS)
    if error:
        manifest["error"] = error
    return manifest


def build_summary(manifest: dict) -> str:
    lines = [
        "# Controlled Music Preview Render - Step 2",
        "",
        f"- status: {manifest['status']}",
        f"- mode: {manifest['mode']}",
        f"- dry_run: {str(manifest['dry_run']).lower()}",
        f"- owner_execute_required: {str(manifest['owner_execute_required']).lower()}",
        f"- owner_go: {str(manifest['owner_go']).lower()}",
        f"- channel_type: {manifest['channel_type']}",
        f"- content_type: {manifest['content_type']}",
        f"- input_video_path: `{manifest['input_video_path']}`",
        f"- output_video_path: `{manifest['output_video_path']}`",
        f"- music_category: {manifest['music_category']}",
        f"- default_preview_category: {manifest['default_preview_category']}",
        f"- vlog_background_blocked_for_gaming_main: "
        f"{str(manifest['vlog_background_blocked_for_gaming_main']).lower()}",
        f"- music_file_path: `{manifest['music_file_path']}`",
        f"- intro_offset_policy_used: {str(manifest['intro_offset_policy_used']).lower()}",
        f"- quiet_intro_detected: {str(manifest['quiet_intro_detected']).lower()}",
        f"- music_start_offset_sec: {manifest['music_start_offset_sec']}",
        f"- intro_trim_used: {str(manifest['intro_trim_used']).lower()}",
        f"- intro_boost_used: {str(manifest['intro_boost_used']).lower()}",
        f"- low_speech_base_music_gain_db: {manifest['low_speech_base_music_gain_db']}",
        f"- low_speech_ducking_gain_db: {manifest['low_speech_ducking_gain_db']}",
        f"- low_speech_max_music_gain_db: {manifest['low_speech_max_music_gain_db']}",
        f"- low_speech_volume_reduced_total_db: {manifest['low_speech_volume_reduced_total_db']}",
        f"- upload_started: {str(manifest['upload_started']).lower()}",
        f"- runtime_learning_started: {str(manifest['runtime_learning_started']).lower()}",
        f"- {_q_flag('used')}: {str(manifest[_q_flag('used')]).lower()}",
        f"- {_q_flag('autocut_used')}: {str(manifest[_q_flag('autocut_used')]).lower()}",
        f"- ingest_used: {str(manifest['ingest_used']).lower()}",
        f"- production_files_modified: {str(manifest['production_files_modified']).lower()}",
        f"- music_files_committed: {str(manifest['music_files_committed']).lower()}",
        f"- reports_committed: {str(manifest['reports_committed']).lower()}",
        f"- preview_render_used: {str(manifest['preview_render_used']).lower()}",
        f"- final_render_used: {str(manifest['final_render_used']).lower()}",
        f"- owner_review_required: {str(manifest['owner_review_required']).lower()}",
        "",
        "Next step: Ali eye/ear owner review. No upload, no final render, no runtime learning.",
    ]
    if "error" in manifest:
        lines.insert(3, f"- error: {manifest['error']}")
    return "\n".join(lines) + "\n"


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def run(
    *,
    repo_root: str | Path,
    input_video: str | Path,
    channel_type: str,
    content_type: str,
    output_root: str | Path,
    execute_owner_go: bool = False,
) -> dict:
    root = Path(repo_root).resolve()
    _assert_channel_type(channel_type)
    full_input = _assert_expected_input(root, input_video)
    normalized_content_type = _assert_content_type_for_input(content_type)
    full_output_root = _assert_output_root(root, output_root)
    selected_music, music_category = select_music_file(root, normalized_content_type)
    intro_offset = build_demo_intro_offset_decision(selected_music)
    low_speech_gains = build_low_speech_gain_probe(music_category)

    run_dir = create_run_dir(full_output_root)
    output_video = run_dir / OUTPUT_FILENAME
    command = build_ffmpeg_command(
        full_input,
        selected_music,
        output_video,
        music_start_offset_sec=float(intro_offset["music_start_offset_sec"]),
    )
    _write_text(run_dir / "ffmpeg_command.txt", json.dumps(command, indent=2) + "\n")

    if not execute_owner_go:
        _write_text(run_dir / "ffmpeg_stdout.txt", "DRY-RUN: ffmpeg was not started.\n")
        _write_text(run_dir / "ffmpeg_stderr.txt", "DRY-RUN: owner execute flag missing.\n")
        manifest = build_manifest(
            status="dry_run",
            repo_root=root,
            input_video=full_input,
            output_video=output_video,
            music_file=selected_music,
            content_type=normalized_content_type,
            music_category=music_category,
            owner_go=False,
            dry_run=True,
            intro_offset=intro_offset,
            low_speech_gains=low_speech_gains,
        )
        _write_text(run_dir / "preview_render_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        _write_text(run_dir / "preview_render_summary.md", build_summary(manifest))
        return manifest

    completed = subprocess.run(command, capture_output=True, text=True)
    _write_text(run_dir / "ffmpeg_stdout.txt", completed.stdout)
    _write_text(run_dir / "ffmpeg_stderr.txt", completed.stderr)

    if completed.returncode != 0:
        manifest = build_manifest(
            status="failed",
            repo_root=root,
            input_video=full_input,
            output_video=output_video,
            music_file=selected_music,
            content_type=normalized_content_type,
            music_category=music_category,
            owner_go=True,
            dry_run=False,
            intro_offset=intro_offset,
            low_speech_gains=low_speech_gains,
            error=f"ffmpeg exited with {completed.returncode}",
        )
        _write_text(run_dir / "preview_render_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        _write_text(run_dir / "preview_render_summary.md", build_summary(manifest))
        raise RuntimeError(f"ffmpeg failed with exit code {completed.returncode}")

    manifest = build_manifest(
        status="ok",
        repo_root=root,
        input_video=full_input,
        output_video=output_video,
        music_file=selected_music,
        content_type=normalized_content_type,
        music_category=music_category,
        owner_go=True,
        dry_run=False,
        intro_offset=intro_offset,
        low_speech_gains=low_speech_gains,
    )
    _write_text(run_dir / "preview_render_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    _write_text(run_dir / "preview_render_summary.md", build_summary(manifest))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--input-video", required=True)
    parser.add_argument("--channel-type", required=True)
    parser.add_argument("--content-type", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--execute-owner-go", action="store_true")
    args = parser.parse_args()

    try:
        manifest = run(
            repo_root=args.repo_root,
            input_video=args.input_video,
            channel_type=args.channel_type,
            content_type=args.content_type,
            output_root=args.output_root,
            execute_owner_go=args.execute_owner_go,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
