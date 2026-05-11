from __future__ import annotations

from typing import Any

from models.energy_peak_signal import EnergyPeakSignalAdapterResult

_PEAK_TYPE_TO_SIGNAL_TYPE: dict[str, str] = {
    "combined": "combined_energy_peak",
    "high_energy": "high_energy_peak",
    "local_maximum": "local_maximum_peak",
    "sudden_rise": "sudden_rise_peak",
}

_HIGH_ENERGY_SIGNAL_TYPES = {"combined_energy_peak", "high_energy_peak"}


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


def extract_peak_dicts(peaks_or_report: Any) -> list[dict[str, Any]]:
    """Normalise any peak-bearing input into a list of peak dicts."""
    if peaks_or_report is None:
        return []

    # 1. Plain list — list[EnergyPeak] or list[dict]
    if isinstance(peaks_or_report, list):
        result: list[dict[str, Any]] = []
        for item in peaks_or_report:
            try:
                if isinstance(item, dict):
                    result.append(item)
                elif hasattr(item, "to_dict"):
                    result.append(item.to_dict())
            except Exception:
                pass
        return result

    # 2. dict — might be EnergyPeakRunReport dict or EnergyPeakDetectionResult dict
    if isinstance(peaks_or_report, dict):
        raw = peaks_or_report.get("peaks", [])
        if isinstance(raw, list):
            return extract_peak_dicts(raw)
        return []

    # 3. Object with .peaks attribute (EnergyPeakDetectionResult, EnergyPeakRunReport, Job-like)
    peaks_attr = getattr(peaks_or_report, "peaks", None)
    if peaks_attr is not None:
        return extract_peak_dicts(peaks_attr)

    # 4. Job-like: energy_peaks attribute
    energy_peaks_attr = getattr(peaks_or_report, "energy_peaks", None)
    if energy_peaks_attr is not None:
        return extract_peak_dicts(energy_peaks_attr)

    # 5. Job-like: energy_peak_report dict attribute with "peaks"
    report_attr = getattr(peaks_or_report, "energy_peak_report", None)
    if isinstance(report_attr, dict):
        raw = report_attr.get("peaks", [])
        if isinstance(raw, list):
            return extract_peak_dicts(raw)

    return []


def energy_peak_to_signal(
    peak: Any,
    signal_window_before_seconds: float = 0.75,
    signal_window_after_seconds: float = 0.75,
    high_priority_threshold: float = 0.80,
) -> dict[str, Any]:
    """Convert a single peak (object or dict) to an edit-signal dict."""
    try:
        if isinstance(peak, dict):
            peak_type = str(peak.get("peak_type", "unknown"))
            start = _safe_float(peak.get("start_seconds"))
            end = _safe_float(peak.get("end_seconds"))
            center_raw = peak.get("center_seconds")
            energy_score = _safe_float(peak.get("energy_score"))
            peak_score_raw = peak.get("peak_score")
            confidence = _safe_float(peak.get("confidence"))
            reason = str(peak.get("reason", ""))
            source_index = peak.get("source_index")
            rules_applied: list[str] = list(peak.get("rules_applied") or [])
            source_peak: dict[str, Any] = dict(peak)
            extra_metadata: dict[str, Any] = dict(peak.get("metadata") or {})
        else:
            peak_type = str(getattr(peak, "peak_type", "unknown"))
            start = _safe_float(getattr(peak, "start_seconds", None))
            end = _safe_float(getattr(peak, "end_seconds", None))
            center_raw = getattr(peak, "center_seconds", None)
            energy_score = _safe_float(getattr(peak, "energy_score", None))
            peak_score_raw = getattr(peak, "peak_score", None)
            confidence = _safe_float(getattr(peak, "confidence", None))
            reason = str(getattr(peak, "reason", ""))
            source_index = getattr(peak, "source_index", None)
            rules_applied = list(getattr(peak, "rules_applied") or [])
            source_peak = peak.to_dict() if hasattr(peak, "to_dict") else {}
            extra_metadata = dict(getattr(peak, "metadata") or {})

        # Resolve center
        if center_raw is not None:
            try:
                center = float(center_raw)
            except (TypeError, ValueError):
                center = (start + end) / 2.0
        else:
            center = (start + end) / 2.0

        # Signal type mapping
        signal_type = _PEAK_TYPE_TO_SIGNAL_TYPE.get(peak_type, "energy_peak")

        # If rules_applied contains threshold_peak, allow high/combined to stay
        if "threshold_peak" in rules_applied and signal_type not in _HIGH_ENERGY_SIGNAL_TYPES:
            signal_type = "energy_peak"

        # Score
        if peak_score_raw is not None:
            try:
                signal_score = _clamp(float(peak_score_raw))
            except (TypeError, ValueError):
                signal_score = _clamp(energy_score)
        else:
            signal_score = _clamp(energy_score)

        # Priority
        if signal_score >= high_priority_threshold or confidence >= 0.85:
            priority = "high"
        elif signal_score >= 0.55:
            priority = "medium"
        else:
            priority = "low"

        # Recommended window
        recommended_start = max(0.0, center - signal_window_before_seconds)
        recommended_end = center + signal_window_after_seconds

        return {
            "signal_type": signal_type,
            "source": "energy_peak_signal_adapter",
            "source_peak_type": peak_type,
            "start_seconds": start,
            "end_seconds": end,
            "center_seconds": center,
            "recommended_start_seconds": recommended_start,
            "recommended_end_seconds": recommended_end,
            "energy_score": energy_score,
            "signal_score": signal_score,
            "confidence": confidence,
            "priority": priority,
            "reason": f"energy_peak_bridge:{signal_type}" if not reason else f"energy_peak_bridge:{reason}",
            "rules_applied": rules_applied,
            "source_index": source_index,
            "source_peak": source_peak,
            "metadata": extra_metadata,
        }

    except Exception:
        return {}


def adapt_energy_peaks_to_signals(
    peaks: Any,
    signal_window_before_seconds: float = 0.75,
    signal_window_after_seconds: float = 0.75,
    high_priority_threshold: float = 0.80,
    max_signals: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> EnergyPeakSignalAdapterResult:
    _meta: dict[str, Any] = dict(metadata or {})
    warnings: list[str] = []
    errors: list[str] = []

    try:
        peak_dicts = extract_peak_dicts(peaks)
        peak_count = len(peak_dicts)

        if peak_count == 0:
            warnings.append("no_energy_peaks_available")
            return EnergyPeakSignalAdapterResult(
                status="skipped_no_peaks",
                peak_count=0,
                warnings=warnings,
                errors=errors,
                recommendation="no_energy_peaks_available",
                metadata=_meta,
            )

        signals: list[dict[str, Any]] = []
        had_bad_peak = False

        for p in peak_dicts:
            sig = energy_peak_to_signal(
                p,
                signal_window_before_seconds=signal_window_before_seconds,
                signal_window_after_seconds=signal_window_after_seconds,
                high_priority_threshold=high_priority_threshold,
            )
            if not sig:
                had_bad_peak = True
                continue
            signals.append(sig)

        if had_bad_peak:
            warnings.append("some_peaks_could_not_be_converted")

        # Sort chronologically
        signals.sort(key=lambda s: s.get("center_seconds", 0.0))

        # Limit by max_signals — keep highest scoring, then re-sort chronologically
        if max_signals is not None and len(signals) > max_signals:
            signals.sort(key=lambda s: s.get("signal_score", 0.0), reverse=True)
            signals = signals[:max_signals]
            signals.sort(key=lambda s: s.get("center_seconds", 0.0))

        # Compute counts and stats
        signal_count = len(signals)
        high_priority_count = sum(1 for s in signals if s.get("priority") == "high")

        signal_types: dict[str, int] = {}
        for s in signals:
            st = str(s.get("signal_type", "unknown"))
            signal_types[st] = signal_types.get(st, 0) + 1

        scores = [s.get("signal_score", 0.0) for s in signals]
        max_signal_score = max(scores) if scores else 0.0
        avg_signal_score = sum(scores) / len(scores) if scores else 0.0

        if signal_count > 0 and not warnings and not errors:
            status = "ok"
            recommendation = "use_edit_signals"
        elif signal_count > 0:
            status = "completed_with_warnings"
            recommendation = "review_warnings"
        else:
            warnings.append("no_signals_produced")
            status = "completed_with_warnings"
            recommendation = "review_warnings"

        return EnergyPeakSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=signal_count,
            peak_count=peak_count,
            high_priority_signal_count=high_priority_count,
            signal_types=signal_types,
            max_signal_score=max_signal_score,
            avg_signal_score=avg_signal_score,
            warnings=warnings,
            errors=errors,
            recommendation=recommendation,
            metadata=_meta,
        )

    except Exception as exc:
        errors.append(f"energy_peak_signal_adapter_failed: {exc}")
        return EnergyPeakSignalAdapterResult(
            status="failed",
            warnings=warnings,
            errors=errors,
            recommendation="retry_or_fix_peak_data",
            metadata=_meta,
        )


def adapt_energy_peak_run_report_to_signals(
    energy_peak_report: Any,
    signal_window_before_seconds: float = 0.75,
    signal_window_after_seconds: float = 0.75,
    high_priority_threshold: float = 0.80,
    max_signals: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> EnergyPeakSignalAdapterResult:
    _meta: dict[str, Any] = dict(metadata or {})

    try:
        # Extract report-level metadata before delegating
        if isinstance(energy_peak_report, dict):
            report_status = str(energy_peak_report.get("status", ""))
            report_recommendation = str(energy_peak_report.get("recommendation", ""))
            report_peak_count = int(energy_peak_report.get("peak_count", 0))
        else:
            report_status = str(getattr(energy_peak_report, "status", ""))
            report_recommendation = str(getattr(energy_peak_report, "recommendation", ""))
            report_peak_count = int(getattr(energy_peak_report, "peak_count", 0))

        result = adapt_energy_peaks_to_signals(
            energy_peak_report,
            signal_window_before_seconds=signal_window_before_seconds,
            signal_window_after_seconds=signal_window_after_seconds,
            high_priority_threshold=high_priority_threshold,
            max_signals=max_signals,
            metadata=metadata,
        )

        result.metadata["energy_peak_status"] = report_status
        result.metadata["energy_peak_recommendation"] = report_recommendation
        result.metadata["peak_count"] = report_peak_count

        return result

    except Exception as exc:
        return EnergyPeakSignalAdapterResult(
            status="failed",
            errors=[f"adapt_energy_peak_run_report_failed: {exc}"],
            recommendation="retry_or_fix_peak_data",
            metadata=_meta,
        )
