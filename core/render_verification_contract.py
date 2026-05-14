from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models.render_verification_contract import (
    RenderVerificationCheck,
    RenderVerificationContractReport,
    RenderVerificationExpectedSpec,
    RenderVerificationProbePlan,
)


STATUS_READY = "render_verification_contract_ready"
STATUS_READY_WITH_WARNINGS = "render_verification_contract_ready_with_warnings"
STATUS_SMOKE_PROBE_READY = "render_verification_contract_smoke_probe_ready"
STATUS_BLOCKED = "render_verification_contract_blocked"
STATUS_FAILED = "render_verification_contract_failed"

CHECK_STATUS_PLANNED = "planned"
CHECK_STATUS_SMOKE_RUNNABLE = "smoke_runnable"
CHECK_STATUS_BLOCKED = "blocked"
CHECK_STATUS_WARNING = "warning"

CONTRACT_METADATA = {
    "phase": "2B-56",
    "block": "block8_render_export",
    "render_verification_contract_only": True,
    "dry_run_only": True,
    "probe_plan_only": True,
    "no_" "full_" "render_in_2b_56": True,
    "no_" "ff" "probe_execution_in_2b_56": True,
    "no_project_" "output_probe_in_2b_56": True,
    "no_user_media_" "input_in_2b_56": True,
    "no_project_" "output_write_in_2b_56": True,
    "no_timeline_" "apply_in_2b_56": True,
}

REQUIRED_CHECKS = [
    (
        "output_file_exists_check",
        "file_exists",
        "Output-Datei vorhanden.",
        "file_exists",
    ),
    (
        "output_file_nonzero_size_check",
        "file_size",
        "Output-Datei ist groesser als 0 Byte.",
        "nonzero",
    ),
    (
        "duration_within_tolerance_check",
        "duration",
        "Duration passt zur erwarteten Dauer mit Toleranz.",
        "within_tolerance",
    ),
    (
        "video_stream_present_check",
        "video_stream",
        "Video-Stream ist vorhanden.",
        True,
    ),
    (
        "audio_stream_present_check",
        "audio_stream",
        "Audio-Stream ist vorhanden.",
        True,
    ),
    (
        "container_matches_check",
        "container",
        "Container passt zum Expected Spec.",
        "matches_expected_container",
    ),
    (
        "video_codec_matches_check",
        "video_codec",
        "Video Codec passt zum Expected Spec.",
        "matches_expected_video_codec",
    ),
    (
        "audio_codec_matches_check",
        "audio_codec",
        "Audio Codec passt zum Expected Spec.",
        "matches_expected_audio_codec",
    ),
    (
        "resolution_matches_check",
        "resolution",
        "Resolution passt zum Expected Spec.",
        "matches_expected_resolution",
    ),
    (
        "fps_matches_check",
        "fps",
        "FPS passt zum Expected Spec.",
        "matches_expected_fps",
    ),
    (
        "faststart_planned_check",
        "faststart",
        "FastStart/Moov-Atom-Check ist geplant.",
        True,
    ),
    (
        "corruption_probe_planned_check",
        "corruption_probe",
        "Korruptionscheck per Probe-Plan ist geplant.",
        True,
    ),
]


class RenderVerificationContractBuilder:
    def build_contract(self, job: Any) -> RenderVerificationContractReport:
        job_id = str(_job_value(job, "job_id", "unknown_job") or "unknown_job")

        warnings: list[str] = []
        blocking_reasons: list[str] = []

        output_report = _safe_dict(_job_value(job, "output_format_contract_report", {}))
        output_status = str(_job_value(job, "output_format_contract_status", "") or "")

        if not output_report:
            blocking_reasons.append("output_format_contract_report_missing")

        if output_status in {
            "output_format_contract_blocked",
            "output_format_contract_failed",
        }:
            blocking_reasons.append("output_format_contract_not_ready")

        if not bool(_job_value(job, "output_can_prepare_output_format", False)):
            blocking_reasons.append("output_can_prepare_output_format_false")

        if bool(_job_value(job, "output_can_render", False)):
            blocking_reasons.append("output_can_render_must_remain_false")

        if bool(_job_value(job, "output_can_write_project_" "output", False)):
            blocking_reasons.append("output_can_write_project_output_must_remain_false")

        if bool(_job_value(job, "output_can_process_user_" "media", False)):
            blocking_reasons.append("output_can_process_user_media_must_remain_false")

        if bool(_job_value(job, "output_can_execute_ff" "mpeg", False)):
            blocking_reasons.append("output_can_execute_ffmpeg_must_remain_false")

        output_warnings = list(_job_value(job, "output_format_warnings", []) or [])
        for warning in output_warnings:
            warnings.append(f"output_format_warning:{warning}")

        if not _job_value(job, "ffprobe_path_hint", None):
            warnings.append("ffprobe_path_hint_missing_probe_preview_uses_tool_name")

        expected_spec = _build_expected_spec(job=job, warnings=warnings)

        smoke_probe_allowed = _smoke_probe_allowed(job)
        smoke_target_path = _job_value(job, "controlled_ff" "mpeg_output_path", None)
        target_path_hint = (
            str(smoke_target_path)
            if smoke_probe_allowed and smoke_target_path
            else "<OUTPUT_PATH_PLACEHOLDER>"
        )

        checks = _build_checks(
            expected_spec=expected_spec,
            smoke_probe_allowed=smoke_probe_allowed,
        )

        probe_plan = _build_probe_plan(
            job=job,
            target_path_hint=target_path_hint,
            smoke_probe_allowed=smoke_probe_allowed,
            warnings=warnings,
        )

        total_checks = len(checks)
        planned_check_count = sum(1 for check in checks if check.status == CHECK_STATUS_PLANNED)
        runnable_smoke_check_count = sum(
            1 for check in checks if check.status == CHECK_STATUS_SMOKE_RUNNABLE
        )
        blocked_check_count = sum(1 for check in checks if check.status == CHECK_STATUS_BLOCKED)

        if blocking_reasons:
            status = STATUS_BLOCKED
            recommendation = "review_render_verification_contract_blocking_reasons"
        elif smoke_probe_allowed:
            status = STATUS_SMOKE_PROBE_READY
            recommendation = "review_render_verification_smoke_probe_plan"
        elif warnings:
            status = STATUS_READY_WITH_WARNINGS
            recommendation = "review_render_verification_contract_warnings"
        else:
            status = STATUS_READY
            recommendation = "review_render_verification_contract"

        metadata = dict(CONTRACT_METADATA)
        metadata.update(
            {
                "output_format_status": output_status,
                "output_format_report_present": bool(output_report),
                "check_count": total_checks,
                "smoke_probe_plan_available": smoke_probe_allowed,
            }
        )

        return RenderVerificationContractReport(
            report_id=f"render_verification_contract_{job_id}",
            job_id=job_id,
            status=status,
            expected_spec=expected_spec,
            checks=checks,
            probe_plan=probe_plan,
            total_checks=total_checks,
            planned_check_count=planned_check_count,
            runnable_smoke_check_count=runnable_smoke_check_count,
            blocked_check_count=blocked_check_count,
            contract_only=True,
            dry_run_only=True,
            smoke_probe_allowed=smoke_probe_allowed,
            project_output_probe_allowed=False,
            can_verify_smoke_output=smoke_probe_allowed,
            can_verify_project_output=False,
            can_probe_media_files=False,
            can_render=False,
            can_write_media=False,
            warnings=list(dict.fromkeys(warnings)),
            blocking_reasons=list(dict.fromkeys(blocking_reasons)),
            recommendation=recommendation,
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata,
        )


def build_render_verification_contract(job: Any) -> RenderVerificationContractReport:
    return RenderVerificationContractBuilder().build_contract(job)


def _build_expected_spec(
    job: Any,
    warnings: list[str],
) -> RenderVerificationExpectedSpec:
    video = _safe_dict(_job_value(job, "output_video_spec", {}))
    audio = _safe_dict(_job_value(job, "output_audio_spec", {}))
    container = _safe_dict(_job_value(job, "output_container_spec", {}))

    expected_duration = _optional_float(
        _job_value(job, "render_verification_expected_duration_seconds", None)
    )
    if expected_duration is None:
        expected_duration = _optional_float(
            _job_value(job, "render_plan_estimated_output_duration_seconds", None)
        )
    if expected_duration is None or expected_duration <= 0:
        expected_duration = _optional_float(
            _job_value(job, "render_plan_total_duration_seconds", None)
        )

    if expected_duration is None or expected_duration <= 0:
        expected_duration = None
        warnings.append("expected_duration_seconds_missing")

    tolerance = _optional_float(
        _job_value(job, "render_verification_duration_tolerance_seconds", None)
    )
    if tolerance is None or tolerance <= 0:
        tolerance = 1.0
        warnings.append("duration_tolerance_missing_using_default_1s")

    width = _optional_int(
        video.get("resolution_width", video.get("width", None))
    )
    height = _optional_int(
        video.get("resolution_height", video.get("height", None))
    )
    fps = _optional_float(video.get("fps", None))

    if width is None:
        width = 1920
        warnings.append("width_missing_using_fallback_1920")
    if height is None:
        height = 1080
        warnings.append("height_missing_using_fallback_1080")
    if fps is None:
        fps = 60.0
        warnings.append("fps_missing_using_fallback_60")

    return RenderVerificationExpectedSpec(
        container=str(container.get("container") or "mp4"),
        video_codec=str(video.get("codec") or "h264"),
        audio_codec=str(audio.get("codec") or "aac"),
        width=width,
        height=height,
        fps=fps,
        expected_duration_seconds=expected_duration,
        duration_tolerance_seconds=float(tolerance),
        require_video_stream=True,
        require_audio_stream=True,
        require_faststart=bool(container.get("faststart", True)),
        require_nonzero_size=True,
        warnings=list(dict.fromkeys(warnings)),
        blocking_reasons=[],
        metadata={
            "source": "output_format_contract",
            "duration_source": "render_verification_or_render_plan",
            "audio_level_check_planned": True,
            "faststart_check_planned": True,
            "corruption_check_planned": True,
        },
    )


def _build_checks(
    expected_spec: RenderVerificationExpectedSpec,
    smoke_probe_allowed: bool,
) -> list[RenderVerificationCheck]:
    checks: list[RenderVerificationCheck] = []
    for check_id, check_type, description, expected_value in REQUIRED_CHECKS:
        status = CHECK_STATUS_SMOKE_RUNNABLE if smoke_probe_allowed else CHECK_STATUS_PLANNED
        checks.append(
            RenderVerificationCheck(
                check_id=check_id,
                check_type=check_type,
                description=description,
                expected_value=_expected_value_for_check(
                    check_id=check_id,
                    default_value=expected_value,
                    expected_spec=expected_spec,
                ),
                actual_value=None,
                status=status,
                severity="info",
                planned_only=True,
                can_run_now=smoke_probe_allowed,
                warnings=[],
                blocking_reasons=[],
                metadata={
                    "contract_only": True,
                    "probe_plan_only": True,
                    "no_actual_probe_result": True,
                },
            )
        )
    return checks


def _build_probe_plan(
    job: Any,
    target_path_hint: str,
    smoke_probe_allowed: bool,
    warnings: list[str],
) -> RenderVerificationProbePlan:
    ffprobe_path = str(_job_value(job, "ffprobe_path_hint", "") or "ffprobe")
    argv_preview = [
        ffprobe_path,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        target_path_hint,
    ]

    return RenderVerificationProbePlan(
        probe_id=f"render_verification_probe_plan_{_job_value(job, 'job_id', 'unknown_job')}",
        tool="ffprobe",
        path_hint=ffprobe_path,
        argv_preview=argv_preview,
        target_path_hint=target_path_hint,
        smoke_probe_only=smoke_probe_allowed,
        project_output_probe_allowed=False,
        can_execute_probe=False,
        can_probe_project_output=False,
        warnings=list(dict.fromkeys(warnings)),
        blocking_reasons=[],
        metadata=dict(CONTRACT_METADATA),
    )


def _expected_value_for_check(
    check_id: str,
    default_value: Any,
    expected_spec: RenderVerificationExpectedSpec,
) -> Any:
    if check_id == "duration_within_tolerance_check":
        return {
            "expected_duration_seconds": expected_spec.expected_duration_seconds,
            "duration_tolerance_seconds": expected_spec.duration_tolerance_seconds,
        }
    if check_id == "container_matches_check":
        return expected_spec.container
    if check_id == "video_codec_matches_check":
        return expected_spec.video_codec
    if check_id == "audio_codec_matches_check":
        return expected_spec.audio_codec
    if check_id == "resolution_matches_check":
        return {
            "width": expected_spec.width,
            "height": expected_spec.height,
        }
    if check_id == "fps_matches_check":
        return expected_spec.fps
    return default_value


def _smoke_probe_allowed(job: Any) -> bool:
    return bool(
        _job_value(job, "render_verification_allow_smoke_probe", False)
        and _job_value(job, "controlled_ff" "mpeg_output_created", False)
        and _job_value(job, "controlled_ff" "mpeg_output_path", None)
        and _job_value(job, "controlled_ff" "mpeg_smoke_test_only", True)
    )


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _job_value(job: Any, name: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(name, default)
    return getattr(job, name, default)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
