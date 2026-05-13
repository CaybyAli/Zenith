from __future__ import annotations

from pathlib import Path

from core.emotional_arc_signal_adapter import adapt_emotional_arc_report_to_signals
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]


def _job_payload(**overrides) -> dict:
    data = {
        "job_id": "job_emotional_arc_registry",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }
    data.update(overrides)
    return data


def _report(status: str = "arc_analysis_ready_with_warnings") -> dict:
    return {
        "report_id": "emotional_arc_report_registry",
        "job_id": "job_emotional_arc_registry",
        "status": status,
        "arc_points": [
            {
                "point_id": "emotional_arc_point_registry",
                "source_item_id": "item_registry",
                "source_segment_id": "seg_registry",
                "start_seconds": 4.0,
                "end_seconds": 9.0,
                "duration_seconds": 5.0,
                "timeline_position_ratio": 0.0,
                "actual_energy_score": 0.42,
                "target_energy_score": 0.95,
                "deviation_score": 0.53,
                "arc_phase": "hook",
                "label": "hook:item_registry",
                "review_required": True,
                "warnings": [],
                "metadata": {},
            }
        ],
        "suggestions": [
            {
                "suggestion_id": "emotional_arc_suggestion_weak_hook",
                "suggestion_type": "weak_hook",
                "source_item_id": "item_registry",
                "arc_phase": "hook",
                "severity": "high",
                "reason": "Hook energy is below the target review threshold.",
                "review_required": True,
                "can_auto_apply": False,
                "metadata": {},
            },
            {
                "suggestion_id": "emotional_arc_suggestion_missing_climax",
                "suggestion_type": "missing_climax",
                "source_item_id": None,
                "arc_phase": "climax",
                "severity": "high",
                "reason": "No clear emotional climax was detected.",
                "review_required": True,
                "can_auto_apply": False,
                "metadata": {},
            },
        ],
        "actual_curve": [],
        "target_curve": [],
        "average_deviation": 0.53,
        "max_deviation": 0.53,
        "flatness_score": 1.0,
        "hook_strength_score": 0.42,
        "climax_strength_score": 0.0,
        "breathing_room_score": 0.0,
        "review_required": True,
        "can_apply_arc": False,
        "can_reorder_timeline": False,
        "can_trim": False,
        "can_extend": False,
        "can_render": False,
        "warnings": ["using_emotional_arc_fallback_score"],
        "blocking_reasons": [],
        "recommendation": "review_emotional_arc_suggestions",
        "metadata": {
            "review_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_38": True,
            "no_render_in_2b_38": True,
            "no_timeline_reorder_in_2b_38": True,
            "no_arc_apply_in_2b_38": True,
        },
    }


def test_signal_adapter_emits_emotional_arc_review_signals() -> None:
    result = adapt_emotional_arc_report_to_signals(_report())
    signal_types = {signal["signal_type"] for signal in result.signals}

    assert "emotional_arc_ready_with_warnings" in signal_types
    assert "emotional_arc_weak_hook" in signal_types
    assert "emotional_arc_missing_climax" in signal_types

    first_signal = result.signals[0]
    assert first_signal["source"] == "emotional_arc"
    assert first_signal["action_hint"] == "review_emotional_arc"
    assert first_signal["metadata"]["review_only"] is True
    assert first_signal["metadata"]["media_unchanged"] is True
    assert first_signal["metadata"]["no_execution_in_2b_38"] is True
    assert first_signal["metadata"]["no_render_in_2b_38"] is True
    assert first_signal["metadata"]["no_timeline_reorder_in_2b_38"] is True
    assert first_signal["metadata"]["no_arc_apply_in_2b_38"] is True
    assert first_signal["metadata"]["can_apply_arc"] is False
    assert first_signal["metadata"]["can_reorder_timeline"] is False
    assert first_signal["metadata"]["can_trim"] is False
    assert first_signal["metadata"]["can_extend"] is False
    assert first_signal["metadata"]["can_render"] is False


def test_signal_adapter_emits_blocked_and_failed_status_signals() -> None:
    blocked = adapt_emotional_arc_report_to_signals(_report(status="blocked"))
    failed = adapt_emotional_arc_report_to_signals(_report(status="failed"))

    assert blocked.blocked_signal_count == 1
    assert blocked.signals[0]["signal_type"] == "emotional_arc_blocked"
    assert failed.failed_signal_count == 1
    assert failed.signals[0]["signal_type"] == "emotional_arc_failed"


def test_registry_imports_and_processes_emotional_arc() -> None:
    text = (ROOT / "core" / "unified_edit_signal_registry.py").read_text(
        encoding="utf-8"
    )

    assert "from core.emotional_arc_signal_adapter import" in text
    assert "adapt_emotional_arc_report_to_signals" in text
    assert 'SOURCE_EMOTIONAL_ARC = "emotional_arc"' in text
    assert "emotional_arc_report" in text
    assert "source_counts[SOURCE_EMOTIONAL_ARC]" in text


def test_registry_runtime_counts_emotional_arc_signals() -> None:
    job = Job.from_dict(_job_payload(emotional_arc_report=_report()))

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["emotional_arc"] >= 3
    assert result.type_counts["emotional_arc_ready_with_warnings"] == 1
    assert result.type_counts["emotional_arc_weak_hook"] == 1
    assert result.type_counts["emotional_arc_missing_climax"] == 1


def test_emotional_arc_registry_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "core/emotional_arc_signal_adapter.py",
        "core/unified_edit_signal_registry.py",
        "tests/test_emotional_arc_registry_integration_smoke.py",
    ):
        content = (ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
