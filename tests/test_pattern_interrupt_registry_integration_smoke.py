from __future__ import annotations

from pathlib import Path

from core.pattern_interrupt_signal_adapter import (
    adapt_pattern_interrupt_report_to_signals,
)
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]


def _job_payload(**overrides) -> dict:
    data = {
        "job_id": "job_pattern_interrupt_registry",
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


def _report(status: str = "pattern_interrupt_ready_with_warnings") -> dict:
    return {
        "report_id": "pattern_interrupt_report_registry",
        "job_id": "job_pattern_interrupt_registry",
        "status": status,
        "windows": [
            {
                "window_id": "pattern_interrupt_window_registry",
                "start_seconds": 0.0,
                "end_seconds": 60.0,
                "duration_seconds": 60.0,
                "item_ids": ["item_registry"],
                "average_energy_score": 0.50,
                "average_cut_rate": 6.0,
                "energy_variation_score": 0.0,
                "pacing_variation_score": 0.0,
                "visual_variation_score": 0.35,
                "reaction_presence_score": 0.0,
                "monotony_score": 0.90,
                "interrupt_needed": True,
                "recommended_interrupt_type": "pacing_shift_needed",
                "review_required": True,
                "warnings": [],
                "metadata": {},
            }
        ],
        "suggestions": [
            {
                "suggestion_id": "pattern_suggestion_needed",
                "suggestion_type": "pattern_interrupt_needed",
                "source_window_id": "pattern_interrupt_window_registry",
                "source_item_id": "item_registry",
                "start_seconds": 0.0,
                "end_seconds": 60.0,
                "severity": "high",
                "reason": "Review interrupt needed.",
                "review_required": True,
                "can_auto_apply": False,
                "can_insert_zoom": False,
                "can_insert_text_overlay": False,
                "can_insert_sfx": False,
                "can_reorder_timeline": False,
                "can_render": False,
                "metadata": {},
            },
            {
                "suggestion_id": "pattern_suggestion_zoom",
                "suggestion_type": "zoom_reaction_candidate",
                "source_window_id": "pattern_interrupt_window_registry",
                "source_item_id": "item_registry",
                "start_seconds": 0.0,
                "end_seconds": 60.0,
                "severity": "medium",
                "reason": "Reaction signal available.",
                "review_required": True,
                "can_auto_apply": False,
                "can_insert_zoom": False,
                "can_insert_text_overlay": False,
                "can_insert_sfx": False,
                "can_reorder_timeline": False,
                "can_render": False,
                "metadata": {},
            },
            {
                "suggestion_id": "pattern_suggestion_text",
                "suggestion_type": "text_overlay_candidate",
                "source_window_id": "pattern_interrupt_window_registry",
                "source_item_id": "item_registry",
                "start_seconds": 0.0,
                "end_seconds": 60.0,
                "severity": "medium",
                "reason": "Keyword signal available.",
                "review_required": True,
                "can_auto_apply": False,
                "can_insert_zoom": False,
                "can_insert_text_overlay": False,
                "can_insert_sfx": False,
                "can_reorder_timeline": False,
                "can_render": False,
                "metadata": {},
            },
        ],
        "total_windows": 1,
        "interrupt_needed_count": 1,
        "monotony_score": 0.90,
        "average_window_duration_seconds": 60.0,
        "recommended_interrupt_count": 3,
        "review_required": True,
        "can_apply_interrupts": False,
        "can_insert_zoom": False,
        "can_insert_text_overlay": False,
        "can_insert_sfx": False,
        "can_reorder_timeline": False,
        "can_trim": False,
        "can_extend": False,
        "can_render": False,
        "warnings": [],
        "blocking_reasons": [],
        "recommendation": "review_pattern_interrupt_suggestions",
        "metadata": {
            "review_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_40": True,
            "no_render_in_2b_40": True,
            "no_timeline_reorder_in_2b_40": True,
            "no_pattern_apply_in_2b_40": True,
            "no_zoom_insert_in_2b_40": True,
            "no_text_overlay_insert_in_2b_40": True,
            "no_sfx_insert_in_2b_40": True,
        },
    }


def test_signal_adapter_emits_pattern_interrupt_review_signals() -> None:
    result = adapt_pattern_interrupt_report_to_signals(_report())
    signal_types = {signal["signal_type"] for signal in result.signals}

    assert "pattern_interrupt_ready_with_warnings" in signal_types
    assert "pattern_interrupt_needed" in signal_types
    assert "pattern_interrupt_zoom_reaction_candidate" in signal_types
    assert "pattern_interrupt_text_overlay_candidate" in signal_types

    first_signal = result.signals[0]
    assert first_signal["source"] == "pattern_interrupt"
    assert first_signal["action_hint"] == "review_pattern_interrupt"
    assert first_signal["metadata"]["review_only"] is True
    assert first_signal["metadata"]["media_unchanged"] is True
    assert first_signal["metadata"]["no_execution_in_2b_40"] is True
    assert first_signal["metadata"]["no_render_in_2b_40"] is True
    assert first_signal["metadata"]["no_timeline_reorder_in_2b_40"] is True
    assert first_signal["metadata"]["no_pattern_apply_in_2b_40"] is True
    assert first_signal["metadata"]["no_zoom_insert_in_2b_40"] is True
    assert first_signal["metadata"]["no_text_overlay_insert_in_2b_40"] is True
    assert first_signal["metadata"]["no_sfx_insert_in_2b_40"] is True
    assert first_signal["metadata"]["can_apply_interrupts"] is False
    assert first_signal["metadata"]["can_insert_zoom"] is False
    assert first_signal["metadata"]["can_insert_text_overlay"] is False
    assert first_signal["metadata"]["can_insert_sfx"] is False
    assert first_signal["metadata"]["can_reorder_timeline"] is False
    assert first_signal["metadata"]["can_trim"] is False
    assert first_signal["metadata"]["can_extend"] is False
    assert first_signal["metadata"]["can_render"] is False


def test_signal_adapter_emits_blocked_and_failed_status_signals() -> None:
    blocked = adapt_pattern_interrupt_report_to_signals(_report(status="blocked"))
    failed = adapt_pattern_interrupt_report_to_signals(_report(status="failed"))

    assert blocked.blocked_signal_count == 1
    assert blocked.signals[0]["signal_type"] == "pattern_interrupt_blocked"
    assert failed.failed_signal_count == 1
    assert failed.signals[0]["signal_type"] == "pattern_interrupt_failed"


def test_registry_imports_and_processes_pattern_interrupt() -> None:
    text = (ROOT / "core" / "unified_edit_signal_registry.py").read_text(
        encoding="utf-8"
    )

    assert "from core.pattern_interrupt_signal_adapter import" in text
    assert "adapt_pattern_interrupt_report_to_signals" in text
    assert 'SOURCE_PATTERN_INTERRUPT = "pattern_interrupt"' in text
    assert "pattern_interrupt_report" in text
    assert "source_counts[SOURCE_PATTERN_INTERRUPT]" in text


def test_registry_runtime_counts_pattern_interrupt_signals() -> None:
    job = Job.from_dict(_job_payload(pattern_interrupt_report=_report()))

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["pattern_interrupt"] >= 4
    assert result.type_counts["pattern_interrupt_ready_with_warnings"] == 1
    assert result.type_counts["pattern_interrupt_needed"] == 1
    assert result.type_counts["pattern_interrupt_zoom_reaction_candidate"] == 1
    assert result.type_counts["pattern_interrupt_text_overlay_candidate"] == 1


def test_pattern_interrupt_registry_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "core/pattern_interrupt_signal_adapter.py",
        "core/unified_edit_signal_registry.py",
        "tests/test_pattern_interrupt_registry_integration_smoke.py",
    ):
        content = (ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
