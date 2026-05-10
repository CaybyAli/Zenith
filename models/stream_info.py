from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StreamInfo:
    index: int | None
    codec_type: str | None
    codec_name: str | None = None

    width: int | None = None
    height: int | None = None
    fps: float | None = None

    channels: int | None = None
    sample_rate: int | None = None
    duration_seconds: float | None = None

    language: str | None = None
    title: str | None = None
    handler_name: str | None = None
    tags: dict[str, Any] = field(default_factory=dict)

    role: str = "unknown"
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "codec_type": self.codec_type,
            "codec_name": self.codec_name,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "channels": self.channels,
            "sample_rate": self.sample_rate,
            "duration_seconds": self.duration_seconds,
            "language": self.language,
            "title": self.title,
            "handler_name": self.handler_name,
            "tags": dict(self.tags),
            "role": self.role,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StreamInfo":
        return cls(
            index=data.get("index"),
            codec_type=data.get("codec_type"),
            codec_name=data.get("codec_name"),
            width=data.get("width"),
            height=data.get("height"),
            fps=data.get("fps"),
            channels=data.get("channels"),
            sample_rate=data.get("sample_rate"),
            duration_seconds=data.get("duration_seconds"),
            language=data.get("language"),
            title=data.get("title"),
            handler_name=data.get("handler_name"),
            tags=dict(data.get("tags") or {}),
            role=str(data.get("role", "unknown")),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            reasons=list(data.get("reasons") or []),
        )


@dataclass
class StreamClassificationResult:
    file_path: str | None = None
    stream_count: int = 0

    video_streams: list[dict[str, Any]] = field(default_factory=list)
    audio_streams: list[dict[str, Any]] = field(default_factory=list)

    primary_video_stream: dict[str, Any] | None = None
    primary_audio_stream: dict[str, Any] | None = None

    voice_audio_candidates: list[dict[str, Any]] = field(default_factory=list)
    game_audio_candidates: list[dict[str, Any]] = field(default_factory=list)
    discord_audio_candidates: list[dict[str, Any]] = field(default_factory=list)
    music_audio_candidates: list[dict[str, Any]] = field(default_factory=list)
    unknown_audio_streams: list[dict[str, Any]] = field(default_factory=list)

    warnings: list[str] = field(default_factory=list)
    needs_manual_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "stream_count": self.stream_count,
            "video_streams": list(self.video_streams),
            "audio_streams": list(self.audio_streams),
            "primary_video_stream": self.primary_video_stream,
            "primary_audio_stream": self.primary_audio_stream,
            "voice_audio_candidates": list(self.voice_audio_candidates),
            "game_audio_candidates": list(self.game_audio_candidates),
            "discord_audio_candidates": list(self.discord_audio_candidates),
            "music_audio_candidates": list(self.music_audio_candidates),
            "unknown_audio_streams": list(self.unknown_audio_streams),
            "warnings": list(self.warnings),
            "needs_manual_review": self.needs_manual_review,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StreamClassificationResult":
        return cls(
            file_path=data.get("file_path"),
            stream_count=int(data.get("stream_count", 0) or 0),
            video_streams=list(data.get("video_streams") or []),
            audio_streams=list(data.get("audio_streams") or []),
            primary_video_stream=data.get("primary_video_stream"),
            primary_audio_stream=data.get("primary_audio_stream"),
            voice_audio_candidates=list(data.get("voice_audio_candidates") or []),
            game_audio_candidates=list(data.get("game_audio_candidates") or []),
            discord_audio_candidates=list(data.get("discord_audio_candidates") or []),
            music_audio_candidates=list(data.get("music_audio_candidates") or []),
            unknown_audio_streams=list(data.get("unknown_audio_streams") or []),
            warnings=list(data.get("warnings") or []),
            needs_manual_review=bool(data.get("needs_manual_review", False)),
        )
