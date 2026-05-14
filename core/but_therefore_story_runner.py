from __future__ import annotations

from typing import Any

from core.but_therefore_story_engine import ButThereforeStoryEngine
from models.but_therefore_story import (
    ButThereforeStoryReport,
    STORY_RECOMMENDATION_FAILED,
    STORY_STATUS_FAILED,
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


def run_but_therefore_story_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> ButThereforeStoryReport:
    run_metadata = {
        "phase": "2B-42",
        "block": "block7_story_pacing",
        "review_only": True,
        "but_therefore_story_only": True,
        "media_unchanged": True,
        "no_execution_in_2b_42": True,
        "no_render_in_2b_42": True,
        "no_timeline_reorder_in_2b_42": True,
        "no_story_apply_in_2b_42": True,
        "no_and_moment_remove_in_2b_42": True,
        **dict(metadata or {}),
    }

    try:
        engine = ButThereforeStoryEngine()
        report = engine.build_report(job)
        report.metadata.update(run_metadata)
        report.enforce_review_only()
        report.refresh_metrics()
        return report
    except Exception as exc:
        report = ButThereforeStoryReport(
            job_id=_get_job_value(job, "job_id"),
            status=STORY_STATUS_FAILED,
            moments=[],
            transitions=[],
            suggestions=[],
            warnings=[],
            blocking_reasons=["but_therefore_story_failed"],
            recommendation=STORY_RECOMMENDATION_FAILED,
            metadata={
                **run_metadata,
                "source": "but_therefore_story_runner",
                "error": str(exc),
            },
        )
        report.enforce_review_only()
        report.refresh_metrics()
        return report


def store_but_therefore_story_run_report_to_job(
    job: Any,
    report: ButThereforeStoryReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = ButThereforeStoryReport.from_dict(report)

    report.enforce_review_only()
    report.refresh_metrics()

    report_dict = report.to_dict()
    moments = [moment.to_dict() for moment in report.moments]
    transitions = [transition.to_dict() for transition in report.transitions]

    _set_job_value(job, "but_therefore_story_report", report_dict)
    _set_job_value(job, "but_therefore_story", report_dict)
    _set_job_value(job, "but_therefore_story_status", report.status)

    _set_job_value(job, "story_moments", moments)
    _set_job_value(job, "story_transitions", transitions)
    _set_job_value(job, "story_suggestions", list(report.suggestions or []))

    _set_job_value(job, "story_total_moments", int(report.total_moments))
    _set_job_value(job, "story_but_count", int(report.but_count))
    _set_job_value(job, "story_therefore_count", int(report.therefore_count))
    _set_job_value(job, "story_and_count", int(report.and_count))
    _set_job_value(job, "story_reaction_count", int(report.reaction_count))
    _set_job_value(job, "story_payoff_count", int(report.payoff_count))
    _set_job_value(job, "story_strong_count", int(report.strong_story_count))

    _set_job_value(
        job,
        "story_but_therefore_ratio",
        float(report.but_therefore_ratio or 0.0),
    )
    _set_job_value(
        job,
        "story_flow_score",
        float(report.story_flow_score or 0.0),
    )
    _set_job_value(job, "story_and_streak_max", int(report.and_streak_max))
    _set_job_value(
        job,
        "story_orphan_reaction_count",
        int(report.orphan_reaction_count),
    )
    _set_job_value(
        job,
        "story_missing_payoff_count",
        int(report.missing_payoff_count),
    )

    _set_job_value(job, "story_review_required", True)

    _set_job_value(job, "story_can_apply_changes", False)
    _set_job_value(job, "story_can_remove_and_moments", False)
    _set_job_value(job, "story_can_reorder_timeline", False)
    _set_job_value(job, "story_can_trim", False)
    _set_job_value(job, "story_can_extend", False)
    _set_job_value(job, "story_can_render", False)

    _set_job_value(
        job,
        "story_blocking_reasons",
        list(report.blocking_reasons or []),
    )
    _set_job_value(
        job,
        "story_warnings",
        list(report.warnings or []),
    )
    _set_job_value(job, "story_recommendation", report.recommendation)

    if hasattr(job, "touch"):
        job.touch()

    return job
