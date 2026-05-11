from __future__ import annotations

from typing import Any

from models.rms_energy_context_adapter import RmsEnergyContextAdapterResult


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


def convert_rms_point_to_energy_context_item(
    point: Any,
    peak_threshold: float = 0.85,
) -> dict[str, Any]:
    if isinstance(point, dict):
        start = _safe_float(point.get("start_seconds"))
        end = _safe_float(point.get("end_seconds"))
        center_raw = point.get("center_seconds")
        rms = _safe_float(point.get("rms"))
        normalized_energy_raw = point.get("normalized_energy")
        if normalized_energy_raw is None:
            normalized_energy_raw = point.get("energy_score")
        normalized_energy = _safe_float(normalized_energy_raw)
        dbfs = point.get("dbfs")
        is_silent = _safe_bool(point.get("is_silent"))
    else:
        start = _safe_float(getattr(point, "start_seconds", None))
        end = _safe_float(getattr(point, "end_seconds", None))
        center_raw = getattr(point, "center_seconds", None)
        rms = _safe_float(getattr(point, "rms", None))
        ne_raw = getattr(point, "normalized_energy", None)
        if ne_raw is None:
            ne_raw = getattr(point, "energy_score", None)
        normalized_energy = _safe_float(ne_raw)
        dbfs = getattr(point, "dbfs", None)
        is_silent = _safe_bool(getattr(point, "is_silent", False))

    if center_raw is not None:
        try:
            center = float(center_raw)
        except (TypeError, ValueError):
            center = (start + end) / 2.0
    else:
        center = (start + end) / 2.0

    dbfs_val: float | None = None
    if dbfs is not None:
        try:
            dbfs_val = float(dbfs)
        except (TypeError, ValueError):
            dbfs_val = None

    return {
        "time_seconds": center,
        "start_seconds": start,
        "end_seconds": end,
        "energy_score": normalized_energy,
        "normalized_energy": normalized_energy,
        "rms": rms,
        "dbfs": dbfs_val,
        "is_silent": is_silent,
        "is_peak": normalized_energy >= peak_threshold,
        "source": "rms_energy_timeline",
    }


def adapt_rms_energy_timeline_to_context(
    rms_timeline_result: Any,
    peak_threshold: float = 0.85,
    include_silent_points: bool = True,
) -> RmsEnergyContextAdapterResult:
    warnings: list[str] = []
    errors: list[str] = []
    energy_timeline: list[dict[str, Any]] = []

    try:
        if isinstance(rms_timeline_result, list):
            raw_points: list[Any] = rms_timeline_result
        elif isinstance(rms_timeline_result, dict):
            raw_points = rms_timeline_result.get("points", [])
            if not isinstance(raw_points, list):
                raw_points = []
        elif rms_timeline_result is not None:
            raw_points = getattr(rms_timeline_result, "points", None)
            if not isinstance(raw_points, list):
                raw_points = []
        else:
            raw_points = []
    except Exception as exc:
        errors.append(f"timeline_input_parse_failed: {exc}")
        return RmsEnergyContextAdapterResult(
            status="failed",
            errors=errors,
            warnings=warnings,
        )

    if not raw_points:
        warnings.append("no_rms_energy_points")
        return RmsEnergyContextAdapterResult(
            status="completed_with_warnings",
            energy_timeline=[],
            point_count=0,
            peak_count=0,
            silent_count=0,
            peak_threshold=peak_threshold,
            warnings=warnings,
            errors=errors,
        )

    for i, point in enumerate(raw_points):
        try:
            item = convert_rms_point_to_energy_context_item(point, peak_threshold=peak_threshold)
            if not include_silent_points and item.get("is_silent"):
                continue
            energy_timeline.append(item)
        except Exception as exc:
            warnings.append(f"invalid_rms_point_{i}: {exc}")

    point_count = len(energy_timeline)
    peak_count = sum(1 for item in energy_timeline if item.get("is_peak"))
    silent_count = sum(1 for item in energy_timeline if item.get("is_silent"))

    scores = [
        item["energy_score"]
        for item in energy_timeline
        if isinstance(item.get("energy_score"), (int, float))
    ]

    min_energy = min(scores) if scores else 0.0
    max_energy = max(scores) if scores else 0.0
    avg_energy = sum(scores) / len(scores) if scores else 0.0

    status = "ok" if not warnings and not errors else "completed_with_warnings"

    return RmsEnergyContextAdapterResult(
        status=status,
        energy_timeline=energy_timeline,
        point_count=point_count,
        peak_count=peak_count,
        silent_count=silent_count,
        peak_threshold=peak_threshold,
        min_energy_score=min_energy,
        max_energy_score=max_energy,
        avg_energy_score=avg_energy,
        warnings=warnings,
        errors=errors,
    )


def adapt_rms_energy_run_report_to_context(
    rms_run_report: Any,
    peak_threshold: float = 0.85,
    include_silent_points: bool = True,
) -> RmsEnergyContextAdapterResult:
    warnings: list[str] = []
    errors: list[str] = []

    try:
        if isinstance(rms_run_report, dict):
            energy_timeline_result = rms_run_report.get("energy_timeline_result")
            source_status = rms_run_report.get("status")
            selected_type = rms_run_report.get("selected_type")
            selected_path = rms_run_report.get("selected_path")
            point_count_hint = rms_run_report.get("point_count", 0)
        else:
            energy_timeline_result = getattr(rms_run_report, "energy_timeline_result", None)
            source_status = getattr(rms_run_report, "status", None)
            selected_type = getattr(rms_run_report, "selected_type", None)
            selected_path = getattr(rms_run_report, "selected_path", None)
            point_count_hint = getattr(rms_run_report, "point_count", 0)
    except Exception as exc:
        errors.append(f"run_report_parse_failed: {exc}")
        return RmsEnergyContextAdapterResult(
            status="failed",
            errors=errors,
            warnings=warnings,
        )

    if energy_timeline_result is None or (
        isinstance(energy_timeline_result, dict) and not energy_timeline_result
    ):
        errors.append("missing_energy_timeline_result")
        return RmsEnergyContextAdapterResult(
            status="failed",
            errors=errors,
            warnings=warnings,
        )

    result = adapt_rms_energy_timeline_to_context(
        rms_timeline_result=energy_timeline_result,
        peak_threshold=peak_threshold,
        include_silent_points=include_silent_points,
    )

    result.metadata.update({
        "source_status": source_status,
        "selected_type": selected_type,
        "selected_path": selected_path,
        "point_count": point_count_hint,
    })

    return result
