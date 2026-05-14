from types import SimpleNamespace

from core.render_readiness_guard_signal_adapter import (
    build_render_readiness_guard_signals,
)
from core.unified_edit_signal_registry import build_unified_edit_signal_result


def _job_with_render_readiness_report():
    return SimpleNamespace(
        render_readiness_guard_report={
            "status": "render_readiness_ready_with_warnings",
            "checks": [
                {
                    "check_id": "timeline_approval_approved",
                    "category": "approval",
                    "status": "warning",
                    "severity": "warning",
                    "message": "Timeline Approval ist nicht approved.",
                },
                {
                    "check_id": "no_execution_permission_leaked",
                    "category": "permission_leak",
                    "status": "blocked",
                    "severity": "blocking",
                    "message": "Ein altes Execution-Feld ist True.",
                },
            ],
            "warnings": ["Timeline Approval ist nicht approved."],
            "blocking_reasons": ["Ein altes Execution-Feld ist True."],
            "metadata": {
                "phase": "2B-45",
                "render_readiness_guard_only": True,
            },
        },
        render_readiness_guard={},
    )


def test_render_readiness_signal_adapter_creates_review_signals():
    signals = build_render_readiness_guard_signals(_job_with_render_readiness_report())

    signal_types = {signal["signal_type"] for signal in signals}

    assert "render_readiness_ready_with_warnings" in signal_types
    assert "render_readiness_ready_for_next_stage" in signal_types
    assert "render_readiness_approval_missing" in signal_types
    assert "render_readiness_execution_permission_leak" in signal_types

    for signal in signals:
        assert signal["source"] == "render_readiness_guard"
        assert signal["action_hint"] == "review_render_readiness"
        assert signal["metadata"]["render_readiness_guard_only"] is True
        assert signal["metadata"]["media_unchanged"] is True
        assert signal["metadata"]["no_execution_in_2b_45"] is True
        assert signal["metadata"]["no_render_in_2b_45"] is True
        assert signal["metadata"]["no_ffmpeg_in_2b_45"] is True
        assert signal["metadata"]["no_media_write_in_2b_45"] is True
        assert signal["metadata"]["no_timeline_apply_in_2b_45"] is True


def test_unified_registry_collects_render_readiness_guard_signals():
    result = build_unified_edit_signal_result(_job_with_render_readiness_report())

    assert result.source_counts["render_readiness_guard"] >= 1

    render_readiness_signals = [
        signal
        for signal in result.signals
        if signal.get("source") == "render_readiness_guard"
    ]

    assert render_readiness_signals
    assert any(
        signal.get("signal_type") == "render_readiness_ready_with_warnings"
        for signal in render_readiness_signals
    )
    assert any(
        signal.get("signal_type") == "render_readiness_execution_permission_leak"
        for signal in render_readiness_signals
    )

    for signal in render_readiness_signals:
        assert signal.get("action_hint") == "review_render_readiness"
        metadata = signal.get("metadata", {})
        assert metadata.get("render_readiness_guard_only") is True
        assert metadata.get("media_unchanged") is True
        assert metadata.get("no_execution_in_2b_45") is True
        assert metadata.get("no_render_in_2b_45") is True


def test_missing_render_readiness_report_creates_failed_signal():
    signals = build_render_readiness_guard_signals(
        SimpleNamespace(render_readiness_guard_report={}, render_readiness_guard={})
    )

    assert len(signals) == 1
    assert signals[0]["signal_type"] == "render_readiness_failed"
    assert signals[0]["source"] == "render_readiness_guard"
    assert signals[0]["action_hint"] == "review_render_readiness"
    assert signals[0]["metadata"]["missing_report"] is True
