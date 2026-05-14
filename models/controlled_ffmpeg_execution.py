"""Models for the 2B-54 controlled FFmpeg execution gate.

This module is data-only. It does not run FFmpeg and does not touch media.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


STATUS_DRY_RUN_READY = "controlled_ffmpeg_execution_dry_run_ready"
STATUS_SMOKE_READY = "controlled_ffmpeg_execution_smoke_ready"
STATUS_SMOKE_SUCCEEDED = "controlled_ffmpeg_execution_smoke_succeeded"
STATUS_SMOKE_FAILED = "controlled_ffmpeg_execution_smoke_failed"
STATUS_BLOCKED = "controlled_ffmpeg_execution_blocked"
STATUS_FAILED = "controlled_ffmpeg_execution_failed"

MODE_DRY_RUN = "dry_run"
MODE_SMOKE_TEST = "smoke_test"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


@dataclass
class ControlledFFmpegExecutionRequest:
    request_id: str = field(default_factory=lambda: _new_id("controlled_ffmpeg_request"))
    job_id: str | None = None
    requested_mode: str = MODE_DRY_RUN
    allow_real_render: bool = False
    allow_ffmpeg_execution: bool = False
    allow_process_spawn: bool = False
    allow_media_write: bool = False
    smoke_test_only: bool = True
    human_approved: bool = False
    dry_run_only: bool = True
    smoke_output_dir_hint: str | None = None
    smoke_duration_seconds: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_job(cls, job: Any, metadata: dict[str, Any] | None = None) -> "ControlledFFmpegExecutionRequest":
        requested_mode = str(
            getattr(job, "ffmpeg_execution_requested_mode", None)
            or getattr(job, "render_execution_requested_mode", None)
            or MODE_DRY_RUN
        )

        allow_real_render = bool(
            getattr(job, "ffmpeg_execution_allow_real_render", False)
        )
        allow_ffmpeg_execution = bool(
            getattr(job, "ffmpeg_execution_allow_ffmpeg_execution", False)
        )
        allow_process_spawn = bool(
            getattr(job, "ffmpeg_execution_allow_process_spawn", False)
        )
        allow_media_write = bool(
            getattr(job, "ffmpeg_execution_allow_media_write", False)
        )
        human_approved = bool(
            getattr(job, "render_execution_human_approved", False)
        )

        smoke_duration_seconds = float(
            getattr(job, "ffmpeg_execution_smoke_duration_seconds", 1.0) or 1.0
        )

        is_smoke = requested_mode == MODE_SMOKE_TEST
        all_real_flags = all(
            [
                allow_real_render,
                allow_ffmpeg_execution,
                allow_process_spawn,
                allow_media_write,
                human_approved,
            ]
        )

        return cls(
            job_id=str(getattr(job, "job_id", None) or getattr(job, "id", "") or ""),
            requested_mode=requested_mode,
            allow_real_render=allow_real_render,
            allow_ffmpeg_execution=allow_ffmpeg_execution,
            allow_process_spawn=allow_process_spawn,
            allow_media_write=allow_media_write,
            smoke_test_only=True,
            human_approved=human_approved,
            dry_run_only=not (is_smoke and all_real_flags),
            smoke_output_dir_hint=getattr(
                job,
                "ffmpeg_execution_smoke_output_dir_hint",
                None,
            ),
            smoke_duration_seconds=smoke_duration_seconds,
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "job_id": self.job_id,
            "requested_mode": self.requested_mode,
            "allow_real_render": bool(self.allow_real_render),
            "allow_ffmpeg_execution": bool(self.allow_ffmpeg_execution),
            "allow_process_spawn": bool(self.allow_process_spawn),
            "allow_media_write": bool(self.allow_media_write),
            "smoke_test_only": bool(self.smoke_test_only),
            "human_approved": bool(self.human_approved),
            "dry_run_only": bool(self.dry_run_only),
            "smoke_output_dir_hint": self.smoke_output_dir_hint,
            "smoke_duration_seconds": float(self.smoke_duration_seconds),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ControlledFFmpegExecutionRequest":
        data = _as_dict(data)
        return cls(
            request_id=str(data.get("request_id") or _new_id("controlled_ffmpeg_request")),
            job_id=data.get("job_id"),
            requested_mode=str(data.get("requested_mode") or MODE_DRY_RUN),
            allow_real_render=bool(data.get("allow_real_render", False)),
            allow_ffmpeg_execution=bool(data.get("allow_ffmpeg_execution", False)),
            allow_process_spawn=bool(data.get("allow_process_spawn", False)),
            allow_media_write=bool(data.get("allow_media_write", False)),
            smoke_test_only=bool(data.get("smoke_test_only", True)),
            human_approved=bool(data.get("human_approved", False)),
            dry_run_only=bool(data.get("dry_run_only", True)),
            smoke_output_dir_hint=data.get("smoke_output_dir_hint"),
            smoke_duration_seconds=float(data.get("smoke_duration_seconds", 1.0) or 1.0),
            metadata=_as_dict(data.get("metadata")),
        )


@dataclass
class ControlledFFmpegExecutionResult:
    result_id: str = field(default_factory=lambda: _new_id("controlled_ffmpeg_result"))
    mode: str = MODE_DRY_RUN
    attempted: bool = False
    succeeded: bool = False
    return_code: int | None = None
    output_created: bool = False
    output_path: str | None = None
    duration_seconds: float = 0.0
    stdout_preview: str = ""
    stderr_preview: str = ""
    skipped_reason: str | None = None
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "mode": self.mode,
            "attempted": bool(self.attempted),
            "succeeded": bool(self.succeeded),
            "return_code": self.return_code,
            "output_created": bool(self.output_created),
            "output_path": self.output_path,
            "duration_seconds": float(self.duration_seconds),
            "stdout_preview": self.stdout_preview,
            "stderr_preview": self.stderr_preview,
            "skipped_reason": self.skipped_reason,
            "warnings": list(self.warnings),
            "blocking_reasons": list(self.blocking_reasons),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ControlledFFmpegExecutionResult":
        data = _as_dict(data)
        return cls(
            result_id=str(data.get("result_id") or _new_id("controlled_ffmpeg_result")),
            mode=str(data.get("mode") or MODE_DRY_RUN),
            attempted=bool(data.get("attempted", False)),
            succeeded=bool(data.get("succeeded", False)),
            return_code=data.get("return_code"),
            output_created=bool(data.get("output_created", False)),
            output_path=data.get("output_path"),
            duration_seconds=float(data.get("duration_seconds", 0.0) or 0.0),
            stdout_preview=str(data.get("stdout_preview") or ""),
            stderr_preview=str(data.get("stderr_preview") or ""),
            skipped_reason=data.get("skipped_reason"),
            warnings=[str(item) for item in _as_list(data.get("warnings"))],
            blocking_reasons=[
                str(item) for item in _as_list(data.get("blocking_reasons"))
            ],
            metadata=_as_dict(data.get("metadata")),
        )


@dataclass
class ControlledFFmpegExecutionReport:
    report_id: str = field(default_factory=lambda: _new_id("controlled_ffmpeg_report"))
    job_id: str | None = None
    status: str = STATUS_DRY_RUN_READY
    request: ControlledFFmpegExecutionRequest = field(
        default_factory=ControlledFFmpegExecutionRequest
    )
    result: ControlledFFmpegExecutionResult = field(
        default_factory=ControlledFFmpegExecutionResult
    )
    dry_run_only: bool = True
    smoke_test_only: bool = True
    real_execution_requested: bool = False
    real_execution_allowed: bool = False
    real_execution_performed: bool = False
    can_execute_full_render: bool = False
    can_render_timeline: bool = False
    can_process_user_media: bool = False
    can_write_project_output: bool = False
    can_spawn_process: bool = False
    output_created: bool = False
    output_path: str | None = None
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str = "keep_dry_run_until_smoke_test_is_explicitly_requested"
    created_at: str = field(default_factory=_utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "job_id": self.job_id,
            "status": self.status,
            "request": self.request.to_dict(),
            "result": self.result.to_dict(),
            "dry_run_only": bool(self.dry_run_only),
            "smoke_test_only": bool(self.smoke_test_only),
            "real_execution_requested": bool(self.real_execution_requested),
            "real_execution_allowed": bool(self.real_execution_allowed),
            "real_execution_performed": bool(self.real_execution_performed),
            "can_execute_full_render": False,
            "can_render_timeline": False,
            "can_process_user_media": False,
            "can_write_project_output": False,
            "can_spawn_process": bool(self.can_spawn_process),
            "output_created": bool(self.output_created),
            "output_path": self.output_path,
            "warnings": list(self.warnings),
            "blocking_reasons": list(self.blocking_reasons),
            "recommendation": self.recommendation,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ControlledFFmpegExecutionReport":
        data = _as_dict(data)
        return cls(
            report_id=str(data.get("report_id") or _new_id("controlled_ffmpeg_report")),
            job_id=data.get("job_id"),
            status=str(data.get("status") or STATUS_DRY_RUN_READY),
            request=ControlledFFmpegExecutionRequest.from_dict(data.get("request")),
            result=ControlledFFmpegExecutionResult.from_dict(data.get("result")),
            dry_run_only=bool(data.get("dry_run_only", True)),
            smoke_test_only=bool(data.get("smoke_test_only", True)),
            real_execution_requested=bool(data.get("real_execution_requested", False)),
            real_execution_allowed=bool(data.get("real_execution_allowed", False)),
            real_execution_performed=bool(data.get("real_execution_performed", False)),
            can_execute_full_render=False,
            can_render_timeline=False,
            can_process_user_media=False,
            can_write_project_output=False,
            can_spawn_process=bool(data.get("can_spawn_process", False)),
            output_created=bool(data.get("output_created", False)),
            output_path=data.get("output_path"),
            warnings=[str(item) for item in _as_list(data.get("warnings"))],
            blocking_reasons=[
                str(item) for item in _as_list(data.get("blocking_reasons"))
            ],
            recommendation=str(
                data.get("recommendation")
                or "keep_dry_run_until_smoke_test_is_explicitly_requested"
            ),
            created_at=str(data.get("created_at") or _utc_now_iso()),
            metadata=_as_dict(data.get("metadata")),
        )

    def summary(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "dry_run_only": bool(self.dry_run_only),
            "smoke_test_only": bool(self.smoke_test_only),
            "real_execution_allowed": bool(self.real_execution_allowed),
            "real_execution_performed": bool(self.real_execution_performed),
            "output_created": bool(self.output_created),
            "recommendation": self.recommendation,
        }

