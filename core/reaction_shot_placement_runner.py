from __future__ import annotations

from typing import Any

from core.reaction_shot_placement_engine import ReactionShotPlacementEngine
from models.reaction_shot_placement import (
    REACTION_SHOT_RECOMMENDATION_FAILED,
    REACTION_SHOT_STATUS_FAILED,
    ReactionShotPlacementReport,
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


def run_reaction_shot_placement_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> ReactionShotPlacementReport:
    run_metadata = {
        "phase": "2B-41",
        "block": "block7_story_pacing",
        "review_only": True,
        "reaction_shot_placement_only": True,
        "media_unchanged": True,
        "no_execution_in_2b_41": True,
        "no_render_in_2b_41": True,
        "no_timeline_reorder_in_2b_41": True,
        "no_reaction_apply_in_2b_41": True,
        "no_reaction_insert_in_2b_41": True,
        "no_facecam_move_in_2b_41": True,
        "no_zoom_insert_in_2b_41": True,
        **dict(metadata or {}),
    }

    try:
        engine = ReactionShotPlacementEngine()
        report = engine.build_report(job)
        report.metadata.update(run_metadata)
        report.enforce_review_only()
        report.refresh_metrics()
        return report
    except Exception as exc:
        report = ReactionShotPlacementReport(
            job_id=_get_job_value(job, "job_id"),
            status=REACTION_SHOT_STATUS_FAILED,
            candidates=[],
            placements=[],
            warnings=[],
            blocking_reasons=["reaction_shot_placement_failed"],
            recommendation=REACTION_SHOT_RECOMMENDATION_FAILED,
            metadata={
                **run_metadata,
                "source": "reaction_shot_placement_runner",
                "error": str(exc),
            },
        )
        report.enforce_review_only()
        report.refresh_metrics()
        return report


def store_reaction_shot_placement_run_report_to_job(
    job: Any,
    report: ReactionShotPlacementReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = ReactionShotPlacementReport.from_dict(report)

    report.enforce_review_only()
    report.refresh_metrics()

    report_dict = report.to_dict()
    candidates = [candidate.to_dict() for candidate in report.candidates]
    placements = [placement.to_dict() for placement in report.placements]

    _set_job_value(job, "reaction_shot_placement_report", report_dict)
    _set_job_value(job, "reaction_shot_placement", report_dict)
    _set_job_value(job, "reaction_shot_placement_status", report.status)

    _set_job_value(job, "reaction_shot_candidates", candidates)
    _set_job_value(job, "reaction_shot_placements", placements)

    _set_job_value(
        job,
        "reaction_shot_total_candidates",
        int(report.total_candidates),
    )
    _set_job_value(
        job,
        "reaction_shot_total_placements",
        int(report.total_placements),
    )
    _set_job_value(
        job,
        "reaction_shot_best_placement_score",
        float(report.best_placement_score or 0.0),
    )
    _set_job_value(
        job,
        "reaction_shot_missing_placeholder_count",
        int(report.missing_reaction_placeholder_count),
    )

    _set_job_value(job, "reaction_shot_review_required", True)

    _set_job_value(job, "reaction_shot_can_apply", False)
    _set_job_value(job, "reaction_shot_can_move_clip", False)
    _set_job_value(job, "reaction_shot_can_insert_clip", False)
    _set_job_value(job, "reaction_shot_can_trim", False)
    _set_job_value(job, "reaction_shot_can_extend", False)
    _set_job_value(job, "reaction_shot_can_reorder_timeline", False)
    _set_job_value(job, "reaction_shot_can_render", False)

    _set_job_value(
        job,
        "reaction_shot_blocking_reasons",
        list(report.blocking_reasons or []),
    )
    _set_job_value(
        job,
        "reaction_shot_warnings",
        list(report.warnings or []),
    )
    _set_job_value(
        job,
        "reaction_shot_recommendation",
        report.recommendation,
    )

    if hasattr(job, "touch"):
        job.touch()

    return job
