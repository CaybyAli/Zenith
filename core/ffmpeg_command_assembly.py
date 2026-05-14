from __future__ import annotations

import re
from typing import Any

from models.ffmpeg_command_assembly import (
    FFmpegArgumentToken,
    FFmpegCommandAssembly,
    FFmpegCommandAssemblyReport,
    STATUS_BLOCKED,
    STATUS_FAILED,
    STATUS_READY,
    STATUS_READY_WITH_WARNINGS,
)

SAFE_METADATA = {
    "phase": "2B-53",
    "block": "block8_render_export",
    "ffmpeg_command_assembly_only": True,
    "dry_run_only": True,
    "assembly_only": True,
    "preview_only": True,
    "no_render_in_2b_53": True,
    "no_process_spawn_in_2b_53": True,
    "no_media_read_in_2b_53": True,
    "no_media_write_in_2b_53": True,
    "no_directory_create_in_2b_53": True,
    "no_timeline_apply_in_2b_53": True,
}

READY_CAPABILITY_STATUSES = {
    "ffmpeg_capability_ready",
    "ffmpeg_capability_ready_with_warnings",
}

READY_EXECUTION_PERMISSION_STATUSES = {
    "render_execution_permission_ready",
    "render_execution_permission_ready_with_warnings",
    "ready",
    "ready_with_warnings",
}

READY_CONTROLLED_EXECUTOR_STATUSES = {
    "controlled_render_executor_dry_run_ready",
    "controlled_render_executor_dry_run_with_warnings",
    "dry_run_ready",
    "dry_run_with_warnings",
}

SHELL_MARKERS = ("&", "|", ";", ">", "<")
BLOCKED_TOKEN_TEXTS = (
    "shell" + "=true",
    "os." + "system",
    "sub" + "process",
    "rm ",
    "del ",
    "erase ",
    "power" + "shell",
    "cmd" + ".exe",
    " /c ",
)
PLACEHOLDER_RE = re.compile(r"^<[^<>]+>$")
URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


def _job_attr(job: Any, name: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(name, default)
    return getattr(job, name, default)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return []


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _string(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _bool_job(job: Any, name: str, default: bool = False) -> bool:
    return bool(_job_attr(job, name, default))


def _collect_existing_reasons(job: Any, field_name: str) -> list[str]:
    return [str(item) for item in _as_list(_job_attr(job, field_name, []))]


def _append_unique(target: list[str], item: str) -> None:
    clean = str(item or "").strip()
    if clean and clean not in target:
        target.append(clean)


def _step_id(step: dict[str, Any], index: int) -> str:
    return _string(
        step.get("step_id")
        or step.get("id")
        or step.get("blueprint_step_id")
        or f"blueprint_step_{index + 1}"
    )


def _segment_ids_from_plan(job: Any) -> list[str]:
    segment_ids: list[str] = []
    for index, segment in enumerate(_as_list(_job_attr(job, "render_plan_segments", []))):
        if not isinstance(segment, dict):
            continue
        segment_id = _string(
            segment.get("segment_id")
            or segment.get("id")
            or segment.get("source_segment_id")
            or f"render_plan_segment_{index + 1}"
        )
        segment_ids.append(segment_id)
    return segment_ids


def _output_target_id(job: Any) -> str | None:
    targets = _as_list(_job_attr(job, "render_plan_output_targets", []))
    if not targets:
        targets = _as_list(_job_attr(job, "render_output_path_plans", []))
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            continue
        return _string(
            target.get("target_id")
            or target.get("output_target_id")
            or target.get("path_plan_id")
            or target.get("id")
            or f"output_target_{index + 1}"
        )
    return None


def _ffmpeg_path_hint(job: Any) -> str:
    path_hint = _string(_job_attr(job, "ffmpeg_path_hint", ""))
    report = _as_dict(_job_attr(job, "ffmpeg_capability_resolver_report", {}))
    ffmpeg_path = _as_dict(report.get("ffmpeg_path"))
    return path_hint or _string(ffmpeg_path.get("path_hint"), "ffmpeg.exe")


def _classify_blueprint_step(step: dict[str, Any]) -> str:
    raw = " ".join(
        [
            _string(step.get("step_type")),
            _string(step.get("operation_type")),
            _string(step.get("intent_type")),
            _string(step.get("action")),
            _string(step.get("description")),
        ]
    ).lower()

    if "subtitle" in raw or "caption" in raw:
        return "subtitle_assembly"
    if "audio" in raw or "mix" in raw or "loudnorm" in raw:
        return "audio_mix_assembly"
    if "censor" in raw or "sfx" in raw or "sound" in raw:
        return "censor_sfx_assembly"
    if "encode" in raw:
        return "encode_assembly"
    if "faststart" in raw:
        return "faststart_assembly"
    if "probe" in raw or "verify" in raw:
        return "probe_verification_assembly_preview"
    if "trim" in raw or "concat" in raw or "cut" in raw:
        return "trim_concat_assembly"
    return "encode_assembly"


def _default_assembly_types(job: Any) -> list[str]:
    operation_intents = _as_list(_job_attr(job, "render_plan_operation_intents", []))
    blueprint_steps = _as_list(_job_attr(job, "render_blueprint_steps", []))

    detected: list[str] = []
    for step in blueprint_steps:
        if isinstance(step, dict):
            _append_unique(detected, _classify_blueprint_step(step))

    for intent in operation_intents:
        if not isinstance(intent, dict):
            continue
        detected_type = _classify_blueprint_step(intent)
        _append_unique(detected, detected_type)

    if not detected:
        detected = ["trim_concat_assembly", "encode_assembly", "faststart_assembly"]

    return detected


def _argv_for_type(ffmpeg_path: str, assembly_type: str) -> list[str]:
    base = [ffmpeg_path, "-hide_banner", "-nostdin", "-y"]

    if assembly_type == "trim_concat_assembly":
        return base + [
            "-i",
            "<INPUT_PLACEHOLDER>",
            "-filter_complex",
            "<TRIM_CONCAT_FILTER_PLACEHOLDER>",
            "-map",
            "<VIDEO_AUDIO_MAP_PLACEHOLDER>",
            "<OUTPUT_PLACEHOLDER>",
        ]

    if assembly_type == "audio_mix_assembly":
        return base + [
            "-i",
            "<INPUT_PLACEHOLDER>",
            "-filter_complex",
            "<AUDIO_MIX_FILTER_PLACEHOLDER>",
            "-map",
            "<AUDIO_MAP_PLACEHOLDER>",
            "<OUTPUT_PLACEHOLDER>",
        ]

    if assembly_type == "censor_sfx_assembly":
        return base + [
            "-i",
            "<INPUT_PLACEHOLDER>",
            "-filter_complex",
            "<CENSOR_SFX_FILTER_PLACEHOLDER>",
            "<OUTPUT_PLACEHOLDER>",
        ]

    if assembly_type == "subtitle_assembly":
        return base + [
            "-i",
            "<INPUT_PLACEHOLDER>",
            "-vf",
            "<SUBTITLE_FILTER_PLACEHOLDER>",
            "<OUTPUT_PLACEHOLDER>",
        ]

    if assembly_type == "faststart_assembly":
        return base + [
            "-i",
            "<INPUT_PLACEHOLDER>",
            "-movflags",
            "+faststart",
            "<OUTPUT_PLACEHOLDER>",
        ]

    if assembly_type == "probe_verification_assembly_preview":
        return [
            ffmpeg_path,
            "-hide_banner",
            "-nostdin",
            "-i",
            "<INPUT_PLACEHOLDER>",
            "-f",
            "null",
            "<NULL_OUTPUT_PLACEHOLDER>",
        ]

    return base + [
        "-i",
        "<INPUT_PLACEHOLDER>",
        "-c:v",
        "<VIDEO_ENCODER_PLACEHOLDER>",
        "-c:a",
        "aac",
        "<OUTPUT_PLACEHOLDER>",
    ]


def _contains_path_traversal(token: str) -> bool:
    pieces = re.split(r"[\\/]+", token)
    return any(piece.strip() == ".." for piece in pieces)


def _token_type(value: str, index: int) -> str:
    if index == 0:
        return "tool_path_hint"
    if PLACEHOLDER_RE.match(value):
        return "placeholder"
    if value.startswith("-"):
        return "option"
    return "argument"


def _validate_token(value: str, index: int) -> tuple[bool, list[str], list[str]]:
    warnings: list[str] = []
    blocking_reasons: list[str] = []
    text = str(value or "")

    if not text:
        blocking_reasons.append("empty_argument_token_blocked")

    lowered = text.lower()

    if "\n" in text or "\r" in text:
        blocking_reasons.append("argument_newline_blocked")

    is_placeholder = bool(PLACEHOLDER_RE.match(text))

    if not is_placeholder and any(marker in text for marker in SHELL_MARKERS):
        blocking_reasons.append("argument_shell_marker_blocked")

    if not is_placeholder and "&&" in text:
        blocking_reasons.append("argument_shell_chain_blocked")

    if URL_RE.match(text) or "://" in lowered:
        blocking_reasons.append("argument_url_blocked")

    if _contains_path_traversal(text):
        blocking_reasons.append("argument_path_traversal_blocked")

    if lowered in {"/" + "c", "cmd", "cmd" + ".exe"}:
        blocking_reasons.append("argument_shell_tool_blocked")

    padded = f" {lowered} "
    if any(blocked in padded for blocked in BLOCKED_TOKEN_TEXTS):
        blocking_reasons.append("argument_forbidden_text_blocked")

    if index == 0 and not lowered.endswith(("ffmpeg.exe", "ffmpeg")):
        blocking_reasons.append("first_argument_not_ffmpeg_path_hint")

    if PLACEHOLDER_RE.match(text):
        warnings.append("argument_placeholder_preview_only")

    return not blocking_reasons, warnings, blocking_reasons


def _build_argument_tokens(argv_preview: list[str]) -> list[FFmpegArgumentToken]:
    tokens: list[FFmpegArgumentToken] = []
    for index, value in enumerate(argv_preview):
        safe, warnings, blocking_reasons = _validate_token(value, index)
        tokens.append(
            FFmpegArgumentToken(
                token_id=f"arg_{index + 1}",
                value=str(value),
                token_type=_token_type(str(value), index),
                safe=safe,
                warnings=warnings,
                blocking_reasons=blocking_reasons,
                metadata={
                    **SAFE_METADATA,
                    "argument_index": index,
                    "preview_only_argument": True,
                },
            )
        )
    return tokens


def _validate_argv(argv_preview: list[str], ffmpeg_path_hint: str) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    blocking_reasons: list[str] = []

    if not argv_preview:
        blocking_reasons.append("argv_preview_empty")
        return warnings, blocking_reasons

    if argv_preview[0] != ffmpeg_path_hint:
        blocking_reasons.append("first_argument_not_exact_ffmpeg_path_hint")

    for token in _build_argument_tokens(argv_preview):
        for warning in token.warnings:
            _append_unique(warnings, warning)
        for reason in token.blocking_reasons:
            _append_unique(blocking_reasons, reason)

    return warnings, blocking_reasons


def _check_prerequisites(job: Any) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    blocking_reasons: list[str] = []

    capability_report = _as_dict(_job_attr(job, "ffmpeg_capability_resolver_report", {}))
    capability_status = _string(_job_attr(job, "ffmpeg_capability_status", ""))

    if not capability_report:
        blocking_reasons.append("ffmpeg_capability_resolver_report_missing")

    if not capability_status:
        blocking_reasons.append("ffmpeg_capability_status_missing")
    elif capability_status not in READY_CAPABILITY_STATUSES:
        blocking_reasons.append("ffmpeg_capability_status_not_ready")

    if not _bool_job(job, "ffmpeg_can_prepare_real_render_tools", False):
        blocking_reasons.append("ffmpeg_can_prepare_real_render_tools_false")

    if _bool_job(job, "ffmpeg_can_render", False):
        blocking_reasons.append("ffmpeg_can_render_true_blocked")
    if _bool_job(job, "ffmpeg_can_process_media", False):
        blocking_reasons.append("ffmpeg_can_process_media_true_blocked")
    if _bool_job(job, "ffmpeg_can_write_media", False):
        blocking_reasons.append("ffmpeg_can_write_media_true_blocked")
    if _bool_job(job, "ffmpeg_can_probe_media_files", False):
        blocking_reasons.append("ffmpeg_can_probe_media_files_true_blocked")

    execution_report = _as_dict(
        _job_attr(job, "render_execution_permission_report", {})
    )
    execution_status = _string(_job_attr(job, "render_execution_permission_status", ""))

    if not execution_report:
        blocking_reasons.append("render_execution_permission_report_missing")

    if not execution_status:
        blocking_reasons.append("render_execution_permission_status_missing")
    elif execution_status not in READY_EXECUTION_PERMISSION_STATUSES:
        blocking_reasons.append("render_execution_permission_status_not_ready")

    if not _bool_job(job, "render_execution_ready_for_real_render_stage", False):
        blocking_reasons.append("render_execution_ready_for_real_render_stage_false")

    if not _bool_job(job, "render_execution_can_prepare_real_render_execution", False):
        blocking_reasons.append("render_execution_can_prepare_real_render_execution_false")

    if not _bool_job(job, "render_execution_human_approved", False):
        blocking_reasons.append("render_execution_human_approved_false")

    controlled_status = _string(_job_attr(job, "controlled_render_executor_status", ""))

    if not _as_dict(_job_attr(job, "controlled_render_executor_report", {})):
        blocking_reasons.append("controlled_render_executor_report_missing")

    if not controlled_status:
        blocking_reasons.append("controlled_render_executor_status_missing")
    elif controlled_status not in READY_CONTROLLED_EXECUTOR_STATUSES:
        blocking_reasons.append("controlled_render_executor_status_not_dry_run_ready")

    if not _bool_job(job, "controlled_render_dry_run_only", True):
        blocking_reasons.append("controlled_render_dry_run_only_false")

    if _bool_job(job, "controlled_render_output_created", False):
        blocking_reasons.append("controlled_render_output_created_true_blocked")

    if not _bool_job(job, "render_blueprint_non_executable", False):
        blocking_reasons.append("render_blueprint_non_executable_false")

    if not _bool_job(job, "render_asset_paths_are_hints_only", False):
        blocking_reasons.append("render_asset_paths_are_hints_only_false")

    if _bool_job(job, "render_asset_can_write_files", False):
        blocking_reasons.append("render_asset_can_write_files_true_blocked")

    warnings.extend(_collect_existing_reasons(job, "ffmpeg_warnings"))
    warnings.extend(_collect_existing_reasons(job, "render_execution_warnings"))
    warnings.extend(_collect_existing_reasons(job, "controlled_render_warnings"))
    warnings.extend(_collect_existing_reasons(job, "render_blueprint_warnings"))
    warnings.extend(_collect_existing_reasons(job, "render_asset_warnings"))
    warnings.extend(_collect_existing_reasons(job, "render_plan_warnings"))

    return warnings, blocking_reasons


def _build_assembly(
    job: Any,
    assembly_type: str,
    index: int,
    ffmpeg_path: str,
    source_step_ids: list[str],
    source_segment_ids: list[str],
    output_target_id: str | None,
) -> FFmpegCommandAssembly:
    argv_preview = _argv_for_type(ffmpeg_path, assembly_type)
    argument_tokens = _build_argument_tokens(argv_preview)
    warnings, blocking_reasons = _validate_argv(argv_preview, ffmpeg_path)

    return FFmpegCommandAssembly(
        assembly_id=f"ffmpeg_command_assembly_{index + 1}",
        assembly_type=assembly_type,
        description=f"Preview-only FFmpeg argument assembly for {assembly_type}.",
        argv_preview=argv_preview,
        argument_tokens=argument_tokens,
        source_blueprint_step_ids=source_step_ids,
        source_render_plan_segment_ids=source_segment_ids,
        output_target_id=output_target_id,
        assembly_only=True,
        preview_only=True,
        can_execute_command=False,
        can_spawn_process=False,
        can_render=False,
        can_write_media=False,
        warnings=warnings,
        blocking_reasons=blocking_reasons,
        metadata={
            **SAFE_METADATA,
            "assembly_index": index,
            "command_is_data_only": True,
        },
    )


def build_ffmpeg_command_assembly_report(job: Any) -> FFmpegCommandAssemblyReport:
    job_id = _string(_job_attr(job, "job_id", ""), "unknown")
    warnings, blocking_reasons = _check_prerequisites(job)

    ffmpeg_path = _ffmpeg_path_hint(job)
    blueprint_steps = [
        item
        for item in _as_list(_job_attr(job, "render_blueprint_steps", []))
        if isinstance(item, dict)
    ]

    source_step_ids = [_step_id(step, index) for index, step in enumerate(blueprint_steps)]
    source_segment_ids = _segment_ids_from_plan(job)
    output_target_id = _output_target_id(job)

    assemblies: list[FFmpegCommandAssembly] = []

    if not blocking_reasons:
        for index, assembly_type in enumerate(_default_assembly_types(job)):
            assembly = _build_assembly(
                job=job,
                assembly_type=assembly_type,
                index=index,
                ffmpeg_path=ffmpeg_path,
                source_step_ids=source_step_ids,
                source_segment_ids=source_segment_ids,
                output_target_id=output_target_id,
            )
            assemblies.append(assembly)
            for warning in assembly.warnings:
                _append_unique(warnings, warning)
            for reason in assembly.blocking_reasons:
                _append_unique(blocking_reasons, reason)

    total_assemblies = len(assemblies)
    blocked_assembly_count = sum(1 for item in assemblies if item.blocking_reasons)
    safe_assembly_count = total_assemblies - blocked_assembly_count

    if blocking_reasons:
        status = STATUS_BLOCKED
        recommendation = "review_ffmpeg_command_assembly_blocking_reasons"
    elif warnings:
        status = STATUS_READY_WITH_WARNINGS
        recommendation = "review_ffmpeg_command_assembly"
    else:
        status = STATUS_READY
        recommendation = "review_ffmpeg_command_assembly"

    ready_for_controlled_execution_stage = bool(
        not blocking_reasons and total_assemblies > 0
    )

    return FFmpegCommandAssemblyReport(
        report_id=f"ffmpeg_command_assembly_{job_id}",
        job_id=job_id,
        status=status,
        assemblies=assemblies,
        total_assemblies=total_assemblies,
        safe_assembly_count=safe_assembly_count,
        blocked_assembly_count=blocked_assembly_count,
        dry_run_only=True,
        assembly_only=True,
        preview_only=True,
        ready_for_controlled_execution_stage=ready_for_controlled_execution_stage,
        can_execute_commands=False,
        can_spawn_process=False,
        can_render=False,
        can_write_media=False,
        can_probe_media_files=False,
        warnings=warnings,
        blocking_reasons=blocking_reasons,
        recommendation=recommendation,
        metadata=SAFE_METADATA.copy(),
    )
