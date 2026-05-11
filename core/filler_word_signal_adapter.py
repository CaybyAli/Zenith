from __future__ import annotations

from typing import Any

from models.filler_word_signal import FillerWordSignalAdapterResult

_FILLER_TYPE_TO_SIGNAL_TYPE: dict[str, str] = {
    "hesitation": "hesitation_filler",
    "discourse_marker": "discourse_marker_filler",
    "phrase_filler": "phrase_filler",
    "repeated_word": "repeated_word_filler",
    "unknown": "filler_word_cut_candidate",
}


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


def extract_filler_occurrence_dicts(occurrences_or_report: Any) -> list[dict[str, Any]]:
    """Normalise any filler-bearing input into a list of occurrence dicts."""
    if occurrences_or_report is None:
        return []

    # 1. Plain list — list[FillerWordOccurrence] or list[dict]
    if isinstance(occurrences_or_report, list):
        result: list[dict[str, Any]] = []
        for item in occurrences_or_report:
            try:
                if isinstance(item, dict):
                    result.append(dict(item))
                elif hasattr(item, "to_dict"):
                    result.append(item.to_dict())
            except Exception:
                pass
        return result

    # 2. dict — might be FillerWordRunReport dict or FillerWordDetectionResult dict
    if isinstance(occurrences_or_report, dict):
        raw = occurrences_or_report.get("occurrences", [])
        if isinstance(raw, list):
            return extract_filler_occurrence_dicts(raw)
        return []

    # 3. Object with .occurrences attribute
    occ_attr = getattr(occurrences_or_report, "occurrences", None)
    if occ_attr is not None:
        return extract_filler_occurrence_dicts(occ_attr)

    # 4. Job-like: filler_word_occurrences attribute
    fw_occ_attr = getattr(occurrences_or_report, "filler_word_occurrences", None)
    if fw_occ_attr is not None:
        return extract_filler_occurrence_dicts(fw_occ_attr)

    # 5. Job-like: filler_word_report dict attribute with "occurrences"
    fw_report_attr = getattr(occurrences_or_report, "filler_word_report", None)
    if isinstance(fw_report_attr, dict):
        raw = fw_report_attr.get("occurrences", [])
        if isinstance(raw, list):
            return extract_filler_occurrence_dicts(raw)

    # 6. Job-like: filler_word_detection_result dict attribute with "occurrences"
    fw_det_attr = getattr(occurrences_or_report, "filler_word_detection_result", None)
    if isinstance(fw_det_attr, dict):
        raw = fw_det_attr.get("occurrences", [])
        if isinstance(raw, list):
            return extract_filler_occurrence_dicts(raw)

    return []


def filler_occurrence_to_signal(
    occurrence: Any,
    signal_window_before_seconds: float = 0.15,
    signal_window_after_seconds: float = 0.15,
    high_priority_threshold: float = 0.80,
) -> dict[str, Any]:
    """Convert a single filler occurrence (object or dict) to an edit-signal dict."""
    try:
        if isinstance(occurrence, dict):
            text = str(occurrence.get("text", ""))
            normalized_text = str(occurrence.get("normalized_text", ""))
            filler_type = str(occurrence.get("filler_type", "unknown"))
            language = str(occurrence.get("language", "unknown"))
            start_raw = occurrence.get("start_seconds")
            end_raw = occurrence.get("end_seconds")
            center_raw = occurrence.get("center_seconds")
            duration_raw = occurrence.get("duration_seconds")
            confidence = _safe_float(occurrence.get("confidence"), 0.75)
            remove_candidate = bool(occurrence.get("remove_candidate", True))
            reason = str(occurrence.get("reason", ""))
            source_segment_index = occurrence.get("source_segment_index")
            source_word_index = occurrence.get("source_word_index")
            source_occurrence: dict[str, Any] = dict(occurrence)
            extra_metadata: dict[str, Any] = dict(occurrence.get("metadata") or {})
        else:
            text = str(getattr(occurrence, "text", ""))
            normalized_text = str(getattr(occurrence, "normalized_text", ""))
            filler_type = str(getattr(occurrence, "filler_type", "unknown"))
            language = str(getattr(occurrence, "language", "unknown"))
            start_raw = getattr(occurrence, "start_seconds", None)
            end_raw = getattr(occurrence, "end_seconds", None)
            center_raw = getattr(occurrence, "center_seconds", None)
            duration_raw = getattr(occurrence, "duration_seconds", None)
            confidence = _safe_float(getattr(occurrence, "confidence", 0.75), 0.75)
            remove_candidate = bool(getattr(occurrence, "remove_candidate", True))
            reason = str(getattr(occurrence, "reason", ""))
            source_segment_index = getattr(occurrence, "source_segment_index", None)
            source_word_index = getattr(occurrence, "source_word_index", None)
            source_occurrence = (
                occurrence.to_dict() if hasattr(occurrence, "to_dict") else {}
            )
            extra_metadata = dict(getattr(occurrence, "metadata") or {})

        # Validate: if no readable text or type info, return empty
        if not text and not normalized_text and filler_type == "unknown":
            return {}

        # Resolve timing
        start_seconds: float | None = None
        end_seconds: float | None = None
        center_seconds: float | None = None
        duration_seconds: float | None = None

        if start_raw is not None:
            try:
                start_seconds = float(start_raw)
            except (TypeError, ValueError):
                pass

        if end_raw is not None:
            try:
                end_seconds = float(end_raw)
            except (TypeError, ValueError):
                pass

        if center_raw is not None:
            try:
                center_seconds = float(center_raw)
            except (TypeError, ValueError):
                pass

        if duration_raw is not None:
            try:
                duration_seconds = float(duration_raw)
            except (TypeError, ValueError):
                pass

        # Derive center if missing
        if center_seconds is None and start_seconds is not None and end_seconds is not None:
            center_seconds = (start_seconds + end_seconds) / 2.0

        # Derive duration if missing
        if duration_seconds is None and start_seconds is not None and end_seconds is not None:
            duration_seconds = max(0.0, end_seconds - start_seconds)

        # Recommended window
        if start_seconds is not None and end_seconds is not None:
            recommended_start = max(0.0, start_seconds - signal_window_before_seconds)
            recommended_end = end_seconds + signal_window_after_seconds
        elif center_seconds is not None:
            recommended_start = max(0.0, center_seconds - signal_window_before_seconds)
            recommended_end = center_seconds + signal_window_after_seconds
        else:
            recommended_start = None
            recommended_end = None

        # Signal type mapping
        signal_type = _FILLER_TYPE_TO_SIGNAL_TYPE.get(filler_type, "filler_word_cut_candidate")

        # Score
        signal_score = confidence
        if remove_candidate:
            signal_score += 0.05
        if filler_type == "repeated_word":
            signal_score += 0.10
        elif filler_type == "hesitation":
            signal_score += 0.05
        signal_score = _clamp(signal_score)

        # Priority
        if signal_score >= high_priority_threshold:
            priority = "high"
        elif signal_score >= 0.55:
            priority = "medium"
        else:
            priority = "low"

        # Reason
        base_reason = reason if reason else "filler_detected"
        full_reason = f"filler_word_bridge:{base_reason}"

        return {
            "signal_type": signal_type,
            "source": "filler_word_signal_adapter",
            "source_filler_type": filler_type,
            "text": text,
            "normalized_text": normalized_text,
            "language": language,
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,
            "center_seconds": center_seconds,
            "recommended_start_seconds": recommended_start,
            "recommended_end_seconds": recommended_end,
            "duration_seconds": duration_seconds,
            "confidence": confidence,
            "signal_score": signal_score,
            "priority": priority,
            "remove_candidate": remove_candidate,
            "reason": full_reason,
            "source_segment_index": source_segment_index,
            "source_word_index": source_word_index,
            "source_occurrence": source_occurrence,
            "metadata": extra_metadata,
        }

    except Exception:
        return {}


def adapt_filler_words_to_signals(
    occurrences: Any,
    signal_window_before_seconds: float = 0.15,
    signal_window_after_seconds: float = 0.15,
    high_priority_threshold: float = 0.80,
    max_signals: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> FillerWordSignalAdapterResult:
    _meta: dict[str, Any] = dict(metadata or {})
    warnings: list[str] = []
    errors: list[str] = []

    try:
        occurrence_dicts = extract_filler_occurrence_dicts(occurrences)
        occurrence_count = len(occurrence_dicts)

        if occurrence_count == 0:
            warnings.append("no_filler_occurrences_available")
            return FillerWordSignalAdapterResult(
                status="skipped_no_fillers",
                occurrence_count=0,
                warnings=warnings,
                errors=errors,
                recommendation="no_filler_occurrences_available",
                metadata=_meta,
            )

        signals: list[dict[str, Any]] = []
        had_bad_occurrence = False

        for occ in occurrence_dicts:
            sig = filler_occurrence_to_signal(
                occ,
                signal_window_before_seconds=signal_window_before_seconds,
                signal_window_after_seconds=signal_window_after_seconds,
                high_priority_threshold=high_priority_threshold,
            )
            if not sig:
                had_bad_occurrence = True
                continue
            signals.append(sig)

        if had_bad_occurrence:
            warnings.append("some_occurrences_could_not_be_converted")

        # Sort chronologically by center_seconds
        signals.sort(key=lambda s: s.get("center_seconds") or 0.0)

        # Limit by max_signals — keep highest scoring, then re-sort chronologically
        if max_signals is not None and len(signals) > max_signals:
            signals.sort(key=lambda s: s.get("signal_score", 0.0), reverse=True)
            signals = signals[:max_signals]
            signals.sort(key=lambda s: s.get("center_seconds") or 0.0)

        # Compute counts and stats
        signal_count = len(signals)
        high_priority_count = sum(1 for s in signals if s.get("priority") == "high")

        signal_types: dict[str, int] = {}
        for s in signals:
            st = str(s.get("signal_type", "unknown"))
            signal_types[st] = signal_types.get(st, 0) + 1

        scores = [_safe_float(s.get("signal_score")) for s in signals]
        max_signal_score = max(scores) if scores else 0.0
        avg_signal_score = sum(scores) / len(scores) if scores else 0.0

        total_duration = sum(
            _safe_float(s.get("duration_seconds"))
            for s in signals
            if s.get("duration_seconds") is not None
        )

        if signal_count > 0 and not warnings and not errors:
            status = "ok"
            recommendation = "use_filler_edit_signals"
        elif signal_count > 0:
            status = "completed_with_warnings"
            recommendation = "review_warnings"
        else:
            warnings.append("no_signals_produced")
            status = "completed_with_warnings"
            recommendation = "review_warnings"

        return FillerWordSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=signal_count,
            occurrence_count=occurrence_count,
            high_priority_signal_count=high_priority_count,
            signal_types=signal_types,
            max_signal_score=max_signal_score,
            avg_signal_score=avg_signal_score,
            total_signal_duration_seconds=total_duration,
            warnings=warnings,
            errors=errors,
            recommendation=recommendation,
            metadata=_meta,
        )

    except Exception as exc:
        errors.append(f"filler_word_signal_adapter_failed: {exc}")
        return FillerWordSignalAdapterResult(
            status="failed",
            warnings=warnings,
            errors=errors,
            recommendation="retry_or_fix_filler_data",
            metadata=_meta,
        )


def adapt_filler_word_run_report_to_signals(
    filler_word_report: Any,
    signal_window_before_seconds: float = 0.15,
    signal_window_after_seconds: float = 0.15,
    high_priority_threshold: float = 0.80,
    max_signals: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> FillerWordSignalAdapterResult:
    _meta: dict[str, Any] = dict(metadata or {})

    try:
        if isinstance(filler_word_report, dict):
            report_status = str(filler_word_report.get("status", ""))
            report_recommendation = str(filler_word_report.get("recommendation", ""))
            report_occurrence_count = int(filler_word_report.get("occurrence_count", 0))
            report_transcript_source = filler_word_report.get("transcript_source")
        else:
            report_status = str(getattr(filler_word_report, "status", ""))
            report_recommendation = str(getattr(filler_word_report, "recommendation", ""))
            report_occurrence_count = int(getattr(filler_word_report, "occurrence_count", 0))
            report_transcript_source = getattr(filler_word_report, "transcript_source", None)

        result = adapt_filler_words_to_signals(
            filler_word_report,
            signal_window_before_seconds=signal_window_before_seconds,
            signal_window_after_seconds=signal_window_after_seconds,
            high_priority_threshold=high_priority_threshold,
            max_signals=max_signals,
            metadata=metadata,
        )

        result.metadata["filler_word_status"] = report_status
        result.metadata["filler_word_recommendation"] = report_recommendation
        result.metadata["occurrence_count"] = report_occurrence_count
        if report_transcript_source is not None:
            result.metadata["transcript_source"] = str(report_transcript_source)

        return result

    except Exception as exc:
        return FillerWordSignalAdapterResult(
            status="failed",
            errors=[f"adapt_filler_word_run_report_failed: {exc}"],
            recommendation="retry_or_fix_filler_data",
            metadata=_meta,
        )
