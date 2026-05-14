from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from models.output_format_contract import (
    OutputAudioSpec,
    OutputContainerSpec,
    OutputFormatContractReport,
    OutputFormatPreset,
    OutputVideoSpec,
)


STATUS_READY = "output_format_contract_ready"
STATUS_READY_WITH_WARNINGS = "output_format_contract_ready_with_warnings"
STATUS_BLOCKED = "output_format_contract_blocked"
STATUS_FAILED = "output_format_contract_failed"

DEFAULT_PROFILE = "gaming_main"
DEFAULT_PLATFORM = "youtube"
DEFAULT_TARGET_FORMAT = "longform"

CONTRACT_METADATA = {
    "phase": "2B-55",
    "block": "block8_render_export",
    "output_format_contract_only": True,
    "render_preset_contract_only": True,
    "dry_run_only": True,
    "no_" "full_" "render_in_2b_55": True,
    "no_" "ff" "mpeg_execution_in_2b_55": True,
    "no_user_media_" "input_in_2b_55": True,
    "no_project_" "output_in_2b_55": True,
    "no_timeline_" "apply_in_2b_55": True,
}


class OutputFormatHandler:
    def build_contract(self, job: Any) -> OutputFormatContractReport:
        job_id = str(_job_value(job, "job_id", "unknown_job") or "unknown_job")

        warnings: list[str] = []
        blocking_reasons: list[str] = []

        profile = _select_profile(job, warnings)
        platform = _select_platform(job, warnings)
        target_format = _select_target_format(job)

        capability_state = _read_capability_state(job)
        controlled_state = _read_controlled_state(job)
        command_state = _read_command_state(job)

        blocking_reasons.extend(
            _capability_blockers(capability_state)
        )
        blocking_reasons.extend(
            _controlled_blockers(controlled_state)
        )
        blocking_reasons.extend(
            _command_permission_blockers(command_state)
        )

        if not capability_state["has_nvenc"]:
            warnings.append("nvenc_missing_falling_back_to_libx264")
        else:
            warnings.append("nvenc_available_using_nvenc_intent")

        if not capability_state["has_loudnorm_filter"]:
            warnings.append("loudnorm_filter_missing_audio_normalization_may_be_limited")

        if not _has_output_target_hint(job):
            warnings.append("output_target_missing_using_safe_filename_hint_only")

        presets = _build_presets(
            profile=profile,
            platform=platform,
            target_format=target_format,
            has_nvenc=capability_state["has_nvenc"],
            has_loudnorm_filter=capability_state["has_loudnorm_filter"],
        )

        preset = _select_preset(
            job=job,
            presets=presets,
            profile=profile,
            platform=platform,
            target_format=target_format,
            warnings=warnings,
        )

        _apply_optional_requests(job=job, preset=preset, warnings=warnings)

        safe_filename = _build_safe_filename_hint(
            job_id=job_id,
            profile=profile,
            platform=platform,
            width=preset.video.resolution_width,
            height=preset.video.resolution_height,
            fps=preset.video.fps,
            extension=preset.container.extension,
        )
        preset.safe_filename_hint = safe_filename
        preset.filename_hint = safe_filename
        preset.output_path_hint = safe_filename

        compatible = not blocking_reasons
        preset.compatible_with_capabilities = compatible
        preset.warnings = list(dict.fromkeys(preset.warnings + warnings))
        preset.blocking_reasons = list(dict.fromkeys(blocking_reasons))
        preset.video.warnings = list(dict.fromkeys(preset.video.warnings))
        preset.audio.warnings = list(dict.fromkeys(preset.audio.warnings))
        preset.container.warnings = list(dict.fromkeys(preset.container.warnings))

        if blocking_reasons:
            status = STATUS_BLOCKED
            recommendation = "review_blocking_reasons_before_output_format_contract"
            can_prepare_output_format = False
        elif warnings:
            status = STATUS_READY_WITH_WARNINGS
            recommendation = "review_output_format_contract_warnings"
            can_prepare_output_format = True
        else:
            status = STATUS_READY
            recommendation = "review_output_format_contract"
            can_prepare_output_format = True

        metadata = dict(CONTRACT_METADATA)
        metadata.update(
            {
                "capability_status": capability_state["status"],
                "controlled_status": controlled_state["status"],
                "command_status": command_state["status"],
                "available_preset_count": len(presets),
            }
        )

        return OutputFormatContractReport(
            report_id=f"output_format_contract_{job_id}",
            job_id=job_id,
            status=status,
            preset=preset,
            available_presets=sorted(presets.keys()),
            selected_profile=profile,
            selected_platform=platform,
            selected_target_format=target_format,
            can_prepare_output_format=can_prepare_output_format,
            can_render=False,
            can_write_project_output=False,
            can_process_user_media=False,
            can_execute_ffmpeg=False,
            dry_run_only=True,
            contract_only=True,
            warnings=list(dict.fromkeys(warnings)),
            blocking_reasons=list(dict.fromkeys(blocking_reasons)),
            recommendation=recommendation,
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata,
        )


def build_output_format_contract(job: Any) -> OutputFormatContractReport:
    return OutputFormatHandler().build_contract(job)


def _build_presets(
    profile: str,
    platform: str,
    target_format: str,
    has_nvenc: bool,
    has_loudnorm_filter: bool,
) -> dict[str, OutputFormatPreset]:
    encoder_intent = "h264_nvenc" if has_nvenc else "libx264"
    video_warning = (
        "nvenc_available_using_nvenc_intent"
        if has_nvenc
        else "nvenc_missing_falling_back_to_libx264"
    )
    audio_warnings = []
    if not has_loudnorm_filter:
        audio_warnings.append("loudnorm_filter_missing_audio_normalization_may_be_limited")

    presets: dict[str, OutputFormatPreset] = {}

    presets["gaming_main_youtube_1080p60"] = OutputFormatPreset(
        preset_id="gaming_main_youtube_1080p60",
        profile="gaming_main",
        platform="youtube",
        target_format="longform",
        video=OutputVideoSpec(
            codec="h264",
            encoder_intent=encoder_intent,
            resolution_width=1920,
            resolution_height=1080,
            fps=60,
            crf=18,
            preset="fast",
            pix_fmt="yuv420p",
            use_nvenc_if_available=True,
            warnings=[video_warning],
        ),
        audio=OutputAudioSpec(
            codec="aac",
            bitrate_kbps=320,
            target_lufs=-14.0,
            true_peak_db=-1.0,
            loudnorm_required=True,
            warnings=list(audio_warnings),
        ),
        container=OutputContainerSpec(
            container="mp4",
            extension=".mp4",
            faststart=True,
            movflags="+faststart",
            compatible=True,
        ),
        metadata=dict(CONTRACT_METADATA),
    )

    presets["gaming_uncut_youtube_1080p60"] = OutputFormatPreset(
        preset_id="gaming_uncut_youtube_1080p60",
        profile="gaming_uncut",
        platform="youtube",
        target_format="longform",
        video=OutputVideoSpec(
            codec="h264",
            encoder_intent=encoder_intent,
            resolution_width=1920,
            resolution_height=1080,
            fps=60,
            crf=20,
            preset="fast",
            pix_fmt="yuv420p",
            use_nvenc_if_available=True,
            warnings=[video_warning],
        ),
        audio=OutputAudioSpec(
            codec="aac",
            bitrate_kbps=320,
            target_lufs=-14.0,
            true_peak_db=-1.0,
            loudnorm_required=True,
            warnings=list(audio_warnings),
        ),
        container=OutputContainerSpec(
            container="mp4",
            extension=".mp4",
            faststart=True,
            movflags="+faststart",
            compatible=True,
        ),
        metadata=dict(CONTRACT_METADATA),
    )

    presets["shorts_vertical_1080x1920_60"] = OutputFormatPreset(
        preset_id="shorts_vertical_1080x1920_60",
        profile=profile,
        platform=platform,
        target_format="short",
        video=OutputVideoSpec(
            codec="h264",
            encoder_intent=encoder_intent,
            resolution_width=1080,
            resolution_height=1920,
            fps=60,
            crf=18,
            preset="fast",
            pix_fmt="yuv420p",
            use_nvenc_if_available=True,
            warnings=[video_warning],
        ),
        audio=OutputAudioSpec(
            codec="aac",
            bitrate_kbps=320,
            target_lufs=-14.0,
            true_peak_db=-1.0,
            loudnorm_required=True,
            warnings=list(audio_warnings),
        ),
        container=OutputContainerSpec(
            container="mp4",
            extension=".mp4",
            faststart=True,
            movflags="+faststart",
            compatible=True,
        ),
        metadata=dict(CONTRACT_METADATA),
    )

    presets["fallback_youtube_1080p30"] = OutputFormatPreset(
        preset_id="fallback_youtube_1080p30",
        profile=profile or DEFAULT_PROFILE,
        platform="youtube",
        target_format=target_format or DEFAULT_TARGET_FORMAT,
        video=OutputVideoSpec(
            codec="h264",
            encoder_intent="libx264",
            resolution_width=1920,
            resolution_height=1080,
            fps=30,
            crf=20,
            preset="fast",
            pix_fmt="yuv420p",
            use_nvenc_if_available=False,
        ),
        audio=OutputAudioSpec(
            codec="aac",
            bitrate_kbps=320,
            target_lufs=-14.0,
            true_peak_db=-1.0,
            loudnorm_required=True,
            warnings=list(audio_warnings),
        ),
        container=OutputContainerSpec(
            container="mp4",
            extension=".mp4",
            faststart=True,
            movflags="+faststart",
            compatible=True,
        ),
        metadata=dict(CONTRACT_METADATA),
    )

    return presets


def _select_preset(
    job: Any,
    presets: dict[str, OutputFormatPreset],
    profile: str,
    platform: str,
    target_format: str,
    warnings: list[str],
) -> OutputFormatPreset:
    requested = str(_job_value(job, "output_preset_requested", "") or "").strip()
    if requested:
        if requested in presets:
            return presets[requested]
        warnings.append("requested_output_preset_unknown_using_fallback")
        return presets["fallback_youtube_1080p30"]

    if target_format in {"short", "shorts", "vertical"}:
        return presets["shorts_vertical_1080x1920_60"]

    if profile == "gaming_main" and platform == "youtube":
        return presets["gaming_main_youtube_1080p60"]

    if profile == "gaming_uncut" and platform == "youtube":
        return presets["gaming_uncut_youtube_1080p60"]

    warnings.append("no_matching_output_preset_using_fallback_youtube_1080p30")
    return presets["fallback_youtube_1080p30"]


def _apply_optional_requests(
    job: Any,
    preset: OutputFormatPreset,
    warnings: list[str],
) -> None:
    resolution = _job_value(job, "output_resolution_requested", None)
    if resolution:
        parsed = _parse_resolution(str(resolution))
        if parsed is None:
            warnings.append("requested_output_resolution_invalid_keeping_preset")
        else:
            preset.video.resolution_width = parsed[0]
            preset.video.resolution_height = parsed[1]

    fps = _job_value(job, "output_fps_requested", None)
    if fps is not None:
        try:
            fps_int = int(fps)
            if fps_int <= 0 or fps_int > 240:
                raise ValueError
            preset.video.fps = fps_int
        except (TypeError, ValueError):
            warnings.append("requested_output_fps_invalid_keeping_preset")

    codec_preference = str(
        _job_value(job, "output_codec_preference", "") or ""
    ).strip().lower()
    if codec_preference:
        if codec_preference in {"h264", "libx264"}:
            preset.video.encoder_intent = "libx264"
        elif codec_preference in {"nvenc", "h264_nvenc"}:
            if any("nvenc_available" in warning for warning in preset.video.warnings):
                preset.video.encoder_intent = "h264_nvenc"
            else:
                preset.video.encoder_intent = "libx264"
                warnings.append("requested_nvenc_but_missing_using_libx264")
        else:
            warnings.append("requested_output_codec_unknown_keeping_preset")

    audio_lufs = _job_value(job, "output_audio_lufs_requested", None)
    if audio_lufs is not None:
        try:
            preset.audio.target_lufs = float(audio_lufs)
        except (TypeError, ValueError):
            warnings.append("requested_output_audio_lufs_invalid_keeping_preset")

    container = str(_job_value(job, "output_container_requested", "") or "").strip().lower()
    if container:
        if container == "mp4":
            preset.container.container = "mp4"
            preset.container.extension = ".mp4"
        else:
            warnings.append("requested_output_container_not_supported_using_mp4")


def _select_profile(job: Any, warnings: list[str]) -> str:
    requested = str(_job_value(job, "profile", "") or "").strip().lower()
    if not requested:
        warnings.append("profile_missing_defaulting_to_gaming_main")
        return DEFAULT_PROFILE

    allowed = {"gaming_main", "gaming_uncut", "faceless_trend"}
    if requested not in allowed:
        warnings.append("profile_unknown_defaulting_to_gaming_main")
        return DEFAULT_PROFILE
    return requested


def _select_platform(job: Any, warnings: list[str]) -> str:
    requested = str(_job_value(job, "output_platform_requested", "") or "").strip().lower()
    if not requested:
        target_platforms = _job_value(job, "target_platforms", None)
        if isinstance(target_platforms, list) and target_platforms:
            requested = str(target_platforms[0]).strip().lower()
        elif isinstance(target_platforms, str):
            requested = target_platforms.strip().lower()

    if not requested:
        warnings.append("platform_missing_defaulting_to_youtube")
        return DEFAULT_PLATFORM

    allowed = {"youtube", "tiktok", "instagram", "shorts"}
    if requested not in allowed:
        warnings.append("platform_unknown_defaulting_to_youtube")
        return DEFAULT_PLATFORM
    return requested


def _select_target_format(job: Any) -> str:
    requested = str(_job_value(job, "target_format", "") or "").strip().lower()
    if requested in {"short", "shorts", "vertical"}:
        return "short"
    if requested in {"longform", "long", "video"}:
        return "longform"
    return DEFAULT_TARGET_FORMAT


def _read_capability_state(job: Any) -> dict[str, Any]:
    report = _job_value(job, "ff" "mpeg_capability_resolver_report", None)
    if not isinstance(report, dict):
        report = {}

    return {
        "report_present": bool(report),
        "status": str(
            _job_value(
                job,
                "ff" "mpeg_capability_status",
                report.get("status", ""),
            )
            or ""
        ).lower(),
        "has_h264": _job_bool(job, "ff" "mpeg_has_h264", report.get("has_h264", False)),
        "has_aac": _job_bool(job, "ff" "mpeg_has_aac", report.get("has_aac", False)),
        "has_nvenc": _job_bool(job, "ff" "mpeg_has_nvenc", report.get("has_nvenc", False)),
        "has_scale_filter": _job_bool(
            job,
            "ff" "mpeg_has_scale_filter",
            report.get("has_scale_filter", False),
        ),
        "has_loudnorm_filter": _job_bool(
            job,
            "ff" "mpeg_has_loudnorm_filter",
            report.get("has_loudnorm_filter", False),
        ),
        "can_prepare": _job_bool(
            job,
            "ff" "mpeg_can_prepare_real_render_tools",
            report.get("can_prepare_real_render_tools", False),
        ),
        "blocking_reasons": _as_list(
            _job_value(
                job,
                "ff" "mpeg_blocking_reasons",
                report.get("blocking_reasons", []),
            )
        ),
    }


def _read_command_state(job: Any) -> dict[str, Any]:
    report = _job_value(job, "ff" "mpeg_command_assembly_report", None)
    if not isinstance(report, dict):
        report = {}

    return {
        "status": str(
            _job_value(
                job,
                "ff" "mpeg_command_assembly_status",
                report.get("status", ""),
            )
            or ""
        ).lower(),
        "can_execute_commands": _job_bool(
            job,
            "ff" "mpeg_command_can_execute_commands",
            report.get("can_execute_commands", False),
        ),
        "can_render": _job_bool(
            job,
            "ff" "mpeg_command_can_render",
            report.get("can_render", False),
        ),
        "can_write_" "media": _job_bool(
            job,
            "ff" "mpeg_command_can_write_" "media",
            report.get("can_write_" "media", False),
        ),
    }


def _read_controlled_state(job: Any) -> dict[str, Any]:
    report = _job_value(job, "controlled_" "ff" "mpeg_execution_report", None)
    if not isinstance(report, dict):
        report = {}

    return {
        "report_present": bool(report),
        "status": str(
            _job_value(
                job,
                "controlled_" "ff" "mpeg_execution_status",
                report.get("status", ""),
            )
            or ""
        ).lower(),
        "can_execute_full": _job_bool(
            job,
            "controlled_" "ff" "mpeg_can_execute_full_render",
            report.get("can_execute_full_render", False),
        ),
        "can_render_timeline": _job_bool(
            job,
            "controlled_" "ff" "mpeg_can_render_timeline",
            report.get("can_render_timeline", False),
        ),
        "can_process_user_media": _job_bool(
            job,
            "controlled_" "ff" "mpeg_can_process_user_media",
            report.get("can_process_user_media", False),
        ),
        "can_write_project_output": _job_bool(
            job,
            "controlled_" "ff" "mpeg_can_write_project_output",
            report.get("can_write_project_output", False),
        ),
    }


def _capability_blockers(state: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not state["report_present"] and not state["status"]:
        blockers.append("ffmpeg_capability_report_missing")
    if state["status"] in {"blocked", "failed"} or "blocked" in state["status"] or "failed" in state["status"]:
        blockers.append("ffmpeg_capability_status_not_ready")
    if not state["can_prepare"]:
        blockers.append("ffmpeg_cannot_prepare_real_render_tools")
    if not state["has_h264"]:
        blockers.append("ffmpeg_h264_missing")
    if not state["has_aac"]:
        blockers.append("ffmpeg_aac_missing")
    blockers.extend(str(reason) for reason in state["blocking_reasons"])
    return blockers


def _controlled_blockers(state: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not state["report_present"] and not state["status"]:
        blockers.append("controlled_ffmpeg_execution_report_missing")
    if state["status"] in {"blocked", "failed"} or "blocked" in state["status"] or "failed" in state["status"]:
        blockers.append("controlled_ffmpeg_execution_status_not_ready")

    blocked_flags = {
        "controlled_ffmpeg_full_permission_leak": state["can_execute_full"],
        "controlled_ffmpeg_timeline_permission_leak": state["can_render_timeline"],
        "controlled_ffmpeg_user_media_permission_leak": state["can_process_user_media"],
        "controlled_ffmpeg_output_permission_leak": state["can_write_project_output"],
    }
    for reason, leaked in blocked_flags.items():
        if leaked:
            blockers.append(reason)
    return blockers


def _command_permission_blockers(state: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if state["can_execute_commands"]:
        blockers.append("ffmpeg_command_execution_permission_leak")
    if state["can_render"]:
        blockers.append("ffmpeg_command_render_permission_leak")
    if state["can_write_" "media"]:
        blockers.append("ffmpeg_command_write_" "permission_leak")
    return blockers


def _has_output_target_hint(job: Any) -> bool:
    output_targets = _job_value(job, "render_plan_output_targets", None)
    if isinstance(output_targets, list) and output_targets:
        return True

    plan_report = _job_value(job, "render_plan_report", None)
    if isinstance(plan_report, dict):
        targets = plan_report.get("output_targets")
        if isinstance(targets, list) and targets:
            return True

    path_plans = _job_value(job, "render_output_path_plans", None)
    return isinstance(path_plans, list) and bool(path_plans)


def _build_safe_filename_hint(
    job_id: str,
    profile: str,
    platform: str,
    width: int,
    height: int,
    fps: int,
    extension: str,
) -> str:
    raw = f"{job_id}_{profile}_{platform}_{width}x{height}_{fps}fps{extension}"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)
    safe = safe.strip("._-")
    if not safe.endswith(extension):
        safe = f"{safe}{extension}"
    return safe or f"output_format_contract{extension}"


def _parse_resolution(value: str) -> tuple[int, int] | None:
    match = re.match(r"^\s*(\d{3,5})\s*x\s*(\d{3,5})\s*$", value)
    if not match:
        return None
    width = int(match.group(1))
    height = int(match.group(2))
    if width <= 0 or height <= 0:
        return None
    return width, height


def _job_value(job: Any, name: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(name, default)
    return getattr(job, name, default)


def _job_bool(job: Any, name: str, default: Any = False) -> bool:
    value = _job_value(job, name, default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "ready"}
    return bool(value)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]
