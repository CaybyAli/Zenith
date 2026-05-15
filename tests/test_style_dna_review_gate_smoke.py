from __future__ import annotations

from core.style_dna_review_gate import build_style_dna_review_gate_report


def _ready_job(**overrides):
    job = {
        "job_id": "job_2b61",
        "style_dna_feedback_update_status": "style_dna_update_draft_ready",
        "style_dna_feedback_update_report": {
            "report_id": "style_dna_feedback_update_report_job_2b61",
            "status": "style_dna_update_draft_ready",
            "proposal_count": 2,
            "ready_for_human_review": True,
            "blocking_reasons": [],
            "draft": {
                "draft_id": "draft_2b61",
                "proposals": [
                    {
                        "proposal_id": "style_dna_proposal_1",
                        "parameter_name": "hook_density",
                        "proposed_value": 0.8,
                    },
                    {
                        "proposal_id": "style_dna_proposal_2",
                        "parameter_name": "reaction_cut_frequency",
                        "proposed_value": 0.6,
                    },
                ],
            },
        },
        "style_dna_update_draft": {
            "draft_id": "draft_2b61",
            "proposals": [
                {
                    "proposal_id": "style_dna_proposal_1",
                    "parameter_name": "hook_density",
                    "proposed_value": 0.8,
                },
                {
                    "proposal_id": "style_dna_proposal_2",
                    "parameter_name": "reaction_cut_frequency",
                    "proposed_value": 0.6,
                },
            ],
        },
        "style_dna_update_proposals": [
            {
                "proposal_id": "style_dna_proposal_1",
                "parameter_name": "hook_density",
                "proposed_value": 0.8,
            },
            {
                "proposal_id": "style_dna_proposal_2",
                "parameter_name": "reaction_cut_frequency",
                "proposed_value": 0.6,
            },
        ],
        "style_dna_update_proposal_count": 2,
        "style_dna_update_ready_for_human_review": True,
        "style_dna_update_blocking_reasons": [],
        "style_dna_update_can_write_style_dna": False,
        "style_dna_update_can_update_profile": False,
        "style_dna_update_can_change_cutting_rules": False,
        "style_dna_update_can_modify_timeline": False,
        "style_dna_update_can_trigger_render": False,
        "style_dna_update_can_publish": False,
    }
    job.update(overrides)
    return job


def test_without_style_dna_draft_blocks_review_gate():
    report = build_style_dna_review_gate_report(
        {
            "job_id": "job_missing",
            "style_dna_feedback_update_status": "style_dna_update_draft_ready",
            "style_dna_update_ready_for_human_review": True,
        }
    ).to_dict()

    assert report["status"] == "style_dna_review_blocked"
    assert "style_dna_update_draft_missing" in report["blocking_reasons"]
    assert report["ready_for_later_apply"] is False


def test_source_update_blocked_or_failed_blocks_review_gate():
    for source_status in ["style_dna_update_blocked", "style_dna_update_failed"]:
        report = build_style_dna_review_gate_report(
            _ready_job(style_dna_feedback_update_status=source_status)
        ).to_dict()

        assert report["status"] == "style_dna_review_blocked"
        assert (
            "style_dna_feedback_update_source_blocked_or_failed"
            in report["blocking_reasons"]
        )


def test_ready_source_without_request_is_pending_review():
    report = build_style_dna_review_gate_report(_ready_job()).to_dict()

    assert report["status"] == "style_dna_review_pending_review"
    assert report["review_required"] is True
    assert report["ready_for_later_apply"] is False
    assert report["gate"]["requested_status"] == "pending_review"


def test_unknown_requested_status_blocks_review_gate():
    report = build_style_dna_review_gate_report(
        _ready_job(style_dna_review_requested_status="publish_now")
    ).to_dict()

    assert report["status"] == "style_dna_review_blocked"
    assert "style_dna_review_requested_status_unknown" in report["blocking_reasons"]


def test_approved_without_reviewed_by_blocks_review_gate():
    report = build_style_dna_review_gate_report(
        _ready_job(style_dna_review_requested_status="approved")
    ).to_dict()

    assert report["status"] == "style_dna_review_blocked"
    assert "style_dna_review_approved_requires_reviewed_by" in report["blocking_reasons"]


def test_approved_with_reviewed_by_sets_ready_for_later_apply_only():
    report = build_style_dna_review_gate_report(
        _ready_job(
            style_dna_review_requested_status="approved",
            style_dna_reviewed_by="hajar",
        )
    ).to_dict()

    assert report["status"] == "style_dna_review_approved"
    assert report["ready_for_later_apply"] is True
    assert report["can_apply_style_dna"] is False
    assert report["can_write_style_dna"] is False
    assert report["can_update_profile"] is False
    assert report["can_change_cutting_rules"] is False
    assert report["can_modify_timeline"] is False
    assert report["can_trigger_render"] is False
    assert report["can_publish"] is False


def test_rejected_sets_ready_for_later_apply_false():
    report = build_style_dna_review_gate_report(
        _ready_job(
            style_dna_review_requested_status="rejected",
            style_dna_reviewed_by="hajar",
        )
    ).to_dict()

    assert report["status"] == "style_dna_review_rejected"
    assert report["ready_for_later_apply"] is False
    assert report["gate"]["rejected_proposal_count"] == 2


def test_needs_manual_changes_sets_ready_for_later_apply_false():
    report = build_style_dna_review_gate_report(
        _ready_job(
            style_dna_review_requested_status="needs_manual_changes",
            style_dna_reviewed_by="hajar",
            style_dna_review_comment="Bitte Hook-Regeln weicher machen.",
        )
    ).to_dict()

    assert report["status"] == "style_dna_review_needs_manual_changes"
    assert report["ready_for_later_apply"] is False
    assert report["gate"]["needs_changes_count"] == 2


def test_proposal_decisions_are_built_and_approved_ids_are_respected():
    report = build_style_dna_review_gate_report(
        _ready_job(
            style_dna_review_requested_status="approved",
            style_dna_reviewed_by="hajar",
            style_dna_review_approved_proposal_ids=["style_dna_proposal_1"],
        )
    ).to_dict()

    decisions = report["gate"]["proposal_decisions"]

    assert len(decisions) == 2
    assert decisions[0]["proposal_id"] == "style_dna_proposal_1"
    assert decisions[0]["status"] == "approved"
    assert decisions[1]["proposal_id"] == "style_dna_proposal_2"
    assert decisions[1]["status"] == "pending_review"
    assert report["gate"]["approved_proposal_count"] == 1


def test_rejected_proposal_ids_are_respected():
    report = build_style_dna_review_gate_report(
        _ready_job(
            style_dna_review_requested_status="rejected",
            style_dna_reviewed_by="hajar",
            style_dna_review_rejected_proposal_ids=["style_dna_proposal_2"],
        )
    ).to_dict()

    decisions = report["gate"]["proposal_decisions"]

    assert decisions[0]["status"] == "pending_review"
    assert decisions[1]["status"] == "rejected"
    assert report["gate"]["rejected_proposal_count"] == 1


def test_unsafe_source_flags_block_review_gate():
    unsafe_flags = [
        "style_dna_update_can_write_style_dna",
        "style_dna_update_can_update_profile",
        "style_dna_update_can_change_cutting_rules",
        "style_dna_update_can_modify_timeline",
        "style_dna_update_can_trigger_render",
        "style_dna_update_can_publish",
    ]

    for flag in unsafe_flags:
        report = build_style_dna_review_gate_report(_ready_job(**{flag: True})).to_dict()

        assert report["status"] == "style_dna_review_blocked"
        assert f"unsafe_source_flag_true:{flag}" in report["blocking_reasons"]


def test_style_dna_update_allow_file_write_warns_but_never_enables_write():
    report = build_style_dna_review_gate_report(
        _ready_job(
            style_dna_review_requested_status="approved",
            style_dna_reviewed_by="hajar",
            style_dna_update_allow_file_write=True,
        )
    ).to_dict()

    assert "style_dna_file_write_still_not_allowed_in_2b_61" in report["warnings"]
    assert report["can_write_style_dna"] is False
    assert report["gate"]["can_write_style_dna"] is False
