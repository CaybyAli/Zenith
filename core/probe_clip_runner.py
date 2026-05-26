from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from core.ffmpeg_helper import apply_ffmpeg_thread_cap
from core.ffmpeg_capability_resolver import resolve_ffmpeg_capabilities
from core.resource_monitor import guarded_ffmpeg_execution

_ENCODER_CACHE: dict[tuple[str, str], str] = {}


def _resolve_encoder(ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> str:
    cache_key = (str(ffmpeg_path), str(ffprobe_path))
    if cache_key in _ENCODER_CACHE:
        return _ENCODER_CACHE[cache_key]

    try:
        report = resolve_ffmpeg_capabilities(
            {
                "job_id": "probe_clip_runner",
                "ffmpeg_path_hint": str(ffmpeg_path),
                "ffprobe_path_hint": str(ffprobe_path),
                "ffmpeg_resolver_allow_tool_probe": True,
            }
        )
        encoder = "h264_nvenc" if bool(getattr(report, "has_nvenc", False)) else "libx264"
    except Exception:
        encoder = "libx264"

    _ENCODER_CACHE[cache_key] = encoder
    return encoder


def run_probe_clip(
    video_path: str,
    output_dir: str,
    start_sec: float = 0.0,
    duration: float = 10.0,
) -> int:
    """
    Render a short probe-clip from video_path using ASS subtitles
    and write it to output_dir.
    """
    from core.caption_ass_builder import (
        DEFAULT_FONTS_DIR,
        build_ass_file,
        escape_ffmpeg_filter_path,
    )

    src = Path(video_path)
    if not src.exists():
        print(f"[probe_clip] ERROR  video not found: {src}", file=sys.stderr)
        return 1

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    test_words = [
        {"word": "PROBE", "start": 0.0, "end": 0.5},
        {"word": "CLIP", "start": 0.5, "end": 1.0},
        {"word": "D7", "start": 1.0, "end": 1.5},
        {"word": "ASS", "start": 1.5, "end": 2.0},
        {"word": "AKTIV", "start": 2.0, "end": 2.5},
    ]

    ass_path = out_dir / "probe_captions.ass"
    build_ass_file(
        segments=test_words,
        highlight_words=["D7"],
        output_path=str(ass_path),
    )
    print(f"[probe_clip] ASS_WRITTEN  {ass_path}")

    escaped_ass_path = escape_ffmpeg_filter_path(ass_path)
    escaped_fonts_dir = escape_ffmpeg_filter_path(DEFAULT_FONTS_DIR)

    ffmpeg_path = "ffmpeg"
    video_encoder = _resolve_encoder(ffmpeg_path)
    if video_encoder == "h264_nvenc":
        video_encoder_args = ["-c:v", video_encoder, "-pix_fmt", "yuv420p", "-cq", "23", "-preset", "fast"]
    else:
        video_encoder_args = ["-c:v", video_encoder, "-crf", "23", "-preset", "fast"]

    out_mp4 = out_dir / "probe_clip.mp4"
    cmd = [
        ffmpeg_path,
        "-y",
        "-ss",
        str(start_sec),
        "-hwaccel",
        "cuda",
        "-hwaccel_output_format",
        "cuda",
        "-i",
        str(src),
        "-t",
        str(duration),
        "-vf",
        (
            "hwdownload,format=nv12,"
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1,"
            f"subtitles={escaped_ass_path}:fontsdir={escaped_fonts_dir}"
        ),
        *video_encoder_args,
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(out_mp4),
    ]

    cmd = apply_ffmpeg_thread_cap(cmd)
    print(f"[probe_clip] CMD  {' '.join(cmd)}")
    with guarded_ffmpeg_execution(cmd):
        result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        fallback_cmd: list[str] = []
        skip_next = 0
        for part in cmd:
            if skip_next > 0:
                skip_next -= 1
                continue
            if part in {"-hwaccel", "-hwaccel_output_format"}:
                skip_next = 1
                continue
            fallback_cmd.append(part)

        for index, part in enumerate(fallback_cmd):
            if part == "-vf" and index + 1 < len(fallback_cmd):
                fallback_cmd[index + 1] = (
                    fallback_cmd[index + 1]
                    .replace("hwdownload,format=nv12,", "")
                    .replace("hwdownload,format=yuv420p,", "")
                )

        print("[probe_clip] HWDEC_FALLBACK  retry_without_cuda_hwaccel")
        fallback_cmd = apply_ffmpeg_thread_cap(fallback_cmd)
        with guarded_ffmpeg_execution(fallback_cmd):
            result = subprocess.run(fallback_cmd, capture_output=False)

    if result.returncode != 0:
        print(
            f"[probe_clip] FFMPEG_ERROR  returncode={result.returncode}",
            file=sys.stderr,
        )
        return 1

    print(f"[probe_clip] OK  {out_mp4}")
    return 0
