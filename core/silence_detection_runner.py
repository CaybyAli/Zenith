from __future__ import annotations

from typing import Any

from core.silence_audio_source_selector import (
    select_silence_audio_source,
    select_silence_audio_source_for_job,
)
from core.silence_detector import detect_silence
from core.silence_parameter_resolver import resolve_silence_detection_parameters
from models.silence_detection_run import SilenceDetectionRunReport

_JOB_FALLBACK_FIELDS: list[str] = [
    "raw_video_path",
    "input_file",
    "source_file",
    "video_path",
    "file_path",
]


def _safe_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    return [value]


def build_silence_detection_run_report(
    preprocessing_manifest: dict[str, Any] | None = None,
    fallback_source_path: str | None = None,
    profile: dict[str, Any] | None = None,
    job: Any | None = None,
    overrides: dict[str, Any] | None = None,
) -> SilenceDetectionRunReport:
    try:
        params = resolve_silence_detection_parameters(
            profile=profile,
            job=job,
            overrides=overrides,
        )
    except Exception as exc:
        return SilenceDetectionRunReport(
            status="failed",
            source_path=None,
            source_type=None,
            threshold_db=None,
            min_duration_seconds=None,
            require_existing_audio=True,
            audio_source_selection={},
            parameters={},
            detection_result={},
            segment_count=0,
            total_silence_seconds=0.0,
            warnings=[],
            errors=[f"parameter_resolver_exception: {exc}"],
            recommendation="retry_or_fix_source",
        )

    try:
        selection = select_silence_audio_source(
            preprocessing_manifest=preprocessing_manifest,
            fallback_source_path=fallback_source_path,
            require_existing_file=params.require_existing_audio,
        )
    except Exception as exc:
        return SilenceDetectionRunReport(
            status="failed",
            source_path=None,
            source_type=None,
            threshold_db=params.threshold_db,
            min_duration_seconds=params.min_duration_seconds,
            require_existing_audio=params.require_existing_audio,
            audio_source_selection={},
            parameters=params.to_dict(),
            detection_result={},
            segment_count=0,
            total_silence_seconds=0.0,
            warnings=list(params.warnings),
            errors=list(params.errors) + [f"audio_source_selector_exception: {exc}"],
            recommendation="retry_or_fix_source",
        )

    base_warnings: list[str] = list(params.warnings) + _safe_list(selection.warnings)
    base_errors: list[str] = list(params.errors) + _safe_list(selection.errors)

    if selection.status == "missing_preprocessed_audio":
        return SilenceDetectionRunReport(
            status="blocked",
            source_path=selection.selected_path,
            source_type=selection.source_type,
            threshold_db=params.threshold_db,
            min_duration_seconds=params.min_duration_seconds,
            require_existing_audio=params.require_existing_audio,
            audio_source_selection=selection.to_dict(),
            parameters=params.to_dict(),
            detection_result={},
            segment_count=0,
            total_silence_seconds=0.0,
            warnings=base_warnings,
            errors=base_errors,
            recommendation="extract_audio_first",
        )

    if not selection.selected_path or not selection.exists:
        return SilenceDetectionRunReport(
            status="skipped_no_audio_source",
            source_path=selection.selected_path,
            source_type=selection.source_type,
            threshold_db=params.threshold_db,
            min_duration_seconds=params.min_duration_seconds,
            require_existing_audio=params.require_existing_audio,
            audio_source_selection=selection.to_dict(),
            parameters=params.to_dict(),
            detection_result={},
            segment_count=0,
            total_silence_seconds=0.0,
            warnings=base_warnings,
            errors=base_errors,
            recommendation=selection.recommendation or "select_audio_source",
        )

    try:
        detection = detect_silence(
            source_path=selection.selected_path,
            threshold_db=params.threshold_db,
            min_duration_seconds=params.min_duration_seconds,
        )
    except Exception as exc:
        return SilenceDetectionRunReport(
            status="failed",
            source_path=selection.selected_path,
            source_type=selection.source_type,
            threshold_db=params.threshold_db,
            min_duration_seconds=params.min_duration_seconds,
            require_existing_audio=params.require_existing_audio,
            audio_source_selection=selection.to_dict(),
            parameters=params.to_dict(),
            detection_result={},
            segment_count=0,
            total_silence_seconds=0.0,
            warnings=base_warnings,
            errors=base_errors + [f"silence_detection_exception: {exc}"],
            recommendation="retry_or_fix_source",
        )

    detection_dict = detection.to_dict() if hasattr(detection, "to_dict") else {}
    detection_warnings = _safe_list(getattr(detection, "warnings", []))
    detection_errors = _safe_list(getattr(detection, "errors", []))

    combined_warnings = base_warnings + detection_warnings
    combined_errors = base_errors + detection_errors

    if getattr(detection, "status", "") == "ok":
        return SilenceDetectionRunReport(
            status="ok",
            source_path=selection.selected_path,
            source_type=selection.source_type,
            threshold_db=params.threshold_db,
            min_duration_seconds=params.min_duration_seconds,
            require_existing_audio=params.require_existing_audio,
            audio_source_selection=selection.to_dict(),
            parameters=params.to_dict(),
            detection_result=detection_dict,
            segment_count=int(getattr(detection, "segment_count", 0) or 0),
            total_silence_seconds=float(getattr(detection, "total_silence_seconds", 0.0) or 0.0),
            warnings=combined_warnings,
            errors=combined_errors,
            recommendation="use_result",
        )

    return SilenceDetectionRunReport(
        status="failed",
        source_path=selection.selected_path,
        source_type=selection.source_type,
        threshold_db=params.threshold_db,
        min_duration_seconds=params.min_duration_seconds,
        require_existing_audio=params.require_existing_audio,
        audio_source_selection=selection.to_dict(),
        parameters=params.to_dict(),
        detection_result=detection_dict,
        segment_count=0,
        total_silence_seconds=0.0,
        warnings=combined_warnings,
        errors=combined_errors,
        recommendation="retry_or_fix_source",
    )


def run_silence_detection_for_job(
    job: Any,
    profile: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> SilenceDetectionRunReport:
    manifest: dict[str, Any] | None = None
    raw_manifest = getattr(job, "preprocessing_manifest", None)
    if isinstance(raw_manifest, dict) and raw_manifest:
        manifest = raw_manifest

    fallback: str | None = None
    for field_name in _JOB_FALLBACK_FIELDS:
        try:
            val = getattr(job, field_name, None)
        except Exception:
            val = None
        if val and isinstance(val, str):
            fallback = val
            break

    return build_silence_detection_run_report(
        preprocessing_manifest=manifest,
        fallback_source_path=fallback,
        profile=profile,
        job=job,
        overrides=overrides,
    )
