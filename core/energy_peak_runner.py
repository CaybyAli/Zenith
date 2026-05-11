from __future__ import annotations

from typing import Any

from core.energy_peak_detector import detect_energy_peaks
from core.rms_energy_context_adapter import adapt_rms_energy_run_report_to_context
from models.energy_peak_run import EnergyPeakRunReport


def _is_non_empty_list(val: Any) -> bool:
    return isinstance(val, list) and len(val) > 0


def build_energy_peak_run_report(
    energy_timeline: Any | None = None,
    rms_run_report: Any | None = None,
    peak_threshold: float = 0.85,
    rise_threshold: float = 0.25,
    min_peak_distance_seconds: float = 0.4,
    local_window_size: int = 1,
    max_peaks: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> EnergyPeakRunReport:
    _meta = dict(metadata or {})
    warnings: list[str] = []
    errors: list[str] = []
    rms_context_adapter_result: dict[str, Any] = {}
    energy_timeline_source: str | None = None
    resolved_timeline: Any = None

    try:
        # --- A) Direct energy_timeline provided ---
        if energy_timeline is not None:
            resolved_timeline = energy_timeline
            energy_timeline_source = "provided_energy_timeline"

        # --- B) Adapt from rms_run_report ---
        elif rms_run_report is not None:
            try:
                adapter_result = adapt_rms_energy_run_report_to_context(rms_run_report)
                rms_context_adapter_result = adapter_result.to_dict()
                warnings.extend(adapter_result.warnings)
                errors.extend(adapter_result.errors)
                resolved_timeline = adapter_result.energy_timeline
                energy_timeline_source = "rms_run_report_adapter"
            except Exception as exc:
                errors.append(f"rms_adapter_failed: {exc}")
                return EnergyPeakRunReport(
                    status="failed",
                    energy_timeline_source="rms_run_report_adapter",
                    peak_threshold=peak_threshold,
                    rise_threshold=rise_threshold,
                    min_peak_distance_seconds=min_peak_distance_seconds,
                    rms_context_adapter_result=rms_context_adapter_result,
                    warnings=warnings,
                    errors=errors,
                    recommendation="retry_or_fix_energy_timeline",
                    metadata=_meta,
                )

        # --- C) Nothing provided ---
        else:
            warnings.append("no_energy_timeline_available")
            return EnergyPeakRunReport(
                status="skipped_no_energy_timeline",
                peak_threshold=peak_threshold,
                rise_threshold=rise_threshold,
                min_peak_distance_seconds=min_peak_distance_seconds,
                warnings=warnings,
                errors=errors,
                recommendation="no_energy_timeline_available",
                metadata=_meta,
            )

        # --- Guard: empty timeline ---
        is_empty = (
            resolved_timeline is None
            or (isinstance(resolved_timeline, list) and len(resolved_timeline) == 0)
        )
        if is_empty:
            warnings.append("empty_energy_timeline")
            return EnergyPeakRunReport(
                status="skipped_no_energy_timeline",
                energy_timeline_source=energy_timeline_source,
                energy_timeline=[],
                peak_threshold=peak_threshold,
                rise_threshold=rise_threshold,
                min_peak_distance_seconds=min_peak_distance_seconds,
                rms_context_adapter_result=rms_context_adapter_result,
                warnings=warnings,
                errors=errors,
                recommendation="no_energy_timeline_available",
                metadata=_meta,
            )

        # --- Run peak detection ---
        peak_result = detect_energy_peaks(
            resolved_timeline,
            peak_threshold=peak_threshold,
            rise_threshold=rise_threshold,
            min_peak_distance_seconds=min_peak_distance_seconds,
            local_window_size=local_window_size,
            max_peaks=max_peaks,
        )

        warnings.extend(peak_result.warnings)
        errors.extend(peak_result.errors)

        peaks_as_dicts = [p.to_dict() for p in peak_result.peaks]
        peak_count = peak_result.peak_count

        # Scores
        peak_scores = [p.peak_score for p in peak_result.peaks]
        max_peak_score = max(peak_scores) if peak_scores else 0.0
        avg_peak_score = sum(peak_scores) / len(peak_scores) if peak_scores else 0.0

        # Top peak by peak_score
        top_peak: dict[str, Any] = {}
        if peak_result.peaks:
            best = max(peak_result.peaks, key=lambda p: p.peak_score)
            top_peak = best.to_dict()

        # Store the energy_timeline we used (list form)
        used_timeline: list[dict[str, Any]] = []
        if isinstance(resolved_timeline, list):
            used_timeline = [item for item in resolved_timeline if isinstance(item, dict)]

        # --- Status and recommendation ---
        if peak_result.status == "failed":
            status = "failed"
            recommendation = "retry_or_fix_energy_timeline"
        elif peak_count > 0 and not warnings and not errors:
            status = "ok"
            recommendation = "use_energy_peaks"
        elif peak_count > 0:
            status = "completed_with_warnings"
            recommendation = "review_warnings"
        else:
            warnings.append("no_energy_peaks_detected")
            status = "completed_with_warnings"
            recommendation = "no_peaks_detected"

        return EnergyPeakRunReport(
            status=status,
            energy_timeline_source=energy_timeline_source,
            energy_timeline=used_timeline,
            peak_detection_result=peak_result.to_dict(),
            peaks=peaks_as_dicts,
            peak_count=peak_count,
            high_energy_peak_count=peak_result.high_energy_peak_count,
            local_max_peak_count=peak_result.local_max_peak_count,
            rise_peak_count=peak_result.rise_peak_count,
            threshold_peak_count=peak_result.threshold_peak_count,
            peak_threshold=peak_threshold,
            rise_threshold=rise_threshold,
            min_peak_distance_seconds=min_peak_distance_seconds,
            max_peak_score=max_peak_score,
            avg_peak_score=avg_peak_score,
            top_peak=top_peak,
            rms_context_adapter_result=rms_context_adapter_result,
            warnings=warnings,
            errors=errors,
            recommendation=recommendation,
            metadata=_meta,
        )

    except Exception as exc:
        errors.append(f"energy_peak_runner_failed: {exc}")
        return EnergyPeakRunReport(
            status="failed",
            energy_timeline_source=energy_timeline_source,
            peak_threshold=peak_threshold,
            rise_threshold=rise_threshold,
            min_peak_distance_seconds=min_peak_distance_seconds,
            rms_context_adapter_result=rms_context_adapter_result,
            warnings=warnings,
            errors=errors,
            recommendation="retry_or_fix_energy_timeline",
            metadata=_meta,
        )


def run_energy_peak_detection_for_job(
    job: Any,
    energy_timeline: Any | None = None,
    rms_run_report: Any | None = None,
    peak_threshold: float = 0.85,
    rise_threshold: float = 0.25,
    min_peak_distance_seconds: float = 0.4,
    local_window_size: int = 1,
    max_peaks: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> EnergyPeakRunReport:
    resolved_timeline: Any = None
    resolved_rms_run_report: Any = rms_run_report

    try:
        # 1. Direct energy_timeline argument wins
        if energy_timeline is not None:
            resolved_timeline = energy_timeline

        else:
            # 2. job.rms_energy_context_timeline
            try:
                ctx_timeline = getattr(job, "rms_energy_context_timeline", None)
                if _is_non_empty_list(ctx_timeline):
                    resolved_timeline = ctx_timeline
            except Exception:
                pass

            # 3. job.energy_timeline
            if resolved_timeline is None:
                try:
                    et = getattr(job, "energy_timeline", None)
                    if _is_non_empty_list(et):
                        resolved_timeline = et
                except Exception:
                    pass

            # 4. job.rms_energy_context_adapter["energy_timeline"]
            if resolved_timeline is None:
                try:
                    adapter_dict = getattr(job, "rms_energy_context_adapter", None)
                    if isinstance(adapter_dict, dict):
                        candidate = adapter_dict.get("energy_timeline")
                        if _is_non_empty_list(candidate):
                            resolved_timeline = candidate
                except Exception:
                    pass

            # 5. Fallback to rms_run_report from job
            if resolved_timeline is None and resolved_rms_run_report is None:
                try:
                    rr = getattr(job, "rms_energy_report", None)
                    if rr is not None:
                        resolved_rms_run_report = rr
                except Exception:
                    pass

            if resolved_timeline is None and resolved_rms_run_report is None:
                try:
                    rr = getattr(job, "rms_energy_run_report", None)
                    if rr is not None:
                        resolved_rms_run_report = rr
                except Exception:
                    pass

    except Exception:
        pass

    return build_energy_peak_run_report(
        energy_timeline=resolved_timeline,
        rms_run_report=resolved_rms_run_report,
        peak_threshold=peak_threshold,
        rise_threshold=rise_threshold,
        min_peak_distance_seconds=min_peak_distance_seconds,
        local_window_size=local_window_size,
        max_peaks=max_peaks,
        metadata=metadata,
    )
