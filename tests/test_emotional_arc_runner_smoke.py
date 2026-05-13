from __future__ import annotations

from dataclasses import fields

from core.emotional_arc_runner import (
    apply_emotional_arc_run_report_to_job,
    run_emotional_arc_builder_for_job,
)
from models.job import Job


def _job_payload(**overrides) -> dict:
    data = {
        "job_id": "job_emotional_arc_runner",
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


def _item(index: int, score: float) -> dict:
    return {
        "item_id": f"card_runner_{index}",
        "source_segment_id": f"seg_runner_{index}",
        "source_start_seconds": float(index * 5),
        "source_end_seconds": float(index * 5 + 5),
        "duration_seconds": 5.0,
        "action": "keep_review",
        "content_value_score": score,
        "review_required": True,
        "blocking_errors": [],
        "warnings": [],
    }


def _job_with_arc_inputs() -> Job:
    items = [_item(index, score) for index, score in enumerate([0.95, 0.55, 0.65, 0.85])]
    return Job.from_dict(
        _job_payload(
            review_timeline_dashboard_package_report={
                "status": "ready_for_dashboard",
                "dashboard_package": {
                    "package_status": "ready_for_dashboard",
                    "item_cards": items,
                    "blocking_errors": [],
                    "warnings": [],
                },
            },
            hook_identification_report={
                "status": "hook_candidate_found",
                "selected_candidate": {
                    "candidate_id": "hook_candidate_runner",
                    "source_item_id": "card_runner_0",
                    "source_segment_id": "seg_runner_0",
                    "hook_score": 0.95,
                    "confidence": 0.95,
                    "review_required": True,
                },
                "candidates": [],
                "review_required": True,
                "can_apply_hook": False,
                "can_reorder_timeline": False,
                "can_render": False,
            },
        )
    )


def test_runner_writes_emotional_arc_job_fields() -> None:
    job = _job_with_arc_inputs()

    report = run_emotional_arc_builder_for_job(job)
    apply_emotional_arc_run_report_to_job(job, report)

    assert job.emotional_arc_status == report.status
    assert job.emotional_arc_report["status"] == report.status
    assert job.emotional_arc["status"] == report.status
    assert len(job.emotional_arc_points) == len(report.arc_points)
    assert len(job.emotional_arc_suggestions) == len(report.suggestions)
    assert job.emotional_arc_average_deviation == report.average_deviation
    assert job.emotional_arc_max_deviation == report.max_deviation
    assert job.emotional_arc_flatness_score == report.flatness_score
    assert job.emotional_arc_hook_strength_score == report.hook_strength_score
    assert job.emotional_arc_climax_strength_score == report.climax_strength_score
    assert job.emotional_arc_breathing_room_score == report.breathing_room_score
    assert job.emotional_arc_review_required is True
    assert job.emotional_arc_can_apply is False
    assert job.emotional_arc_can_reorder_timeline is False
    assert job.emotional_arc_can_trim is False
    assert job.emotional_arc_can_extend is False
    assert job.emotional_arc_can_render is False
    assert job.emotional_arc_recommendation == report.recommendation


def test_job_dataclass_contains_emotional_arc_fields() -> None:
    job_field_names = {field.name for field in fields(Job)}
    required_fields = {
        "emotional_arc_report",
        "emotional_arc",
        "emotional_arc_status",
        "emotional_arc_points",
        "emotional_arc_suggestions",
        "emotional_arc_average_deviation",
        "emotional_arc_max_deviation",
        "emotional_arc_flatness_score",
        "emotional_arc_hook_strength_score",
        "emotional_arc_climax_strength_score",
        "emotional_arc_breathing_room_score",
        "emotional_arc_review_required",
        "emotional_arc_can_apply",
        "emotional_arc_can_reorder_timeline",
        "emotional_arc_can_trim",
        "emotional_arc_can_extend",
        "emotional_arc_can_render",
        "emotional_arc_blocking_reasons",
        "emotional_arc_warnings",
        "emotional_arc_recommendation",
    }

    assert required_fields.issubset(job_field_names)


def test_job_from_dict_loads_emotional_arc_fields_and_forces_flags_false() -> None:
    job = Job.from_dict(
        _job_payload(
            emotional_arc_status="arc_analysis_ready_with_warnings",
            emotional_arc_report={"status": "arc_analysis_ready_with_warnings"},
            emotional_arc={"status": "arc_analysis_ready_with_warnings"},
            emotional_arc_points=[{"point_id": "emotional_arc_point_from_dict"}],
            emotional_arc_suggestions=[
                {"suggestion_id": "emotional_arc_suggestion_from_dict"}
            ],
            emotional_arc_average_deviation=0.12,
            emotional_arc_max_deviation=0.31,
            emotional_arc_flatness_score=0.8,
            emotional_arc_hook_strength_score=0.72,
            emotional_arc_climax_strength_score=0.9,
            emotional_arc_breathing_room_score=0.55,
            emotional_arc_review_required=True,
            emotional_arc_can_apply=True,
            emotional_arc_can_reorder_timeline=True,
            emotional_arc_can_trim=True,
            emotional_arc_can_extend=True,
            emotional_arc_can_render=True,
            emotional_arc_blocking_reasons=["continuity_arc_blocked"],
            emotional_arc_warnings=["using_emotional_arc_fallback_score"],
            emotional_arc_recommendation="review_emotional_arc_suggestions",
        )
    )

    assert job.emotional_arc_status == "arc_analysis_ready_with_warnings"
    assert job.emotional_arc_points[0]["point_id"] == "emotional_arc_point_from_dict"
    assert job.emotional_arc_suggestions[0]["suggestion_id"] == (
        "emotional_arc_suggestion_from_dict"
    )
    assert job.emotional_arc_average_deviation == 0.12
    assert job.emotional_arc_max_deviation == 0.31
    assert job.emotional_arc_flatness_score == 0.8
    assert job.emotional_arc_hook_strength_score == 0.72
    assert job.emotional_arc_climax_strength_score == 0.9
    assert job.emotional_arc_breathing_room_score == 0.55
    assert job.emotional_arc_review_required is True
    assert job.emotional_arc_can_apply is False
    assert job.emotional_arc_can_reorder_timeline is False
    assert job.emotional_arc_can_trim is False
    assert job.emotional_arc_can_extend is False
    assert job.emotional_arc_can_render is False
    assert job.emotional_arc_blocking_reasons == ["continuity_arc_blocked"]
    assert job.emotional_arc_warnings == ["using_emotional_arc_fallback_score"]
