from __future__ import annotations

import json
import math
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from core.ffmpeg_helper import get_ffmpeg_path, get_ffprobe_path


@dataclass(frozen=True)
class AudioProfileResult:
    """Stable audio payload used by style_fingerprint.json."""

    lufs_integrated: float
    rms_curve_sampled: list[float]
    peak_db: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_MAX_VOLUME_RE = re.compile(r"max_volume:\s*(?P<value>-?(?:inf|[0-9]+(?:\.[0-9]+)?))\s*dB")
_MEAN_VOLUME_RE = re.compile(r"mean_volume:\s*(?P<value>-?(?:inf|[0-9]+(?:\.[0-9]+)?))\s*dB")


def extract_audio_profile(
    media_path: str | Path,
    *,
    sample_interval_seconds: float = 5.0,
    ffmpeg_path: str | None = None,
    ffprobe_path: str | None = None,
) -> dict[str, Any]:
    """
    Extract passive local audio metrics for one media input.

    Output schema:
    - lufs_integrated
    - rms_curve_sampled
    - peak_db
    """

    path = Path(media_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio-profile input does not exist: {path}")

    if sample_interval_seconds <= 0:
        raise ValueError("sample_interval_seconds must be greater than zero")

    lufs_integrated = extract_lufs_integrated(path, ffmpeg_path=ffmpeg_path)
    peak_db = extract_peak_db(path, ffmpeg_path=ffmpeg_path)
    rms_curve = extract_rms_curve_sampled(
        path,
        sample_interval_seconds=sample_interval_seconds,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
    )

    return AudioProfileResult(
        lufs_integrated=lufs_integrated,
        rms_curve_sampled=rms_curve,
        peak_db=peak_db,
    ).to_dict()


def extract_lufs_integrated(
    media_path: str | Path,
    *,
    ffmpeg_path: str | None = None,
) -> float:
    """Read integrated LUFS via local FFmpeg loudnorm JSON output."""

    path = Path(media_path)
    command = [
        ffmpeg_path or get_ffmpeg_path(),
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
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

    payload = parse_loudnorm_json(completed.stderr)
    value = payload.get("input_i")
    return _safe_float(value, default=0.0)


def extract_peak_db(
    media_path: str | Path,
    *,
    ffmpeg_path: str | None = None,
) -> float:
    """Read max peak dB via local FFmpeg volumedetect."""

    path = Path(media_path)
    command = [
        ffmpeg_path or get_ffmpeg_path(),
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        "volumedetect",
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

    match = _MAX_VOLUME_RE.search(completed.stderr)
    if not match:
        return 0.0

    return _safe_float(match.group("value"), default=0.0)


def extract_rms_curve_sampled(
    media_path: str | Path,
    *,
    sample_interval_seconds: float,
    ffmpeg_path: str | None = None,
    ffprobe_path: str | None = None,
) -> list[float]:
    """
    Build a sampled RMS-like curve from FFmpeg astats RMS_level values.

    The output is a deterministic list of dB values sampled in fixed windows.
    """

    path = Path(media_path)
    duration_seconds = probe_media_duration_seconds(path, ffprobe_path=ffprobe_path)
    if duration_seconds <= 0:
        return []

    windows = build_sample_windows(duration_seconds, sample_interval_seconds)
    values: list[float] = []

    for start_seconds, window_duration in windows:
        values.append(
            extract_window_rms_db(
                path,
                start_seconds=start_seconds,
                window_duration=window_duration,
                ffmpeg_path=ffmpeg_path,
            )
        )

    return values


def extract_window_rms_db(
    media_path: str | Path,
    *,
    start_seconds: float,
    window_duration: float,
    ffmpeg_path: str | None = None,
) -> float:
    """Read one RMS-level value from a time window using FFmpeg astats."""

    path = Path(media_path)
    command = [
        ffmpeg_path or get_ffmpeg_path(),
        "-hide_banner",
        "-nostats",
        "-ss",
        _format_seconds(start_seconds),
        "-t",
        _format_seconds(window_duration),
        "-i",
        str(path),
        "-vn",
        "-af",
        "astats=metadata=1:reset=0",
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

    return parse_rms_db_from_astats_output(completed.stderr)


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

    return max(_safe_float(completed.stdout.strip(), default=0.0), 0.0)


def build_sample_windows(
    duration_seconds: float,
    sample_interval_seconds: float,
) -> list[tuple[float, float]]:
    """Build deterministic non-overlapping sample windows."""

    if duration_seconds <= 0:
        return []
    if sample_interval_seconds <= 0:
        raise ValueError("sample_interval_seconds must be greater than zero")

    window_count = max(1, math.ceil(duration_seconds / sample_interval_seconds))
    windows: list[tuple[float, float]] = []

    for index in range(window_count):
        start = round(index * sample_interval_seconds, 3)
        remaining = duration_seconds - start
        if remaining <= 0:
            break

        window_duration = round(min(sample_interval_seconds, remaining), 3)
        windows.append((start, window_duration))

    return windows


def parse_loudnorm_json(output: str) -> dict[str, Any]:
    """Parse the JSON object printed by FFmpeg loudnorm."""

    text = output or ""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return {}

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}

    if isinstance(parsed, dict):
        return parsed
    return {}


def parse_rms_db_from_astats_output(output: str) -> float:
    """Parse RMS level from FFmpeg astats output."""

    text = output or ""
    rms_values: list[float] = []

    for line in text.splitlines():
        if "RMS level dB" not in line:
            continue

        raw_value = line.rsplit(":", 1)[-1].strip()
        value = _safe_float(raw_value, default=float("nan"))
        if math.isfinite(value):
            rms_values.append(value)

    if rms_values:
        return round(sum(rms_values) / len(rms_values), 6)

    mean_match = _MEAN_VOLUME_RE.search(text)
    if mean_match:
        return _safe_float(mean_match.group("value"), default=0.0)

    return 0.0


def _safe_float(value: Any, *, default: float) -> float:
    try:
        converted = float(str(value).strip())
    except (TypeError, ValueError):
        return default

    if not math.isfinite(converted):
        return default

    return round(converted, 6)


def _format_seconds(value: float) -> str:
    return f"{max(value, 0.0):.3f}"
