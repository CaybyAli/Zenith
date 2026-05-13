from __future__ import annotations

from typing import Any

from core.emotional_arc_builder import build_emotional_arc_for_job
from models.emotional_arc import (
    EMOTIONAL_ARC_RECOMMENDATION_FAILED,
    EMOTIONAL_ARC_STATUS_FAILED,
    EmotionalArcReport,
)


def _get_job_value(job: Any, key: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(key, default)
    return getattr(job, key, default)


def _set_job_value(job: Any, key: str, value: Any) -> None:
    if isinstance(job, dict):
        job[key] = value
        return
    setattr(job, key, value)


def run_emotional_arc_builder_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> EmotionalArcReport:
    run_metadata = {
        "phase": "2B-38",
        "block": "block7_story_pacing",
        "review_only": True,
        "emotional_arc_only": True,
        "media_unchanged": True,
        "no_execution_in_2b_38": True,
        "no_render_in_2b_38": True,
        "no_timeline_reorder_in_2b_38": True,
        "no_arc_apply_in_2b_38": True,
        **dict(metadata or {}),
    }

    try:
        return build_emotional_arc_for_job(
            job,
            metadata=run_metadata,
        )
    except Exception as exc:
        report = EmotionalArcReport(
            job_id=_get_job_value(job, "job_id"),
            status=EMOTIONAL_ARC_STATUS_FAILED,
            arc_points=[],
            suggestions=[],
            warnings=[],
            blocking_reasons=["emotional_arc_failed"],
            recommendation=EMOTIONAL_ARC_RECOMMENDATION_FAILED,
            metadata={
                **run_metadata,
                "source": "emotional_arc_runner",
                "error": str(exc),
            },
        )
        report.enforce_review_only()
        return report


def apply_emotional_arc_run_report_to_job(
    job: Any,
    report: EmotionalArcReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = EmotionalArcReport.from_dict(report)

    report.enforce_review_only()
    report_dict = report.to_dict()
    arc_points = [point.to_dict() for point in report.arc_points]
    suggestions = [suggestion.to_dict() for suggestion in report.suggestions]

    _set_job_value(job, "emotional_arc_report", report_dict)
    _set_job_value(job, "emotional_arc", report_dict)
    _set_job_value(job, "emotional_arc_status", report.status)
    _set_job_value(job, "emotional_arc_points", arc_points)
    _set_job_value(job, "emotional_arc_suggestions", suggestions)
    _set_job_value(
        job,
        "emotional_arc_average_deviation",
        float(report.average_deviation or 0.0),
    )
    _set_job_value(
        job,
        "emotional_arc_max_deviation",
        float(report.max_deviation or 0.0),
    )
    _set_job_value(
        job,
        "emotional_arc_flatness_score",
        float(report.flatness_score or 0.0),
    )
    _set_job_value(
        job,
        "emotional_arc_hook_strength_score",
        float(report.hook_strength_score or 0.0),
    )
    _set_job_value(
        job,
        "emotional_arc_climax_strength_score",
        float(report.climax_strength_score or 0.0),
    )
    _set_job_value(
        job,
        "emotional_arc_breathing_room_score",
        float(report.breathing_room_score or 0.0),
    )
    _set_job_value(job, "emotional_arc_review_required", True)
    _set_job_value(job, "emotional_arc_can_apply", False)
    _set_job_value(job, "emotional_arc_can_reorder_timeline", False)
    _set_job_value(job, "emotional_arc_can_trim", False)
    _set_job_value(job, "emotional_arc_can_extend", False)
    _set_job_value(job, "emotional_arc_can_render", False)
    _set_job_value(
        job,
        "emotional_arc_blocking_reasons",
        list(report.blocking_reasons or []),
    )
    _set_job_value(job, "emotional_arc_warnings", list(report.warnings or []))
    _set_job_value(job, "emotional_arc_recommendation", report.recommendation)

    if hasattr(job, "touch"):
        job.touch()

    return job
