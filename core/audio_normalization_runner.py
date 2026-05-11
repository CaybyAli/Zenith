from __future__ import annotations

import pathlib
from typing import Any

from core.audio_normalization_analyzer import analyze_wav_audio_normalization
from core.audio_normalization_source_selector import (
    select_audio_normalization_source,
    select_audio_normalization_source_for_job,
)
from models.audio_normalization_run import AudioNormalizationRunReport

# Maps analyzer-level recommendations to runner-level vocabulary.
_REC_MAP: dict[str, str] = {
    "apply_gain": "use_normalization_plan",
    "reduce_gain": "use_normalization_plan",
    "no_normalization_needed": "no_normalization_needed",
    "fix_clipping": "review_warnings",
    "audio_silent": "review_warnings",
    "retry_or_fix_audio": "retry_or_fix_audio",
}


def _normalize_selection(source_selection: Any) -> dict[str, Any]:
    if isinstance(source_selection, dict):
        return source_selection
    try:
        d = source_selection.to_dict()
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    try:
        return dict(vars(source_selection))
    except Exception:
        return {}


def build_audio_normalization_run_report(
    preprocessing_manifest: Any | None = None,
    original_source_path: str | None = None,
    source_selection: Any | None = None,
    target_rms_dbfs: float = -18.0,
    target_peak_dbfs: float = -1.0,
    require_existing_file: bool = True,
    allow_original_wav_fallback: bool = True,
    metadata: dict[str, Any] | None = None,
) -> AudioNormalizationRunReport:
    meta = metadata or {}

    try:
        if source_selection is not None:
            sel_dict = _normalize_selection(source_selection)
        else:
            sel = select_audio_normalization_source(
                preprocessing_manifest=preprocessing_manifest,
                original_source_path=original_source_path,
                require_existing_file=require_existing_file,
                allow_original_wav_fallback=allow_original_wav_fallback,
                metadata=meta,
            )
            sel_dict = sel.to_dict()

        sel_status = str(sel_dict.get("status", "unavailable"))
        sel_path = sel_dict.get("selected_path")
        sel_type = sel_dict.get("selected_type")
        sel_warnings: list[str] = list(sel_dict.get("warnings") or [])
        sel_errors: list[str] = list(sel_dict.get("errors") or [])

        # ── selected or selected_fallback ─────────────────────────────────────
        if sel_status in ("selected", "selected_fallback"):
            if (
                sel_path
                and isinstance(sel_path, str)
                and sel_path.lower().endswith(".wav")
                and pathlib.Path(sel_path).exists()
            ):
                analyzer_result = analyze_wav_audio_normalization(
                    sel_path,
                    target_rms_dbfs=target_rms_dbfs,
                    target_peak_dbfs=target_peak_dbfs,
                    metadata=meta,
                )

                stats = analyzer_result.stats
                all_warnings = sel_warnings + list(analyzer_result.warnings)
                all_errors = sel_errors + list(analyzer_result.errors)

                if analyzer_result.status == "failed":
                    runner_status = "failed"
                    runner_rec = "retry_or_fix_audio"
                elif all_warnings:
                    runner_status = "completed_with_warnings"
                    runner_rec = "review_warnings"
                else:
                    runner_status = "ok"
                    runner_rec = _REC_MAP.get(
                        analyzer_result.recommendation,
                        analyzer_result.recommendation,
                    )

                return AudioNormalizationRunReport(
                    status=runner_status,
                    source_selection=sel_dict,
                    selected_path=sel_path,
                    selected_type=sel_type,
                    normalization_result=analyzer_result.to_dict(),
                    level_status=analyzer_result.level_status,
                    normalization_needed=analyzer_result.normalization_needed,
                    recommendation=runner_rec,
                    target_rms_dbfs=target_rms_dbfs,
                    target_peak_dbfs=target_peak_dbfs,
                    recommended_gain_db=analyzer_result.recommended_gain_db,
                    limited_gain_db=analyzer_result.limited_gain_db,
                    gain_limited_by_peak=analyzer_result.gain_limited_by_peak,
                    would_clip_after_gain=analyzer_result.would_clip_after_gain,
                    peak_dbfs=stats.peak_dbfs,
                    rms_dbfs=stats.rms_dbfs,
                    peak_amplitude=stats.peak_amplitude,
                    rms=stats.rms,
                    clipping_sample_count=stats.clipping_sample_count,
                    clipping_ratio=stats.clipping_ratio,
                    sample_count=stats.sample_count,
                    duration_seconds=stats.duration_seconds,
                    sample_rate=stats.sample_rate,
                    channels=stats.channels,
                    warnings=all_warnings,
                    errors=all_errors,
                    metadata=meta,
                )

            # Stale selection: file disappeared or path is not WAV
            reason = "selected_path_not_wav" if sel_path and not sel_path.lower().endswith(".wav") else "selected_wav_file_missing"
            return AudioNormalizationRunReport(
                status="failed",
                source_selection=sel_dict,
                selected_path=sel_path,
                selected_type=sel_type,
                recommendation="retry_or_fix_audio",
                warnings=sel_warnings,
                errors=sel_errors + [reason],
                metadata=meta,
            )

        # ── missing preprocessed audio ────────────────────────────────────────
        if sel_status == "missing_preprocessed_audio":
            return AudioNormalizationRunReport(
                status="blocked_missing_preprocessed_audio",
                source_selection=sel_dict,
                selected_path=sel_path,
                selected_type=sel_type,
                recommendation="generate_preprocessed_audio",
                warnings=sel_warnings,
                errors=sel_errors,
                metadata=meta,
            )

        # ── unsupported source (MP4/MKV/MOV/…) ───────────────────────────────
        if sel_status == "skipped_unsupported_source":
            return AudioNormalizationRunReport(
                status="skipped_unsupported_source",
                source_selection=sel_dict,
                selected_path=sel_path,
                selected_type=sel_type,
                recommendation="extract_audio_first",
                warnings=sel_warnings,
                errors=sel_errors,
                metadata=meta,
            )

        # ── no source available ───────────────────────────────────────────────
        if sel_status == "unavailable":
            return AudioNormalizationRunReport(
                status="skipped_no_audio_source",
                source_selection=sel_dict,
                recommendation="no_audio_source_available",
                warnings=sel_warnings,
                errors=sel_errors,
                metadata=meta,
            )

        # ── unexpected selection status ───────────────────────────────────────
        return AudioNormalizationRunReport(
            status="failed",
            source_selection=sel_dict,
            selected_path=sel_path,
            selected_type=sel_type,
            recommendation="retry_or_fix_audio",
            warnings=sel_warnings,
            errors=sel_errors + [f"unexpected_selection_status_{sel_status}"],
            metadata=meta,
        )

    except Exception as exc:
        return AudioNormalizationRunReport(
            status="failed",
            recommendation="retry_or_fix_audio",
            errors=[f"audio_normalization_runner_failed: {exc}"],
            metadata=meta,
        )


def run_audio_normalization_for_job(
    job: Any,
    source_selection: Any | None = None,
    target_rms_dbfs: float = -18.0,
    target_peak_dbfs: float = -1.0,
    require_existing_file: bool = True,
    allow_original_wav_fallback: bool = True,
    metadata: dict[str, Any] | None = None,
) -> AudioNormalizationRunReport:
    meta = metadata or {}
    try:
        if source_selection is not None:
            return build_audio_normalization_run_report(
                source_selection=source_selection,
                target_rms_dbfs=target_rms_dbfs,
                target_peak_dbfs=target_peak_dbfs,
                metadata=meta,
            )

        sel = select_audio_normalization_source_for_job(
            job=job,
            require_existing_file=require_existing_file,
            allow_original_wav_fallback=allow_original_wav_fallback,
            metadata=meta,
        )

        return build_audio_normalization_run_report(
            source_selection=sel,
            target_rms_dbfs=target_rms_dbfs,
            target_peak_dbfs=target_peak_dbfs,
            metadata=meta,
        )

    except Exception as exc:
        return AudioNormalizationRunReport(
            status="failed",
            recommendation="retry_or_fix_audio",
            errors=[f"audio_normalization_runner_failed: {exc}"],
            metadata=meta,
        )
