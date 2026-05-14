from __future__ import annotations

from typing import Any

from core.ffmpeg_command_assembly import build_ffmpeg_command_assembly_report
from models.ffmpeg_command_assembly import FFmpegCommandAssemblyReport


FFMPEG_COMMAND_SAFE_FALSE_FIELDS = {
    "ffmpeg_command_can_execute_commands": False,
    "ffmpeg_command_can_spawn_process": False,
    "ffmpeg_command_can_render": False,
    "ffmpeg_command_can_write_media": False,
    "ffmpeg_command_can_probe_media_files": False,
}


def _set_job_attr(job: Any, name: str, value: Any) -> None:
    if isinstance(job, dict):
        job[name] = value
        return
    setattr(job, name, value)


def _assemblies_to_dicts(report: FFmpegCommandAssemblyReport) -> list[dict[str, Any]]:
    return [assembly.to_dict() for assembly in report.assemblies]


def apply_ffmpeg_command_assembly_report_to_job(
    job: Any,
    report: FFmpegCommandAssemblyReport,
) -> Any:
    report_dict = report.to_dict()
    assemblies = _assemblies_to_dicts(report)

    _set_job_attr(job, "ffmpeg_command_assembly_report", report_dict)
    _set_job_attr(job, "ffmpeg_command_assembly_status", report.status)
    _set_job_attr(job, "ffmpeg_command_assemblies", assemblies)

    _set_job_attr(job, "ffmpeg_command_total_assemblies", report.total_assemblies)
    _set_job_attr(
        job,
        "ffmpeg_command_safe_assembly_count",
        report.safe_assembly_count,
    )
    _set_job_attr(
        job,
        "ffmpeg_command_blocked_assembly_count",
        report.blocked_assembly_count,
    )

    _set_job_attr(job, "ffmpeg_command_dry_run_only", True)
    _set_job_attr(job, "ffmpeg_command_assembly_only", True)
    _set_job_attr(job, "ffmpeg_command_preview_only", True)

    _set_job_attr(
        job,
        "ffmpeg_command_ready_for_controlled_execution_stage",
        report.ready_for_controlled_execution_stage,
    )

    for key, value in FFMPEG_COMMAND_SAFE_FALSE_FIELDS.items():
        _set_job_attr(job, key, value)

    _set_job_attr(
        job,
        "ffmpeg_command_blocking_reasons",
        list(report.blocking_reasons),
    )
    _set_job_attr(job, "ffmpeg_command_warnings", list(report.warnings))
    _set_job_attr(job, "ffmpeg_command_recommendation", report.recommendation)

    return job


def run_ffmpeg_command_assembly_for_job(job: Any) -> FFmpegCommandAssemblyReport:
    report = build_ffmpeg_command_assembly_report(job)
    apply_ffmpeg_command_assembly_report_to_job(job, report)
    return report
