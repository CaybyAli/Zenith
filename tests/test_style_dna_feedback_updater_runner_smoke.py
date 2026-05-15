from __future__ import annotations

from types import SimpleNamespace

from core.style_dna_feedback_updater_runner import run_style_dna_feedback_updater_for_job


def test_runner_writes_style_dna_update_fields():
    job = SimpleNamespace(
        job_id="runner_job_1",
        profile="gaming_main",
        feedback_intake_status="feedback_intake_ready",
        feedback_intake_report={
            "report_id": "feedback_report_runner",
            "status": "feedback_intake_ready",
            "submission_count": 2,
            "timestamp_feedback_count": 2,
            "average_video_score": 6.0,
            "tags_summary": {"bad_pacing": 2, "wrong_hook": 2},
            "ready_for_style_dna_update": True,
            "blocking_reasons": [],
            "warnings": [],
        },
        feedback_blocking_reasons=[],
        feedback_can_update_style_dna=False,
        feedback_can_change_profile=False,
        feedback_can_modify_timeline=False,
        feedback_can_trigger_render=False,
        feedback_can_publish=False,
        existing_style_dna_snapshot={"preferred_avg_clip_duration": 4.0},
        style_dna_update_allow_file_write=False,
    )

    payload = run_style_dna_feedback_updater_for_job(job)

    assert payload["status"] in {
        "style_dna_update_draft_ready",
        "style_dna_update_draft_ready_with_warnings",
    }
    assert job.style_dna_feedback_update_report == payload
    assert job.style_dna_feedback_update_status == payload["status"]
    assert job.style_dna_update_draft == payload["draft"]
    assert job.style_dna_update_proposals == payload["draft"]["proposals"]
    assert job.style_dna_update_proposal_count == payload["proposal_count"]
    assert job.style_dna_update_ready_for_human_review is True
    assert job.style_dna_update_ready_for_later_apply is True
    assert job.style_dna_update_can_write_style_dna is False
    assert job.style_dna_update_can_update_profile is False
    assert job.style_dna_update_can_change_cutting_rules is False
    assert job.style_dna_update_can_modify_timeline is False
    assert job.style_dna_update_can_trigger_render is False
    assert job.style_dna_update_can_publish is False


def test_runner_supports_dict_job():
    job = {
        "job_id": "runner_dict_job",
        "feedback_intake_status": "feedback_intake_ready",
        "feedback_intake_report": {
            "report_id": "feedback_report_runner_dict",
            "status": "feedback_intake_ready",
            "submission_count": 2,
            "timestamp_feedback_count": 2,
            "average_video_score": 6.0,
            "tags_summary": {"missing_reaction": 2},
            "ready_for_style_dna_update": True,
            "blocking_reasons": [],
            "warnings": [],
        },
        "feedback_blocking_reasons": [],
        "feedback_can_update_style_dna": False,
        "feedback_can_change_profile": False,
        "feedback_can_modify_timeline": False,
        "feedback_can_trigger_render": False,
        "feedback_can_publish": False,
    }

    payload = run_style_dna_feedback_updater_for_job(job)

    assert job["style_dna_feedback_update_report"] == payload
    assert job["style_dna_update_proposal_count"] == payload["proposal_count"]
    assert job["style_dna_update_can_write_style_dna"] is False


def test_job_from_dict_loads_style_dna_update_fields():
    from models.job import Job

    job = Job.from_dict(
        {
            "job_id": "from_dict_style_dna_job",
            "style_dna_feedback_update_report": {"status": "style_dna_update_draft_ready"},
            "style_dna_feedback_update_status": "style_dna_update_draft_ready",
            "style_dna_update_draft": {"overfitting_risk": "low"},
            "style_dna_update_proposals": [{"parameter_name": "pacing_sensitivity"}],
            "style_dna_update_proposal_count": 1,
            "style_dna_update_confidence": 0.7,
            "style_dna_update_overfitting_risk": "low",
            "style_dna_update_ready_for_human_review": True,
            "style_dna_update_ready_for_later_apply": True,
            "style_dna_update_can_write_style_dna": True,
            "style_dna_update_can_update_profile": True,
            "style_dna_update_can_change_cutting_rules": True,
            "style_dna_update_can_modify_timeline": True,
            "style_dna_update_can_trigger_render": True,
            "style_dna_update_can_publish": True,
            "style_dna_update_warnings": ["warning_a"],
            "style_dna_update_blocking_reasons": ["blocker_a"],
            "style_dna_update_recommendation": "review_style_dna_update_draft",
            "existing_style_dna_snapshot": {"pacing_sensitivity": 0.5},
            "style_dna_profile_name": "gaming_main",
            "style_dna_update_requested_by": "tester",
            "style_dna_update_requested_at": "2026-01-01T00:00:00Z",
            "style_dna_update_allow_file_write": True,
        }
    )

    assert job.style_dna_feedback_update_status == "style_dna_update_draft_ready"
    assert job.style_dna_update_proposal_count == 1
    assert job.style_dna_update_ready_for_human_review is True
    assert job.style_dna_update_ready_for_later_apply is True
    assert job.style_dna_update_can_write_style_dna is False
    assert job.style_dna_update_can_update_profile is False
    assert job.style_dna_update_can_change_cutting_rules is False
    assert job.style_dna_update_can_modify_timeline is False
    assert job.style_dna_update_can_trigger_render is False
    assert job.style_dna_update_can_publish is False
    assert job.existing_style_dna_snapshot == {"pacing_sensitivity": 0.5}
    assert job.style_dna_update_allow_file_write is True
