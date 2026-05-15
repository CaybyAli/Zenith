from dataclasses import fields

from models.job import Job


FIELD_GROUPS = {
    "2B-59 feedback": [
        "feedback_intake_report",
        "feedback_intake_status",
        "feedback_submissions",
        "feedback_submission_count",
        "feedback_ready_for_style_dna_update",
    ],
    "2B-60 style dna update": [
        "style_dna_feedback_update_report",
        "style_dna_feedback_update_status",
        "style_dna_update_draft",
        "style_dna_update_proposals",
        "style_dna_update_ready_for_human_review",
        "style_dna_update_ready_for_later_apply",
    ],
    "2B-61 review gate": [
        "style_dna_review_gate_report",
        "style_dna_review_gate",
        "style_dna_review_status",
        "style_dna_review_ready_for_later_apply",
    ],
    "2B-62 apply plan": [
        "style_dna_apply_plan_report",
        "style_dna_apply_plan",
        "style_dna_apply_plan_status",
        "style_dna_apply_after_preview",
        "style_dna_apply_ready_for_future_file_write",
    ],
    "2B-63 persistence gate": [
        "style_dna_persistence_gate_report",
        "style_dna_persistence_gate",
        "style_dna_persistence_status",
        "style_dna_persistence_write_intent",
        "style_dna_persistence_write_permission_ready_for_future",
    ],
    "2B-64 learning pattern": [
        "learning_pattern_recognition_report",
        "learning_pattern_status",
        "learning_pattern_trends",
        "learning_pattern_clusters",
        "learning_pattern_ready_for_future_style_dna_proposal",
    ],
}


HARD_FALSE_FIELDS = [
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
        "job_id": "block9-job-field-audit",
        "title": "Block 9 Job Field Audit",
        "source_path": "sample-input.mp4",
        "input_path": "sample-input.mp4",
        "channel": "gaming_main",
        "channel_type": "gaming_main",
        "target_format": "longform",
        "pipeline_type": "gaming_pipeline",
        "job_type": "gaming",
    }


def test_job_model_declares_all_block9_field_groups():
    declared = {field.name for field in fields(Job)}

    missing = {}
    for group_name, group_fields in FIELD_GROUPS.items():
        group_missing = [field_name for field_name in group_fields if field_name not in declared]
        if group_missing:
            missing[group_name] = group_missing

    assert missing == {}


def test_job_model_declares_all_hard_false_block9_safety_fields():
    declared = {field.name for field in fields(Job)}

    missing = [field_name for field_name in HARD_FALSE_FIELDS if field_name not in declared]
    assert missing == []


def test_job_from_dict_loads_block9_data_fields():
    data = _base_job_data()
    data.update(
        {
            "feedback_intake_status": "ready",
            "feedback_submission_count": 5,
            "feedback_ready_for_style_dna_update": True,
            "style_dna_feedback_update_status": "draft_ready",
            "style_dna_update_ready_for_human_review": True,
            "style_dna_update_ready_for_later_apply": True,
            "style_dna_review_status": "approved",
            "style_dna_review_ready_for_later_apply": True,
            "style_dna_apply_plan_status": "ready",
            "style_dna_apply_after_preview": {"tone": "faster"},
            "style_dna_apply_ready_for_future_file_write": True,
            "style_dna_persistence_status": "approved_write",
            "style_dna_persistence_write_permission_ready_for_future": True,
            "learning_pattern_status": "ready",
            "learning_pattern_trend_count": 4,
            "learning_pattern_cluster_count": 2,
            "learning_pattern_ready_for_future_style_dna_proposal": True,
        }
    )

    job = Job.from_dict(data)

    assert job.feedback_intake_status == "ready"
    assert job.feedback_submission_count == 5
    assert job.feedback_ready_for_style_dna_update is True
    assert job.style_dna_feedback_update_status == "draft_ready"
    assert job.style_dna_update_ready_for_human_review is True
    assert job.style_dna_update_ready_for_later_apply is True
    assert job.style_dna_review_status == "approved"
    assert job.style_dna_review_ready_for_later_apply is True
    assert job.style_dna_apply_plan_status == "ready"
    assert job.style_dna_apply_after_preview == {"tone": "faster"}
    assert job.style_dna_apply_ready_for_future_file_write is True
    assert job.style_dna_persistence_status == "approved_write"
    assert job.style_dna_persistence_write_permission_ready_for_future is True
    assert job.learning_pattern_status == "ready"
    assert job.learning_pattern_trend_count == 4
    assert job.learning_pattern_cluster_count == 2
    assert job.learning_pattern_ready_for_future_style_dna_proposal is True


def test_job_from_dict_forces_all_block9_dangerous_fields_to_false():
    data = _base_job_data()

    for field_name in HARD_FALSE_FIELDS:
        data[field_name] = True

    job = Job.from_dict(data)

    leaking = {
        field_name: getattr(job, field_name)
        for field_name in HARD_FALSE_FIELDS
        if getattr(job, field_name) is not False
    }

    assert leaking == {}
