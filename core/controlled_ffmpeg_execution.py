"""Controlled FFmpeg execution gate for 2B-54.

This module is intentionally narrow:
- default is dry-run
- full timeline rendering is never allowed here
- user media input is never allowed here
- project output is never allowed here
- only an internal lavfi smoke command may call subprocess.run
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from models.controlled_ffmpeg_execution import (
    MODE_DRY_RUN,
    MODE_SMOKE_TEST,
    STATUS_BLOCKED,
    STATUS_DRY_RUN_READY,
    STATUS_FAILED,
    STATUS_SMOKE_FAILED,
    STATUS_SMOKE_READY,
    STATUS_SMOKE_SUCCEEDED,
    ControlledFFmpegExecutionReport,
    ControlledFFmpegExecutionRequest,
    ControlledFFmpegExecutionResult,
)


ALLOWED_READY_STATUSES = {"ready", "ready_with_warnings"}
ALLOWED_PERMISSION_STATUSES = {
    "render_execution_permission_ready",
    "render_execution_permission_ready_with_warnings",
    "ready",
    "ready_with_warnings",
}
ALLOWED_CAPABILITY_STATUSES = {
    "ffmpeg_capability_ready",
    "ffmpeg_capability_ready_with_warnings",
    "ready",
    "ready_with_warnings",
}
ALLOWED_COMMAND_STATUSES = {
    "ffmpeg_command_assembly_ready",
    "ffmpeg_command_assembly_ready_with_warnings",
    "ready",
    "ready_with_warnings",
}

MAX_SMOKE_DURATION_SECONDS = 2.0
DEFAULT_SMOKE_TIMEOUT_SECONDS = 15

BASE_METADATA = {
    "phase": "2B-54",
    "block": "block8_render_export",
    "controlled_ffmpeg_execution_gate": True,
    "default_dry_run": True,
    "smoke_test_only_when_explicitly_allowed": True,
    "no_full_render_in_2b_54": True,
    "no_user_media_input_in_2b_54": True,
    "no_project_output_in_2b_54": True,
    "no_timeline_apply_in_2b_54": True,
}


def _job_attr(job: Any, name: str, default: Any = None) -> Any:
    if job is None:
        return default
    return getattr(job, name, default)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return [str(value)]


def _status_ready(status: Any, allowed: set[str]) -> bool:
    if status is None:
        return False
    status_text = str(status)
    return status_text in allowed or status_text in ALLOWED_READY_STATUSES


def _preview(value: Any, limit: int = 1200) -> str:
    text = "" if value is None else str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "...<truncated>"


def _merge_metadata(metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = dict(BASE_METADATA)
    if metadata:
        merged.update(dict(metadata))
    return merged


def _safe_smoke_output_dir(path_hint: str | None) -> Path:
    if path_hint:
        candidate = Path(path_hint).expanduser().resolve()
    else:
        candidate = Path(tempfile.gettempdir()).joinpath("zenith_2b54_ffmpeg_smoke").resolve()

    text = str(candidate).lower()
    safe_markers = ["temp", "tmp", "smoke", "pytest"]
    if not any(marker in text for marker in safe_markers):
        raise ValueError("smoke_output_dir_must_be_temp_or_smoke_path")

    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def _build_internal_smoke_command(
    ffmpeg_path: str,
    output_path: Path,
    duration_seconds: float,
) -> list[str]:
    safe_duration = max(0.1, min(float(duration_seconds), MAX_SMOKE_DURATION_SECONDS))
    duration_text = f"{safe_duration:.3f}".rstrip("0").rstrip(".")

    return [
        ffmpeg_path,
        "-hide_banner",
        "-nostdin",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=size=320x180:rate=10:duration={duration_text}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=1000:duration={duration_text}",
        "-shortest",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        str(output_path),
    ]


def _collect_prerequisite_blocks(job: Any) -> list[str]:
    blocking: list[str] = []

    permission_status = _job_attr(job, "render_execution_permission_status")
    if not _status_ready(permission_status, ALLOWED_PERMISSION_STATUSES):
        blocking.append("render_execution_permission_not_ready")

    if not bool(_job_attr(job, "render_execution_human_approved", False)):
        blocking.append("render_execution_human_approval_missing")

    if not bool(_job_attr(job, "render_execution_ready_for_real_render_stage", False)):
        blocking.append("render_execution_not_ready_for_real_render_stage")

    if not bool(_job_attr(job, "render_execution_can_prepare_real_render_execution", False)):
        blocking.append("render_execution_cannot_prepare_real_render_execution")

    capability_status = _job_attr(job, "ffmpeg_capability_status")
    if not _status_ready(capability_status, ALLOWED_CAPABILITY_STATUSES):
        blocking.append("ffmpeg_capability_not_ready")

    if not bool(_job_attr(job, "ffmpeg_can_prepare_real_render_tools", False)):
        blocking.append("ffmpeg_cannot_prepare_real_render_tools")

    if bool(_job_attr(job, "ffmpeg_can_render", False)):
        blocking.append("ffmpeg_render_permission_must_remain_false_before_2b54")

    if bool(_job_attr(job, "ffmpeg_can_process_media", False)):
        blocking.append("ffmpeg_process_media_permission_must_remain_false_before_2b54")

    if bool(_job_attr(job, "ffmpeg_can_write_media", False)):
        blocking.append("ffmpeg_write_media_permission_must_remain_false_before_2b54")

    command_status = _job_attr(job, "ffmpeg_command_assembly_status")
    if not _status_ready(command_status, ALLOWED_COMMAND_STATUSES):
        blocking.append("ffmpeg_command_assembly_not_ready")

    if not bool(_job_attr(job, "ffmpeg_command_ready_for_controlled_execution_stage", False)):
        blocking.append("ffmpeg_command_not_ready_for_controlled_execution_stage")

    if bool(_job_attr(job, "ffmpeg_command_can_execute_commands", False)):
        blocking.append("ffmpeg_command_execution_permission_must_remain_false_before_2b54")

    if bool(_job_attr(job, "ffmpeg_command_can_spawn_process", False)):
        blocking.append("ffmpeg_command_spawn_permission_must_remain_false_before_2b54")

    if bool(_job_attr(job, "ffmpeg_command_can_render", False)):
        blocking.append("ffmpeg_command_render_permission_must_remain_false_before_2b54")

    if bool(_job_attr(job, "ffmpeg_command_can_write_media", False)):
        blocking.append("ffmpeg_command_write_media_permission_must_remain_false_before_2b54")

    blocking.extend(_as_list(_job_attr(job, "render_execution_blocking_reasons", [])))
    blocking.extend(_as_list(_job_attr(job, "ffmpeg_blocking_reasons", [])))
    blocking.extend(_as_list(_job_attr(job, "ffmpeg_command_blocking_reasons", [])))

    return sorted(set(reason for reason in blocking if reason))


def _build_report(
    job: Any,
    request: ControlledFFmpegExecutionRequest,
    result: ControlledFFmpegExecutionResult,
    status: str,
    warnings: list[str] | None = None,
    blocking_reasons: list[str] | None = None,
    recommendation: str | None = None,
    metadata: dict[str, Any] | None = None,
    real_execution_allowed: bool = False,
    can_spawn_process: bool = False,
) -> ControlledFFmpegExecutionReport:
    output_created = bool(result.output_created)
    output_path = result.output_path

    return ControlledFFmpegExecutionReport(
        job_id=request.job_id,
        status=status,
        request=request,
        result=result,
        dry_run_only=bool(request.dry_run_only),
        smoke_test_only=True,
        real_execution_requested=request.requested_mode == MODE_SMOKE_TEST,
        real_execution_allowed=bool(real_execution_allowed),
        real_execution_performed=bool(result.attempted),
        can_execute_full_render=False,
        can_render_timeline=False,
        can_process_user_media=False,
        can_write_project_output=False,
        can_spawn_process=bool(can_spawn_process),
        output_created=output_created,
        output_path=output_path,
        warnings=list(warnings or []),
        blocking_reasons=list(blocking_reasons or []),
        recommendation=recommendation
        or "review_controlled_ffmpeg_execution_before_any_future_render_stage",
        metadata=_merge_metadata(metadata),
    )


def build_controlled_ffmpeg_execution_report(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> ControlledFFmpegExecutionReport:
    request = ControlledFFmpegExecutionRequest.from_job(
        job,
        metadata=_merge_metadata(metadata),
    )

    prerequisite_blocks = _collect_prerequisite_blocks(job)
    if prerequisite_blocks:
        result = ControlledFFmpegExecutionResult(
            mode=request.requested_mode,
            attempted=False,
            succeeded=False,
            output_created=False,
            skipped_reason="controlled_ffmpeg_execution_prerequisites_blocked",
            blocking_reasons=prerequisite_blocks,
        )
        return _build_report(
            job=job,
            request=request,
            result=result,
            status=STATUS_BLOCKED,
            blocking_reasons=prerequisite_blocks,
            recommendation="fix_upstream_render_permission_capability_and_command_gates",
            metadata=metadata,
            real_execution_allowed=False,
            can_spawn_process=False,
        )

    if request.requested_mode != MODE_SMOKE_TEST:
        result = ControlledFFmpegExecutionResult(
            mode=MODE_DRY_RUN,
            attempted=False,
            succeeded=True,
            output_created=False,
            skipped_reason="dry_run_only_no_real_execution_requested",
        )
        return _build_report(
            job=job,
            request=request,
            result=result,
            status=STATUS_DRY_RUN_READY,
            warnings=["controlled_ffmpeg_execution_defaulted_to_dry_run"],
            recommendation="keep_dry_run_or_request_explicit_smoke_test",
            metadata=metadata,
            real_execution_allowed=False,
            can_spawn_process=False,
        )

    missing_flags = []
    if not request.allow_real_render:
        missing_flags.append("allow_real_render_missing")
    if not request.allow_ffmpeg_execution:
        missing_flags.append("allow_ffmpeg_execution_missing")
    if not request.allow_process_spawn:
        missing_flags.append("allow_process_spawn_missing")
    if not request.allow_media_write:
        missing_flags.append("allow_media_write_missing")
    if not request.human_approved:
        missing_flags.append("human_approved_missing")
    if request.smoke_duration_seconds > MAX_SMOKE_DURATION_SECONDS:
        missing_flags.append("smoke_duration_too_long")

    if missing_flags:
        result = ControlledFFmpegExecutionResult(
            mode=MODE_SMOKE_TEST,
            attempted=False,
            succeeded=False,
            output_created=False,
            skipped_reason="smoke_test_request_missing_required_flags",
            blocking_reasons=missing_flags,
        )
        return _build_report(
            job=job,
            request=request,
            result=result,
            status=STATUS_BLOCKED,
            blocking_reasons=missing_flags,
            recommendation="set_all_smoke_test_flags_before_controlled_execution",
            metadata=metadata,
            real_execution_allowed=False,
            can_spawn_process=False,
        )

    result = ControlledFFmpegExecutionResult(
        mode=MODE_SMOKE_TEST,
        attempted=False,
        succeeded=True,
        output_created=False,
        skipped_reason="smoke_test_ready_but_not_executed_by_report_builder",
    )
    request.dry_run_only = False
    return _build_report(
        job=job,
        request=request,
        result=result,
        status=STATUS_SMOKE_READY,
        warnings=["use_execute_controlled_ffmpeg_smoke_test_for_real_smoke_run"],
        recommendation="ready_for_optional_controlled_smoke_test_only",
        metadata=metadata,
        real_execution_allowed=True,
        can_spawn_process=True,
    )


def execute_controlled_ffmpeg_smoke_test(
    job: Any,
    metadata: dict[str, Any] | None = None,
    timeout_seconds: int = DEFAULT_SMOKE_TIMEOUT_SECONDS,
) -> ControlledFFmpegExecutionReport:
    ready_report = build_controlled_ffmpeg_execution_report(job, metadata=metadata)
    request = ready_report.request

    if ready_report.status != STATUS_SMOKE_READY or not ready_report.real_execution_allowed:
        return ready_report

    ffmpeg_path = str(_job_attr(job, "ffmpeg_path_hint", "") or "").strip()
    if not ffmpeg_path:
        result = ControlledFFmpegExecutionResult(
            mode=MODE_SMOKE_TEST,
            attempted=False,
            succeeded=False,
            output_created=False,
            skipped_reason="ffmpeg_path_missing",
            blocking_reasons=["ffmpeg_path_missing"],
        )
        return _build_report(
            job=job,
            request=request,
            result=result,
            status=STATUS_BLOCKED,
            blocking_reasons=["ffmpeg_path_missing"],
            recommendation="provide_safe_ffmpeg_path_before_smoke_test",
            metadata=metadata,
            real_execution_allowed=False,
            can_spawn_process=False,
        )

    try:
        output_dir = _safe_smoke_output_dir(request.smoke_output_dir_hint)
    except ValueError as exc:
        reason = str(exc)
        result = ControlledFFmpegExecutionResult(
            mode=MODE_SMOKE_TEST,
            attempted=False,
            succeeded=False,
            output_created=False,
            skipped_reason=reason,
            blocking_reasons=[reason],
        )
        return _build_report(
            job=job,
            request=request,
            result=result,
            status=STATUS_BLOCKED,
            blocking_reasons=[reason],
            recommendation="use_temp_or_smoke_output_directory_only",
            metadata=metadata,
            real_execution_allowed=False,
            can_spawn_process=False,
        )

    output_path = output_dir / f"zenith_2b54_ffmpeg_smoke_{int(time.time() * 1000)}.mp4"
    command = _build_internal_smoke_command(
        ffmpeg_path=ffmpeg_path,
        output_path=output_path,
        duration_seconds=request.smoke_duration_seconds,
    )

    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        elapsed = time.perf_counter() - started
        output_created = output_path.exists() and output_path.stat().st_size > 0
        succeeded = completed.returncode == 0 and output_created
        result = ControlledFFmpegExecutionResult(
            mode=MODE_SMOKE_TEST,
            attempted=True,
            succeeded=succeeded,
            return_code=int(completed.returncode),
            output_created=output_created,
            output_path=str(output_path) if output_created else str(output_path),
            duration_seconds=round(float(elapsed), 6),
            stdout_preview=_preview(completed.stdout),
            stderr_preview=_preview(completed.stderr),
            metadata={
                "command_kind": "internal_lavfi_smoke_command",
                "shell": False,
                "timeout_seconds": int(timeout_seconds),
                "uses_lavfi_testsrc": True,
                "uses_lavfi_sine": True,
                "no_user_media_input": True,
                "no_project_output": True,
            },
        )
        status = STATUS_SMOKE_SUCCEEDED if succeeded else STATUS_SMOKE_FAILED
        return _build_report(
            job=job,
            request=request,
            result=result,
            status=status,
            warnings=[] if succeeded else ["controlled_ffmpeg_smoke_test_failed"],
            blocking_reasons=[] if succeeded else ["controlled_ffmpeg_smoke_test_failed"],
            recommendation="smoke_test_succeeded_no_full_render_unlocked"
            if succeeded
            else "inspect_ffmpeg_smoke_test_failure",
            metadata=metadata,
            real_execution_allowed=True,
            can_spawn_process=True,
        )
    except Exception as exc:  # pragma: no cover - defensive safety report
        elapsed = time.perf_counter() - started
        reason = f"controlled_ffmpeg_execution_exception:{type(exc).__name__}"
        result = ControlledFFmpegExecutionResult(
            mode=MODE_SMOKE_TEST,
            attempted=True,
            succeeded=False,
            output_created=False,
            output_path=str(output_path),
            duration_seconds=round(float(elapsed), 6),
            stderr_preview=_preview(str(exc)),
            skipped_reason=reason,
            blocking_reasons=[reason],
        )
        return _build_report(
            job=job,
            request=request,
            result=result,
            status=STATUS_FAILED,
            warnings=[reason],
            blocking_reasons=[reason],
            recommendation="inspect_controlled_ffmpeg_execution_exception",
            metadata=metadata,
            real_execution_allowed=True,
            can_spawn_process=True,
        )


def apply_controlled_ffmpeg_execution_report_to_job(
    job: Any,
    report: ControlledFFmpegExecutionReport,
) -> Any:
    report_dict = report.to_dict()

    job.controlled_ffmpeg_execution_report = report_dict
    job.controlled_ffmpeg_execution_status = report.status
    job.controlled_ffmpeg_execution_request = report.request.to_dict()
    job.controlled_ffmpeg_execution_result = report.result.to_dict()
    job.controlled_ffmpeg_dry_run_only = bool(report.dry_run_only)
    job.controlled_ffmpeg_smoke_test_only = True
    job.controlled_ffmpeg_real_execution_requested = bool(
        report.real_execution_requested
    )
    job.controlled_ffmpeg_real_execution_allowed = bool(report.real_execution_allowed)
    job.controlled_ffmpeg_real_execution_performed = bool(
        report.real_execution_performed
    )
    job.controlled_ffmpeg_can_execute_full_render = False
    job.controlled_ffmpeg_can_render_timeline = False
    job.controlled_ffmpeg_can_process_user_media = False
    job.controlled_ffmpeg_can_write_project_output = False
    job.controlled_ffmpeg_can_spawn_process = bool(report.can_spawn_process)
    job.controlled_ffmpeg_output_created = bool(report.output_created)
    job.controlled_ffmpeg_output_path = report.output_path
    job.controlled_ffmpeg_blocking_reasons = list(report.blocking_reasons)
    job.controlled_ffmpeg_warnings = list(report.warnings)
    job.controlled_ffmpeg_recommendation = report.recommendation

    if hasattr(job, "touch"):
        job.touch()

    return job

