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
    frame_extraction_plan: dict[str, Any] = field(default_factory=dict)
    frame_targets: list[dict[str, Any]] = field(default_factory=list)

    cache_validation: dict[str, Any] = field(default_factory=dict)
    cache_validation_status: str | None = None
    cache_reuse_allowed: bool = False

    audio_extraction_result: dict[str, Any] = field(default_factory=dict)
    audio_extraction_status: str | None = None
    ready_audio_targets: list[str] = field(default_factory=list)
    missing_audio_targets: list[str] = field(default_factory=list)
    failed_audio_targets: list[str] = field(default_factory=list)

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
            "frame_extraction_plan": dict(self.frame_extraction_plan),
            "frame_targets": list(self.frame_targets),
            "cache_validation": dict(self.cache_validation),
            "cache_validation_status": self.cache_validation_status,
            "cache_reuse_allowed": self.cache_reuse_allowed,
            "audio_extraction_result": dict(self.audio_extraction_result),
            "audio_extraction_status": self.audio_extraction_status,
            "ready_audio_targets": list(self.ready_audio_targets),
            "missing_audio_targets": list(self.missing_audio_targets),
            "failed_audio_targets": list(self.failed_audio_targets),
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
            frame_extraction_plan=dict(data.get("frame_extraction_plan") or {}),
            frame_targets=list(data.get("frame_targets") or []),
            cache_validation=dict(data.get("cache_validation") or {}),
            cache_validation_status=data.get("cache_validation_status"),
            cache_reuse_allowed=bool(data.get("cache_reuse_allowed", False)),
            audio_extraction_result=dict(data.get("audio_extraction_result") or {}),
            audio_extraction_status=data.get("audio_extraction_status"),
            ready_audio_targets=list(data.get("ready_audio_targets") or []),
            missing_audio_targets=list(data.get("missing_audio_targets") or []),
            failed_audio_targets=list(data.get("failed_audio_targets") or []),
            status=str(data.get("status", "ready")),
            reused_cache=bool(data.get("reused_cache", False)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),

        )
