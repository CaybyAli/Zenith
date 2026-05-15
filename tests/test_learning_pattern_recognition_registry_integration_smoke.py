from core.learning_pattern_recognition_runner import run_learning_pattern_recognition_for_job
from core.learning_pattern_recognition_signal_adapter import (
    build_learning_pattern_recognition_signals,
)
from core.unified_edit_signal_registry import build_unified_edit_signal_result


def test_learning_pattern_signal_adapter_emits_status_and_safety_signals():
    job = {
        "job_id": "job_signal",
        "feedback_intake_status": "feedback_intake_ready",
        "feedback_submission_count": 2,
        "feedback_tags_summary": {"bad_pacing": 2},
    }
    run_learning_pattern_recognition_for_job(job)

    signals = build_learning_pattern_recognition_signals(job)
    signal_types = {signal["signal_type"] for signal in signals}

    assert "learning_pattern_ready_with_warnings" in signal_types
    assert "learning_pattern_repeated_issue_detected" in signal_types
    assert "learning_pattern_cluster_detected" in signal_types
    assert "learning_pattern_style_dna_update_still_not_allowed" in signal_types
    assert "learning_pattern_profile_change_still_not_allowed" in signal_types
    assert "learning_pattern_timeline_modify_still_not_allowed" in signal_types
    assert "learning_pattern_render_trigger_still_not_allowed" in signal_types

    for signal in signals:
        assert signal["source"] == "learning_pattern_recognition"
        assert signal["action_hint"] == "review_learning_pattern_recognition"
        assert signal["metadata"]["learning_pattern_recognition_only"] is True
        assert signal["metadata"]["feedback_trend_analysis_only"] is True
        assert signal["metadata"]["no_style_dna_file_write_in_2b_64"] is True
        assert signal["metadata"]["no_profile_change_in_2b_64"] is True
        assert signal["metadata"]["no_cutting_rule_activation_in_2b_64"] is True
        assert signal["metadata"]["no_timeline_modify_in_2b_64"] is True
        assert signal["metadata"]["no_render_trigger_in_2b_64"] is True
        assert signal["metadata"]["no_publish_in_2b_64"] is True


def test_unified_registry_collects_learning_pattern_signals():
    job = {
        "job_id": "job_registry",
        "feedback_intake_status": "feedback_intake_ready",
        "feedback_submission_count": 2,
        "feedback_tags_summary": {"wrong_hook": 2},
    }
    run_learning_pattern_recognition_for_job(job)

    result = build_unified_edit_signal_result(job)
    payload = result.to_dict() if hasattr(result, "to_dict") else result

    assert payload["source_counts"]["learning_pattern_recognition"] >= 1
    assert any(
        signal["source"] == "learning_pattern_recognition"
        for signal in payload["signals"]
    )
