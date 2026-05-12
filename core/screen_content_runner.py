from __future__ import annotations

from typing import Any

from core.screen_content_classifier import classify_screen_content
from core.screen_content_source_selector import select_screen_content_source
from models.screen_content_run import (
    SCREEN_CONTENT_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    SCREEN_CONTENT_RUN_STATUS_FAILED,
    SCREEN_CONTENT_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    ScreenContentRunReport,
)
from models.screen_content_source import (
    SCREEN_CONTENT_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    SCREEN_CONTENT_SOURCE_STATUS_FAILED,
    SCREEN_CONTENT_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE,
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
) -> ScreenContentRunReport:
    return ScreenContentRunReport(
        status=status,
        source="screen_content_runner",
        source_selection=source_selection,
        selected_path=source_selection.selected_path,
        selected_type=source_selection.selected_type,
        screen_content_result=None,
        screen_content_points=[],
        screen_content_segments=[],
        point_count=0,
        segment_count=0,
        gameplay_segment_count=0,
        menu_segment_count=0,
        loading_segment_count=0,
        scoreboard_segment_count=0,
        death_screen_segment_count=0,
        victory_screen_segment_count=0,
        black_screen_segment_count=0,
        duration_seconds=None,
        frame_sample_rate=frame_sample_rate,
        recommendation=source_selection.recommendation,
        warnings=list(source_selection.warnings),
        errors=list(source_selection.errors),
        metadata={"source_selector_status": source_selection.status},
    )


def _build_report_from_screen_content_result(
    source_selection: Any,
    screen_content_result: Any,
) -> ScreenContentRunReport:
    return ScreenContentRunReport(
        status=screen_content_result.status,
        source="screen_content_runner",
        source_selection=source_selection,
        selected_path=source_selection.selected_path,
        selected_type=source_selection.selected_type,
        screen_content_result=screen_content_result,
        screen_content_points=_result_points_as_dicts(screen_content_result),
        screen_content_segments=_result_segments_as_dicts(screen_content_result),
        point_count=screen_content_result.point_count,
        segment_count=screen_content_result.segment_count,
        gameplay_segment_count=screen_content_result.gameplay_segment_count,
        menu_segment_count=screen_content_result.menu_segment_count,
        loading_segment_count=screen_content_result.loading_segment_count,
        scoreboard_segment_count=screen_content_result.scoreboard_segment_count,
        death_screen_segment_count=screen_content_result.death_screen_segment_count,
        victory_screen_segment_count=screen_content_result.victory_screen_segment_count,
        black_screen_segment_count=screen_content_result.black_screen_segment_count,
        duration_seconds=screen_content_result.duration_seconds,
        frame_sample_rate=screen_content_result.frame_sample_rate,
        recommendation=screen_content_result.recommendation,
        warnings=list(source_selection.warnings) + list(screen_content_result.warnings),
        errors=list(source_selection.errors) + list(screen_content_result.errors),
        metadata={
            "source_selector_status": source_selection.status,
            "screen_content_classifier_status": screen_content_result.status,
        },
    )


def run_screen_content_classification_for_job(
    job: Any,
    frame_sample_rate: float = 2.0,
    resize_width: int = 320,
    resize_height: int = 180,
    black_brightness_threshold: float = 0.08,
    ui_density_threshold: float = 0.35,
    text_like_threshold: float = 0.25,
    confidence_threshold: float = 0.50,
) -> ScreenContentRunReport:
    try:
        source_selection = select_screen_content_source(job)

        if source_selection.status == SCREEN_CONTENT_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE:
            return _build_report_from_blocked_source(
                status=SCREEN_CONTENT_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
                source_selection=source_selection,
                frame_sample_rate=frame_sample_rate,
            )

        if source_selection.status == SCREEN_CONTENT_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE:
            return _build_report_from_blocked_source(
                status=SCREEN_CONTENT_RUN_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
                source_selection=source_selection,
                frame_sample_rate=frame_sample_rate,
            )

        if source_selection.status == SCREEN_CONTENT_SOURCE_STATUS_FAILED:
            return _build_report_from_blocked_source(
                status=SCREEN_CONTENT_RUN_STATUS_FAILED,
                source_selection=source_selection,
                frame_sample_rate=frame_sample_rate,
            )

        if not source_selection.selected_path:
            return _build_report_from_blocked_source(
                status=SCREEN_CONTENT_RUN_STATUS_SKIPPED_NO_VIDEO_SOURCE,
                source_selection=source_selection,
                frame_sample_rate=frame_sample_rate,
            )

        screen_content_result = classify_screen_content(
            input_path=source_selection.selected_path,
            frame_sample_rate=frame_sample_rate,
            resize_width=resize_width,
            resize_height=resize_height,
            black_brightness_threshold=black_brightness_threshold,
            ui_density_threshold=ui_density_threshold,
            text_like_threshold=text_like_threshold,
            confidence_threshold=confidence_threshold,
        )

        return _build_report_from_screen_content_result(
            source_selection=source_selection,
            screen_content_result=screen_content_result,
        )

    except Exception as exc:
        return ScreenContentRunReport(
            status=SCREEN_CONTENT_RUN_STATUS_FAILED,
            source="screen_content_runner",
            source_selection=None,
            selected_path=None,
            selected_type=None,
            screen_content_result=None,
            screen_content_points=[],
            screen_content_segments=[],
            point_count=0,
            segment_count=0,
            gameplay_segment_count=0,
            menu_segment_count=0,
            loading_segment_count=0,
            scoreboard_segment_count=0,
            death_screen_segment_count=0,
            victory_screen_segment_count=0,
            black_screen_segment_count=0,
            duration_seconds=None,
            frame_sample_rate=frame_sample_rate,
            recommendation="review_screen_content_runner_error",
            warnings=[],
            errors=[f"screen_content_runner_failed: {exc}"],
            metadata={},
        )


def apply_screen_content_run_report_to_job(
    job: Any,
    report: ScreenContentRunReport,
) -> Any:
    report_dict = report.to_dict()

    _set_job_value(job, "screen_content_report", report_dict)
    _set_job_value(job, "screen_content_status", report.status)
    _set_job_value(job, "screen_content_selected_path", report.selected_path)
    _set_job_value(job, "screen_content_selected_type", report.selected_type)
    _set_job_value(
        job,
        "screen_content_result",
        report.screen_content_result.to_dict()
        if report.screen_content_result
        else {},
    )
    _set_job_value(job, "screen_content_points", list(report.screen_content_points))
    _set_job_value(job, "screen_content_segments", list(report.screen_content_segments))
    _set_job_value(job, "screen_content_point_count", report.point_count)
    _set_job_value(job, "screen_content_segment_count", report.segment_count)
    _set_job_value(
        job,
        "screen_content_gameplay_segment_count",
        report.gameplay_segment_count,
    )
    _set_job_value(
        job,
        "screen_content_menu_segment_count",
        report.menu_segment_count,
    )
    _set_job_value(
        job,
        "screen_content_loading_segment_count",
        report.loading_segment_count,
    )
    _set_job_value(
        job,
        "screen_content_scoreboard_segment_count",
        report.scoreboard_segment_count,
    )
    _set_job_value(
        job,
        "screen_content_death_screen_segment_count",
        report.death_screen_segment_count,
    )
    _set_job_value(
        job,
        "screen_content_victory_screen_segment_count",
        report.victory_screen_segment_count,
    )
    _set_job_value(
        job,
        "screen_content_black_screen_segment_count",
        report.black_screen_segment_count,
    )
    _set_job_value(
        job,
        "screen_content_duration_seconds",
        report.duration_seconds,
    )
    _set_job_value(
        job,
        "screen_content_frame_sample_rate",
        report.frame_sample_rate,
    )
    _set_job_value(
        job,
        "screen_content_recommendation",
        report.recommendation,
    )

    return job
