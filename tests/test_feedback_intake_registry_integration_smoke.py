from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.feedback_intake_runner import run_feedback_intake_for_job
from core.feedback_intake_signal_adapter import build_feedback_intake_signals
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job


def test_feedback_intake_signal_adapter_emits_expected_signals():
    job = SimpleNamespace(
        job_id="signal_job",
        feedback_video_score=9,
        feedback_tags=["strong_hook"],
        feedback_timestamp_items=[
            {
                "timestamp_seconds": 2,
                "category": "hook",
                "tag": "strong_hook",
                "sentiment": "positive",
                "severity": "high",
            }
        ],
    )
    run_feedback_intake_for_job(job)

    signals = build_feedback_intake_signals(job)
    signal_types = {signal["signal_type"] for signal in signals}

    assert "feedback_intake_ready" in signal_types
    assert "feedback_video_score_received" in signal_types
    assert "feedback_timestamp_item_received" in signal_types
    assert "feedback_positive_received" in signal_types
    assert "feedback_tag_received" in signal_types
    assert "feedback_ready_for_style_dna_update" in signal_types
    assert "feedback_style_dna_update_still_not_allowed" in signal_types
    assert "feedback_timeline_modify_still_not_allowed" in signal_types
    assert "feedback_render_trigger_still_not_allowed" in signal_types

    for signal in signals:
        assert signal["source"] == "feedback_intake"
        assert signal["action_hint"] == "review_feedback_intake"
        assert signal["metadata"]["feedback_intake_only"] is True
        assert signal["metadata"]["review_feedback_only"] is True


def test_unified_registry_collects_feedback_intake_source():
    job = SimpleNamespace(
        job_id="registry_job",
        feedback_video_score=8,
        feedback_timestamp_items=[
            {
                "timestamp_seconds": 4,
                "category": "pacing",
                "tag": "good_pacing",
                "sentiment": "positive",
            }
        ],
    )
    run_feedback_intake_for_job(job)

    result = run_unified_edit_signal_registry_for_job(job)
    payload = result.to_dict() if hasattr(result, "to_dict") else result

    assert payload["source_counts"]["feedback_intake"] >= 1
    assert any(
        signal["source"] == "feedback_intake"
        for signal in payload["signals"]
    )


def test_unified_registry_has_feedback_intake_wiring():
    text = Path("core/unified_edit_signal_registry.py").read_text(encoding="utf-8")

    assert "build_feedback_intake_signals" in text
    assert 'SOURCE_FEEDBACK_INTAKE = "feedback_intake"' in text
    assert 'feedback_intake_report = _job_attr(job, "feedback_intake_report")' in text
