from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


STATUS_READY = "ffmpeg_command_assembly_ready"
STATUS_READY_WITH_WARNINGS = "ffmpeg_command_assembly_ready_with_warnings"
STATUS_BLOCKED = "ffmpeg_command_assembly_blocked"
STATUS_FAILED = "ffmpeg_command_assembly_failed"

EXECUTION_MODE_ASSEMBLY_ONLY = "assembly_only"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class FFmpegArgumentToken:
    token_id: str
    value: str
    token_type: str = "unknown"
    source: str = "ffmpeg_command_assembly"
    safe: bool = True
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FFmpegArgumentToken":
        return cls(
            token_id=str(data.get("token_id") or ""),
            value=str(data.get("value") or ""),
            token_type=str(data.get("token_type") or "unknown"),
            source=str(data.get("source") or "ffmpeg_command_assembly"),
            safe=bool(data.get("safe", True)),
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class FFmpegCommandAssembly:
    assembly_id: str
    assembly_type: str
    description: str = ""
    argv_preview: list[str] = field(default_factory=list)
    argument_tokens: list[FFmpegArgumentToken] = field(default_factory=list)
    source_blueprint_step_ids: list[str] = field(default_factory=list)
    source_render_plan_segment_ids: list[str] = field(default_factory=list)
    output_target_id: str | None = None

    assembly_only: bool = True
    preview_only: bool = True
    execution_mode: str = EXECUTION_MODE_ASSEMBLY_ONLY

    can_execute_command: bool = False
    can_spawn_process: bool = False
    can_render: bool = False
    can_write_media: bool = False

    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["assembly_only"] = True
        data["preview_only"] = True
        data["execution_mode"] = EXECUTION_MODE_ASSEMBLY_ONLY
        data["can_execute_command"] = False
        data["can_spawn_process"] = False
        data["can_render"] = False
        data["can_write_media"] = False
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FFmpegCommandAssembly":
        token_items = data.get("argument_tokens") or []

        return cls(
            assembly_id=str(data.get("assembly_id") or ""),
            assembly_type=str(data.get("assembly_type") or ""),
            description=str(data.get("description") or ""),
            argv_preview=[str(item) for item in list(data.get("argv_preview") or [])],
            argument_tokens=[
                FFmpegArgumentToken.from_dict(item)
                for item in token_items
                if isinstance(item, dict)
            ],
            source_blueprint_step_ids=[
                str(item) for item in list(data.get("source_blueprint_step_ids") or [])
            ],
            source_render_plan_segment_ids=[
                str(item)
                for item in list(data.get("source_render_plan_segment_ids") or [])
            ],
            output_target_id=data.get("output_target_id"),
            assembly_only=True,
            preview_only=True,
            execution_mode=EXECUTION_MODE_ASSEMBLY_ONLY,
            can_execute_command=False,
            can_spawn_process=False,
            can_render=False,
            can_write_media=False,
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class FFmpegCommandAssemblyReport:
    report_id: str
    job_id: str
    status: str = STATUS_READY_WITH_WARNINGS
    assemblies: list[FFmpegCommandAssembly] = field(default_factory=list)

    total_assemblies: int = 0
    safe_assembly_count: int = 0
    blocked_assembly_count: int = 0

    dry_run_only: bool = True
    assembly_only: bool = True
    preview_only: bool = True
    execution_mode: str = EXECUTION_MODE_ASSEMBLY_ONLY

    ready_for_controlled_execution_stage: bool = False

    can_execute_commands: bool = False
    can_spawn_process: bool = False
    can_render: bool = False
    can_write_media: bool = False
    can_probe_media_files: bool = False

    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["dry_run_only"] = True
        data["assembly_only"] = True
        data["preview_only"] = True
        data["execution_mode"] = EXECUTION_MODE_ASSEMBLY_ONLY
        data["can_execute_commands"] = False
        data["can_spawn_process"] = False
        data["can_render"] = False
        data["can_write_media"] = False
        data["can_probe_media_files"] = False
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FFmpegCommandAssemblyReport":
        assembly_items = data.get("assemblies") or []

        return cls(
            report_id=str(data.get("report_id") or ""),
            job_id=str(data.get("job_id") or ""),
            status=str(data.get("status") or STATUS_READY_WITH_WARNINGS),
            assemblies=[
                FFmpegCommandAssembly.from_dict(item)
                for item in assembly_items
                if isinstance(item, dict)
            ],
            total_assemblies=int(data.get("total_assemblies", 0) or 0),
            safe_assembly_count=int(data.get("safe_assembly_count", 0) or 0),
            blocked_assembly_count=int(data.get("blocked_assembly_count", 0) or 0),
            dry_run_only=True,
            assembly_only=True,
            preview_only=True,
            execution_mode=EXECUTION_MODE_ASSEMBLY_ONLY,
            ready_for_controlled_execution_stage=bool(
                data.get("ready_for_controlled_execution_stage", False)
            ),
            can_execute_commands=False,
            can_spawn_process=False,
            can_render=False,
            can_write_media=False,
            can_probe_media_files=False,
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            recommendation=data.get("recommendation"),
            created_at=str(data.get("created_at") or utc_now_iso()),
            metadata=dict(data.get("metadata") or {}),
        )
