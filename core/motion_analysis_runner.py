from __future__ import annotations

from typing import Any

from core.motion_analysis_source_selector import select_motion_analysis_source
from core.motion_analyzer import analyze_motion
from core.power_profile import PowerProfile
from core.visual_analysis_proxy import (
    ensure_visual_analysis_proxy_for_job,
    with_visual_analysis_proxy_source_selection,
)
from models.motion_analysis_run import (
    MOTION_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    MOTION_RUN_STATUS_FAILED,
    MOTION_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    MotionAnalysisRunReport,
)
from models.motion_analysis_source import (
    MOTION_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    MOTION_SOURCE_STATUS_FAILED,
    MOTION_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE,
)


def _set_job_value(job: Any, key: str, value: Any) -> None:
    if isinstance(job, dict):
        job[key] = value
        return

    setattr(job, key, value)


def _job_power_profile(job: Any) -> str | None:
    if isinstance(job, dict):
        return job.get("power_profile")
    return getattr(job, "power_profile", None)


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


def _build_report_from_blocked_source(
    status: str,
    source_selection: Any,
) -> MotionAnalysisRunReport:
    return MotionAnalysisRunReport(
        status=status,
        source="motion_analysis_runner",
        source_selection=source_selection,
        selected_path=source_selection.selected_path,
        selected_type=source_selection.selected_type,
        motion_analysis_result=None,
        motion_points=[],
        motion_segments=[],
        point_count=0,
        segment_count=0,
        low_motion_segment_count=0,
        high_motion_segment_count=0,
        dead_visual_candidate_count=0,
        duration_seconds=None,
        frame_sample_rate=2.0,
        recommendation=source_selection.recommendation,
        warnings=list(source_selection.warnings),
        errors=list(source_selection.errors),
        metadata={
            "source_selector_status": source_selection.status,
        },
    )


def _build_report_from_motion_result(
    source_selection: Any,
    motion_result: Any,
) -> MotionAnalysisRunReport:
    return MotionAnalysisRunReport(
        status=motion_result.status,
        source="motion_analysis_runner",
        source_selection=source_selection,
        selected_path=source_selection.selected_path,
        selected_type=source_selection.selected_type,
        motion_analysis_result=motion_result,
        motion_points=_result_points_as_dicts(motion_result),
        motion_segments=_result_segments_as_dicts(motion_result),
        point_count=motion_result.point_count,
        segment_count=motion_result.segment_count,
        low_motion_segment_count=motion_result.low_motion_segment_count,
        high_motion_segment_count=motion_result.high_motion_segment_count,
        dead_visual_candidate_count=motion_result.dead_visual_candidate_count,
        duration_seconds=motion_result.duration_seconds,
        frame_sample_rate=motion_result.frame_sample_rate,
        recommendation=motion_result.recommendation,
        warnings=list(source_selection.warnings) + list(motion_result.warnings),
        errors=list(source_selection.errors) + list(motion_result.errors),
        metadata={
            "source_selector_status": source_selection.status,
            "motion_analyzer_status": motion_result.status,
        },
    )


def run_motion_analysis_for_job(
    job: Any,
    frame_sample_rate: float | None = None,
    low_motion_threshold: float = 0.08,
    high_motion_threshold: float = 0.35,
    dead_visual_min_duration_seconds: float = 3.0,
    resize_width: int = 160,
    resize_height: int = 90,
) -> MotionAnalysisRunReport:
    resolved_frame_sample_rate = (
        float(frame_sample_rate)
        if frame_sample_rate is not None
        else PowerProfile.resolve_visual_analysis_frame_sample_rate(
            _job_power_profile(job),
            "motion",
        )
    )
    try:
        source_selection = select_motion_analysis_source(job)

        if source_selection.status == MOTION_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE:
            return _build_report_from_blocked_source(
                status=MOTION_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
                source_selection=source_selection,
            )

        if source_selection.status == MOTION_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE:
            return _build_report_from_blocked_source(
                status=MOTION_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
                source_selection=source_selection,
            )

        if source_selection.status == MOTION_SOURCE_STATUS_FAILED:
            return _build_report_from_blocked_source(
                status=MOTION_RUN_STATUS_FAILED,
                source_selection=source_selection,
            )

        if not source_selection.selected_path:
            return _build_report_from_blocked_source(
                status=MOTION_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
                source_selection=source_selection,
            )

        proxy_path = ensure_visual_analysis_proxy_for_job(job, source_selection.selected_path)
        source_selection = with_visual_analysis_proxy_source_selection(
            source_selection,
            proxy_path,
        )

        motion_result = analyze_motion(
            input_path=source_selection.selected_path,
            frame_sample_rate=resolved_frame_sample_rate,
            low_motion_threshold=low_motion_threshold,
            high_motion_threshold=high_motion_threshold,
            dead_visual_min_duration_seconds=dead_visual_min_duration_seconds,
            resize_width=resize_width,
            resize_height=resize_height,
        )

        return _build_report_from_motion_result(
            source_selection=source_selection,
            motion_result=motion_result,
        )

    except Exception as exc:
        return MotionAnalysisRunReport(
            status=MOTION_RUN_STATUS_FAILED,
            source="motion_analysis_runner",
            source_selection=None,
            selected_path=None,
            selected_type=None,
            motion_analysis_result=None,
            motion_points=[],
            motion_segments=[],
            point_count=0,
            segment_count=0,
            low_motion_segment_count=0,
            high_motion_segment_count=0,
            dead_visual_candidate_count=0,
            duration_seconds=None,
            frame_sample_rate=resolved_frame_sample_rate,
            recommendation="review_motion_analysis_runner_error",
            warnings=[],
            errors=[f"motion_analysis_runner_failed: {exc}"],
            metadata={},
        )


def apply_motion_analysis_run_report_to_job(
    job: Any,
    report: MotionAnalysisRunReport,
) -> Any:
    report_dict = report.to_dict()

    _set_job_value(job, "motion_analysis_report", report_dict)
    _set_job_value(job, "motion_analysis_status", report.status)
    _set_job_value(job, "motion_analysis_selected_path", report.selected_path)
    _set_job_value(job, "motion_analysis_selected_type", report.selected_type)
    _set_job_value(
        job,
        "motion_analysis_result",
        (
            report.motion_analysis_result.to_dict()
            if report.motion_analysis_result
            else {}
        ),
    )
    _set_job_value(job, "motion_analysis_points", list(report.motion_points))
    _set_job_value(job, "motion_analysis_segments", list(report.motion_segments))
    _set_job_value(job, "motion_analysis_point_count", report.point_count)
    _set_job_value(job, "motion_analysis_segment_count", report.segment_count)
    _set_job_value(
        job,
        "motion_analysis_low_motion_segment_count",
        report.low_motion_segment_count,
    )
    _set_job_value(
        job,
        "motion_analysis_high_motion_segment_count",
        report.high_motion_segment_count,
    )
    _set_job_value(
        job,
        "motion_analysis_dead_visual_candidate_count",
        report.dead_visual_candidate_count,
    )
    _set_job_value(
        job,
        "motion_analysis_duration_seconds",
        report.duration_seconds,
    )
    _set_job_value(
        job,
        "motion_analysis_frame_sample_rate",
        report.frame_sample_rate,
    )
    _set_job_value(
        job,
        "motion_analysis_recommendation",
        report.recommendation,
    )

    return job
