from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PreprocessingManifest:
    job_id: str
    source_path: str
    source_fingerprint: dict[str, Any]
    cache_key: str

    preprocessed_dir: str
    audio_dir: str
    frames_dir: str
    thumbnails_dir: str
    temp_dir: str
    manifest_path: str

    analysis_audio_path: str
    speech_audio_path: str
    music_audio_path: str
    frame_pattern: str
    thumbnail_pattern: str

    audio_extraction_plan: dict[str, Any] = field(default_factory=dict)
    audio_targets: list[dict[str, Any]] = field(default_factory=list)

    status: str = "ready"
    reused_cache: bool = False

    created_at: str | None = None
    updated_at: str | None = None

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_path": self.source_path,
            "source_fingerprint": dict(self.source_fingerprint),
            "cache_key": self.cache_key,
            "preprocessed_dir": self.preprocessed_dir,
            "audio_dir": self.audio_dir,
            "frames_dir": self.frames_dir,
            "thumbnails_dir": self.thumbnails_dir,
            "temp_dir": self.temp_dir,
            "manifest_path": self.manifest_path,
            "analysis_audio_path": self.analysis_audio_path,
            "speech_audio_path": self.speech_audio_path,
            "music_audio_path": self.music_audio_path,
            "frame_pattern": self.frame_pattern,
            "thumbnail_pattern": self.thumbnail_pattern,
            "audio_extraction_plan": dict(self.audio_extraction_plan),
            "audio_targets": list(self.audio_targets),
            "status": self.status,
            "reused_cache": self.reused_cache,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PreprocessingManifest":
        return cls(
            job_id=str(data.get("job_id", "")),
            source_path=str(data.get("source_path", "")),
            source_fingerprint=dict(data.get("source_fingerprint") or {}),
            cache_key=str(data.get("cache_key", "")),
            preprocessed_dir=str(data.get("preprocessed_dir", "")),
            audio_dir=str(data.get("audio_dir", "")),
            frames_dir=str(data.get("frames_dir", "")),
            thumbnails_dir=str(data.get("thumbnails_dir", "")),
            temp_dir=str(data.get("temp_dir", "")),
            manifest_path=str(data.get("manifest_path", "")),
            analysis_audio_path=str(data.get("analysis_audio_path", "")),
            speech_audio_path=str(data.get("speech_audio_path", "")),
            music_audio_path=str(data.get("music_audio_path", "")),
            frame_pattern=str(data.get("frame_pattern", "")),
            thumbnail_pattern=str(data.get("thumbnail_pattern", "")),
            audio_extraction_plan=dict(data.get("audio_extraction_plan") or {}),
            audio_targets=list(data.get("audio_targets") or []),
            status=str(data.get("status", "ready")),
            reused_cache=bool(data.get("reused_cache", False)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),

        )
