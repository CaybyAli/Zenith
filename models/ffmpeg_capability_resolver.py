from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


STATUS_READY = "ffmpeg_capability_ready"
STATUS_READY_WITH_WARNINGS = "ffmpeg_capability_ready_with_warnings"
STATUS_BLOCKED = "ffmpeg_capability_blocked"
STATUS_FAILED = "ffmpeg_capability_failed"

DEFAULT_FFMPEG_PATH_HINT = r"D:\Tools\ffmpeg\bin\ffmpeg.exe"
DEFAULT_FFPROBE_PATH_HINT = r"D:\Tools\ffmpeg\bin\ffprobe.exe"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class FFmpegToolPath:
    tool_name: str
    path_hint: str | None = None
    path_safety_status: str = "unknown"
    exists_hint: bool = False
    is_absolute_hint: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FFmpegToolPath":
        return cls(
            tool_name=str(data.get("tool_name") or ""),
            path_hint=data.get("path_hint"),
            path_safety_status=str(data.get("path_safety_status") or "unknown"),
            exists_hint=bool(data.get("exists_hint", False)),
            is_absolute_hint=bool(data.get("is_absolute_hint", False)),
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class FFmpegCapability:
    capability_id: str
    capability_type: str
    name: str
    available: bool = False
    source_probe: str = "not_probed"
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FFmpegCapability":
        return cls(
            capability_id=str(data.get("capability_id") or ""),
            capability_type=str(data.get("capability_type") or ""),
            name=str(data.get("name") or ""),
            available=bool(data.get("available", False)),
            source_probe=str(data.get("source_probe") or "not_probed"),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class FFmpegCapabilityResolverReport:
    report_id: str
    job_id: str
    status: str = STATUS_READY_WITH_WARNINGS
    ffmpeg_path: FFmpegToolPath | None = None
    ffprobe_path: FFmpegToolPath | None = None
    allow_tool_probe: bool = False
    tool_probe_attempted: bool = False
    tool_probe_succeeded: bool = False
    ffmpeg_version: str | None = None
    ffprobe_version: str | None = None
    capabilities: list[FFmpegCapability] = field(default_factory=list)

    has_h264: bool = False
    has_aac: bool = False
    has_nvenc: bool = False
    has_scale_filter: bool = False
    has_concat_support: bool = False
    has_loudnorm_filter: bool = False

    can_prepare_real_render_tools: bool = False
    can_render: bool = False
    can_process_media: bool = False
    can_write_media: bool = False
    can_probe_media_files: bool = False

    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["can_render"] = False
        data["can_process_media"] = False
        data["can_write_media"] = False
        data["can_probe_media_files"] = False
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FFmpegCapabilityResolverReport":
        ffmpeg_path_data = data.get("ffmpeg_path")
        ffprobe_path_data = data.get("ffprobe_path")
        capability_items = data.get("capabilities") or []

        return cls(
            report_id=str(data.get("report_id") or ""),
            job_id=str(data.get("job_id") or ""),
            status=str(data.get("status") or STATUS_READY_WITH_WARNINGS),
            ffmpeg_path=(
                FFmpegToolPath.from_dict(ffmpeg_path_data)
                if isinstance(ffmpeg_path_data, dict)
                else None
            ),
            ffprobe_path=(
                FFmpegToolPath.from_dict(ffprobe_path_data)
                if isinstance(ffprobe_path_data, dict)
                else None
            ),
            allow_tool_probe=bool(data.get("allow_tool_probe", False)),
            tool_probe_attempted=bool(data.get("tool_probe_attempted", False)),
            tool_probe_succeeded=bool(data.get("tool_probe_succeeded", False)),
            ffmpeg_version=data.get("ffmpeg_version"),
            ffprobe_version=data.get("ffprobe_version"),
            capabilities=[
                FFmpegCapability.from_dict(item)
                for item in capability_items
                if isinstance(item, dict)
            ],
            has_h264=bool(data.get("has_h264", False)),
            has_aac=bool(data.get("has_aac", False)),
            has_nvenc=bool(data.get("has_nvenc", False)),
            has_scale_filter=bool(data.get("has_scale_filter", False)),
            has_concat_support=bool(data.get("has_concat_support", False)),
            has_loudnorm_filter=bool(data.get("has_loudnorm_filter", False)),
            can_prepare_real_render_tools=bool(
                data.get("can_prepare_real_render_tools", False)
            ),
            can_render=False,
            can_process_media=False,
            can_write_media=False,
            can_probe_media_files=False,
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            recommendation=data.get("recommendation"),
            created_at=str(data.get("created_at") or utc_now_iso()),
            metadata=dict(data.get("metadata") or {}),
        )
