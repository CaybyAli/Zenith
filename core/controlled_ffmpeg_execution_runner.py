"""Runner for the 2B-54 controlled FFmpeg execution gate."""

from __future__ import annotations

from typing import Any

from core.controlled_ffmpeg_execution import (
    BASE_METADATA,
    apply_controlled_ffmpeg_execution_report_to_job,
    build_controlled_ffmpeg_execution_report,
    execute_controlled_ffmpeg_smoke_test,
)
from models.controlled_ffmpeg_execution import (
    MODE_SMOKE_TEST,
    STATUS_SMOKE_READY,
    ControlledFFmpegExecutionReport,
)


RUNNER_METADATA = {
    **BASE_METADATA,
    "runner": "controlled_ffmpeg_execution_runner",
    "writes_job_fields": True,
    "does_not_unlock_full_render": True,
}


def _merge_metadata(metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = dict(RUNNER_METADATA)
    if metadata:
        merged.update(dict(metadata))
    return merged


def run_controlled_ffmpeg_execution_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
    execute_smoke_if_allowed: bool = True,
) -> ControlledFFmpegExecutionReport:
    """Run the controlled execution gate for one job.

    Default job settings remain dry-run and do not spawn a process.
    A real subprocess call can only happen when:
    - requested mode is smoke_test
    - all allow flags are true
    - upstream gates are ready
    - execute_smoke_if_allowed is true
    """

    safe_metadata = _merge_metadata(metadata)

    preview_report = build_controlled_ffmpeg_execution_report(
        job,
        metadata=safe_metadata,
    )

    should_attempt_smoke = (
        execute_smoke_if_allowed
        and preview_report.status == STATUS_SMOKE_READY
        and preview_report.request.requested_mode == MODE_SMOKE_TEST
        and preview_report.real_execution_allowed
    )

    if should_attempt_smoke:
        report = execute_controlled_ffmpeg_smoke_test(
            job,
            metadata=safe_metadata,
        )
    else:
        report = preview_report

    apply_controlled_ffmpeg_execution_report_to_job(job, report)
    return report


def run_controlled_ffmpeg_execution_dry_run_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> ControlledFFmpegExecutionReport:
    """Run the gate without allowing even the smoke subprocess."""

    report = build_controlled_ffmpeg_execution_report(
        job,
        metadata=_merge_metadata(metadata),
    )
    apply_controlled_ffmpeg_execution_report_to_job(job, report)
    return report

