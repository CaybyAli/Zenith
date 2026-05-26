from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class AudioStreamInspectionError(RuntimeError):
    """Raised when ffprobe cannot inspect the media stream layout."""


@dataclass(frozen=True)
class AudioStream:
    index: int
    channels: int
    sample_rate: int
    codec: str
    duration_seconds: float
    label: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "channels": self.channels,
            "sample_rate": self.sample_rate,
            "codec": self.codec,
            "duration_seconds": self.duration_seconds,
            "label": self.label,
        }


@dataclass(frozen=True)
class AudioStreamInventory:
    streams: list[AudioStream]
    is_multi_track: bool
    has_mic_track: bool
    has_discord_track: bool
    has_ingame_track: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "streams": [stream.to_dict() for stream in self.streams],
            "is_multi_track": self.is_multi_track,
            "has_mic_track": self.has_mic_track,
            "has_discord_track": self.has_discord_track,
            "has_ingame_track": self.has_ingame_track,
        }


class AudioStreamInspector:
    """Inspect audio streams in a media file via local ffprobe."""

    def __init__(self, ffprobe_path: str = "ffprobe") -> None:
        self.ffprobe_path = ffprobe_path

    def inspect(self, video_path: str) -> AudioStreamInventory:
        source = Path(video_path)
        if not source.exists():
            raise FileNotFoundError(f"Audio stream source not found: {video_path}")

        command = [
            self.ffprobe_path,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(source),
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise AudioStreamInspectionError(f"ffprobe failed: {exc}") from exc

        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout or "").strip()
            raise AudioStreamInspectionError(
                f"ffprobe returned {completed.returncode}: {message}"
            )

        try:
            payload = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise AudioStreamInspectionError("ffprobe returned invalid JSON") from exc

        inventory = self._inventory_from_ffprobe_payload(payload)
        if len(inventory.streams) == 1:
            logger.warning(
                "single_audio_stream_fallback path=%s stream_index=%s",
                str(source),
                inventory.streams[0].index,
            )

        return inventory

    def _inventory_from_ffprobe_payload(
        self,
        payload: dict[str, Any],
    ) -> AudioStreamInventory:
        streams_payload = payload.get("streams") or []
        if not isinstance(streams_payload, list):
            streams_payload = []

        format_payload = payload.get("format") or {}
        format_duration = _safe_float(format_payload.get("duration"), default=0.0)

        audio_payloads = [
            stream
            for stream in streams_payload
            if isinstance(stream, dict) and stream.get("codec_type") == "audio"
        ]

        audio_streams: list[AudioStream] = []
        for audio_ordinal, stream in enumerate(audio_payloads):
            index = _safe_int(stream.get("index"), default=audio_ordinal)
            channels = _safe_int(stream.get("channels"), default=0)
            sample_rate = _safe_int(stream.get("sample_rate"), default=0)
            codec = str(stream.get("codec_name") or "unknown").strip() or "unknown"
            duration = _safe_float(stream.get("duration"), default=format_duration)
            label = self._label_for_audio_stream(
                audio_ordinal=audio_ordinal,
                audio_stream_count=len(audio_payloads),
                channels=channels,
            )
            audio_streams.append(
                AudioStream(
                    index=index,
                    channels=channels,
                    sample_rate=sample_rate,
                    codec=codec,
                    duration_seconds=duration,
                    label=label,
                )
            )

        return AudioStreamInventory(
            streams=audio_streams,
            is_multi_track=len(audio_streams) >= 2,
            has_mic_track=any(stream.label == "mic" for stream in audio_streams),
            has_discord_track=any(
                stream.label == "discord" for stream in audio_streams
            ),
            has_ingame_track=any(stream.label == "ingame" for stream in audio_streams),
        )

    def _label_for_audio_stream(
        self,
        *,
        audio_ordinal: int,
        audio_stream_count: int,
        channels: int,
    ) -> str:
        if audio_stream_count <= 1:
            return "unknown"

        if audio_ordinal == 0 and channels == 1:
            return "mic"

        if audio_ordinal == 1 and channels == 2:
            return "discord"

        if audio_ordinal == 2 and channels == 2:
            return "ingame"

        return "unknown"


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
