from __future__ import annotations

import re
import subprocess
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Callable

from models.ffmpeg_capability_resolver import (
    DEFAULT_FFMPEG_PATH_HINT,
    DEFAULT_FFPROBE_PATH_HINT,
    FFmpegCapability,
    FFmpegCapabilityResolverReport,
    FFmpegToolPath,
    STATUS_BLOCKED,
    STATUS_FAILED,
    STATUS_READY,
    STATUS_READY_WITH_WARNINGS,
)

ProbeRunner = Callable[[list[str]], tuple[bool, str, str]]


SAFE_METADATA = {
    "phase": "2B-52",
    "block": "block8_render_export",
    "ffmpeg_capability_resolver_only": True,
    "tool_probe_only": True,
    "no_render_in_2b_52": True,
    "no_media_input_in_2b_52": True,
    "no_media_output_in_2b_52": True,
    "no_timeline_apply_in_2b_52": True,
    "controlled_tool_probe_only": True,
}

_ALLOWED_PROBES_BY_TOOL = {
    "ffmpeg": [
        ["-version"],
        ["-encoders"],
        ["-decoders"],
        ["-filters"],
        ["-hwaccels"],
    ],
    "ffprobe": [
        ["-version"],
    ],
}

_STANDARD_HINTS = {
    DEFAULT_FFMPEG_PATH_HINT.lower(),
    DEFAULT_FFPROBE_PATH_HINT.lower(),
}

_SHELL_PATH_MARKERS = ["&", "|", ";", ">", "<"]


def _job_attr(job: Any, name: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(name, default)
    return getattr(job, name, default)


def _string_or_default(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return text or default


def _path_basename(path_hint: str) -> str:
    normalized = path_hint.replace("/", "\\")
    return normalized.rsplit("\\", 1)[-1].strip().lower()


def _looks_absolute(path_hint: str) -> bool:
    return PureWindowsPath(path_hint).is_absolute() or PurePosixPath(path_hint).is_absolute()


def _has_path_traversal(path_hint: str) -> bool:
    parts = re.split(r"[\\/]+", path_hint)
    return any(part.strip() == ".." for part in parts)


def _looks_like_url(path_hint: str) -> bool:
    lowered = path_hint.lower()
    return lowered.startswith(("http://", "https://", "ftp://")) or "://" in lowered


def _looks_like_path_with_options(path_hint: str) -> bool:
    return bool(re.search(r"\s-{1,2}[A-Za-z0-9]", path_hint))


def validate_tool_path(tool_name: str, path_hint: str | None) -> FFmpegToolPath:
    clean_tool_name = str(tool_name or "").strip().lower()
    clean_path = str(path_hint or "").strip()

    warnings: list[str] = []
    blocking_reasons: list[str] = []

    allowed_names = {
        "ffmpeg": {"ffmpeg.exe", "ffmpeg"},
        "ffprobe": {"ffprobe.exe", "ffprobe"},
    }

    if not clean_path:
        blocking_reasons.append(f"{clean_tool_name}_path_empty")

    if clean_path and _has_path_traversal(clean_path):
        blocking_reasons.append(f"{clean_tool_name}_path_traversal_blocked")

    if clean_path and _looks_like_url(clean_path):
        blocking_reasons.append(f"{clean_tool_name}_path_url_blocked")

    if clean_path and any(marker in clean_path for marker in _SHELL_PATH_MARKERS):
        blocking_reasons.append(f"{clean_tool_name}_path_shell_marker_blocked")

    if clean_path and _looks_like_path_with_options(clean_path):
        blocking_reasons.append(f"{clean_tool_name}_path_looks_like_tool_invocation")

    basename = _path_basename(clean_path) if clean_path else ""
    if clean_path and basename not in allowed_names.get(clean_tool_name, set()):
        blocking_reasons.append(f"{clean_tool_name}_path_wrong_tool_name")

    is_absolute = _looks_absolute(clean_path) if clean_path else False
    if clean_path and not is_absolute:
        warnings.append(f"{clean_tool_name}_path_relative_hint")

    if clean_path and clean_path.lower() not in _STANDARD_HINTS:
        warnings.append(f"{clean_tool_name}_path_non_standard_hint")

    status = "safe" if not blocking_reasons else "unsafe"

    return FFmpegToolPath(
        tool_name=clean_tool_name,
        path_hint=clean_path or None,
        path_safety_status=status,
        exists_hint=False,
        is_absolute_hint=is_absolute,
        warnings=warnings,
        blocking_reasons=blocking_reasons,
        metadata={
            **SAFE_METADATA,
            "tool_name": clean_tool_name,
            "path_hint_checked_as_string_only": True,
            "filesystem_existence_not_checked": True,
        },
    )


def _make_capability(
    capability_id: str,
    capability_type: str,
    name: str,
    available: bool,
    source_probe: str,
    confidence: float,
) -> FFmpegCapability:
    return FFmpegCapability(
        capability_id=capability_id,
        capability_type=capability_type,
        name=name,
        available=available,
        source_probe=source_probe,
        confidence=confidence,
        metadata=SAFE_METADATA.copy(),
    )


def _safe_tool_probe(probe_vector: list[str]) -> tuple[bool, str, str]:
    completed = subprocess.run(
        probe_vector,
        shell=False,
        timeout=10,
        capture_output=True,
        text=True,
        check=False,
    )
    combined_text = "\n".join(
        part for part in [completed.stdout, completed.stderr] if part
    )
    if completed.returncode != 0:
        return False, combined_text, f"tool_probe_returncode_{completed.returncode}"
    return True, combined_text, ""


def _run_allowed_probe(
    tool_name: str,
    tool_path: str,
    probe_args: list[str],
    probe_runner: ProbeRunner | None,
) -> tuple[bool, str, str]:
    allowed_args = _ALLOWED_PROBES_BY_TOOL.get(tool_name, [])
    if probe_args not in allowed_args:
        return False, "", f"{tool_name}_probe_not_allowed"

    probe_vector = [tool_path] + list(probe_args)
    runner = probe_runner or _safe_tool_probe
    return runner(probe_vector)


def _first_version_line(text: str) -> str | None:
    for line in str(text or "").splitlines():
        clean = line.strip()
        if clean:
            return clean
    return None


def _contains_wordish(text: str, needle: str) -> bool:
    return needle.lower() in str(text or "").lower()


def _parse_capabilities(probe_outputs: dict[str, str]) -> list[FFmpegCapability]:
    encoders = probe_outputs.get("ffmpeg_encoders", "")
    decoders = probe_outputs.get("ffmpeg_decoders", "")
    filters = probe_outputs.get("ffmpeg_filters", "")
    hwaccels = probe_outputs.get("ffmpeg_hwaccels", "")

    has_h264 = _contains_wordish(encoders, "libx264") or _contains_wordish(
        encoders, " h264"
    )
    has_aac = _contains_wordish(encoders, "aac")
    has_nvenc = _contains_wordish(encoders, "h264_nvenc") or _contains_wordish(
        encoders, "hevc_nvenc"
    )
    has_scale = _contains_wordish(filters, "scale")
    has_loudnorm = _contains_wordish(filters, "loudnorm")
    has_concat = _contains_wordish(filters, "concat") or _contains_wordish(
        decoders, "concat"
    )
    has_cuda = _contains_wordish(hwaccels, "cuda") or _contains_wordish(
        hwaccels, "d3d11va"
    )

    return [
        _make_capability("h264_encoder", "encoder", "h264", has_h264, "ffmpeg_encoders", 0.95),
        _make_capability("aac_encoder", "encoder", "aac", has_aac, "ffmpeg_encoders", 0.95),
        _make_capability("nvenc_encoder", "hardware_encoder", "nvenc", has_nvenc, "ffmpeg_encoders", 0.95),
        _make_capability("scale_filter", "filter", "scale", has_scale, "ffmpeg_filters", 0.95),
        _make_capability("loudnorm_filter", "filter", "loudnorm", has_loudnorm, "ffmpeg_filters", 0.95),
        _make_capability("concat_support", "container_or_filter", "concat", has_concat, "ffmpeg_filters_or_decoders", 0.70),
        _make_capability("hardware_accel", "hardware", "cuda_or_d3d11va", has_cuda, "ffmpeg_hwaccels", 0.80),
    ]


def _unknown_capabilities() -> list[FFmpegCapability]:
    return [
        _make_capability("h264_encoder", "encoder", "h264", False, "not_probed", 0.0),
        _make_capability("aac_encoder", "encoder", "aac", False, "not_probed", 0.0),
        _make_capability("nvenc_encoder", "hardware_encoder", "nvenc", False, "not_probed", 0.0),
        _make_capability("scale_filter", "filter", "scale", False, "not_probed", 0.0),
        _make_capability("loudnorm_filter", "filter", "loudnorm", False, "not_probed", 0.0),
        _make_capability("concat_support", "container_or_filter", "concat", False, "not_probed", 0.0),
        _make_capability("hardware_accel", "hardware", "cuda_or_d3d11va", False, "not_probed", 0.0),
    ]


def _capability_available(capabilities: list[FFmpegCapability], capability_id: str) -> bool:
    for capability in capabilities:
        if capability.capability_id == capability_id:
            return bool(capability.available)
    return False


def resolve_ffmpeg_capabilities(
    job: Any,
    probe_runner: ProbeRunner | None = None,
) -> FFmpegCapabilityResolverReport:
    job_id = str(_job_attr(job, "job_id", "") or "")

    raw_ffmpeg_path_hint = _job_attr(job, "ffmpeg_path_hint", None)
    raw_ffprobe_path_hint = _job_attr(job, "ffprobe_path_hint", None)

    ffmpeg_path_hint = (
        DEFAULT_FFMPEG_PATH_HINT
        if raw_ffmpeg_path_hint is None
        else str(raw_ffmpeg_path_hint).strip()
    )
    ffprobe_path_hint = (
        DEFAULT_FFPROBE_PATH_HINT
        if raw_ffprobe_path_hint is None
        else str(raw_ffprobe_path_hint).strip()
    )

    expected_path = str(_job_attr(job, "ffmpeg_expected_path", "") or "").strip()
    if expected_path and ffmpeg_path_hint != expected_path:
        ffmpeg_path_hint = expected_path

    allow_tool_probe = bool(_job_attr(job, "ffmpeg_resolver_allow_tool_probe", False))

    ffmpeg_path = validate_tool_path("ffmpeg", ffmpeg_path_hint)
    ffprobe_path = validate_tool_path("ffprobe", ffprobe_path_hint)

    warnings: list[str] = []
    blocking_reasons: list[str] = []

    warnings.extend(ffmpeg_path.warnings)
    warnings.extend(ffprobe_path.warnings)
    blocking_reasons.extend(ffmpeg_path.blocking_reasons)
    blocking_reasons.extend(ffprobe_path.blocking_reasons)

    if not allow_tool_probe:
        warnings.append("ffmpeg_tool_probe_not_allowed")

    probe_outputs: dict[str, str] = {}
    tool_probe_attempted = False
    tool_probe_succeeded = False
    ffmpeg_version: str | None = None
    ffprobe_version: str | None = None

    if allow_tool_probe and not blocking_reasons:
        tool_probe_attempted = True
        probe_plan = [
            ("ffmpeg", ffmpeg_path_hint, ["-version"], "ffmpeg_version"),
            ("ffprobe", ffprobe_path_hint, ["-version"], "ffprobe_version"),
            ("ffmpeg", ffmpeg_path_hint, ["-encoders"], "ffmpeg_encoders"),
            ("ffmpeg", ffmpeg_path_hint, ["-decoders"], "ffmpeg_decoders"),
            ("ffmpeg", ffmpeg_path_hint, ["-filters"], "ffmpeg_filters"),
            ("ffmpeg", ffmpeg_path_hint, ["-hwaccels"], "ffmpeg_hwaccels"),
        ]

        probe_success_count = 0
        for tool_name, tool_path, probe_args, output_key in probe_plan:
            try:
                ok, output_text, error_code = _run_allowed_probe(
                    tool_name=tool_name,
                    tool_path=tool_path,
                    probe_args=probe_args,
                    probe_runner=probe_runner,
                )
            except Exception as exc:
                ok = False
                output_text = ""
                error_code = f"{output_key}_exception_{type(exc).__name__}"

            if ok:
                probe_success_count += 1
                probe_outputs[output_key] = output_text
            else:
                warnings.append(error_code or f"{output_key}_failed")

        tool_probe_succeeded = probe_success_count == len(probe_plan)
        ffmpeg_version = _first_version_line(probe_outputs.get("ffmpeg_version", ""))
        ffprobe_version = _first_version_line(probe_outputs.get("ffprobe_version", ""))

    capabilities = (
        _parse_capabilities(probe_outputs)
        if tool_probe_attempted
        else _unknown_capabilities()
    )

    has_h264 = _capability_available(capabilities, "h264_encoder")
    has_aac = _capability_available(capabilities, "aac_encoder")
    has_nvenc = _capability_available(capabilities, "nvenc_encoder")
    has_scale_filter = _capability_available(capabilities, "scale_filter")
    has_concat_support = _capability_available(capabilities, "concat_support")
    has_loudnorm_filter = _capability_available(capabilities, "loudnorm_filter")

    basics_available = has_h264 and has_aac and has_scale_filter
    can_prepare_real_render_tools = bool(basics_available and not blocking_reasons)

    if blocking_reasons:
        status = STATUS_BLOCKED
        recommendation = "review_ffmpeg_path_hints_before_any_future_render_stage"
    elif allow_tool_probe and tool_probe_succeeded and basics_available:
        status = STATUS_READY
        recommendation = "review_ffmpeg_capabilities"
    elif allow_tool_probe and tool_probe_attempted and not tool_probe_succeeded:
        status = STATUS_READY_WITH_WARNINGS
        recommendation = "review_ffmpeg_tool_probe_warnings"
    elif allow_tool_probe and not basics_available:
        status = STATUS_READY_WITH_WARNINGS
        recommendation = "review_missing_basic_ffmpeg_capabilities"
    elif not allow_tool_probe:
        status = STATUS_READY_WITH_WARNINGS
        recommendation = "enable_controlled_tool_probe_to_confirm_ffmpeg_capabilities"
    else:
        status = STATUS_FAILED
        recommendation = "review_ffmpeg_capability_resolver_failure"

    return FFmpegCapabilityResolverReport(
        report_id=f"ffmpeg_capability_resolver_{job_id or 'unknown'}",
        job_id=job_id,
        status=status,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
        allow_tool_probe=allow_tool_probe,
        tool_probe_attempted=tool_probe_attempted,
        tool_probe_succeeded=tool_probe_succeeded,
        ffmpeg_version=ffmpeg_version,
        ffprobe_version=ffprobe_version,
        capabilities=capabilities,
        has_h264=has_h264,
        has_aac=has_aac,
        has_nvenc=has_nvenc,
        has_scale_filter=has_scale_filter,
        has_concat_support=has_concat_support,
        has_loudnorm_filter=has_loudnorm_filter,
        can_prepare_real_render_tools=can_prepare_real_render_tools,
        can_render=False,
        can_process_media=False,
        can_write_media=False,
        can_probe_media_files=False,
        warnings=warnings,
        blocking_reasons=blocking_reasons,
        recommendation=recommendation,
        metadata=SAFE_METADATA.copy(),
    )
