from __future__ import annotations

from typing import Any

from core.face_reaction_analyzer import analyze_face_reactions
from core.face_reaction_source_selector import select_face_reaction_source
from models.face_reaction_run import (
    FACE_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    FACE_RUN_STATUS_FAILED,
    FACE_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    FaceReactionRunReport,
)
from models.face_reaction_source import (
    FACE_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    FACE_SOURCE_STATUS_FAILED,
    FACE_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE,
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
) -> FaceReactionRunReport:
    return FaceReactionRunReport(
        status=status,
        source="face_reaction_runner",
        source_selection=source_selection,
        selected_path=source_selection.selected_path,
        selected_type=source_selection.selected_type,
        face_reaction_result=None,
        face_reaction_points=[],
        face_reaction_segments=[],
        point_count=0,
        segment_count=0,
        face_detected_point_count=0,
        reaction_candidate_count=0,
        high_reaction_segment_count=0,
        duration_seconds=None,
        frame_sample_rate=frame_sample_rate,
        recommendation=source_selection.recommendation,
        warnings=list(source_selection.warnings),
        errors=list(source_selection.errors),
        metadata={"source_selector_status": source_selection.status},
    )


def _build_report_from_face_reaction_result(
    source_selection: Any,
    face_reaction_result: Any,
) -> FaceReactionRunReport:
    return FaceReactionRunReport(
        status=face_reaction_result.status,
        source="face_reaction_runner",
        source_selection=source_selection,
        selected_path=source_selection.selected_path,
        selected_type=source_selection.selected_type,
        face_reaction_result=face_reaction_result,
        face_reaction_points=_result_points_as_dicts(face_reaction_result),
        face_reaction_segments=_result_segments_as_dicts(face_reaction_result),
        point_count=face_reaction_result.point_count,
        segment_count=face_reaction_result.segment_count,
        face_detected_point_count=face_reaction_result.face_detected_point_count,
        reaction_candidate_count=face_reaction_result.reaction_candidate_count,
        high_reaction_segment_count=(
            face_reaction_result.high_reaction_segment_count
        ),
        duration_seconds=face_reaction_result.duration_seconds,
        frame_sample_rate=face_reaction_result.frame_sample_rate,
        recommendation=face_reaction_result.recommendation,
        warnings=list(source_selection.warnings) + list(face_reaction_result.warnings),
        errors=list(source_selection.errors) + list(face_reaction_result.errors),
        metadata={
            "source_selector_status": source_selection.status,
            "face_reaction_analyzer_status": face_reaction_result.status,
        },
    )


def run_face_reaction_for_job(
    job: Any,
    frame_sample_rate: float = 2.0,
    min_face_area_ratio: float = 0.005,
    high_reaction_threshold: float = 0.55,
    min_reaction_segment_duration_seconds: float = 0.5,
    resize_width: int = 320,
    resize_height: int = 180,
) -> FaceReactionRunReport:
    try:
        source_selection = select_face_reaction_source(job)

        if source_selection.status == FACE_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE:
            return _build_report_from_blocked_source(
                status=FACE_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
                source_selection=source_selection,
                frame_sample_rate=frame_sample_rate,
            )

        if source_selection.status == FACE_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE:
            return _build_report_from_blocked_source(
                status=FACE_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
                source_selection=source_selection,
                frame_sample_rate=frame_sample_rate,
            )

        if source_selection.status == FACE_SOURCE_STATUS_FAILED:
            return _build_report_from_blocked_source(
                status=FACE_RUN_STATUS_FAILED,
                source_selection=source_selection,
                frame_sample_rate=frame_sample_rate,
            )

        if not source_selection.selected_path:
            return _build_report_from_blocked_source(
                status=FACE_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
                source_selection=source_selection,
                frame_sample_rate=frame_sample_rate,
            )

        face_reaction_result = analyze_face_reactions(
            input_path=source_selection.selected_path,
            frame_sample_rate=frame_sample_rate,
            min_face_area_ratio=min_face_area_ratio,
            high_reaction_threshold=high_reaction_threshold,
            min_reaction_segment_duration_seconds=(
                min_reaction_segment_duration_seconds
            ),
            resize_width=resize_width,
            resize_height=resize_height,
        )

        return _build_report_from_face_reaction_result(
            source_selection=source_selection,
            face_reaction_result=face_reaction_result,
        )

    except Exception as exc:
        return FaceReactionRunReport(
            status=FACE_RUN_STATUS_FAILED,
            source="face_reaction_runner",
            source_selection=None,
            selected_path=None,
            selected_type=None,
            face_reaction_result=None,
            face_reaction_points=[],
            face_reaction_segments=[],
            point_count=0,
            segment_count=0,
            face_detected_point_count=0,
            reaction_candidate_count=0,
            high_reaction_segment_count=0,
            duration_seconds=None,
            frame_sample_rate=frame_sample_rate,
            recommendation="review_face_reaction_runner_error",
            warnings=[],
            errors=[f"face_reaction_runner_failed: {exc}"],
            metadata={},
        )


def apply_face_reaction_run_report_to_job(
    job: Any,
    report: FaceReactionRunReport,
) -> Any:
    report_dict = report.to_dict()

    _set_job_value(job, "face_reaction_report", report_dict)
    _set_job_value(job, "face_reaction_status", report.status)
    _set_job_value(job, "face_reaction_selected_path", report.selected_path)
    _set_job_value(job, "face_reaction_selected_type", report.selected_type)
    _set_job_value(
        job,
        "face_reaction_result",
        report.face_reaction_result.to_dict()
        if report.face_reaction_result
        else {},
    )
    _set_job_value(job, "face_reaction_points", list(report.face_reaction_points))
    _set_job_value(job, "face_reaction_segments", list(report.face_reaction_segments))
    _set_job_value(job, "face_reaction_point_count", report.point_count)
    _set_job_value(job, "face_reaction_segment_count", report.segment_count)
    _set_job_value(
        job,
        "face_reaction_detected_point_count",
        report.face_detected_point_count,
    )
    _set_job_value(
        job,
        "face_reaction_candidate_count",
        report.reaction_candidate_count,
    )
    _set_job_value(
        job,
        "face_reaction_high_segment_count",
        report.high_reaction_segment_count,
    )
    _set_job_value(
        job,
        "face_reaction_duration_seconds",
        report.duration_seconds,
    )
    _set_job_value(
        job,
        "face_reaction_frame_sample_rate",
        report.frame_sample_rate,
    )
    _set_job_value(
        job,
        "face_reaction_recommendation",
        report.recommendation,
    )

    return job
