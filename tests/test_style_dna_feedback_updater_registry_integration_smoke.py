from __future__ import annotations

from types import SimpleNamespace

from core.style_dna_feedback_updater_runner import run_style_dna_feedback_updater_for_job
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job


def test_registry_collects_style_dna_feedback_update_signals():
    job = SimpleNamespace(
        job_id="registry_style_dna_job",
        profile="gaming_main",
        feedback_intake_status="feedback_intake_ready",
        feedback_intake_report={
            "report_id": "feedback_report_registry",
            "status": "feedback_intake_ready",
            "submission_count": 2,
            "timestamp_feedback_count": 2,
            "average_video_score": 6.0,
            "tags_summary": {"bad_pacing": 2},
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
        existing_style_dna_snapshot={},
        style_dna_update_allow_file_write=False,
    )

    run_style_dna_feedback_updater_for_job(job)
    result = run_unified_edit_signal_registry_for_job(job)
    payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)

    signals = payload.get("signals", [])
    signal_types = {signal.get("signal_type") for signal in signals}
    sources = {signal.get("source") for signal in signals}

    assert "style_dna_feedback_update" in sources
    assert "style_dna_proposal_created" in signal_types
    assert "style_dna_ready_for_human_review" in signal_types
    assert "style_dna_file_write_still_not_allowed" in signal_types
    assert "style_dna_profile_change_still_not_allowed" in signal_types
    assert "style_dna_timeline_modify_still_not_allowed" in signal_types
    assert "style_dna_render_trigger_still_not_allowed" in signal_types


def test_signal_adapter_metadata_is_safe():
    from core.style_dna_feedback_updater_signal_adapter import (
        build_style_dna_feedback_update_signals,
    )

    job = {
        "style_dna_feedback_update_report": {
            "status": "style_dna_update_draft_ready",
            "proposal_count": 1,
            "ready_for_human_review": True,
            "ready_for_later_apply": True,
            "draft": {"overfitting_risk": "low"},
        }
    }

    signals = build_style_dna_feedback_update_signals(job)
    assert signals

    for signal in signals:
        metadata = signal["metadata"]
        assert metadata["style_dna_update_proposal_only"] is True
        assert metadata["style_dna_draft_only"] is True
        assert metadata["no_style_dna_file_write_in_2b_60"] is True
        assert metadata["no_profile_change_in_2b_60"] is True
        assert metadata["no_cutting_rule_activation_in_2b_60"] is True
        assert metadata["no_timeline_modify_in_2b_60"] is True
        assert metadata["no_render_trigger_in_2b_60"] is True
        assert metadata["no_publish_in_2b_60"] is True
