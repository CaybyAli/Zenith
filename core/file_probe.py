from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from core.ffmpeg_helper import get_ffprobe_path
from models.file_info import FileInfo


SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".webm",
    ".flv",
}


class FileProbeError(RuntimeError):
    pass


def _extension(path: str | Path) -> str:
    return Path(path).suffix.lower()


def is_supported_video_extension(path: str | Path) -> bool:
    return _extension(path) in SUPPORTED_VIDEO_EXTENSIONS


def _parse_fps(value: Any) -> float | None:
    if not value:
        return None

    raw = str(value).strip()

    if "/" in raw:
        left, right = raw.split("/", 1)
        try:
            numerator = float(left)
            denominator = float(right)
            if denominator == 0:
                return None
            return round(numerator / denominator, 3)
        except Exception:
            return None

    try:
        return round(float(raw), 3)
    except Exception:
        return None


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except Exception:
        return None


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except Exception:
        return None


def _unique_strings(values: list[Any]) -> list[str]:
    result: list[str] = []

    for value in values:
        if value is None:
            continue

        text = str(value).strip()
        if not text:
            continue

        if text not in result:
            result.append(text)

    return result


def parse_ffprobe_json(
    path: str | Path,
    ffprobe_data: dict[str, Any],
) -> FileInfo:
    file_path = Path(path)
    extension = _extension(file_path)

    if not isinstance(ffprobe_data, dict):
        ffprobe_data = {}

    format_data = ffprobe_data.get("format") or {}
    if not isinstance(format_data, dict):
        format_data = {}

    streams = ffprobe_data.get("streams") or []
    if not isinstance(streams, list):
        streams = []

    video_streams: list[dict[str, Any]] = []
    audio_streams: list[dict[str, Any]] = []

    for stream in streams:
        if not isinstance(stream, dict):
            continue

        codec_type = stream.get("codec_type")

        if codec_type == "video":
            video_streams.append(stream)

        if codec_type == "audio":
            audio_streams.append(stream)

    first_video = video_streams[0] if video_streams else {}

    video_codecs = _unique_strings(
        [stream.get("codec_name") for stream in video_streams]
    )
    audio_codecs = _unique_strings(
        [stream.get("codec_name") for stream in audio_streams]
    )

    size_bytes = None
    if file_path.exists():
        try:
            size_bytes = file_path.stat().st_size
        except Exception:
            size_bytes = None

    return FileInfo(
        path=str(file_path),
        exists=file_path.exists(),
        extension=extension,
        size_bytes=size_bytes,
        is_supported_format=is_supported_video_extension(file_path),
        duration_seconds=_parse_float(format_data.get("duration")),
        container_format=format_data.get("format_name"),
        video_stream_count=len(video_streams),
        audio_stream_count=len(audio_streams),
        has_video=len(video_streams) > 0,
        has_audio=len(audio_streams) > 0,
        width=_parse_int(first_video.get("width")),
        height=_parse_int(first_video.get("height")),
        fps=_parse_fps(
            first_video.get("r_frame_rate")
            or first_video.get("avg_frame_rate")
        ),
        video_codecs=video_codecs,
        audio_codecs=audio_codecs,
        raw_ffprobe=ffprobe_data,
        probe_status="parsed",
        probe_error=None,
    )


def probe_file(
    path: str | Path,
    ffprobe_path: str | None = None,
) -> FileInfo:
    file_path = Path(path)
    extension = _extension(file_path)

    if not file_path.exists():
        return FileInfo(
            path=str(file_path),
            exists=False,
            extension=extension,
            is_supported_format=is_supported_video_extension(file_path),
            probe_status="missing",
            probe_error="file_not_found",
        )

    try:
        resolved_ffprobe_path = ffprobe_path or get_ffprobe_path()
    except Exception as exc:
        return FileInfo(
            path=str(file_path),
            exists=True,
            extension=extension,
            size_bytes=file_path.stat().st_size,
            is_supported_format=is_supported_video_extension(file_path),
            probe_status="failed",
            probe_error=str(exc),
        )

    command = [
        resolved_ffprobe_path,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return FileInfo(
                path=str(file_path),
                exists=True,
                extension=extension,
                size_bytes=file_path.stat().st_size,
                is_supported_format=is_supported_video_extension(file_path),
                probe_status="failed",
                probe_error=result.stderr.strip() or "ffprobe_failed",
            )

        data = json.loads(result.stdout or "{}")
        info = parse_ffprobe_json(file_path, data)
        info.probe_status = "ok"
        info.probe_error = None
        return info

    except Exception as exc:
        return FileInfo(
            path=str(file_path),
            exists=True,
            extension=extension,
            size_bytes=file_path.stat().st_size if file_path.exists() else None,
            is_supported_format=is_supported_video_extension(file_path),
            probe_status="failed",
            probe_error=str(exc),
        )
