from __future__ import annotations

from typing import Any

from core.visual_energy_calculator import calculate_visual_energy_from_job
from models.visual_energy_run import (
    VISUAL_ENERGY_RUN_STATUS_FAILED,
    VisualEnergyRunReport,
)


def _set_job_value(job: Any, key: str, value: Any) -> None:
    if isinstance(job, dict):
        job[key] = value
        return

    setattr(job, key, value)


def _result_points_as_dicts(result: Any) -> list[dict[str, Any]]:
    points = getattr(result, "points", []) or []
    return [
        point.to_dict() if hasattr(point, "to_dict") else dict(point)
        for point in points
    ]


def _result_segments_as_dicts(result: Any) -> list[dict[str, Any]]:
    segments = getattr(result, "segments", []) or []
    return [
        segment.to_dict() if hasattr(segment, "to_dict") else dict(segment)
        for segment in segments
    ]


def _build_report_from_visual_energy_result(
    visual_energy_result: Any,
) -> VisualEnergyRunReport:
    return VisualEnergyRunReport(
        status=visual_energy_result.status,
        source="visual_energy_runner",
        visual_energy_result=visual_energy_result,
        visual_energy_points=_result_points_as_dicts(visual_energy_result),
        visual_energy_segments=_result_segments_as_dicts(visual_energy_result),
        point_count=visual_energy_result.point_count,
        segment_count=visual_energy_result.segment_count,
        high_energy_segment_count=visual_energy_result.high_energy_segment_count,
        low_energy_segment_count=visual_energy_result.low_energy_segment_count,
        technical_warning_segment_count=(
            visual_energy_result.technical_warning_segment_count
        ),
        duration_seconds=visual_energy_result.duration_seconds,
        frame_sample_rate=visual_energy_result.frame_sample_rate,
        recommendation=visual_energy_result.recommendation,
        warnings=list(visual_energy_result.warnings),
        errors=list(visual_energy_result.errors),
        metadata={
            "visual_energy_calculator_status": visual_energy_result.status,
            "no_cut_decision": True,
            "no_auto_remove": True,
            "no_auto_highlight": True,
        },
    )


def run_visual_energy_for_job(job: Any) -> VisualEnergyRunReport:
    try:
        visual_energy_result = calculate_visual_energy_from_job(job)
        return _build_report_from_visual_energy_result(visual_energy_result)

    except Exception as exc:
        return VisualEnergyRunReport(
            status=VISUAL_ENERGY_RUN_STATUS_FAILED,
            source="visual_energy_runner",
            visual_energy_result=None,
            visual_energy_points=[],
            visual_energy_segments=[],
            point_count=0,
            segment_count=0,
            high_energy_segment_count=0,
            low_energy_segment_count=0,
            technical_warning_segment_count=0,
            duration_seconds=None,
            frame_sample_rate=2.0,
            recommendation="review_visual_energy_runner_error",
            warnings=[],
            errors=[f"visual_energy_runner_failed: {exc}"],
            metadata={
                "no_cut_decision": True,
                "no_auto_remove": True,
                "no_auto_highlight": True,
            },
        )


def apply_visual_energy_run_report_to_job(
    job: Any,
    report: VisualEnergyRunReport,
) -> Any:
    report_dict = report.to_dict()

    _set_job_value(job, "visual_energy_report", report_dict)
    _set_job_value(job, "visual_energy_status", report.status)
    _set_job_value(
        job,
        "visual_energy_result",
        (
            report.visual_energy_result.to_dict()
            if report.visual_energy_result
            else {}
        ),
    )
    _set_job_value(job, "visual_energy_points", list(report.visual_energy_points))
    _set_job_value(job, "visual_energy_segments", list(report.visual_energy_segments))
    _set_job_value(job, "visual_energy_point_count", report.point_count)
    _set_job_value(job, "visual_energy_segment_count", report.segment_count)
    _set_job_value(
        job,
        "visual_energy_high_segment_count",
        report.high_energy_segment_count,
    )
    _set_job_value(
        job,
        "visual_energy_low_segment_count",
        report.low_energy_segment_count,
    )
    _set_job_value(
        job,
        "visual_energy_technical_warning_segment_count",
        report.technical_warning_segment_count,
    )
    _set_job_value(
        job,
        "visual_energy_duration_seconds",
        report.duration_seconds,
    )
    _set_job_value(
        job,
        "visual_energy_frame_sample_rate",
        report.frame_sample_rate,
    )
    _set_job_value(
        job,
        "visual_energy_recommendation",
        report.recommendation,
    )

    return job
