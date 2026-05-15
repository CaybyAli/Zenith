from __future__ import annotations

from core.style_dna_apply_plan_runner import run_style_dna_apply_plan_for_job
from models.job import Job


def _job() -> Job:
    job = Job.from_dict({"job_id": "job_runner_2b62"})
    job.style_dna_profile_name = "gaming_main"
    job.existing_style_dna_snapshot = {"preferred_hook_energy_min": 0.85}
    job.style_dna_review_status = "style_dna_review_approved"
    job.style_dna_review_ready_for_later_apply = True
    job.style_dna_review_blocking_reasons = []
    job.style_dna_review_gate_report = {
        "report_id": "review_report_runner",
        "status": "style_dna_review_approved",
    }
    job.style_dna_review_gate = {"gate_id": "gate_runner"}
    job.style_dna_update_draft = {"draft_id": "draft_runner"}
    job.style_dna_update_proposals = [
        {
            "proposal_id": "proposal_runner",
            "parameter_name": "preferred_hook_energy_min",
            "current_value": 0.85,
            "proposed_value": 0.90,
            "delta": 0.05,
        }
    ]
    job.style_dna_review_proposal_decisions = [
        {"proposal_id": "proposal_runner", "status": "approved"}
    ]
    return job


def test_runner_writes_apply_plan_fields_to_job():
    job = _job()

    report = run_style_dna_apply_plan_for_job(job)

    assert report["status"] in {
        "style_dna_apply_plan_ready",
        "style_dna_apply_plan_ready_with_warnings",
    }
    assert job.style_dna_apply_plan_report["status"] == report["status"]
    assert job.style_dna_apply_plan["plan_id"] == "job_runner_2b62_style_dna_apply_plan"
    assert job.style_dna_apply_plan_status == report["status"]
    assert job.style_dna_apply_operation_count == 1
    assert job.style_dna_apply_approved_operation_count == 1
    assert job.style_dna_apply_skipped_operation_count == 0
    assert job.style_dna_apply_before_snapshot["preferred_hook_energy_min"] == 0.85
    assert job.style_dna_apply_after_preview["preferred_hook_energy_min"] == 0.90
    assert job.style_dna_apply_ready_for_future_file_write is True


def test_runner_keeps_write_apply_profile_timeline_render_publish_flags_false():
    job = _job()

    run_style_dna_apply_plan_for_job(job)

    assert job.style_dna_apply_can_write_style_dna is False
    assert job.style_dna_apply_can_apply_style_dna is False
    assert job.style_dna_apply_can_update_profile is False
    assert job.style_dna_apply_can_change_cutting_rules is False
    assert job.style_dna_apply_can_modify_timeline is False
    assert job.style_dna_apply_can_trigger_render is False
    assert job.style_dna_apply_can_publish is False


def test_job_from_dict_loads_apply_fields_and_forces_safety_flags_false():
    data = _job().to_dict()
    data.update(
        {
            "style_dna_apply_plan_status": "style_dna_apply_plan_ready",
            "style_dna_apply_operation_count": 1,
            "style_dna_apply_approved_operation_count": 1,
            "style_dna_apply_skipped_operation_count": 0,
            "style_dna_apply_before_snapshot": {"preferred_hook_energy_min": 0.85},
            "style_dna_apply_after_preview": {"preferred_hook_energy_min": 0.90},
            "style_dna_apply_ready_for_future_file_write": True,
            "style_dna_apply_can_write_style_dna": True,
            "style_dna_apply_can_apply_style_dna": True,
            "style_dna_apply_can_update_profile": True,
            "style_dna_apply_can_change_cutting_rules": True,
            "style_dna_apply_can_modify_timeline": True,
            "style_dna_apply_can_trigger_render": True,
            "style_dna_apply_can_publish": True,
            "style_dna_apply_requested_by": "hajar",
            "style_dna_apply_requested_at": "2026-05-15T00:00:00+00:00",
            "style_dna_apply_allow_file_write": True,
        }
    )

    loaded = Job.from_dict(data)

    assert loaded.style_dna_apply_plan_status == "style_dna_apply_plan_ready"
    assert loaded.style_dna_apply_operation_count == 1
    assert loaded.style_dna_apply_ready_for_future_file_write is True
    assert loaded.style_dna_apply_requested_by == "hajar"
    assert loaded.style_dna_apply_allow_file_write is True
    assert loaded.style_dna_apply_can_write_style_dna is False
    assert loaded.style_dna_apply_can_apply_style_dna is False
    assert loaded.style_dna_apply_can_update_profile is False
    assert loaded.style_dna_apply_can_change_cutting_rules is False
    assert loaded.style_dna_apply_can_modify_timeline is False
    assert loaded.style_dna_apply_can_trigger_render is False
    assert loaded.style_dna_apply_can_publish is False
