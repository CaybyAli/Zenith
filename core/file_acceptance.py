from __future__ import annotations

from pathlib import Path
from typing import Any

from core.file_probe import probe_file
from models.file_acceptance import FileAcceptanceResult
from models.file_info import FileInfo


DEFAULT_MIN_DURATION_SECONDS = 1.0
DEFAULT_MAX_DURATION_WARNING_SECONDS = 4 * 60 * 60


def _profile_value(profile: dict[str, Any] | None, key: str, default: Any) -> Any:
    if isinstance(profile, dict) and key in profile:
        return profile.get(key)
    return default


def _profile_id(profile: dict[str, Any] | None) -> str | None:
    if isinstance(profile, dict):
        return profile.get("profile_id") or profile.get("id") or profile.get("name")
    return None


def _add_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def build_file_acceptance_result(
    file_info: FileInfo,
    reasons: list[str],
    warnings: list[str],
    errors: list[str],
    profile: dict[str, Any] | None = None,
) -> FileAcceptanceResult:
    accepted = len(errors) == 0

    if accepted and warnings:
        status = "accepted_with_warnings"
        severity = "warning"
    elif accepted:
        status = "accepted"
        severity = "ok"
    else:
        status = "rejected"
        severity = "error"

    recommendation = "accept" if accepted else "reject"
    if accepted and warnings:
        recommendation = "accept_with_review"

    return FileAcceptanceResult(
        accepted=accepted,
        status=status,
        severity=severity,
        reasons=list(reasons),
        warnings=list(warnings),
        errors=list(errors),
        file_path=file_info.path,
        extension=file_info.extension,
        profile_id=_profile_id(profile),
        recommendation=recommendation,
        details={
            "exists": file_info.exists,
            "is_supported_format": file_info.is_supported_format,
            "probe_status": file_info.probe_status,
            "probe_error": file_info.probe_error,
            "duration_seconds": file_info.duration_seconds,
            "has_video": file_info.has_video,
            "has_audio": file_info.has_audio,
            "video_stream_count": file_info.video_stream_count,
            "audio_stream_count": file_info.audio_stream_count,
            "width": file_info.width,
            "height": file_info.height,
            "fps": file_info.fps,
        },
    )


def validate_file_info(
    file_info: FileInfo,
    profile: dict[str, Any] | None = None,
) -> FileAcceptanceResult:
    reasons: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    require_audio = bool(_profile_value(profile, "require_audio", False))
    min_duration_seconds = float(
        _profile_value(profile, "min_duration_seconds", DEFAULT_MIN_DURATION_SECONDS)
    )
    max_duration_warning_seconds = float(
        _profile_value(
            profile,
            "max_duration_warning_seconds",
            DEFAULT_MAX_DURATION_WARNING_SECONDS,
        )
    )

    if not file_info.exists:
        _add_once(errors, "file_missing")

    if not file_info.is_supported_format:
        _add_once(errors, "unsupported_extension")

    if file_info.probe_status == "failed":
        _add_once(errors, "probe_failed")

    if file_info.probe_status == "missing":
        _add_once(errors, "file_missing")

    if file_info.exists and not file_info.has_video:
        _add_once(errors, "no_video_stream")

    if file_info.exists and not file_info.has_audio:
        if require_audio:
            _add_once(errors, "no_audio_stream")
        else:
            _add_once(warnings, "no_audio_stream")

    if file_info.duration_seconds is None:
        _add_once(warnings, "duration_unknown")
    elif file_info.duration_seconds <= 0:
        _add_once(errors, "invalid_duration")
    elif file_info.duration_seconds < min_duration_seconds:
        _add_once(errors, "duration_too_short")
    elif file_info.duration_seconds > max_duration_warning_seconds:
        _add_once(warnings, "very_long_file")

    if file_info.exists and file_info.has_video:
        if file_info.width is None or file_info.height is None:
            _add_once(warnings, "resolution_unknown")

        if file_info.fps is None:
            _add_once(warnings, "fps_unknown")

    if not errors:
        _add_once(reasons, "file_passed_acceptance_rules")

    return build_file_acceptance_result(
        file_info=file_info,
        reasons=reasons,
        warnings=warnings,
        errors=errors,
        profile=profile,
    )


def validate_file_path(
    path: str | Path,
    profile: dict[str, Any] | None = None,
) -> FileAcceptanceResult:
    file_info = probe_file(path)
    return validate_file_info(file_info=file_info, profile=profile)
