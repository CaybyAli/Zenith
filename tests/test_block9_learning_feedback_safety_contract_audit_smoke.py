from __future__ import annotations

from models.job import Job


DANGEROUS_FALSE_FIELDS = [
    "feedback_can_update_style_dna",
    "feedback_can_change_profile",
    "feedback_can_change_cutting_rules",
    "feedback_can_modify_timeline",
    "feedback_can_trigger_render",
    "feedback_can_publish",
    "style_dna_update_can_write_style_dna",
    "style_dna_update_can_update_profile",
    "style_dna_update_can_change_cutting_rules",
    "style_dna_update_can_modify_timeline",
    "style_dna_update_can_trigger_render",
    "style_dna_update_can_publish",
    "style_dna_review_can_apply_style_dna",
    "style_dna_review_can_write_style_dna",
    "style_dna_review_can_update_profile",
    "style_dna_review_can_change_cutting_rules",
    "style_dna_review_can_modify_timeline",
    "style_dna_review_can_trigger_render",
    "style_dna_review_can_publish",
    "style_dna_apply_can_write_style_dna",
    "style_dna_apply_can_apply_style_dna",
    "style_dna_apply_can_update_profile",
    "style_dna_apply_can_change_cutting_rules",
    "style_dna_apply_can_modify_timeline",
    "style_dna_apply_can_trigger_render",
    "style_dna_apply_can_publish",
    "style_dna_persistence_can_write_style_dna",
    "style_dna_persistence_can_apply_style_dna",
    "style_dna_persistence_can_update_profile",
    "style_dna_persistence_can_change_cutting_rules",
    "style_dna_persistence_can_modify_timeline",
    "style_dna_persistence_can_trigger_render",
    "style_dna_persistence_can_publish",
    "learning_pattern_can_update_style_dna",
    "learning_pattern_can_write_style_dna",
    "learning_pattern_can_change_profile",
    "learning_pattern_can_change_cutting_rules",
    "learning_pattern_can_modify_timeline",
    "learning_pattern_can_trigger_render",
    "learning_pattern_can_publish",
]


def _base_job_data() -> dict:
    return {
        "job_id": "block9-final-audit-job",
        "title": "Block 9 Final Audit Job",
        "source_path": "sample-input.mp4",
        "input_path": "sample-input.mp4",
        "channel": "gaming_main",
        "channel_type": "gaming_main",
        "target_format": "longform",
        "pipeline_type": "gaming_pipeline",
        "job_type": "gaming",
    }


def _job_from(overrides: dict) -> Job:
    data = _base_job_data()
    data.update(overrides)

    for field_name in DANGEROUS_FALSE_FIELDS:
        data[field_name] = True

    return Job.from_dict(data)


def _assert_no_dangerous_rights(job: Job):
    leaking = {
        field_name: getattr(job, field_name)
        for field_name in DANGEROUS_FALSE_FIELDS
        if getattr(job, field_name) is not False
    }

    assert leaking == {}


def test_case_a_complete_safe_block9_flow_still_has_no_dangerous_rights():
    job = _job_from(
        {
            "feedback_intake_status": "ready",
            "feedback_submission_count": 2,
            "feedback_ready_for_style_dna_update": True,
            "style_dna_feedback_update_status": "draft_ready",
            "style_dna_update_ready_for_human_review": True,
            "style_dna_update_ready_for_later_apply": True,
            "style_dna_review_status": "approved",
            "style_dna_review_ready_for_later_apply": True,
            "style_dna_apply_plan_status": "ready",
            "style_dna_apply_after_preview": {"pacing": "faster"},
            "style_dna_apply_ready_for_future_file_write": True,
            "style_dna_persistence_status": "approved_write",
            "style_dna_persistence_write_permission_ready_for_future": True,
            "learning_pattern_status": "ready",
            "learning_pattern_ready_for_future_style_dna_proposal": True,
        }
    )

    assert job.feedback_ready_for_style_dna_update is True
    assert job.style_dna_update_ready_for_later_apply is True
    assert job.style_dna_review_ready_for_later_apply is True
    assert job.style_dna_apply_ready_for_future_file_write is True
    assert job.style_dna_persistence_write_permission_ready_for_future is True
    assert job.learning_pattern_ready_for_future_style_dna_proposal is True
    _assert_no_dangerous_rights(job)


def test_case_b_missing_feedback_waiting_flow_has_no_dangerous_rights():
    job = _job_from(
        {
            "feedback_intake_status": "waiting",
            "feedback_submission_count": 0,
            "feedback_ready_for_style_dna_update": False,
            "style_dna_feedback_update_status": "waiting",
            "learning_pattern_status": "waiting",
        }
    )

    assert job.feedback_ready_for_style_dna_update is False
    _assert_no_dangerous_rights(job)


def test_case_c_blocked_feedback_keeps_later_stages_safe():
    job = _job_from(
        {
            "feedback_intake_status": "blocked",
            "feedback_blocking_reasons": ["invalid_feedback"],
            "style_dna_feedback_update_status": "blocked",
            "style_dna_review_status": "waiting",
            "style_dna_apply_plan_status": "waiting",
            "style_dna_persistence_status": "waiting",
            "learning_pattern_status": "blocked",
        }
    )

    assert "invalid_feedback" in job.feedback_blocking_reasons
    _assert_no_dangerous_rights(job)


def test_case_d_approved_style_dna_draft_is_only_ready_for_later_apply():
    job = _job_from(
        {
            "style_dna_feedback_update_status": "draft_ready",
            "style_dna_update_ready_for_later_apply": True,
            "style_dna_update_draft": {"draft_only": True},
        }
    )

    assert job.style_dna_update_ready_for_later_apply is True
    assert job.style_dna_update_can_write_style_dna is False
    _assert_no_dangerous_rights(job)


def test_case_e_apply_plan_ready_has_preview_but_no_write_power():
    job = _job_from(
        {
            "style_dna_apply_plan_status": "ready",
            "style_dna_apply_after_preview": {"hook_density": "higher"},
            "style_dna_apply_ready_for_future_file_write": True,
        }
    )

    assert job.style_dna_apply_after_preview == {"hook_density": "higher"}
    assert job.style_dna_apply_ready_for_future_file_write is True
    assert job.style_dna_apply_can_write_style_dna is False
    _assert_no_dangerous_rights(job)


def test_case_f_persistence_approved_write_is_only_future_permission_marker():
    job = _job_from(
        {
            "style_dna_persistence_status": "approved_write",
            "style_dna_persistence_write_permission_ready_for_future": True,
            "style_dna_persistence_write_intent": {"target": "style_dna"},
        }
    )

    assert job.style_dna_persistence_write_permission_ready_for_future is True
    assert job.style_dna_persistence_can_write_style_dna is False
    _assert_no_dangerous_rights(job)


def test_case_g_learning_pattern_ready_is_only_future_proposal_marker():
    job = _job_from(
        {
            "learning_pattern_status": "ready",
            "learning_pattern_ready_for_future_style_dna_proposal": True,
            "learning_pattern_trend_count": 3,
            "learning_pattern_cluster_count": 2,
        }
    )

    assert job.learning_pattern_ready_for_future_style_dna_proposal is True
    assert job.learning_pattern_can_update_style_dna is False
    _assert_no_dangerous_rights(job)
