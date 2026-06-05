from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import pair_track_truth_loader
from core.ffmpeg_helper import apply_ffmpeg_thread_cap, get_ffmpeg_path

PLAN_FILENAME = "k7_control_plan.json"
MANIFEST_FILENAME = "k7_control_manifest.json"
OUTPUT_VIDEO_FILENAME = "k7_control_preview.mp4"

MIN_DURATION_SECONDS = 10.0
MAX_DURATION_SECONDS = 120.0
TARGET_RESOLUTION = "1080x1920"

BLOCKED_SOURCE_PARTS = {"reports", "exports", "shorts"}
BLOCKED_SOURCE_NAME_TOKENS = ("caption", "subtitle", "preview", "proof", "emoji")
ALLOWED_SOURCE_EXTENSIONS = {".mp4", ".mov", ".mkv"}
OUTPUT_DIR_SEQUENCE = ("reports", "phase5", "k7_control_run")


def _casefold_parts(path: Path) -> list[str]:
    return [part.casefold() for part in path.parts]


def _path_contains_part(path: Path, blocked_parts: set[str]) -> bool:
    parts = set(_casefold_parts(path))
    return bool(parts.intersection(blocked_parts))


def _path_contains_sequence(path: Path, sequence: tuple[str, ...]) -> bool:
    parts = _casefold_parts(path.resolve())
    wanted = [item.casefold() for item in sequence]
    width = len(wanted)

    for index in range(0, max(0, len(parts) - width + 1)):
        if parts[index:index + width] == wanted:
            return True

    return False


def validate_source_path(source: str | Path) -> Path:
    path = Path(source)

    if not path.exists():
        raise RuntimeError("K7_SOURCE_NOT_FOUND")

    if not path.is_file():
        raise RuntimeError("K7_SOURCE_NOT_FILE")

    if path.suffix.casefold() not in ALLOWED_SOURCE_EXTENSIONS:
        raise RuntimeError("K7_SOURCE_EXTENSION_NOT_ALLOWED")

    if _path_contains_part(path, BLOCKED_SOURCE_PARTS):
        raise RuntimeError("K7_SOURCE_FORBIDDEN_LOCATION")

    name = path.name.casefold()
    if any(token in name for token in BLOCKED_SOURCE_NAME_TOKENS):
        raise RuntimeError("K7_SOURCE_FORBIDDEN_NAME_TOKEN")

    return path.resolve()


def validate_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)

    if not _path_contains_sequence(path, OUTPUT_DIR_SEQUENCE):
        raise RuntimeError("K7_OUTPUT_DIR_MUST_BE_UNDER_REPORTS_PHASE5_K7_CONTROL_RUN")

    return path.resolve()


def validate_duration(duration: float) -> float:
    value = float(duration)

    if value < MIN_DURATION_SECONDS or value > MAX_DURATION_SECONDS:
        raise RuntimeError("K7_DURATION_OUT_OF_RANGE")

    return value


def load_pair_truth_entry(pair_id: str) -> dict[str, Any]:
    truth = pair_track_truth_loader.load_truth()

    if pair_id not in truth:
        raise RuntimeError("K7_PAIR_ID_NOT_FOUND_IN_PAIR_TRACK_TRUTH")

    entry = truth[pair_id]
    if not isinstance(entry, dict):
        raise RuntimeError("K7_PAIR_TRUTH_ENTRY_INVALID")

    return entry


def ffmpeg_audio_map_from_pair_source(audio_source: str) -> str:
    value = str(audio_source or "").strip().lower()

    if not value.startswith("a"):
        raise RuntimeError("K7_AUDIO_SOURCE_INVALID")

    index_text = value[1:]
    if not index_text.isdigit():
        raise RuntimeError("K7_AUDIO_SOURCE_INVALID")

    return f"0:a:{int(index_text)}"


def build_plan(
    *,
    source: Path,
    output_dir: Path,
    duration: float,
    pair_id: str,
    status: str,
) -> dict[str, Any]:
    ali_source = pair_track_truth_loader.get_ali_source(pair_id)
    truth_entry = load_pair_truth_entry(pair_id)

    if not ali_source:
        raise RuntimeError("K7_ALI_SOURCE_MISSING")

    return {
        "status": status,
        "source": str(source),
        "output_dir": str(output_dir),
        "duration": float(duration),
        "pair_id": pair_id,
        "ali_source": ali_source,
        "friend_source": truth_entry.get("friend_source"),
        "game_source": truth_entry.get("game_source"),
        "qwen": False,
        "music": False,
        "ingest": False,
        "phase5_5": False,
        "full_batch": False,
        "clean_source_guard": True,
        "pair_truth_source": "video_configs/pair_track_truth.json",
        "legacy_trackmap_trusted": False,
        "expected_next_step": "real_control_run_after_master_go",
    }


def write_json(payload: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def write_plan(plan: dict[str, Any], output_dir: Path) -> Path:
    return write_json(plan, output_dir / PLAN_FILENAME)


def build_control_filter(duration: float) -> str:
    duration_text = f"{float(duration):.3f}"

    return (
        "[0:v]split=2[leftsrc][rightsrc];"
        f"[leftsrc]trim=duration={duration_text},setpts=PTS-STARTPTS,"
        "crop=iw/2:ih:0:0,"
        "scale=1080:540:force_original_aspect_ratio=decrease,"
        "pad=1080:540:(ow-iw)/2:(oh-ih)/2[left];"
        f"[rightsrc]trim=duration={duration_text},setpts=PTS-STARTPTS,"
        "crop=iw/2:ih:iw/2:0,"
        "scale=1080:1080:force_original_aspect_ratio=increase,"
        "crop=1080:1080[right];"
        f"color=c=black:s=1080x1920:r=30:d={duration_text}[base];"
        "[base][right]overlay=0:120:shortest=1[tmp];"
        "[tmp][left]overlay=0:1260:shortest=1[v]"
    )


def build_ffmpeg_command(
    *,
    source: Path,
    output_video: Path,
    duration: float,
    ali_source: str,
) -> list[str]:
    audio_map = ffmpeg_audio_map_from_pair_source(ali_source)

    return [
        get_ffmpeg_path(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        "0",
        "-t",
        f"{float(duration):.3f}",
        "-i",
        str(source),
        "-filter_complex",
        build_control_filter(duration),
        "-map",
        "[v]",
        "-map",
        audio_map,
        "-t",
        f"{float(duration):.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-shortest",
        "-movflags",
        "+faststart",
        str(output_video),
    ]


def run_ffmpeg_command(cmd: list[str]) -> None:
    safe_cmd = apply_ffmpeg_thread_cap(list(cmd))
    completed = subprocess.run(
        safe_cmd,
        shell=False,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(
            "K7_CONTROL_RUN_FAILED\n"
            f"STDOUT:\n{stdout}\n"
            f"STDERR:\n{stderr}"
        )


def build_manifest(
    *,
    plan: dict[str, Any],
    output_video: Path,
    command: list[str],
) -> dict[str, Any]:
    return {
        "status": "ok",
        "source": plan["source"],
        "output_video": str(output_video),
        "duration": plan["duration"],
        "target_resolution": TARGET_RESOLUTION,
        "pair_id": plan["pair_id"],
        "ali_source": plan["ali_source"],
        "friend_source": plan["friend_source"],
        "game_source": plan["game_source"],
        "qwen": False,
        "music": False,
        "ingest": False,
        "phase5_5": False,
        "full_batch": False,
        "clean_source_guard": True,
        "real_run_enabled": True,
        "audio_present_expected": True,
        "audio_strategy": f"map_{plan['ali_source']}_minimal_control_audio",
        "captions_generated": False,
        "captions_reason": (
            "K7 runner control render only; full caption pipeline remains checked "
            "by K3 and K7 Ali review"
        ),
        "layout_or_reframe_applied": True,
        "ffmpeg_command": command,
        "notes": [
            "Uses locked clean source only.",
            "Does not call old batch render entrypoints.",
            "Does not call external AI autocut.",
            "Does not add background audio.",
            "Documents pair truth in plan and manifest.",
        ],
        "next_step": "Ali eye/ear review",
    }


def run_real_control_run(
    *,
    source: Path,
    output_dir: Path,
    duration: float,
    plan: dict[str, Any],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    output_video = output_dir / OUTPUT_VIDEO_FILENAME
    command = build_ffmpeg_command(
        source=source,
        output_video=output_video,
        duration=duration,
        ali_source=str(plan["ali_source"]),
    )

    run_ffmpeg_command(command)

    manifest = build_manifest(
        plan=plan,
        output_video=output_video,
        command=command,
    )
    return write_json(manifest, output_dir / MANIFEST_FILENAME)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="K7 control-run guard runner. Real run requires explicit enable flag."
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--pair-id", default="pair_001")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--enable-real-run", action="store_true")
    parser.add_argument("--no-qwen", action="store_true", default=True)
    parser.add_argument("--no-music", action="store_true", default=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> Path:
    args = parse_args(argv)

    source = validate_source_path(args.source)
    output_dir = validate_output_dir(args.output_dir)
    duration = validate_duration(args.duration)

    if args.dry_run:
        plan = build_plan(
            source=source,
            output_dir=output_dir,
            duration=duration,
            pair_id=str(args.pair_id),
            status="dry_run_ok",
        )
        plan_path = write_plan(plan, output_dir)
        print(f"K7_CONTROL_DRY_RUN_OK={plan_path}")
        return plan_path

    if not args.enable_real_run:
        raise RuntimeError("K7_REAL_RUN_NOT_ENABLED_YET")

    plan = build_plan(
        source=source,
        output_dir=output_dir,
        duration=duration,
        pair_id=str(args.pair_id),
        status="real_run_enabled",
    )
    write_plan(plan, output_dir)

    manifest_path = run_real_control_run(
        source=source,
        output_dir=output_dir,
        duration=duration,
        plan=plan,
    )
    print(f"K7_CONTROL_REAL_RUN_OK={manifest_path}")
    return manifest_path


if __name__ == "__main__":
    main()
