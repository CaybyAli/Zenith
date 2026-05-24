from __future__ import annotations

import subprocess
import sys
from pathlib import Path


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

    out_mp4 = out_dir / "probe_clip.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start_sec),
        "-i",
        str(src),
        "-t",
        str(duration),
        "-vf",
        (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1,"
            f"subtitles={escaped_ass_path}:fontsdir={escaped_fonts_dir}"
        ),
        "-c:v",
        "libx264",
        "-crf",
        "23",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(out_mp4),
    ]

    print(f"[probe_clip] CMD  {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        print(
            f"[probe_clip] FFMPEG_ERROR  returncode={result.returncode}",
            file=sys.stderr,
        )
        return 1

    print(f"[probe_clip] OK  {out_mp4}")
    return 0
