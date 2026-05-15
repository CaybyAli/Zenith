from __future__ import annotations

from core.style_dna_review_gate_runner import run_style_dna_review_gate_for_job
from models.job import Job


def _job() -> Job:
    job = Job.from_dict({"job_id": "job_runner_2b61"})
    job.style_dna_feedback_update_status = "style_dna_update_draft_ready"
    job.style_dna_feedback_update_report = {
        "report_id": "source_report",
        "status": "style_dna_update_draft_ready",
        "proposal_count": 1,
        "ready_for_human_review": True,
        "blocking_reasons": [],
        "draft": {
            "draft_id": "source_draft",
            "proposals": [
                {
                    "proposal_id": "style_dna_proposal_1",
                    "parameter_name": "hook_density",
                    "proposed_value": 0.8,
                }
            ],
        },
    }
    job.style_dna_update_draft = job.style_dna_feedback_update_report["draft"]
    job.style_dna_update_proposals = job.style_dna_update_draft["proposals"]
    job.style_dna_update_proposal_count = 1
    job.style_dna_update_ready_for_human_review = True
    job.style_dna_review_requested_status = "approved"
    job.style_dna_reviewed_by = "hajar"
    return job


def test_runner_writes_review_gate_fields_to_job():
    job = _job()

    payload = run_style_dna_review_gate_for_job(job)

    assert payload["status"] == "style_dna_review_approved"
    assert job.style_dna_review_gate_report["status"] == "style_dna_review_approved"
    assert job.style_dna_review_gate["status"] == "style_dna_review_approved"
    assert job.style_dna_review_status == "style_dna_review_approved"
    assert job.style_dna_review_requested_status == "approved"
    assert job.style_dna_reviewed_by == "hajar"
    assert job.style_dna_review_proposal_decisions
    assert job.style_dna_review_approved_proposal_count == 1
    assert job.style_dna_review_required is False
    assert job.style_dna_review_ready_for_later_apply is True


def test_runner_keeps_all_apply_write_profile_timeline_render_publish_flags_false():
    job = _job()

    run_style_dna_review_gate_for_job(job)

    assert job.style_dna_review_can_apply_style_dna is False
    assert job.style_dna_review_can_write_style_dna is False
    assert job.style_dna_review_can_update_profile is False
    assert job.style_dna_review_can_change_cutting_rules is False
    assert job.style_dna_review_can_modify_timeline is False
    assert job.style_dna_review_can_trigger_render is False
    assert job.style_dna_review_can_publish is False


def test_job_from_dict_loads_review_gate_fields_and_forces_safety_flags_false():
    data = _job().to_dict()
    data.update(
        {
            "style_dna_review_status": "style_dna_review_approved",
            "style_dna_review_requested_status": "approved",
            "style_dna_reviewed_by": "hajar",
            "style_dna_review_ready_for_later_apply": True,
            "style_dna_review_can_apply_style_dna": True,
            "style_dna_review_can_write_style_dna": True,
            "style_dna_review_can_update_profile": True,
            "style_dna_review_can_change_cutting_rules": True,
            "style_dna_review_can_modify_timeline": True,
            "style_dna_review_can_trigger_render": True,
            "style_dna_review_can_publish": True,
        }
    )

    loaded = Job.from_dict(data)

    assert loaded.style_dna_review_status == "style_dna_review_approved"
    assert loaded.style_dna_review_requested_status == "approved"
    assert loaded.style_dna_reviewed_by == "hajar"
    assert loaded.style_dna_review_ready_for_later_apply is True
    assert loaded.style_dna_review_can_apply_style_dna is False
    assert loaded.style_dna_review_can_write_style_dna is False
    assert loaded.style_dna_review_can_update_profile is False
    assert loaded.style_dna_review_can_change_cutting_rules is False
    assert loaded.style_dna_review_can_modify_timeline is False
    assert loaded.style_dna_review_can_trigger_render is False
    assert loaded.style_dna_review_can_publish is False
