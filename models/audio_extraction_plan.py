from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AudioExtractionTarget:
    target_id: str
    purpose: str
    output_path: str
    format: str = "wav"
    sample_rate: int | None = None
    channels: int | None = None
    source_stream_index: int | None = None
    enabled: bool = True
    status: str = "planned"
    command_preview: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "purpose": self.purpose,
            "output_path": self.output_path,
            "format": self.format,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "source_stream_index": self.source_stream_index,
            "enabled": self.enabled,
            "status": self.status,
            "command_preview": list(self.command_preview),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AudioExtractionTarget":
        return cls(
            target_id=str(data.get("target_id", "")),
            purpose=str(data.get("purpose", "")),
            output_path=str(data.get("output_path", "")),
            format=str(data.get("format", "wav")),
            sample_rate=(
                int(data["sample_rate"])
                if data.get("sample_rate") is not None
                else None
            ),
            channels=(
                int(data["channels"])
                if data.get("channels") is not None
                else None
            ),
            source_stream_index=(
                int(data["source_stream_index"])
                if data.get("source_stream_index") is not None
                else None
            ),
            enabled=bool(data.get("enabled", True)),
            status=str(data.get("status", "planned")),
            command_preview=list(data.get("command_preview") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class AudioExtractionPlan:
    job_id: str
    source_path: str
    audio_dir: str
    targets: list[AudioExtractionTarget] = field(default_factory=list)
    status: str = "planned"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_path": self.source_path,
            "audio_dir": self.audio_dir,
            "targets": [target.to_dict() for target in self.targets],
            "status": self.status,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AudioExtractionPlan":
        return cls(
            job_id=str(data.get("job_id", "")),
            source_path=str(data.get("source_path", "")),
            audio_dir=str(data.get("audio_dir", "")),
            targets=[
                AudioExtractionTarget.from_dict(target)
                for target in list(data.get("targets") or [])
            ],
            status=str(data.get("status", "planned")),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
