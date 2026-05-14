from __future__ import annotations

from typing import Any

from core.ffmpeg_capability_resolver import ProbeRunner, resolve_ffmpeg_capabilities
from models.ffmpeg_capability_resolver import FFmpegCapabilityResolverReport


def _set_job_attr(job: Any, name: str, value: Any) -> None:
    if isinstance(job, dict):
        job[name] = value
        return
    setattr(job, name, value)


def _capabilities_to_dicts(report: FFmpegCapabilityResolverReport) -> list[dict[str, Any]]:
    return [capability.to_dict() for capability in report.capabilities]


def apply_ffmpeg_capability_report_to_job(
    job: Any,
    report: FFmpegCapabilityResolverReport,
) -> Any:
    report_dict = report.to_dict()
    capabilities = _capabilities_to_dicts(report)

    _set_job_attr(job, "ffmpeg_capability_resolver_report", report_dict)
    _set_job_attr(job, "ffmpeg_capability_status", report.status)

    _set_job_attr(
        job,
        "ffmpeg_path_hint",
        report.ffmpeg_path.path_hint if report.ffmpeg_path else None,
    )
    _set_job_attr(
        job,
        "ffprobe_path_hint",
        report.ffprobe_path.path_hint if report.ffprobe_path else None,
    )
    _set_job_attr(job, "ffmpeg_resolver_allow_tool_probe", report.allow_tool_probe)

    _set_job_attr(job, "ffmpeg_tool_probe_attempted", report.tool_probe_attempted)
    _set_job_attr(job, "ffmpeg_tool_probe_succeeded", report.tool_probe_succeeded)
    _set_job_attr(job, "ffmpeg_version", report.ffmpeg_version)
    _set_job_attr(job, "ffprobe_version", report.ffprobe_version)
    _set_job_attr(job, "ffmpeg_capabilities", capabilities)

    _set_job_attr(job, "ffmpeg_has_h264", report.has_h264)
    _set_job_attr(job, "ffmpeg_has_aac", report.has_aac)
    _set_job_attr(job, "ffmpeg_has_nvenc", report.has_nvenc)
    _set_job_attr(job, "ffmpeg_has_scale_filter", report.has_scale_filter)
    _set_job_attr(job, "ffmpeg_has_concat_support", report.has_concat_support)
    _set_job_attr(job, "ffmpeg_has_loudnorm_filter", report.has_loudnorm_filter)

    _set_job_attr(
        job,
        "ffmpeg_can_prepare_real_render_tools",
        report.can_prepare_real_render_tools,
    )

    _set_job_attr(job, "ffmpeg_can_render", False)
    _set_job_attr(job, "ffmpeg_can_process_media", False)
    _set_job_attr(job, "ffmpeg_can_write_media", False)
    _set_job_attr(job, "ffmpeg_can_probe_media_files", False)

    _set_job_attr(job, "ffmpeg_blocking_reasons", list(report.blocking_reasons))
    _set_job_attr(job, "ffmpeg_warnings", list(report.warnings))
    _set_job_attr(job, "ffmpeg_recommendation", report.recommendation)

    return job


def run_ffmpeg_capability_resolver(
    job: Any,
    probe_runner: ProbeRunner | None = None,
) -> FFmpegCapabilityResolverReport:
    report = resolve_ffmpeg_capabilities(job, probe_runner=probe_runner)
    apply_ffmpeg_capability_report_to_job(job, report)
    return report
