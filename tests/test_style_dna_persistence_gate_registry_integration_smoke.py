from __future__ import annotations

from core.style_dna_persistence_gate_runner import run_style_dna_persistence_gate_for_job
from core.unified_edit_signal_registry import build_unified_edit_signal_result


def _job():
    job = {
        "job_id": "registry_2b63",
        "style_dna_apply_plan_status": "style_dna_apply_plan_ready",
        "style_dna_apply_plan": {
            "plan_id": "registry_2b63_style_dna_apply_plan",
            "profile": "gaming_main",
        },
        "style_dna_apply_operation_count": 1,
        "style_dna_apply_approved_operation_count": 1,
        "style_dna_apply_before_snapshot": {"zoom_intensity": 1.0},
        "style_dna_apply_after_preview": {"zoom_intensity": 1.2},
        "style_dna_apply_ready_for_future_file_write": True,
        "style_dna_persistence_requested_status": "approved_write",
        "style_dna_persistence_approved_by": "Hajar",
        "style_dna_persistence_target_path_hint": "profiles/style_dna.json",
        "style_dna_persistence_backup_required": True,
    }
    run_style_dna_persistence_gate_for_job(job)
    return job


def test_registry_collects_style_dna_persistence_gate_signals():
    result = build_unified_edit_signal_result(_job())
    data = result.to_dict() if hasattr(result, "to_dict") else result
    signals = data["signals"]
    signal_types = {signal["signal_type"] for signal in signals}
    sources = {signal["source"] for signal in signals}

    assert "style_dna_persistence_gate" in sources
    assert "style_dna_persistence_approved_write" in signal_types
    assert "style_dna_write_intent_created" in signal_types
    assert "style_dna_write_preview_hash_created" in signal_types
    assert "style_dna_write_permission_ready_for_future" in signal_types
    assert "style_dna_file_write_still_not_allowed" in signal_types
    assert "style_dna_backup_write_still_not_allowed" in signal_types
    assert "style_dna_apply_still_not_allowed" in signal_types
    assert "style_dna_profile_change_still_not_allowed" in signal_types
    assert "style_dna_timeline_modify_still_not_allowed" in signal_types
    assert "style_dna_render_trigger_still_not_allowed" in signal_types

    persistence_signals = [
        signal for signal in signals if signal["source"] == "style_dna_persistence_gate"
    ]
    assert persistence_signals
    assert all(
        signal["action_hint"] == "review_style_dna_persistence_gate"
        for signal in persistence_signals
    )
    assert all(
        signal["metadata"]["style_dna_persistence_gate_only"] is True
        for signal in persistence_signals
    )
    assert all(
        signal["metadata"]["no_style_dna_file_write_in_2b_63"] is True
        for signal in persistence_signals
    )
