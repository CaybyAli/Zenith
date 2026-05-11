from __future__ import annotations

from typing import Any

from core.rms_energy_analyzer import analyze_wav_rms_energy
from core.rms_energy_audio_source_selector import (
    select_rms_energy_audio_source,
    select_rms_energy_audio_source_for_job,
)
from models.rms_energy_run import RmsEnergyRunReport

_JOB_FALLBACK_FIELDS: list[str] = [
    "raw_video_path",
    "input_file",
    "source_file",
    "video_path",
    "file_path",
]


def build_rms_energy_run_report(
    preprocessing_manifest: dict[str, Any] | None = None,
    fallback_source_path: str | None = None,
    require_existing_file: bool = True,
    allow_original_wav_fallback: bool = True,
    frame_ms: float = 10.0,
    hop_ms: float = 5.0,
    silence_rms_threshold: float = 0.001,
    metadata: dict[str, Any] | None = None,
) -> RmsEnergyRunReport:
    _meta = dict(metadata or {})
    try:
        selection = select_rms_energy_audio_source(
            preprocessing_manifest=preprocessing_manifest,
            fallback_source_path=fallback_source_path,
            require_existing_file=require_existing_file,
            allow_original_wav_fallback=allow_original_wav_fallback,
        )
    except Exception as exc:
        return RmsEnergyRunReport(
            status="failed",
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            errors=["rms_energy_runner_failed"],
            recommendation="retry_or_fix_audio",
            metadata=_meta,
        )

    sel_status = selection.status

    # --- Blocked: preprocessed audio not yet generated ---
    if sel_status == "missing_preprocessed_audio":
        return RmsEnergyRunReport(
            status="blocked_missing_preprocessed_audio",
            source_selection=selection.to_dict(),
            selected_path=selection.selected_path,
            selected_type=selection.selected_type,
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            warnings=list(selection.warnings),
            errors=list(selection.errors),
            recommendation="generate_preprocessed_audio",
            metadata=_meta,
        )

    # --- Skipped: video source that needs audio extraction first ---
    if sel_status == "unsupported_original_source":
        return RmsEnergyRunReport(
            status="skipped_unsupported_source",
            source_selection=selection.to_dict(),
            selected_path=selection.selected_path,
            selected_type=selection.selected_type,
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            warnings=list(selection.warnings),
            errors=list(selection.errors),
            recommendation="extract_audio_first",
            metadata=_meta,
        )

    # --- Failed: no audio source at all ---
    if sel_status == "unavailable":
        return RmsEnergyRunReport(
            status="failed",
            source_selection=selection.to_dict(),
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            warnings=list(selection.warnings),
            errors=list(selection.errors),
            recommendation="no_audio_source_available",
            metadata=_meta,
        )

    # --- Guard: selected/selected_fallback but source is unusable ---
    can_analyze = (
        sel_status in ("selected", "selected_fallback")
        and bool(selection.selected_path)
        and selection.exists
        and selection.is_wav
    )

    if not can_analyze:
        return RmsEnergyRunReport(
            status="failed",
            source_selection=selection.to_dict(),
            selected_path=selection.selected_path,
            selected_type=selection.selected_type,
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            warnings=list(selection.warnings),
            errors=list(selection.errors) + ["invalid_rms_audio_source_selection"],
            recommendation="retry_or_fix_audio",
            metadata=_meta,
        )

    # --- Run the analyzer ---
    try:
        timeline = analyze_wav_rms_energy(
            selection.selected_path,  # type: ignore[arg-type]
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            silence_rms_threshold=silence_rms_threshold,
        )
    except Exception:
        return RmsEnergyRunReport(
            status="failed",
            source_selection=selection.to_dict(),
            selected_path=selection.selected_path,
            selected_type=selection.selected_type,
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            warnings=list(selection.warnings),
            errors=list(selection.errors) + ["rms_energy_runner_failed"],
            recommendation="retry_or_fix_audio",
            metadata=_meta,
        )

    combined_warnings = list(selection.warnings) + list(timeline.warnings)
    combined_errors = list(selection.errors) + list(timeline.errors)

    if timeline.status == "ok":
        report_status = "ok"
        recommendation = "use_energy_timeline"
    elif timeline.status == "completed_with_warnings":
        report_status = "completed_with_warnings"
        recommendation = "review_warnings"
    else:
        report_status = "failed"
        recommendation = "retry_or_fix_audio"

    return RmsEnergyRunReport(
        status=report_status,
        source_selection=selection.to_dict(),
        energy_timeline_result=timeline.to_dict(),
        selected_path=selection.selected_path,
        selected_type=selection.selected_type,
        timeline_status=timeline.status,
        point_count=timeline.point_count,
        duration_seconds=timeline.duration_seconds,
        sample_rate=timeline.sample_rate,
        channels=timeline.channels,
        frame_ms=timeline.frame_ms,
        hop_ms=timeline.hop_ms,
        min_rms=timeline.min_rms,
        max_rms=timeline.max_rms,
        avg_rms=timeline.avg_rms,
        min_normalized_energy=timeline.min_normalized_energy,
        max_normalized_energy=timeline.max_normalized_energy,
        avg_normalized_energy=timeline.avg_normalized_energy,
        warnings=combined_warnings,
        errors=combined_errors,
        recommendation=recommendation,
        metadata=_meta,
    )


def run_rms_energy_for_job(
    job: Any,
    require_existing_file: bool = True,
    allow_original_wav_fallback: bool = True,
    frame_ms: float = 10.0,
    hop_ms: float = 5.0,
    silence_rms_threshold: float = 0.001,
    metadata: dict[str, Any] | None = None,
) -> RmsEnergyRunReport:
    manifest: dict[str, Any] | None = None
    try:
        raw_manifest = getattr(job, "preprocessing_manifest", None)
        if isinstance(raw_manifest, dict) and raw_manifest:
            manifest = raw_manifest
    except Exception:
        pass

    fallback: str | None = None
    for field_name in _JOB_FALLBACK_FIELDS:
        try:
            val = getattr(job, field_name, None)
            if val and isinstance(val, str):
                fallback = val
                break
        except Exception:
            pass

    return build_rms_energy_run_report(
        preprocessing_manifest=manifest,
        fallback_source_path=fallback,
        require_existing_file=require_existing_file,
        allow_original_wav_fallback=allow_original_wav_fallback,
        frame_ms=frame_ms,
        hop_ms=hop_ms,
        silence_rms_threshold=silence_rms_threshold,
        metadata=metadata,
    )
