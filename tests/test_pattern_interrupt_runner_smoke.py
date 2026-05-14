from __future__ import annotations

from dataclasses import fields

from core.pattern_interrupt_runner import (
    run_pattern_interrupt_for_job,
    store_pattern_interrupt_run_report_to_job,
)
from models.job import Job


def _job_payload(**overrides) -> dict:
    data = {
        "job_id": "job_pattern_interrupt_runner",
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
    start = float(index * 10)
    return {
        "item_id": f"card_pattern_runner_{index}",
        "source_segment_id": f"seg_pattern_runner_{index}",
        "source_start_seconds": start,
        "source_end_seconds": start + duration,
        "duration_seconds": duration,
        "action": "keep_review",
        "content_value_score": score,
        "review_required": True,
        "blocking_errors": [],
        "warnings": [],
    }


def _job_with_pattern_inputs() -> Job:
    items = [_item(index, 10.0, 0.50) for index in range(6)]
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
            dynamic_pacing_suggestions=[
                {
                    "suggestion_id": "runner_dynamic_breathing",
                    "suggestion_type": "missing_breathing_room",
                    "source_item_id": "card_pattern_runner_0",
                    "review_required": True,
                    "can_auto_apply": False,
                }
            ],
        )
    )


def test_runner_writes_pattern_interrupt_job_fields() -> None:
    job = _job_with_pattern_inputs()

    report = run_pattern_interrupt_for_job(job)
    store_pattern_interrupt_run_report_to_job(job, report)

    assert job.pattern_interrupt_status == report.status
    assert job.pattern_interrupt_report["status"] == report.status
    assert job.pattern_interrupt["status"] == report.status
    assert len(job.pattern_interrupt_windows) == len(report.windows)
    assert len(job.pattern_interrupt_suggestions) == len(report.suggestions)
    assert job.pattern_interrupt_total_windows == report.total_windows
    assert job.pattern_interrupt_needed_count == report.interrupt_needed_count
    assert job.pattern_interrupt_monotony_score == report.monotony_score
    assert job.pattern_interrupt_average_window_duration_seconds == (
        report.average_window_duration_seconds
    )
    assert job.pattern_interrupt_recommended_count == (
        report.recommended_interrupt_count
    )
    assert job.pattern_interrupt_review_required is True
    assert job.pattern_interrupt_can_apply is False
    assert job.pattern_interrupt_can_insert_zoom is False
    assert job.pattern_interrupt_can_insert_text_overlay is False
    assert job.pattern_interrupt_can_insert_sfx is False
    assert job.pattern_interrupt_can_reorder_timeline is False
    assert job.pattern_interrupt_can_trim is False
    assert job.pattern_interrupt_can_extend is False
    assert job.pattern_interrupt_can_render is False
    assert job.pattern_interrupt_recommendation == report.recommendation


def test_job_dataclass_contains_pattern_interrupt_fields() -> None:
    job_field_names = {field.name for field in fields(Job)}
    required_fields = {
        "pattern_interrupt_report",
        "pattern_interrupt",
        "pattern_interrupt_status",
        "pattern_interrupt_windows",
        "pattern_interrupt_suggestions",
        "pattern_interrupt_total_windows",
        "pattern_interrupt_needed_count",
        "pattern_interrupt_monotony_score",
        "pattern_interrupt_average_window_duration_seconds",
        "pattern_interrupt_recommended_count",
        "pattern_interrupt_review_required",
        "pattern_interrupt_can_apply",
        "pattern_interrupt_can_insert_zoom",
        "pattern_interrupt_can_insert_text_overlay",
        "pattern_interrupt_can_insert_sfx",
        "pattern_interrupt_can_reorder_timeline",
        "pattern_interrupt_can_trim",
        "pattern_interrupt_can_extend",
        "pattern_interrupt_can_render",
        "pattern_interrupt_blocking_reasons",
        "pattern_interrupt_warnings",
        "pattern_interrupt_recommendation",
    }

    assert required_fields.issubset(job_field_names)


def test_job_from_dict_loads_pattern_interrupt_fields_and_forces_flags_false() -> None:
    job = Job.from_dict(
        _job_payload(
            pattern_interrupt_status="pattern_interrupt_ready_with_warnings",
            pattern_interrupt_report={
                "status": "pattern_interrupt_ready_with_warnings"
            },
            pattern_interrupt={"status": "pattern_interrupt_ready_with_warnings"},
            pattern_interrupt_windows=[
                {"window_id": "pattern_interrupt_window_from_dict"}
            ],
            pattern_interrupt_suggestions=[
                {"suggestion_id": "pattern_interrupt_suggestion_from_dict"}
            ],
            pattern_interrupt_total_windows=2,
            pattern_interrupt_needed_count=1,
            pattern_interrupt_monotony_score=0.75,
            pattern_interrupt_average_window_duration_seconds=60.0,
            pattern_interrupt_recommended_count=3,
            pattern_interrupt_review_required=True,
            pattern_interrupt_can_apply=True,
            pattern_interrupt_can_insert_zoom=True,
            pattern_interrupt_can_insert_text_overlay=True,
            pattern_interrupt_can_insert_sfx=True,
            pattern_interrupt_can_reorder_timeline=True,
            pattern_interrupt_can_trim=True,
            pattern_interrupt_can_extend=True,
            pattern_interrupt_can_render=True,
            pattern_interrupt_blocking_reasons=["continuity_interrupt_blocked"],
            pattern_interrupt_warnings=["missing_visual_variation_signals"],
            pattern_interrupt_recommendation="review_pattern_interrupt_suggestions",
        )
    )

    assert job.pattern_interrupt_status == "pattern_interrupt_ready_with_warnings"
    assert job.pattern_interrupt_windows[0]["window_id"] == (
        "pattern_interrupt_window_from_dict"
    )
    assert job.pattern_interrupt_suggestions[0]["suggestion_id"] == (
        "pattern_interrupt_suggestion_from_dict"
    )
    assert job.pattern_interrupt_total_windows == 2
    assert job.pattern_interrupt_needed_count == 1
    assert job.pattern_interrupt_monotony_score == 0.75
    assert job.pattern_interrupt_average_window_duration_seconds == 60.0
    assert job.pattern_interrupt_recommended_count == 3
    assert job.pattern_interrupt_review_required is True
    assert job.pattern_interrupt_can_apply is False
    assert job.pattern_interrupt_can_insert_zoom is False
    assert job.pattern_interrupt_can_insert_text_overlay is False
    assert job.pattern_interrupt_can_insert_sfx is False
    assert job.pattern_interrupt_can_reorder_timeline is False
    assert job.pattern_interrupt_can_trim is False
    assert job.pattern_interrupt_can_extend is False
    assert job.pattern_interrupt_can_render is False
    assert job.pattern_interrupt_blocking_reasons == ["continuity_interrupt_blocked"]
    assert job.pattern_interrupt_warnings == ["missing_visual_variation_signals"]
