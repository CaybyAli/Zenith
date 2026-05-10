from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FileInfo:
    path: str
    exists: bool
    extension: str
    size_bytes: int | None = None
    is_supported_format: bool = False

    duration_seconds: float | None = None
    container_format: str | None = None

    video_stream_count: int = 0
    audio_stream_count: int = 0
    has_video: bool = False
    has_audio: bool = False

    width: int | None = None
    height: int | None = None
    fps: float | None = None

    video_codecs: list[str] = field(default_factory=list)
    audio_codecs: list[str] = field(default_factory=list)

    raw_ffprobe: dict[str, Any] = field(default_factory=dict)

    probe_status: str = "not_run"
    probe_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "exists": self.exists,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "is_supported_format": self.is_supported_format,
            "duration_seconds": self.duration_seconds,
            "container_format": self.container_format,
            "video_stream_count": self.video_stream_count,
            "audio_stream_count": self.audio_stream_count,
            "has_video": self.has_video,
            "has_audio": self.has_audio,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "video_codecs": list(self.video_codecs),
            "audio_codecs": list(self.audio_codecs),
            "raw_ffprobe": dict(self.raw_ffprobe),
            "probe_status": self.probe_status,
            "probe_error": self.probe_error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileInfo":
        return cls(
            path=str(data.get("path", "")),
            exists=bool(data.get("exists", False)),
            extension=str(data.get("extension", "")),
            size_bytes=data.get("size_bytes"),
            is_supported_format=bool(data.get("is_supported_format", False)),
            duration_seconds=data.get("duration_seconds"),
            container_format=data.get("container_format"),
            video_stream_count=int(data.get("video_stream_count", 0) or 0),
            audio_stream_count=int(data.get("audio_stream_count", 0) or 0),
            has_video=bool(data.get("has_video", False)),
            has_audio=bool(data.get("has_audio", False)),
            width=data.get("width"),
            height=data.get("height"),
            fps=data.get("fps"),
            video_codecs=list(data.get("video_codecs") or []),
            audio_codecs=list(data.get("audio_codecs") or []),
            raw_ffprobe=dict(data.get("raw_ffprobe") or {}),
            probe_status=str(data.get("probe_status", "not_run")),
            probe_error=data.get("probe_error"),
        )
