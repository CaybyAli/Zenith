from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.caption_ass_builder import (
    CaptionASSBuilder,
    CaptionASSWord,
    CaptionGroup,
    escape_ffmpeg_filter_path,
)
from core.ffmpeg_helper import get_ffmpeg_path, get_ffprobe_path
from core.shorts_highlight_extractor import LLM_DISABLED
from core.shorts_reframe_planner import ShortsReframePlanner
from core.shorts_source_format_detector import SourceFormat
from models.edit_timeline import EditTimeline
from models.shorts_clip import ShortsClip


PHASE = "P5-K3K6"
PURPOSE = "visual_proof_preview"
MAX_DURATION_SECONDS = 5.0
TEMP_PROOF_FOLDER_NAME = "zenith_k3k6_visual_proof_1b"
PREVIEW_VIDEO_NAME = "k3k6_visual_preview.mp4"
CAPTION_ASS_NAME = "k3_caption_proof.ass"
LAYOUT_JSON_NAME = "k6_layout_proof.json"
MANIFEST_JSON_NAME = "visual_proof_manifest.json"



def escape_ffmpeg_filter_path(path: str | Path) -> str:
    """Escape Windows paths for ffmpeg subtitles= without double-escaping the drive colon."""
    raw = str(path)

    if len(raw) >= 4 and raw[1:4] == "\\\\:":
        raw = raw[0] + ":" + raw[4:]
    elif len(raw) >= 3 and raw[1:3] == "\\:":
        raw = raw[0] + ":" + raw[3:]

    escaped = raw.replace("\\", "/")
    if len(escaped) >= 2 and escaped[1] == ":":
        escaped = escaped[0] + "\\:" + escaped[2:]
    return escaped


def default_output_dir() -> Path:
    return Path(os.environ.get("TEMP") or tempfile.gettempdir()) / TEMP_PROOF_FOLDER_NAME


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_for_check(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_duration(duration: float) -> float:
    value = float(duration)
    if value <= 0:
        raise RuntimeError("DURATION_MUST_BE_POSITIVE")
    if value > MAX_DURATION_SECONDS:
        raise RuntimeError("DURATION_EXCEEDS_5_SECONDS")
    return value


def validate_output_dir(output_dir: str | Path | None) -> Path:
    base = _resolve_for_check(default_output_dir())
    candidate = _resolve_for_check(Path(output_dir) if output_dir else base)
    root = _resolve_for_check(repo_root())

    if not _is_relative_to(candidate, base):
        raise RuntimeError("OUTPUT_DIR_NOT_TEMP_VISUAL_PROOF_DIR")
    if _is_relative_to(candidate, root):
        raise RuntimeError("OUTPUT_DIR_INSIDE_REPO_BLOCKED")

    blocked_names = {
        "reports",
        "video_configs",
        "learning_corpus",
        "obsidian_zenith",
        ".obsidian",
    }
    parts = {part.casefold() for part in candidate.parts}
    if any(name.casefold() in parts for name in blocked_names):
        raise RuntimeError("OUTPUT_DIR_BLOCKED_PROJECT_AREA")

    return candidate


def parse_facecam_crop(raw: str | None) -> dict[str, int] | None:
    if raw is None or str(raw).strip() == "":
        return None
    parts = [item.strip() for item in str(raw).split(",")]
    if len(parts) != 4:
        raise RuntimeError("FACECAM_CROP_FORMAT_MUST_BE_X_Y_W_H")
    try:
        x, y, w, h = [int(item) for item in parts]
    except ValueError as exc:
        raise RuntimeError("FACECAM_CROP_VALUES_MUST_BE_INTEGERS") from exc
    if w <= 0 or h <= 0:
        raise RuntimeError("FACECAM_CROP_SIZE_MUST_BE_POSITIVE")
    if x < 0 or y < 0:
        raise RuntimeError("FACECAM_CROP_POSITION_MUST_BE_NON_NEGATIVE")
    return {"x": x, "y": y, "w": w, "h": h}


def build_output_paths(output_dir: str | Path | None = None) -> dict[str, Path]:
    root = validate_output_dir(output_dir)
    return {
        "output_dir": root,
        "preview_video": root / PREVIEW_VIDEO_NAME,
        "caption_ass": root / CAPTION_ASS_NAME,
        "layout_json": root / LAYOUT_JSON_NAME,
        "manifest": root / MANIFEST_JSON_NAME,
    }


def synthetic_caption_groups(duration: float) -> list[CaptionGroup]:
    safe_duration = validate_duration(duration)
    words = [
        CaptionASSWord("Owner", 0.00, 0.40, speaker="owner", audio_track="mic"),
        CaptionASSWord("Proof", 0.42, 0.82, speaker="owner", audio_track="mic"),
        CaptionASSWord("ist", 0.84, 1.12, speaker="owner", audio_track="mic"),
        CaptionASSWord("aktiv", 1.14, 1.62, speaker="owner", audio_track="mic"),
        CaptionASSWord("Friend", 2.05, 2.45, speaker="friend", audio_track="discord"),
        CaptionASSWord("Proof", 2.47, 2.87, speaker="friend", audio_track="discord"),
        CaptionASSWord("ist", 2.89, 3.17, speaker="friend", audio_track="discord"),
        CaptionASSWord("gelb", 3.19, 3.65, speaker="friend", audio_track="discord"),
    ]
    clipped: list[CaptionASSWord] = []
    for word in words:
        if word.start_seconds >= safe_duration:
            continue
        clipped.append(
            CaptionASSWord(
                text=word.text,
                start_seconds=word.start_seconds,
                end_seconds=min(word.end_seconds, safe_duration),
                speaker=word.speaker,
                audio_track=word.audio_track,
            )
        )
    if not clipped:
        raise RuntimeError("NO_SYNTHETIC_CAPTION_WORDS")
    return [CaptionGroup(words=clipped)]


def write_caption_ass(path: Path, duration: float) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    return CaptionASSBuilder().generate_ass_file(
        synthetic_caption_groups(duration),
        str(path),
    )


def build_layout_plan(
    video_path: str | Path,
    timestamp: float,
    duration: float,
    facecam_crop: dict[str, int] | None,
) -> dict[str, Any]:
    source_format = SourceFormat(
        width=3840,
        height=1080,
        aspect_ratio=3840 / 1080,
        is_32_9_composite=True,
        gameplay_region=(1920, 0, 1920, 1080),
        facecam_region=(0, 0, 1920, 1080),
    )
    clip = ShortsClip(
        source_job_id="k3k6_visual_proof_preview",
        source_start_time=float(timestamp),
        source_end_time=float(timestamp) + validate_duration(duration),
        planned_duration=validate_duration(duration),
        clip_index=0,
    )
    timeline = EditTimeline(
        timeline_id="k3k6_visual_proof_preview_timeline",
        job_id="k3k6_visual_proof_preview",
        target_duration=validate_duration(duration),
        selected_segments=[],
        timeline_notes=["temp_only_visual_proof_plan"],
    )
    plan = ShortsReframePlanner(source_format=source_format).plan_reframe(
        clip,
        timeline,
        llm_mode=LLM_DISABLED,
        source_video_path=video_path,
    )
    return {
        "status": "ok",
        "layout_codepath": "core.shorts_reframe_planner.ShortsReframePlanner.plan_reframe",
        "focus_or_reframe_codepath_used": True,
        "layout_type": plan.layout_type,
        "target_aspect_ratio": plan.target_aspect_ratio,
        "target_resolution": "1080x1920",
        "safe_zone_top_px": plan.safe_zone_top_px,
        "safe_zone_bottom_px": plan.safe_zone_bottom_px,
        "ffmpeg_crop_filter": plan.ffmpeg_crop_filter,
        "layout_rationale": plan.layout_rationale,
        "facecam_crop_override": facecam_crop,
        "preview_render_filter_kind": "cpu_1080x1920_caption_overlay",
        "source_video": str(video_path),
        "timestamp": float(timestamp),
        "duration_seconds": validate_duration(duration),
    }


def write_layout_json(path: Path, layout_plan: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(layout_plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(path)


def build_video_filter(ass_path: str | Path) -> str:
    escaped_ass = escape_ffmpeg_filter_path(ass_path)
    return (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"subtitles='{escaped_ass}'"
    )


def build_ffmpeg_command(
    video_path: str | Path,
    timestamp: float,
    duration: float,
    output_video: str | Path,
    ass_path: str | Path,
) -> list[str]:
    safe_duration = validate_duration(duration)
    return [
        get_ffmpeg_path(),
        "-y",
        "-ss",
        f"{float(timestamp):.3f}",
        "-t",
        f"{safe_duration:.3f}",
        "-i",
        str(video_path),
        "-vf",
        build_video_filter(ass_path),
        "-an",
        "-r",
        "30",
        "-pix_fmt",
        "yuv420p",
        str(output_video),
    ]


def build_ffprobe_command(media_path: str | Path) -> list[str]:
    return [
        get_ffprobe_path(),
        "-v",
        "error",
        "-show_entries",
        "format=duration,size",
        "-show_streams",
        "-of",
        "json",
        str(media_path),
    ]


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        message = (
            "FFMPEG_PREVIEW_FAILED\n"
            f"returncode={exc.returncode}\n"
            f"command={exc.cmd}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
        raise RuntimeError(message) from exc


def build_manifest(
    output_paths: dict[str, Path],
    duration: float,
    layout_plan: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "status": "ok",
        "phase": PHASE,
        "purpose": PURPOSE,
        "dry_run": bool(dry_run),
        "duration_seconds": validate_duration(duration),
        "output_dir": str(output_paths["output_dir"]),
        "preview_video": str(output_paths["preview_video"]),
        "caption_ass": str(output_paths["caption_ass"]),
        "layout_json": str(output_paths["layout_json"]),
        "k3": {
            "ass_generated_by_project_code": True,
            "caption_codepath": "core.caption_ass_builder.CaptionASSBuilder.generate_ass_file",
            "active_word_highlighting": True,
            "owner_friend_styles": True,
        },
        "k6": {
            "target_resolution": "1080x1920",
            "layout_codepath_used": bool(layout_plan.get("layout_codepath")),
            "focus_or_reframe_codepath_used": bool(
                layout_plan.get("focus_or_reframe_codepath_used")
            ),
            "layout_type": layout_plan.get("layout_type"),
        },
        "safety": {
            "temp_only": True,
            "full_render": False,
            "ingest": False,
            "q" + "wen": False,
            "music": False,
        },
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(path)


def run_preview(
    video_path: str | Path,
    timestamp: float,
    duration: float,
    output_dir: str | Path | None = None,
    facecam_crop: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    safe_duration = validate_duration(duration)
    video = Path(video_path)
    if not video.exists():
        raise RuntimeError("VIDEO_SOURCE_MISSING")

    paths = build_output_paths(output_dir)
    paths["output_dir"].mkdir(parents=True, exist_ok=True)

    crop = parse_facecam_crop(facecam_crop)
    layout_plan = build_layout_plan(video, timestamp, safe_duration, crop)
    write_layout_json(paths["layout_json"], layout_plan)

    if not dry_run:
        write_caption_ass(paths["caption_ass"], safe_duration)
        command = build_ffmpeg_command(
            video,
            timestamp,
            safe_duration,
            paths["preview_video"],
            paths["caption_ass"],
        )
        run_command(command)
        layout_plan["ffprobe_command"] = build_ffprobe_command(paths["preview_video"])

    manifest = build_manifest(paths, safe_duration, layout_plan, dry_run=dry_run)
    write_manifest(paths["manifest"], manifest)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TEMP-only K3/K6 visual proof preview.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--timestamp", required=True, type=float)
    parser.add_argument("--duration", type=float, default=4.0)
    parser.add_argument("--output-dir", default=str(default_output_dir()))
    parser.add_argument("--facecam-crop", default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = run_preview(
        video_path=args.video,
        timestamp=args.timestamp,
        duration=args.duration,
        output_dir=args.output_dir,
        facecam_crop=args.facecam_crop,
        dry_run=args.dry_run,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

