from types import SimpleNamespace

from core.final_quality_validator_signal_adapter import (
    build_final_quality_validator_signals,
)
from core.unified_edit_signal_registry import build_unified_edit_signal_result


def _job_with_final_quality_report():
    return SimpleNamespace(
        final_quality_validation_report={
            "status": "final_quality_ready_with_warnings",
            "checks": [
                {
                    "check_id": "hook_score_strong",
                    "category": "story",
                    "status": "warning",
                    "severity": "warning",
                    "message": "Hook Score ist unter Zielwert.",
                },
                {
                    "check_id": "no_execution_permission",
                    "category": "safety",
                    "status": "blocked",
                    "severity": "blocking",
                    "message": "Gef?hrliches Ausf?hrungs-Flag ist True.",
                },
            ],
            "warnings": ["Hook Score ist unter Zielwert."],
            "blocking_reasons": ["Gef?hrliches Ausf?hrungs-Flag ist True."],
            "metadata": {
                "phase": "2B-43",
                "review_only": True,
            },
        },
        final_quality_validator={},
    )


def test_final_quality_signal_adapter_creates_review_signals():
    signals = build_final_quality_validator_signals(_job_with_final_quality_report())

    signal_types = {signal["signal_type"] for signal in signals}

    assert "final_quality_ready_with_warnings" in signal_types
    assert "final_quality_story_warning" in signal_types
    assert "final_quality_safety_blocked" in signal_types
    assert "final_quality_hook_weak" in signal_types
    assert "final_quality_execution_not_allowed" in signal_types

    for signal in signals:
        assert signal["source"] == "final_quality_validator"
        assert signal["action_hint"] == "review_final_quality"
        assert signal["metadata"]["review_only"] is True
        assert signal["metadata"]["media_unchanged"] is True
        assert signal["metadata"]["no_execution_in_2b_43"] is True
        assert signal["metadata"]["no_render_in_2b_43"] is True
        assert signal["metadata"]["no_timeline_reorder_in_2b_43"] is True
        assert signal["metadata"]["no_quality_fix_apply_in_2b_43"] is True


def test_unified_registry_collects_final_quality_validator_signals():
    result = build_unified_edit_signal_result(_job_with_final_quality_report())

    assert result.source_counts["final_quality_validator"] >= 1

    final_quality_signals = [
        signal
        for signal in result.signals
        if signal.get("source") == "final_quality_validator"
    ]

    assert final_quality_signals
    assert any(
        signal.get("signal_type") == "final_quality_hook_weak"
        for signal in final_quality_signals
    )
    assert any(
        signal.get("signal_type") == "final_quality_execution_not_allowed"
        for signal in final_quality_signals
    )

    for signal in final_quality_signals:
        assert signal.get("action_hint") == "review_final_quality"
        assert signal.get("metadata", {}).get("review_only") is True
        assert signal.get("metadata", {}).get("media_unchanged") is True


def test_missing_final_quality_report_creates_failed_signal():
    signals = build_final_quality_validator_signals(
        SimpleNamespace(final_quality_validation_report={}, final_quality_validator={})
    )

    assert len(signals) == 1
    assert signals[0]["signal_type"] == "final_quality_failed"
    assert signals[0]["source"] == "final_quality_validator"
    assert signals[0]["action_hint"] == "review_final_quality"
    assert signals[0]["metadata"]["missing_report"] is True
