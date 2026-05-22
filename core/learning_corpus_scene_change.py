from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from core.ffmpeg_helper import get_ffmpeg_path, get_ffprobe_path


@dataclass(frozen=True)
class SceneChangeResult:
    """Stable scene-change payload used by style_fingerprint.json."""

    count: int
    rate_per_minute: float
    boundaries_seconds: list[float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SHOWINFO_PTS_TIME_RE = re.compile(r"pts_time:(?P<time>[0-9]+(?:\.[0-9]+)?)")


def extract_scene_changes(
    media_path: str | Path,
    *,
    threshold: float = 0.35,
    ffmpeg_path: str | None = None,
    ffprobe_path: str | None = None,
) -> dict[str, Any]:
    """
    Detect scene changes with local FFmpeg only.

    Output schema:
    - count
    - rate_per_minute
    - boundaries_seconds
    """

    path = Path(media_path)
    if not path.exists():
        raise FileNotFoundError(f"Scene-change input does not exist: {path}")

    if threshold <= 0 or threshold >= 1:
        raise ValueError("threshold must be between 0 and 1")

    duration_seconds = probe_media_duration_seconds(path, ffprobe_path=ffprobe_path)
    boundaries = detect_scene_boundaries_with_ffmpeg(
        path,
        threshold=threshold,
        ffmpeg_path=ffmpeg_path,
    )

    count = len(boundaries)
    if duration_seconds > 0:
        rate_per_minute = round(count / (duration_seconds / 60.0), 6)
    else:
        rate_per_minute = 0.0

    return SceneChangeResult(
        count=count,
        rate_per_minute=rate_per_minute,
        boundaries_seconds=boundaries,
    ).to_dict()


def probe_media_duration_seconds(
    media_path: str | Path,
    *,
    ffprobe_path: str | None = None,
) -> float:
    """Return media duration in seconds via ffprobe."""

    path = Path(media_path)
    command = [
        ffprobe_path or get_ffprobe_path(),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]

    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    raw_duration = completed.stdout.strip()
    try:
        duration = float(raw_duration)
    except ValueError as exc:
        raise ValueError(f"Could not parse media duration for {path}: {raw_duration!r}") from exc

    if duration < 0:
        return 0.0
    return duration


def detect_scene_boundaries_with_ffmpeg(
    media_path: str | Path,
    *,
    threshold: float,
    ffmpeg_path: str | None = None,
) -> list[float]:
    """
    Run FFmpeg scene detection and return deterministic boundary times.

    FFmpeg writes showinfo lines to stderr. We parse pts_time values from those
    lines and normalize the result to sorted unique millisecond values.
    """

    path = Path(media_path)
    filter_expr = f"select='gt(scene,{threshold})',showinfo"
    command = [
        ffmpeg_path or get_ffmpeg_path(),
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-filter:v",
        filter_expr,
        "-an",
        "-f",
        "null",
        "-",
    ]

    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    return parse_scene_boundaries_from_ffmpeg_output(completed.stderr)


def parse_scene_boundaries_from_ffmpeg_output(output: str) -> list[float]:
    """Parse unique pts_time values from FFmpeg showinfo output."""

    found: set[float] = set()
    for match in _SHOWINFO_PTS_TIME_RE.finditer(output or ""):
        try:
            value = round(float(match.group("time")), 3)
        except ValueError:
            continue

        if value >= 0:
            found.add(value)

    return sorted(found)
