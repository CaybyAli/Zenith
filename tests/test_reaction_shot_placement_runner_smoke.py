from __future__ import annotations

from dataclasses import fields

from core.reaction_shot_placement_runner import (
    run_reaction_shot_placement_for_job,
    store_reaction_shot_placement_run_report_to_job,
)
from models.job import Job


def _job_payload(**overrides) -> dict:
    data = {
        "job_id": "job_reaction_shot_runner",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }
    data.update(overrides)
    return data


def _job_with_reaction_inputs() -> Job:
    return Job.from_dict(
        _job_payload(
            review_timeline_plan_items=[
                {
                    "item_id": "runner_highlight",
                    "segment_id": "runner_highlight_seg",
                    "start_seconds": 10.0,
                    "end_seconds": 14.0,
                    "duration_seconds": 4.0,
                    "action": "highlight",
                    "content_value_score": 0.90,
                    "hook_score": 0.85,
                }
            ],
            face_reaction_segments=[
                {
                    "segment_id": "runner_face_reaction",
                    "start_seconds": 15.0,
                    "end_seconds": 17.0,
                    "duration_seconds": 2.0,
                    "reaction_type": "hype_reaction",
                    "reaction_score": 0.90,
                    "face_reaction_score": 0.95,
                    "expressiveness_score": 0.95,
                }
            ],
        )
    )


def test_runner_writes_reaction_shot_job_fields() -> None:
    job = _job_with_reaction_inputs()

    report = run_reaction_shot_placement_for_job(job)
    store_reaction_shot_placement_run_report_to_job(job, report)

    assert job.reaction_shot_placement_status == report.status
    assert job.reaction_shot_placement_report["status"] == report.status
    assert job.reaction_shot_placement["status"] == report.status

    assert len(job.reaction_shot_candidates) == len(report.candidates)
    assert len(job.reaction_shot_placements) == len(report.placements)

    assert job.reaction_shot_total_candidates == report.total_candidates
    assert job.reaction_shot_total_placements == report.total_placements
    assert job.reaction_shot_best_placement_score == report.best_placement_score
    assert job.reaction_shot_missing_placeholder_count == (
        report.missing_reaction_placeholder_count
    )

    assert job.reaction_shot_review_required is True
    assert job.reaction_shot_can_apply is False
    assert job.reaction_shot_can_move_clip is False
    assert job.reaction_shot_can_insert_clip is False
    assert job.reaction_shot_can_trim is False
    assert job.reaction_shot_can_extend is False
    assert job.reaction_shot_can_reorder_timeline is False
    assert job.reaction_shot_can_render is False

    assert job.reaction_shot_blocking_reasons == list(
        report.blocking_reasons or []
    )
    assert job.reaction_shot_warnings == list(report.warnings or [])
    assert job.reaction_shot_recommendation == report.recommendation


def test_job_dataclass_contains_reaction_shot_fields() -> None:
    job_field_names = {field.name for field in fields(Job)}
    required_fields = {
        "reaction_shot_placement_report",
        "reaction_shot_placement",
        "reaction_shot_placement_status",
        "reaction_shot_candidates",
        "reaction_shot_placements",
        "reaction_shot_total_candidates",
        "reaction_shot_total_placements",
        "reaction_shot_best_placement_score",
        "reaction_shot_missing_placeholder_count",
        "reaction_shot_review_required",
        "reaction_shot_can_apply",
        "reaction_shot_can_move_clip",
        "reaction_shot_can_insert_clip",
        "reaction_shot_can_trim",
        "reaction_shot_can_extend",
        "reaction_shot_can_reorder_timeline",
        "reaction_shot_can_render",
        "reaction_shot_blocking_reasons",
        "reaction_shot_warnings",
        "reaction_shot_recommendation",
    }

    assert required_fields.issubset(job_field_names)


def test_job_from_dict_loads_reaction_shot_fields_and_forces_flags_false() -> None:
    job = Job.from_dict(
        _job_payload(
            reaction_shot_placement_status="reaction_placement_ready_with_warnings",
            reaction_shot_placement_report={
                "status": "reaction_placement_ready_with_warnings"
            },
            reaction_shot_placement={
                "status": "reaction_placement_ready_with_warnings"
            },
            reaction_shot_candidates=[
                {"candidate_id": "reaction_candidate_from_dict"}
            ],
            reaction_shot_placements=[
                {"placement_id": "reaction_placement_from_dict"}
            ],
            reaction_shot_total_candidates=2,
            reaction_shot_total_placements=3,
            reaction_shot_best_placement_score=0.91,
            reaction_shot_missing_placeholder_count=1,
            reaction_shot_review_required=True,
            reaction_shot_can_apply=True,
            reaction_shot_can_move_clip=True,
            reaction_shot_can_insert_clip=True,
            reaction_shot_can_trim=True,
            reaction_shot_can_extend=True,
            reaction_shot_can_reorder_timeline=True,
            reaction_shot_can_render=True,
            reaction_shot_blocking_reasons=[
                "reaction_shot_continuity_blocked"
            ],
            reaction_shot_warnings=[
                "consecutive_reaction_risk",
                "too_short_reaction",
            ],
            reaction_shot_recommendation="review_reaction_shot_placement",
        )
    )

    assert job.reaction_shot_placement_status == (
        "reaction_placement_ready_with_warnings"
    )
    assert job.reaction_shot_candidates[0]["candidate_id"] == (
        "reaction_candidate_from_dict"
    )
    assert job.reaction_shot_placements[0]["placement_id"] == (
        "reaction_placement_from_dict"
    )
    assert job.reaction_shot_total_candidates == 2
    assert job.reaction_shot_total_placements == 3
    assert job.reaction_shot_best_placement_score == 0.91
    assert job.reaction_shot_missing_placeholder_count == 1
    assert job.reaction_shot_review_required is True

    assert job.reaction_shot_can_apply is False
    assert job.reaction_shot_can_move_clip is False
    assert job.reaction_shot_can_insert_clip is False
    assert job.reaction_shot_can_trim is False
    assert job.reaction_shot_can_extend is False
    assert job.reaction_shot_can_reorder_timeline is False
    assert job.reaction_shot_can_render is False

    assert job.reaction_shot_blocking_reasons == [
        "reaction_shot_continuity_blocked"
    ]
    assert job.reaction_shot_warnings == [
        "consecutive_reaction_risk",
        "too_short_reaction",
    ]
    assert job.reaction_shot_recommendation == "review_reaction_shot_placement"