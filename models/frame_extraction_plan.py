from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FrameExtractionTarget:
    target_id: str
    purpose: str
    output_pattern: str
    format: str = "jpg"
    interval_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
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
            "output_pattern": self.output_pattern,
            "format": self.format,
            "interval_seconds": self.interval_seconds,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "enabled": self.enabled,
            "status": self.status,
            "command_preview": list(self.command_preview),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FrameExtractionTarget":
        return cls(
            target_id=str(data.get("target_id", "")),
            purpose=str(data.get("purpose", "")),
            output_pattern=str(data.get("output_pattern", "")),
            format=str(data.get("format", "jpg")),
            interval_seconds=(
                float(data["interval_seconds"])
                if data.get("interval_seconds") is not None
                else None
            ),
            width=(
                int(data["width"])
                if data.get("width") is not None
                else None
            ),
            height=(
                int(data["height"])
                if data.get("height") is not None
                else None
            ),
            fps=(
                float(data["fps"])
                if data.get("fps") is not None
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
class FrameExtractionPlan:
    job_id: str
    source_path: str
    frames_dir: str
    thumbnails_dir: str
    targets: list[FrameExtractionTarget] = field(default_factory=list)
    status: str = "planned"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_path": self.source_path,
            "frames_dir": self.frames_dir,
            "thumbnails_dir": self.thumbnails_dir,
            "targets": [target.to_dict() for target in self.targets],
            "status": self.status,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FrameExtractionPlan":
        return cls(
            job_id=str(data.get("job_id", "")),
            source_path=str(data.get("source_path", "")),
            frames_dir=str(data.get("frames_dir", "")),
            thumbnails_dir=str(data.get("thumbnails_dir", "")),
            targets=[
                FrameExtractionTarget.from_dict(target)
                for target in list(data.get("targets") or [])
            ],
            status=str(data.get("status", "planned")),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            metadata=dict(data.get("metadata") or {}),
        )
