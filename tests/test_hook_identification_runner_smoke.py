from __future__ import annotations

from dataclasses import fields

from core.hook_identification_runner import (
    apply_hook_identification_run_report_to_job,
    run_hook_identification_for_job,
)
from models.job import Job


def _job_payload(**overrides) -> dict:
    data = {
        "job_id": "job_hook_runner",
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


def _job_with_hook_inputs() -> Job:
    return Job.from_dict(
        _job_payload(
            review_timeline_dashboard_package_report={
                "status": "ready_for_dashboard",
                "dashboard_package": {
                    "package_status": "ready_for_dashboard",
                    "item_cards": [
                        {
                            "item_id": "card_runner",
                            "source_segment_id": "seg_runner",
                            "source_start_seconds": 2.0,
                            "source_end_seconds": 7.0,
                            "duration_seconds": 5.0,
                            "action": "keep_review",
                            "review_required": True,
                            "blocking_errors": [],
                        }
                    ],
                },
            },
            energy_peak_report={
                "peaks": [
                    {
                        "segment_id": "seg_runner",
                        "start_seconds": 2.0,
                        "end_seconds": 7.0,
                        "peak_score": 0.85,
                    }
                ]
            },
            keyword_emotion_report={
                "segment_scores": [
                    {
                        "segment_id": "seg_runner",
                        "shock_score": 0.8,
                        "emotion_score": 0.8,
                    }
                ]
            },
        )
    )


def test_runner_writes_hook_job_fields() -> None:
    job = _job_with_hook_inputs()

    report = run_hook_identification_for_job(job)
    apply_hook_identification_run_report_to_job(job, report)

    assert job.hook_identification_status == "hook_candidate_found"
    assert job.hook_identification_report["status"] == "hook_candidate_found"
    assert job.hook_identification["status"] == "hook_candidate_found"
    assert len(job.hook_candidates) == 1
    assert job.hook_selected_candidate["source_segment_id"] == "seg_runner"
    assert job.hook_best_score == report.best_hook_score
    assert job.hook_review_required is True
    assert job.hook_can_apply is False
    assert job.hook_can_reorder_timeline is False
    assert job.hook_can_render is False
    assert job.hook_recommendation == "review_hook_candidate"


def test_job_dataclass_contains_hook_fields() -> None:
    job_field_names = {field.name for field in fields(Job)}
    required_fields = {
        "hook_identification_report",
        "hook_identification",
        "hook_identification_status",
        "hook_candidates",
        "hook_selected_candidate",
        "hook_best_score",
        "hook_review_required",
        "hook_can_apply",
        "hook_can_reorder_timeline",
        "hook_can_render",
        "hook_blocking_reasons",
        "hook_warnings",
        "hook_recommendation",
    }

    assert required_fields.issubset(job_field_names)


def test_job_from_dict_loads_hook_fields_and_forces_execution_flags_false() -> None:
    job = Job.from_dict(
        _job_payload(
            hook_identification_status="hook_candidate_found",
            hook_identification_report={"status": "hook_candidate_found"},
            hook_identification={"status": "hook_candidate_found"},
            hook_candidates=[{"candidate_id": "hook_candidate_from_dict"}],
            hook_selected_candidate={"candidate_id": "hook_candidate_from_dict"},
            hook_best_score=0.91,
            hook_review_required=True,
            hook_can_apply=True,
            hook_can_reorder_timeline=True,
            hook_can_render=True,
            hook_blocking_reasons=["review_required"],
            hook_warnings=["duration_warning"],
            hook_recommendation="review_hook_candidate",
        )
    )

    assert job.hook_identification_status == "hook_candidate_found"
    assert job.hook_candidates[0]["candidate_id"] == "hook_candidate_from_dict"
    assert job.hook_selected_candidate["candidate_id"] == "hook_candidate_from_dict"
    assert job.hook_best_score == 0.91
    assert job.hook_review_required is True
    assert job.hook_can_apply is False
    assert job.hook_can_reorder_timeline is False
    assert job.hook_can_render is False
    assert job.hook_blocking_reasons == ["review_required"]
    assert job.hook_warnings == ["duration_warning"]
