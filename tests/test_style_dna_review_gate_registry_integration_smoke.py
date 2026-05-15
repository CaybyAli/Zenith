from __future__ import annotations

from core.style_dna_review_gate_runner import run_style_dna_review_gate_for_job
from core.unified_edit_signal_registry import (
    SOURCE_STYLE_DNA_REVIEW_GATE,
    build_unified_edit_signal_result,
)
from models.job import Job


def _job() -> Job:
    job = Job.from_dict({"job_id": "job_registry_2b61"})
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


def test_registry_collects_style_dna_review_gate_signals():
    job = _job()
    run_style_dna_review_gate_for_job(job)

    result = build_unified_edit_signal_result(job)

    assert SOURCE_STYLE_DNA_REVIEW_GATE in result.source_counts
    signal_types = {signal["signal_type"] for signal in result.signals}
    assert "style_dna_review_approved" in signal_types
    assert "style_dna_review_proposal_approved" in signal_types
    assert "style_dna_review_ready_for_later_apply" in signal_types
    assert "style_dna_apply_still_not_allowed" in signal_types
    assert "style_dna_file_write_still_not_allowed" in signal_types
    assert "style_dna_profile_change_still_not_allowed" in signal_types
    assert "style_dna_timeline_modify_still_not_allowed" in signal_types
    assert "style_dna_render_trigger_still_not_allowed" in signal_types


def test_registry_signal_metadata_marks_review_gate_only():
    job = _job()
    run_style_dna_review_gate_for_job(job)

    result = build_unified_edit_signal_result(job)
    review_signals = [
        signal
        for signal in result.signals
        if signal.get("source") == SOURCE_STYLE_DNA_REVIEW_GATE
    ]

    assert review_signals
    for signal in review_signals:
        metadata = signal.get("metadata") or {}
        assert metadata["style_dna_review_gate_only"] is True
        assert metadata["human_approval_gate_only"] is True
        assert metadata["no_style_dna_file_write_in_2b_61"] is True
        assert metadata["no_profile_change_in_2b_61"] is True
        assert metadata["no_cutting_rule_activation_in_2b_61"] is True
        assert metadata["no_timeline_modify_in_2b_61"] is True
        assert metadata["no_render_trigger_in_2b_61"] is True
        assert metadata["no_publish_in_2b_61"] is True
