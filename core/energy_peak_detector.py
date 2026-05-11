from __future__ import annotations

from typing import Any

from models.energy_peak import EnergyPeak, EnergyPeakDetectionResult

DEFAULT_PEAK_THRESHOLD: float = 0.85
DEFAULT_RISE_THRESHOLD: float = 0.25
DEFAULT_MIN_PEAK_DISTANCE_SECONDS: float = 0.4
DEFAULT_LOCAL_WINDOW_SIZE: int = 1


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_bool(val: Any, default: bool = False) -> bool:
    if val is None:
        return default
    return bool(val)


def extract_energy_items(energy_timeline: Any) -> list[dict[str, Any]]:
    raw_items: list[Any] = []

    try:
        if isinstance(energy_timeline, list):
            raw_items = energy_timeline
        elif isinstance(energy_timeline, dict):
            if "energy_timeline" in energy_timeline:
                candidate = energy_timeline["energy_timeline"]
                raw_items = candidate if isinstance(candidate, list) else []
            elif "points" in energy_timeline:
                candidate = energy_timeline["points"]
                raw_items = candidate if isinstance(candidate, list) else []
            else:
                raw_items = []
        elif energy_timeline is not None:
            # Try RmsEnergyContextAdapterResult-like object (has energy_timeline)
            et = getattr(energy_timeline, "energy_timeline", None)
            if isinstance(et, list):
                raw_items = et
            else:
                # Try RmsEnergyTimelineResult-like object (has points)
                pts = getattr(energy_timeline, "points", None)
                if isinstance(pts, list):
                    raw_items = pts
                else:
                    raw_items = []
    except Exception:
        return []

    result: list[dict[str, Any]] = []
    for i, item in enumerate(raw_items):
        try:
            if isinstance(item, dict):
                time_raw = item.get("time_seconds")
                start_raw = item.get("start_seconds", 0.0)
                end_raw = item.get("end_seconds", 0.0)
                energy_raw = item.get("energy_score")
                if energy_raw is None:
                    energy_raw = item.get("normalized_energy")
                is_silent = _safe_bool(item.get("is_silent"))
                source_item = item
            else:
                # Object with attributes (e.g. RmsEnergyPoint)
                time_raw = getattr(item, "time_seconds", None)
                start_raw = getattr(item, "start_seconds", 0.0)
                end_raw = getattr(item, "end_seconds", 0.0)
                energy_raw = getattr(item, "energy_score", None)
                if energy_raw is None:
                    energy_raw = getattr(item, "normalized_energy", None)
                is_silent = _safe_bool(getattr(item, "is_silent", False))
                try:
                    source_item = item.to_dict() if hasattr(item, "to_dict") else {}
                except Exception:
                    source_item = {}

            start = _safe_float(start_raw)
            end = _safe_float(end_raw)

            if time_raw is not None:
                try:
                    time_seconds = float(time_raw)
                except (TypeError, ValueError):
                    time_seconds = (start + end) / 2.0
            else:
                center_raw = (
                    item.get("center_seconds")
                    if isinstance(item, dict)
                    else getattr(item, "center_seconds", None)
                )
                if center_raw is not None:
                    try:
                        time_seconds = float(center_raw)
                    except (TypeError, ValueError):
                        time_seconds = (start + end) / 2.0
                else:
                    time_seconds = (start + end) / 2.0

            if energy_raw is None:
                energy_score = 0.0
            else:
                try:
                    energy_score = float(energy_raw)
                except (TypeError, ValueError):
                    energy_score = 0.0

            result.append({
                "time_seconds": time_seconds,
                "start_seconds": start,
                "end_seconds": end,
                "energy_score": energy_score,
                "source_index": i,
                "is_silent": is_silent,
                "source_item": source_item,
            })
        except Exception:
            continue

    return result


def detect_energy_peak_at_index(
    items: list[dict[str, Any]],
    index: int,
    peak_threshold: float = DEFAULT_PEAK_THRESHOLD,
    rise_threshold: float = DEFAULT_RISE_THRESHOLD,
    local_window_size: int = DEFAULT_LOCAL_WINDOW_SIZE,
) -> EnergyPeak | None:
    if not items or index < 0 or index >= len(items):
        return None

    try:
        current = items[index]
        current_energy = _safe_float(current.get("energy_score"))
        is_silent = _safe_bool(current.get("is_silent"))
        start = _safe_float(current.get("start_seconds"))
        end = _safe_float(current.get("end_seconds"))
        time_seconds = _safe_float(current.get("time_seconds"), (start + end) / 2.0)
        src_index = current.get("source_index", index)

        # Silent items with low energy are not peaks
        if is_silent and current_energy < peak_threshold:
            return None

        prev_energy: float | None = None
        next_energy: float | None = None

        if index > 0:
            try:
                prev_energy = _safe_float(items[index - 1].get("energy_score"))
            except Exception:
                prev_energy = None

        if index < len(items) - 1:
            try:
                next_energy = _safe_float(items[index + 1].get("energy_score"))
            except Exception:
                next_energy = None

        rise_delta = current_energy - prev_energy if prev_energy is not None else 0.0
        fall_delta = current_energy - next_energy if next_energy is not None else 0.0

        # Local maximum: current >= all neighbours in window and > at least one, and >= 0.5
        is_local_maximum = False
        if current_energy >= 0.5:
            w_start = max(0, index - local_window_size)
            w_end = min(len(items) - 1, index + local_window_size)
            neighbour_energies = [
                _safe_float(items[j].get("energy_score"))
                for j in range(w_start, w_end + 1)
                if j != index
            ]
            if neighbour_energies:
                if current_energy >= max(neighbour_energies) and current_energy > min(neighbour_energies):
                    is_local_maximum = True

        threshold_peak = current_energy >= peak_threshold
        sudden_rise = rise_delta >= rise_threshold and current_energy >= 0.5

        if not threshold_peak and not is_local_maximum and not sudden_rise:
            return None

        rules_applied: list[str] = []
        if threshold_peak:
            rules_applied.append("threshold_peak")
        if is_local_maximum:
            rules_applied.append("local_maximum")
        if sudden_rise:
            rules_applied.append("sudden_rise")

        active_rules = sum([threshold_peak, is_local_maximum, sudden_rise])
        if active_rules > 1:
            peak_type = "combined"
        elif threshold_peak:
            peak_type = "high_energy"
        elif is_local_maximum:
            peak_type = "local_maximum"
        elif sudden_rise:
            peak_type = "sudden_rise"
        else:
            peak_type = "unknown"

        peak_score = min(
            1.0,
            current_energy * 0.65
            + max(rise_delta, 0.0) * 0.20
            + max(fall_delta, 0.0) * 0.10
            + (0.05 if is_local_maximum else 0.0),
        )

        confidence_map = {
            "combined": 0.90,
            "high_energy": 0.80,
            "local_maximum": 0.75,
            "sudden_rise": 0.70,
            "unknown": 0.50,
        }
        confidence = confidence_map.get(peak_type, 0.50)

        reason_map = {
            "combined": "combined_energy_peak",
            "high_energy": "energy_above_peak_threshold",
            "local_maximum": "local_maximum_detected",
            "sudden_rise": "sudden_energy_rise_detected",
            "unknown": "unknown_peak_reason",
        }
        reason = reason_map.get(peak_type, "unknown_peak_reason")

        return EnergyPeak(
            start_seconds=start,
            end_seconds=end,
            center_seconds=time_seconds,
            energy_score=current_energy,
            peak_score=peak_score,
            peak_type=peak_type,
            confidence=confidence,
            reason=reason,
            source_index=src_index if isinstance(src_index, int) else index,
            is_local_maximum=is_local_maximum,
            rise_delta=rise_delta,
            fall_delta=fall_delta,
            window_energy_before=prev_energy,
            window_energy_after=next_energy,
            source_item=dict(current.get("source_item") or {}),
            rules_applied=rules_applied,
        )
    except Exception:
        return None


def detect_energy_peaks(
    energy_timeline: Any,
    peak_threshold: float = DEFAULT_PEAK_THRESHOLD,
    rise_threshold: float = DEFAULT_RISE_THRESHOLD,
    min_peak_distance_seconds: float = DEFAULT_MIN_PEAK_DISTANCE_SECONDS,
    local_window_size: int = DEFAULT_LOCAL_WINDOW_SIZE,
    max_peaks: int | None = None,
) -> EnergyPeakDetectionResult:
    warnings: list[str] = []
    errors: list[str] = []

    try:
        items = extract_energy_items(energy_timeline)
    except Exception as exc:
        errors.append(f"extract_energy_items_failed: {exc}")
        return EnergyPeakDetectionResult(
            status="failed",
            peak_threshold=peak_threshold,
            min_peak_distance_seconds=min_peak_distance_seconds,
            warnings=warnings,
            errors=errors,
        )

    if not items:
        warnings.append("no_energy_items")
        return EnergyPeakDetectionResult(
            status="completed_with_warnings",
            peaks=[],
            peak_count=0,
            peak_threshold=peak_threshold,
            min_peak_distance_seconds=min_peak_distance_seconds,
            warnings=warnings,
            errors=errors,
        )

    raw_peaks: list[EnergyPeak] = []
    for i in range(len(items)):
        try:
            peak = detect_energy_peak_at_index(
                items=items,
                index=i,
                peak_threshold=peak_threshold,
                rise_threshold=rise_threshold,
                local_window_size=local_window_size,
            )
            if peak is not None:
                raw_peaks.append(peak)
        except Exception:
            continue

    # Distance-based deduplication: keep best peak within min_peak_distance_seconds
    deduped: list[EnergyPeak] = []
    for peak in raw_peaks:
        merged = False
        for j, kept in enumerate(deduped):
            distance = abs(peak.center_seconds - kept.center_seconds)
            if distance < min_peak_distance_seconds:
                # Keep the one with the higher peak_score; tie-break by energy_score
                if (peak.peak_score > kept.peak_score) or (
                    peak.peak_score == kept.peak_score
                    and peak.energy_score > kept.energy_score
                ):
                    deduped[j] = peak
                merged = True
                break
        if not merged:
            deduped.append(peak)

    # Sort chronologically
    deduped.sort(key=lambda p: p.center_seconds)

    # Apply max_peaks by score then re-sort chronologically
    if max_peaks is not None and len(deduped) > max_peaks:
        deduped.sort(key=lambda p: p.peak_score, reverse=True)
        deduped = deduped[:max_peaks]
        deduped.sort(key=lambda p: p.center_seconds)

    peak_count = len(deduped)
    high_energy_peak_count = sum(1 for p in deduped if "threshold_peak" in p.rules_applied)
    local_max_peak_count = sum(1 for p in deduped if "local_maximum" in p.rules_applied)
    rise_peak_count = sum(1 for p in deduped if "sudden_rise" in p.rules_applied)
    threshold_peak_count = high_energy_peak_count

    top_score = max((p.peak_score for p in deduped), default=0.0)

    status = "ok" if peak_count > 0 and not warnings and not errors else "completed_with_warnings"

    return EnergyPeakDetectionResult(
        status=status,
        peaks=deduped,
        peak_count=peak_count,
        high_energy_peak_count=high_energy_peak_count,
        local_max_peak_count=local_max_peak_count,
        rise_peak_count=rise_peak_count,
        threshold_peak_count=threshold_peak_count,
        peak_threshold=peak_threshold,
        min_peak_distance_seconds=min_peak_distance_seconds,
        warnings=warnings,
        errors=errors,
        metadata={"top_peak_score": top_score},
    )
