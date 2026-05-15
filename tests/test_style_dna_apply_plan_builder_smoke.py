from __future__ import annotations

from core.style_dna_apply_plan_builder import build_style_dna_apply_plan_report


def _approved_job(**overrides):
    job = {
        "job_id": "job_2b62",
        "style_dna_profile_name": "gaming_main",
        "existing_style_dna_snapshot": {
            "preferred_hook_energy_min": 0.85,
            "reaction_shot_priority": 0.40,
        },
        "style_dna_feedback_update_report": {
            "report_id": "update_report_2b62",
            "status": "style_dna_update_draft_ready",
            "draft_id": "draft_2b62",
        },
        "style_dna_update_draft": {"draft_id": "draft_2b62"},
        "style_dna_update_proposals": [
            {
                "proposal_id": "proposal_approved",
                "parameter_name": "preferred_hook_energy_min",
                "current_value": 0.85,
                "proposed_value": 0.90,
                "delta": 0.05,
                "reason": "Hook soll staerker starten.",
                "source_tags": ["wrong_hook"],
                "confidence": 0.72,
            },
            {
                "proposal_id": "proposal_rejected",
                "parameter_name": "reaction_shot_priority",
                "current_value": 0.40,
                "proposed_value": 0.55,
                "delta": 0.15,
            },
            {
                "proposal_id": "proposal_needs_changes",
                "parameter_name": "pacing_sensitivity",
                "current_value": 0.50,
                "proposed_value": 0.45,
                "delta": -0.05,
            },
            {
                "proposal_id": "proposal_pending",
                "parameter_name": "hook_density",
                "current_value": 0.30,
                "proposed_value": 0.35,
                "delta": 0.05,
            },
        ],
        "style_dna_review_gate_report": {
            "report_id": "review_report_2b62",
            "status": "style_dna_review_approved",
            "gate": {"gate_id": "gate_2b62"},
        },
        "style_dna_review_gate": {"gate_id": "gate_2b62"},
        "style_dna_review_status": "style_dna_review_approved",
        "style_dna_review_ready_for_later_apply": True,
        "style_dna_review_blocking_reasons": [],
        "style_dna_review_proposal_decisions": [
            {"proposal_id": "proposal_approved", "status": "approved"},
            {"proposal_id": "proposal_rejected", "status": "rejected"},
            {"proposal_id": "proposal_needs_changes", "status": "needs_manual_changes"},
            {"proposal_id": "proposal_pending", "status": "pending_review"},
        ],
        "style_dna_review_can_apply_style_dna": False,
        "style_dna_review_can_write_style_dna": False,
        "style_dna_review_can_update_profile": False,
        "style_dna_review_can_change_cutting_rules": False,
        "style_dna_review_can_modify_timeline": False,
        "style_dna_review_can_trigger_render": False,
        "style_dna_review_can_publish": False,
        "style_dna_apply_allow_file_write": False,
    }
    job.update(overrides)
    return job


def test_without_review_gate_waits_or_blocks_without_operations():
    report = build_style_dna_apply_plan_report({"job_id": "job_missing_review"})

    assert report["status"] in {
        "style_dna_apply_plan_waiting_for_review",
        "style_dna_apply_plan_blocked",
    }
    assert report["operation_count"] == 0
    assert report["ready_for_future_file_write"] is False
    assert report["can_write_style_dna"] is False
    assert report["can_apply_style_dna"] is False


def test_review_blocked_or_failed_blocks_apply_plan():
    for status in ["style_dna_review_blocked", "style_dna_review_failed"]:
        report = build_style_dna_apply_plan_report(
            _approved_job(
                style_dna_review_status=status,
                style_dna_review_blocking_reasons=["review_problem"],
            )
        )

        assert report["status"] == "style_dna_apply_plan_blocked"
        assert report["operation_count"] == 0
        assert "style_dna_review_gate_blocked_or_failed" in report["blocking_reasons"]
        assert report["can_write_style_dna"] is False
        assert report["can_apply_style_dna"] is False


def test_review_pending_rejected_or_needs_changes_waits_without_operations():
    for status in [
        "style_dna_review_pending_review",
        "style_dna_review_rejected",
        "style_dna_review_needs_manual_changes",
    ]:
        report = build_style_dna_apply_plan_report(
            _approved_job(style_dna_review_status=status)
        )

        assert report["status"] == "style_dna_apply_plan_waiting_for_review"
        assert report["operation_count"] == 0
        assert report["ready_for_future_file_write"] is False


def test_approved_review_builds_ready_apply_plan_only_for_approved_decisions():
    report = build_style_dna_apply_plan_report(_approved_job())

    assert report["status"] in {
        "style_dna_apply_plan_ready",
        "style_dna_apply_plan_ready_with_warnings",
    }
    assert report["operation_count"] == 1
    assert report["approved_operation_count"] == 1
    assert report["skipped_operation_count"] == 3
    assert report["ready_for_future_file_write"] is True

    operation = report["plan"]["operations"][0]
    assert operation["proposal_id"] == "proposal_approved"
    assert operation["parameter_name"] == "preferred_hook_energy_min"
    assert operation["current_value"] == 0.85
    assert operation["proposed_value"] == 0.90
    assert operation["delta"] == 0.05
    assert operation["approved"] is True
    assert operation["planned_only"] is True
    assert operation["safe_to_apply_later"] is True

    assert report["plan"]["before_snapshot"]["preferred_hook_energy_min"] == 0.85
    assert report["plan"]["after_preview"]["preferred_hook_energy_min"] == 0.90
    assert report["plan"]["after_preview"]["reaction_shot_priority"] == 0.40


def test_file_write_request_never_writes_and_blocks_future_write_for_now():
    report = build_style_dna_apply_plan_report(
        _approved_job(style_dna_apply_allow_file_write=True)
    )

    assert report["status"] == "style_dna_apply_plan_blocked"
    assert "style_dna_file_write_not_allowed_in_2b_62" in report["warnings"]
    assert "style_dna_file_write_not_allowed_in_2b_62" in report["blocking_reasons"]
    assert report["ready_for_future_file_write"] is False
    assert report["can_write_style_dna"] is False
    assert report["can_apply_style_dna"] is False
    assert report["can_update_profile"] is False
    assert report["can_change_cutting_rules"] is False
    assert report["can_modify_timeline"] is False
    assert report["can_trigger_render"] is False
    assert report["can_publish"] is False


def test_unsafe_review_flags_block_apply_plan():
    unsafe_flags = [
        "style_dna_review_can_apply_style_dna",
        "style_dna_review_can_write_style_dna",
        "style_dna_review_can_update_profile",
        "style_dna_review_can_change_cutting_rules",
        "style_dna_review_can_modify_timeline",
        "style_dna_review_can_trigger_render",
        "style_dna_review_can_publish",
    ]

    for flag in unsafe_flags:
        report = build_style_dna_apply_plan_report(_approved_job(**{flag: True}))

        assert report["status"] == "style_dna_apply_plan_blocked"
        assert "style_dna_review_gate_contains_unsafe_permission" in report["blocking_reasons"]
        assert report["can_write_style_dna"] is False
        assert report["can_apply_style_dna"] is False
