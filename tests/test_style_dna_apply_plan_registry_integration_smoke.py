from __future__ import annotations

from core.style_dna_apply_plan_runner import run_style_dna_apply_plan_for_job
from core.unified_edit_signal_registry import (
    SOURCE_STYLE_DNA_APPLY_PLAN,
    build_unified_edit_signal_result,
)
from models.job import Job


def _job() -> Job:
    job = Job.from_dict({"job_id": "job_registry_2b62"})
    job.style_dna_profile_name = "gaming_main"
    job.existing_style_dna_snapshot = {"preferred_hook_energy_min": 0.85}
    job.style_dna_review_status = "style_dna_review_approved"
    job.style_dna_review_ready_for_later_apply = True
    job.style_dna_review_blocking_reasons = []
    job.style_dna_review_gate_report = {
        "report_id": "review_report_registry",
        "status": "style_dna_review_approved",
    }
    job.style_dna_review_gate = {"gate_id": "gate_registry"}
    job.style_dna_update_draft = {"draft_id": "draft_registry"}
    job.style_dna_update_proposals = [
        {
            "proposal_id": "proposal_registry",
            "parameter_name": "preferred_hook_energy_min",
            "current_value": 0.85,
            "proposed_value": 0.90,
            "delta": 0.05,
        }
    ]
    job.style_dna_review_proposal_decisions = [
        {"proposal_id": "proposal_registry", "status": "approved"}
    ]
    return job


def test_registry_collects_style_dna_apply_plan_signals():
    job = _job()
    run_style_dna_apply_plan_for_job(job)

    result = build_unified_edit_signal_result(job)

    assert SOURCE_STYLE_DNA_APPLY_PLAN in result.source_counts
    signal_types = {signal["signal_type"] for signal in result.signals}
    assert "style_dna_apply_operation_planned" in signal_types
    assert "style_dna_after_preview_created" in signal_types
    assert "style_dna_ready_for_future_file_write" in signal_types
    assert "style_dna_apply_still_not_allowed" in signal_types
    assert "style_dna_file_write_still_not_allowed" in signal_types
    assert "style_dna_profile_change_still_not_allowed" in signal_types
    assert "style_dna_timeline_modify_still_not_allowed" in signal_types
    assert "style_dna_render_trigger_still_not_allowed" in signal_types


def test_registry_signal_metadata_marks_apply_plan_only():
    job = _job()
    run_style_dna_apply_plan_for_job(job)

    result = build_unified_edit_signal_result(job)
    apply_signals = [
        signal
        for signal in result.signals
        if signal.get("source") == SOURCE_STYLE_DNA_APPLY_PLAN
    ]

    assert apply_signals
    for signal in apply_signals:
        metadata = signal.get("metadata") or {}
        assert metadata["style_dna_apply_plan_only"] is True
        assert metadata["non_writing_apply_contract"] is True
        assert metadata["style_dna_preview_only"] is True
        assert metadata["no_style_dna_file_write_in_2b_62"] is True
        assert metadata["no_profile_change_in_2b_62"] is True
        assert metadata["no_cutting_rule_activation_in_2b_62"] is True
        assert metadata["no_timeline_modify_in_2b_62"] is True
        assert metadata["no_render_trigger_in_2b_62"] is True
        assert metadata["no_publish_in_2b_62"] is True
