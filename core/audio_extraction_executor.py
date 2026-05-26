from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.ffmpeg_helper import apply_ffmpeg_thread_cap, get_ffmpeg_path
from core.resource_monitor import guarded_ffmpeg_execution
from models.audio_extraction_plan import AudioExtractionPlan, AudioExtractionTarget
from models.preprocessing_manifest import PreprocessingManifest


_FFMPEG_TIMEOUT_SECONDS = 600
_STDOUT_TAIL_LIMIT = 4000
_STDERR_TAIL_LIMIT = 4000


@dataclass
class AudioExtractionTargetResult:
    target_id: str
    purpose: str
    output_path: str
    status: str
    command: list[str] = field(default_factory=list)
    returncode: int | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    duration_seconds: float | None = None
    output_size_bytes: int | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "purpose": self.purpose,
            "output_path": self.output_path,
            "status": self.status,
            "command": list(self.command),
            "returncode": self.returncode,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "duration_seconds": self.duration_seconds,
            "output_size_bytes": self.output_size_bytes,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass
class AudioExtractionResult:
    job_id: str
    source_path: str
    audio_dir: str
    status: str
    targets: list[AudioExtractionTargetResult] = field(default_factory=list)
    ready_target_ids: list[str] = field(default_factory=list)
    missing_target_ids: list[str] = field(default_factory=list)
    failed_target_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_path": self.source_path,
            "audio_dir": self.audio_dir,
            "status": self.status,
            "targets": [target.to_dict() for target in self.targets],
            "ready_target_ids": list(self.ready_target_ids),
            "missing_target_ids": list(self.missing_target_ids),
            "failed_target_ids": list(self.failed_target_ids),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }


def _tail(text: str | bytes | None, limit: int) -> str:
    if text is None:
        return ""

    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8", errors="replace")
        except Exception:
            text = ""

    if not text:
        return ""

    if len(text) <= limit:
        return text

    return text[-limit:]


def _build_command(ffmpeg_path: str, target: AudioExtractionTarget, source_path: str) -> list[str]:
    command: list[str] = [
        ffmpeg_path,
        "-hide_banner",
        "-nostdin",
        "-loglevel", "error",
        "-y",
        "-i", source_path,
        "-vn",
    ]

    if target.source_stream_index is not None:
        command.extend(["-map", f"0:{target.source_stream_index}"])

    if target.channels is not None:
        command.extend(["-ac", str(target.channels)])

    if target.sample_rate is not None:
        command.extend(["-ar", str(target.sample_rate)])

    command.extend(["-c:a", "pcm_s16le"])
    command.append(target.output_path)
    return command


def _existing_output_is_reusable(output_path: str) -> bool:
    path = Path(output_path)
    if not path.exists():
        return False

    try:
        return path.stat().st_size > 0
    except OSError:
        return False


def _resolve_ffmpeg_or_none() -> tuple[str | None, str | None]:
    try:
        return get_ffmpeg_path(), None
    except FileNotFoundError as exc:
        return None, str(exc)


def _execute_target(
    target: AudioExtractionTarget,
    source_path: str,
    ffmpeg_path: str | None,
    ffmpeg_error: str | None,
    overwrite_existing: bool,
) -> AudioExtractionTargetResult:
    output_path = target.output_path or ""
    result = AudioExtractionTargetResult(
        target_id=target.target_id,
        purpose=target.purpose,
        output_path=output_path,
        status="planned",
    )

    if not target.enabled:
        result.status = "skipped_disabled"
        return result

    if not source_path or not Path(source_path).exists():
        result.status = "blocked_missing_source"
        result.errors.append("source_missing")
        return result

    if not output_path:
        result.status = "failed"
        result.errors.append("output_path_missing")
        return result

    if not overwrite_existing and _existing_output_is_reusable(output_path):
        result.status = "skipped_existing_reusable"
        try:
            result.output_size_bytes = Path(output_path).stat().st_size
        except OSError:
            result.output_size_bytes = None
        return result

    if ffmpeg_path is None:
        result.status = "failed"
        result.errors.append("ffmpeg_unavailable")
        if ffmpeg_error:
            result.stderr_tail = _tail(ffmpeg_error, _STDERR_TAIL_LIMIT)
        return result

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    command = apply_ffmpeg_thread_cap(_build_command(ffmpeg_path, target, source_path))
    result.command = list(command)

    try:
        with guarded_ffmpeg_execution(command):
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=_FFMPEG_TIMEOUT_SECONDS,
                check=False,
            )
    except subprocess.TimeoutExpired as exc:
        result.status = "failed"
        result.errors.append("ffmpeg_timeout")
        result.stderr_tail = _tail(getattr(exc, "stderr", None), _STDERR_TAIL_LIMIT)
        return result
    except OSError as exc:
        result.status = "failed"
        result.errors.append("ffmpeg_invocation_error")
        result.stderr_tail = _tail(str(exc), _STDERR_TAIL_LIMIT)
        return result

    result.returncode = int(completed.returncode)
    result.stdout_tail = _tail(completed.stdout, _STDOUT_TAIL_LIMIT)
    result.stderr_tail = _tail(completed.stderr, _STDERR_TAIL_LIMIT)

    output = Path(output_path)
    if not output.exists():
        result.status = "failed"
        result.errors.append("output_not_created")
        return result

    try:
        size_bytes = output.stat().st_size
    except OSError:
        size_bytes = 0

    result.output_size_bytes = size_bytes

    if completed.returncode != 0:
        result.status = "failed"
        result.errors.append("ffmpeg_returned_nonzero")
        return result

    if size_bytes <= 0:
        result.status = "failed"
        result.errors.append("output_empty")
        return result

    result.status = "ok"
    return result


def _aggregate_result(
    job_id: str,
    source_path: str,
    audio_dir: str,
    targets: list[AudioExtractionTargetResult],
    metadata: dict[str, Any] | None,
) -> AudioExtractionResult:
    ready: list[str] = []
    missing: list[str] = []
    failed: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    for target in targets:
        status = target.status

        if status in {"ok", "skipped_existing_reusable"}:
            ready.append(target.target_id)
        elif status == "skipped_disabled":
            continue
        elif status == "blocked_missing_source":
            missing.append(target.target_id)
            for err in target.errors:
                if err not in errors:
                    errors.append(err)
        elif status == "failed":
            failed.append(target.target_id)
            for err in target.errors:
                if err not in errors:
                    errors.append(err)
        else:
            missing.append(target.target_id)

    required_ready = {"analysis_audio", "speech_audio"}
    ready_set = set(ready)
    missing_required = sorted(required_ready - ready_set)

    if missing_required:
        for target_id in missing_required:
            warning = f"required_audio_target_not_ready:{target_id}"
            if warning not in warnings:
                warnings.append(warning)

    if failed:
        status = "failed"
    elif missing_required:
        status = "incomplete"
    elif missing:
        status = "completed_with_warnings"
    else:
        status = "ok"

    return AudioExtractionResult(
        job_id=job_id,
        source_path=source_path,
        audio_dir=audio_dir,
        status=status,
        targets=targets,
        ready_target_ids=ready,
        missing_target_ids=missing,
        failed_target_ids=failed,
        warnings=warnings,
        errors=errors,
        metadata=dict(metadata or {}),
    )


def execute_audio_extraction_plan(
    plan: AudioExtractionPlan,
    overwrite_existing: bool = False,
    metadata: dict[str, Any] | None = None,
) -> AudioExtractionResult:
    ffmpeg_path, ffmpeg_error = _resolve_ffmpeg_or_none()

    target_results: list[AudioExtractionTargetResult] = []

    for target in plan.targets:
        target_results.append(
            _execute_target(
                target=target,
                source_path=plan.source_path,
                ffmpeg_path=ffmpeg_path,
                ffmpeg_error=ffmpeg_error,
                overwrite_existing=overwrite_existing,
            )
        )

    aggregated = _aggregate_result(
        job_id=plan.job_id,
        source_path=plan.source_path,
        audio_dir=plan.audio_dir,
        targets=target_results,
        metadata=metadata,
    )

    if ffmpeg_path is None:
        aggregated.warnings.append("ffmpeg_unavailable")
        if ffmpeg_error and ffmpeg_error not in aggregated.errors:
            aggregated.errors.append(ffmpeg_error)

    return aggregated


def apply_audio_extraction_result_to_manifest(
    manifest: PreprocessingManifest,
    result: AudioExtractionResult,
) -> PreprocessingManifest:
    result_dict = result.to_dict()
    manifest.audio_extraction_result = result_dict
    manifest.audio_extraction_status = result.status
    manifest.ready_audio_targets = list(result.ready_target_ids)
    manifest.missing_audio_targets = list(result.missing_target_ids)
    manifest.failed_audio_targets = list(result.failed_target_ids)
    return manifest


def apply_audio_extraction_result_to_job(
    job: Any,
    result: AudioExtractionResult,
) -> Any:
    result_dict = result.to_dict()
    job.audio_extraction_result = result_dict
    job.audio_extraction_status = result.status
    job.ready_audio_targets = list(result.ready_target_ids)
    job.missing_audio_targets = list(result.missing_target_ids)
    job.failed_audio_targets = list(result.failed_target_ids)

    if hasattr(job, "touch"):
        job.touch()

    return job
