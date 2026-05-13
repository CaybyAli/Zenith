from __future__ import annotations

from dataclasses import fields

from core.dynamic_pacing_runner import (
    apply_dynamic_pacing_run_report_to_job,
    run_dynamic_pacing_for_job,
)
from models.job import Job


def _job_payload(**overrides) -> dict:
    data = {
        "job_id": "job_dynamic_pacing_runner",
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


def _item(index: int, duration: float, score: float) -> dict:
    start = float(index * 5)
    return {
        "item_id": f"card_pacing_runner_{index}",
        "source_segment_id": f"seg_pacing_runner_{index}",
        "source_start_seconds": start,
        "source_end_seconds": start + duration,
        "duration_seconds": duration,
        "action": "keep_review",
        "content_value_score": score,
        "review_required": True,
        "blocking_errors": [],
        "warnings": [],
    }


def _job_with_pacing_inputs() -> Job:
    items = [
        _item(0, 6.0, 0.90),
        _item(1, 4.0, 0.65),
        _item(2, 2.0, 0.30),
    ]
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
            emotional_arc_points=[
                {
                    "point_id": "arc_runner_0",
                    "source_item_id": "card_pacing_runner_0",
                    "source_segment_id": "seg_pacing_runner_0",
                    "start_seconds": 0.0,
                    "end_seconds": 6.0,
                    "duration_seconds": 6.0,
                    "actual_energy_score": 0.90,
                    "arc_phase": "climax",
                }
            ],
        )
    )


def test_runner_writes_dynamic_pacing_job_fields() -> None:
    job = _job_with_pacing_inputs()

    report = run_dynamic_pacing_for_job(job)
    apply_dynamic_pacing_run_report_to_job(job, report)

    assert job.dynamic_pacing_status == report.status
    assert job.dynamic_pacing_report["status"] == report.status
    assert job.dynamic_pacing["status"] == report.status
    assert len(job.dynamic_pacing_segments) == len(report.pacing_segments)
    assert len(job.dynamic_pacing_suggestions) == len(report.suggestions)
    assert job.dynamic_pacing_average_cut_rate == report.average_cut_rate
    assert job.dynamic_pacing_target_cut_rate_range == report.target_cut_rate_range
    assert job.dynamic_pacing_match_score == report.pacing_match_score
    assert job.dynamic_pacing_monotony_score == report.monotony_score
    assert job.dynamic_pacing_breathing_room_score == report.breathing_room_score
    assert job.dynamic_pacing_fast_run_count == report.fast_run_count
    assert job.dynamic_pacing_slow_run_count == report.slow_run_count
    assert job.dynamic_pacing_review_required is True
    assert job.dynamic_pacing_can_apply is False
    assert job.dynamic_pacing_can_split_clips is False
    assert job.dynamic_pacing_can_merge_clips is False
    assert job.dynamic_pacing_can_trim is False
    assert job.dynamic_pacing_can_extend is False
    assert job.dynamic_pacing_can_reorder_timeline is False
    assert job.dynamic_pacing_can_render is False
    assert job.dynamic_pacing_recommendation == report.recommendation


def test_job_dataclass_contains_dynamic_pacing_fields() -> None:
    job_field_names = {field.name for field in fields(Job)}
    required_fields = {
        "dynamic_pacing_report",
        "dynamic_pacing",
        "dynamic_pacing_status",
        "dynamic_pacing_segments",
        "dynamic_pacing_suggestions",
        "dynamic_pacing_average_cut_rate",
        "dynamic_pacing_target_cut_rate_range",
        "dynamic_pacing_match_score",
        "dynamic_pacing_monotony_score",
        "dynamic_pacing_breathing_room_score",
        "dynamic_pacing_fast_run_count",
        "dynamic_pacing_slow_run_count",
        "dynamic_pacing_review_required",
        "dynamic_pacing_can_apply",
        "dynamic_pacing_can_split_clips",
        "dynamic_pacing_can_merge_clips",
        "dynamic_pacing_can_trim",
        "dynamic_pacing_can_extend",
        "dynamic_pacing_can_reorder_timeline",
        "dynamic_pacing_can_render",
        "dynamic_pacing_blocking_reasons",
        "dynamic_pacing_warnings",
        "dynamic_pacing_recommendation",
    }

    assert required_fields.issubset(job_field_names)


def test_job_from_dict_loads_dynamic_pacing_fields_and_forces_flags_false() -> None:
    job = Job.from_dict(
        _job_payload(
            dynamic_pacing_status="pacing_analysis_ready_with_warnings",
            dynamic_pacing_report={"status": "pacing_analysis_ready_with_warnings"},
            dynamic_pacing={"status": "pacing_analysis_ready_with_warnings"},
            dynamic_pacing_segments=[{"segment_id": "pacing_segment_from_dict"}],
            dynamic_pacing_suggestions=[
                {"suggestion_id": "pacing_suggestion_from_dict"}
            ],
            dynamic_pacing_average_cut_rate=18.5,
            dynamic_pacing_target_cut_rate_range={"min": 4.0, "max": 40.0},
            dynamic_pacing_match_score=0.75,
            dynamic_pacing_monotony_score=0.25,
            dynamic_pacing_breathing_room_score=0.5,
            dynamic_pacing_fast_run_count=3,
            dynamic_pacing_slow_run_count=2,
            dynamic_pacing_review_required=True,
            dynamic_pacing_can_apply=True,
            dynamic_pacing_can_split_clips=True,
            dynamic_pacing_can_merge_clips=True,
            dynamic_pacing_can_trim=True,
            dynamic_pacing_can_extend=True,
            dynamic_pacing_can_reorder_timeline=True,
            dynamic_pacing_can_render=True,
            dynamic_pacing_blocking_reasons=["continuity_pacing_blocked"],
            dynamic_pacing_warnings=["using_dynamic_pacing_fallback_score"],
            dynamic_pacing_recommendation="review_dynamic_pacing_suggestions",
        )
    )

    assert job.dynamic_pacing_status == "pacing_analysis_ready_with_warnings"
    assert job.dynamic_pacing_segments[0]["segment_id"] == "pacing_segment_from_dict"
    assert job.dynamic_pacing_suggestions[0]["suggestion_id"] == (
        "pacing_suggestion_from_dict"
    )
    assert job.dynamic_pacing_average_cut_rate == 18.5
    assert job.dynamic_pacing_target_cut_rate_range == {"min": 4.0, "max": 40.0}
    assert job.dynamic_pacing_match_score == 0.75
    assert job.dynamic_pacing_monotony_score == 0.25
    assert job.dynamic_pacing_breathing_room_score == 0.5
    assert job.dynamic_pacing_fast_run_count == 3
    assert job.dynamic_pacing_slow_run_count == 2
    assert job.dynamic_pacing_review_required is True
    assert job.dynamic_pacing_can_apply is False
    assert job.dynamic_pacing_can_split_clips is False
    assert job.dynamic_pacing_can_merge_clips is False
    assert job.dynamic_pacing_can_trim is False
    assert job.dynamic_pacing_can_extend is False
    assert job.dynamic_pacing_can_reorder_timeline is False
    assert job.dynamic_pacing_can_render is False
    assert job.dynamic_pacing_blocking_reasons == ["continuity_pacing_blocked"]
    assert job.dynamic_pacing_warnings == ["using_dynamic_pacing_fallback_score"]
