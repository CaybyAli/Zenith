from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import subprocess

from core.ffmpeg_helper import get_ffprobe_path


@dataclass(frozen=True)
class SourceFormat:
    width: int
    height: int
    aspect_ratio: float
    is_32_9_composite: bool
    gameplay_region: tuple[int, int, int, int]
    facecam_region: tuple[int, int, int, int]


class ShortsSourceFormatDetector:
    @staticmethod
    def detect(video_path: str | Path, ffprobe_binary: str | None = None) -> SourceFormat:
        resolved_ffprobe = str(ffprobe_binary or get_ffprobe_path())
        cmd = [
            resolved_ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(video_path),
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(completed.stdout)
        streams = data.get("streams") or []
        if not streams:
            raise ValueError(f"ffprobe returned no video stream for {video_path}")

        stream = streams[0]
        width = int(stream["width"])
        height = int(stream["height"])
        if width <= 0 or height <= 0:
            raise ValueError(
                f"Invalid source dimensions from ffprobe: width={width} height={height}"
            )

        aspect_ratio = width / height
        is_32_9_composite = aspect_ratio > 3.0
        half_width = width // 2
        gameplay_region = (0, 0, half_width, height)
        facecam_region = (half_width, 0, width - half_width, height)

        return SourceFormat(
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            is_32_9_composite=is_32_9_composite,
            gameplay_region=gameplay_region,
            facecam_region=facecam_region,
        )
