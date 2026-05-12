from __future__ import annotations

from typing import Any

from core.stutter_detection_source_selector import select_stutter_detection_source
from core.stutter_detector import analyze_stutter_frames
from models.stutter_detection_run import (
    STUTTER_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    STUTTER_RUN_STATUS_FAILED,
    STUTTER_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    StutterDetectionRunReport,
)
from models.stutter_detection_source import (
    STUTTER_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    STUTTER_SOURCE_STATUS_FAILED,
    STUTTER_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE,
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


def _build_report_from_blocked_source(
    status: str,
    source_selection: Any,
    frame_sample_rate: float,
) -> StutterDetectionRunReport:
    return StutterDetectionRunReport(
        status=status,
        source="stutter_detection_runner",
        source_selection=source_selection,
        selected_path=source_selection.selected_path,
        selected_type=source_selection.selected_type,
        stutter_detection_result=None,
        stutter_points=[],
        stutter_segments=[],
        point_count=0,
        segment_count=0,
        duplicate_candidate_count=0,
        stutter_segment_count=0,
        freeze_segment_count=0,
        duration_seconds=None,
        frame_sample_rate=frame_sample_rate,
        recommendation=source_selection.recommendation,
        warnings=list(source_selection.warnings),
        errors=list(source_selection.errors),
        metadata={"source_selector_status": source_selection.status},
    )


def _build_report_from_stutter_result(
    source_selection: Any,
    stutter_result: Any,
) -> StutterDetectionRunReport:
    return StutterDetectionRunReport(
        status=stutter_result.status,
        source="stutter_detection_runner",
        source_selection=source_selection,
        selected_path=source_selection.selected_path,
        selected_type=source_selection.selected_type,
        stutter_detection_result=stutter_result,
        stutter_points=_result_points_as_dicts(stutter_result),
        stutter_segments=_result_segments_as_dicts(stutter_result),
        point_count=stutter_result.point_count,
        segment_count=stutter_result.segment_count,
        duplicate_candidate_count=stutter_result.duplicate_candidate_count,
        stutter_segment_count=stutter_result.stutter_segment_count,
        freeze_segment_count=stutter_result.freeze_segment_count,
        duration_seconds=stutter_result.duration_seconds,
        frame_sample_rate=stutter_result.frame_sample_rate,
        recommendation=stutter_result.recommendation,
        warnings=list(source_selection.warnings) + list(stutter_result.warnings),
        errors=list(source_selection.errors) + list(stutter_result.errors),
        metadata={
            "source_selector_status": source_selection.status,
            "stutter_detector_status": stutter_result.status,
        },
    )


def run_stutter_detection_for_job(
    job: Any,
    frame_sample_rate: float = 10.0,
    duplicate_score_threshold: float = 0.985,
    difference_score_threshold: float = 0.015,
    min_duplicate_frames_for_stutter: int = 4,
    min_stutter_duration_seconds: float = 0.13,
    resize_width: int = 160,
    resize_height: int = 90,
) -> StutterDetectionRunReport:
    try:
        source_selection = select_stutter_detection_source(job)

        if source_selection.status == STUTTER_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE:
            return _build_report_from_blocked_source(
                status=STUTTER_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
                source_selection=source_selection,
                frame_sample_rate=frame_sample_rate,
            )

        if source_selection.status == STUTTER_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE:
            return _build_report_from_blocked_source(
                status=STUTTER_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
                source_selection=source_selection,
                frame_sample_rate=frame_sample_rate,
            )

        if source_selection.status == STUTTER_SOURCE_STATUS_FAILED:
            return _build_report_from_blocked_source(
                status=STUTTER_RUN_STATUS_FAILED,
                source_selection=source_selection,
                frame_sample_rate=frame_sample_rate,
            )

        if not source_selection.selected_path:
            return _build_report_from_blocked_source(
                status=STUTTER_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
                source_selection=source_selection,
                frame_sample_rate=frame_sample_rate,
            )

        stutter_result = analyze_stutter_frames(
            input_path=source_selection.selected_path,
            frame_sample_rate=frame_sample_rate,
            duplicate_score_threshold=duplicate_score_threshold,
            difference_score_threshold=difference_score_threshold,
            min_duplicate_frames_for_stutter=min_duplicate_frames_for_stutter,
            min_stutter_duration_seconds=min_stutter_duration_seconds,
            resize_width=resize_width,
            resize_height=resize_height,
        )

        return _build_report_from_stutter_result(
            source_selection=source_selection,
            stutter_result=stutter_result,
        )

    except Exception as exc:
        return StutterDetectionRunReport(
            status=STUTTER_RUN_STATUS_FAILED,
            source="stutter_detection_runner",
            source_selection=None,
            selected_path=None,
            selected_type=None,
            stutter_detection_result=None,
            stutter_points=[],
            stutter_segments=[],
            point_count=0,
            segment_count=0,
            duplicate_candidate_count=0,
            stutter_segment_count=0,
            freeze_segment_count=0,
            duration_seconds=None,
            frame_sample_rate=frame_sample_rate,
            recommendation="review_stutter_detection_runner_error",
            warnings=[],
            errors=[f"stutter_detection_runner_failed: {exc}"],
            metadata={},
        )


def apply_stutter_detection_run_report_to_job(
    job: Any,
    report: StutterDetectionRunReport,
) -> Any:
    report_dict = report.to_dict()

    _set_job_value(job, "stutter_detection_report", report_dict)
    _set_job_value(job, "stutter_detection_status", report.status)
    _set_job_value(job, "stutter_detection_selected_path", report.selected_path)
    _set_job_value(job, "stutter_detection_selected_type", report.selected_type)
    _set_job_value(
        job,
        "stutter_detection_result",
        report.stutter_detection_result.to_dict()
        if report.stutter_detection_result
        else {},
    )
    _set_job_value(job, "stutter_detection_points", list(report.stutter_points))
    _set_job_value(job, "stutter_detection_segments", list(report.stutter_segments))
    _set_job_value(job, "stutter_detection_point_count", report.point_count)
    _set_job_value(job, "stutter_detection_segment_count", report.segment_count)
    _set_job_value(
        job,
        "stutter_detection_duplicate_candidate_count",
        report.duplicate_candidate_count,
    )
    _set_job_value(
        job,
        "stutter_detection_stutter_segment_count",
        report.stutter_segment_count,
    )
    _set_job_value(
        job,
        "stutter_detection_freeze_segment_count",
        report.freeze_segment_count,
    )
    _set_job_value(
        job,
        "stutter_detection_duration_seconds",
        report.duration_seconds,
    )
    _set_job_value(
        job,
        "stutter_detection_frame_sample_rate",
        report.frame_sample_rate,
    )
    _set_job_value(
        job,
        "stutter_detection_recommendation",
        report.recommendation,
    )

    return job
