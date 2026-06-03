from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AudioTrackRole:
    role: str
    audio_track: str
    speaker: str
    ffmpeg_audio_index: int
    transcribe_for_captions: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "audio_track": self.audio_track,
            "speaker": self.speaker,
            "ffmpeg_audio_index": self.ffmpeg_audio_index,
            "transcribe_for_captions": self.transcribe_for_captions,
        }


@dataclass(frozen=True)
class AudioTrackMappingConfig:
    video_id: str
    source_path: str | None
    config_path: str
    tracks: tuple[AudioTrackRole, ...]

    def caption_tracks(self) -> list[AudioTrackRole]:
        allowed = {"owner", "friend", "mic", "discord"}
        result: list[AudioTrackRole] = []
        for track in self.tracks:
            marker = f"{track.role} {track.audio_track}".casefold()
            if not track.transcribe_for_captions:
                continue
            if any(item in marker for item in allowed):
                result.append(track)
        return result

    def track_for_audio_track(self, audio_track: str) -> AudioTrackRole | None:
        target = str(audio_track or "").strip().casefold()
        for track in self.tracks:
            if track.audio_track.casefold() == target:
                return track
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "source_path": self.source_path,
            "config_path": self.config_path,
            "audio_tracks": [track.to_dict() for track in self.tracks],
        }


def load_audio_track_mapping_config(
    source_video_path: str | Path,
    *,
    config_dir: str | Path = "video_configs",
) -> AudioTrackMappingConfig | None:
    source = Path(source_video_path)
    config_root = Path(config_dir)

    candidates = _candidate_config_paths(source=source, config_root=config_root)
    for path in candidates:
        if path.exists():
            return _load_config(path)

    return None


def _candidate_config_paths(source: Path, config_root: Path) -> list[Path]:
    candidates: list[Path] = []

    if source.parent.name:
        candidates.append(config_root / f"{source.parent.name}.audio_tracks.json")

    if source.stem:
        candidates.append(config_root / f"{source.stem}.audio_tracks.json")

    # Keep order stable while removing duplicates.
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def _load_config(path: Path) -> AudioTrackMappingConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_tracks = payload.get("audio_tracks") or payload.get("tracks") or []
    tracks: list[AudioTrackRole] = []

    for raw in raw_tracks:
        tracks.append(
            AudioTrackRole(
                role=_safe_label(raw.get("role"), "unknown"),
                audio_track=_safe_label(raw.get("audio_track"), "unknown"),
                speaker=_safe_label(raw.get("speaker"), "unknown"),
                ffmpeg_audio_index=_parse_ffmpeg_audio_index(raw.get("ffmpeg_audio_index")),
                transcribe_for_captions=bool(raw.get("transcribe_for_captions", False)),
            )
        )

    return AudioTrackMappingConfig(
        video_id=str(payload.get("video_id") or path.name.removesuffix(".audio_tracks.json")),
        source_path=payload.get("source_path"),
        config_path=str(path),
        tracks=tuple(tracks),
    )


def _safe_label(value: Any, default: str) -> str:
    clean = str(value or "").strip().lower()
    return clean or default


def _parse_ffmpeg_audio_index(value: Any) -> int:
    if isinstance(value, int):
        if value < 0:
            raise ValueError("ffmpeg_audio_index must not be negative")
        return value

    text = str(value or "").strip().lower()
    if text.isdigit():
        return int(text)

    match = re.fullmatch(r"0:a:(\d+)", text)
    if match:
        return int(match.group(1))

    raise ValueError(f"Invalid ffmpeg_audio_index: {value!r}")
