from __future__ import annotations

from pathlib import Path

from core.dynamic_pacing_signal_adapter import adapt_dynamic_pacing_report_to_signals
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]


def _job_payload(**overrides) -> dict:
    data = {
        "job_id": "job_dynamic_pacing_registry",
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


def _report(status: str = "pacing_analysis_ready_with_warnings") -> dict:
    return {
        "report_id": "dynamic_pacing_report_registry",
        "job_id": "job_dynamic_pacing_registry",
        "status": status,
        "pacing_segments": [
            {
                "segment_id": "pacing_segment_good",
                "source_item_id": "item_good",
                "source_segment_id": "seg_good",
                "start_seconds": 4.0,
                "end_seconds": 8.0,
                "duration_seconds": 4.0,
                "energy_score": 0.65,
                "arc_phase": "build_up",
                "target_cut_rate_min": 10.0,
                "target_cut_rate_max": 20.0,
                "actual_cut_rate": 15.0,
                "pacing_status": "good_pacing_match",
                "review_required": True,
                "warnings": [],
                "metadata": {},
            }
        ],
        "suggestions": [
            {
                "suggestion_id": "pacing_suggestion_too_slow",
                "suggestion_type": "pacing_too_slow_for_energy",
                "source_item_id": "item_slow",
                "source_segment_id": "seg_slow",
                "severity": "high",
                "reason": "Actual cut rate is below target.",
                "review_required": True,
                "can_auto_apply": False,
                "metadata": {
                    "start_seconds": 0.0,
                    "end_seconds": 6.0,
                    "duration_seconds": 6.0,
                    "energy_score": 0.92,
                    "actual_cut_rate": 10.0,
                },
            },
            {
                "suggestion_id": "pacing_suggestion_breathing",
                "suggestion_type": "missing_breathing_room",
                "source_item_id": "item_fast",
                "source_segment_id": "seg_fast",
                "severity": "medium",
                "reason": "Three fast clips appear consecutively.",
                "review_required": True,
                "can_auto_apply": False,
                "metadata": {"fast_run_count": 3},
            },
        ],
        "average_cut_rate": 15.0,
        "target_cut_rate_range": {"min": 10.0, "max": 20.0},
        "pacing_match_score": 1.0,
        "monotony_score": 0.0,
        "breathing_room_score": 0.5,
        "fast_run_count": 3,
        "slow_run_count": 0,
        "review_required": True,
        "can_apply_pacing": False,
        "can_split_clips": False,
        "can_merge_clips": False,
        "can_trim": False,
        "can_extend": False,
        "can_reorder_timeline": False,
        "can_render": False,
        "warnings": [],
        "blocking_reasons": [],
        "recommendation": "review_dynamic_pacing_suggestions",
        "metadata": {
            "review_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_39": True,
            "no_render_in_2b_39": True,
            "no_timeline_reorder_in_2b_39": True,
            "no_pacing_apply_in_2b_39": True,
            "no_split_merge_trim_extend_in_2b_39": True,
        },
    }


def test_signal_adapter_emits_dynamic_pacing_review_signals() -> None:
    result = adapt_dynamic_pacing_report_to_signals(_report())
    signal_types = {signal["signal_type"] for signal in result.signals}

    assert "dynamic_pacing_ready_with_warnings" in signal_types
    assert "dynamic_pacing_good_match" in signal_types
    assert "dynamic_pacing_too_slow_for_energy" in signal_types
    assert "dynamic_pacing_missing_breathing_room" in signal_types

    first_signal = result.signals[0]
    assert first_signal["source"] == "dynamic_pacing"
    assert first_signal["action_hint"] == "review_dynamic_pacing"
    assert first_signal["metadata"]["review_only"] is True
    assert first_signal["metadata"]["media_unchanged"] is True
    assert first_signal["metadata"]["no_execution_in_2b_39"] is True
    assert first_signal["metadata"]["no_render_in_2b_39"] is True
    assert first_signal["metadata"]["no_timeline_reorder_in_2b_39"] is True
    assert first_signal["metadata"]["no_pacing_apply_in_2b_39"] is True
    assert first_signal["metadata"]["no_split_merge_trim_extend_in_2b_39"] is True
    assert first_signal["metadata"]["can_apply_pacing"] is False
    assert first_signal["metadata"]["can_split_clips"] is False
    assert first_signal["metadata"]["can_merge_clips"] is False
    assert first_signal["metadata"]["can_trim"] is False
    assert first_signal["metadata"]["can_extend"] is False
    assert first_signal["metadata"]["can_reorder_timeline"] is False
    assert first_signal["metadata"]["can_render"] is False


def test_signal_adapter_emits_blocked_and_failed_status_signals() -> None:
    blocked = adapt_dynamic_pacing_report_to_signals(_report(status="blocked"))
    failed = adapt_dynamic_pacing_report_to_signals(_report(status="failed"))

    assert blocked.blocked_signal_count == 1
    assert blocked.signals[0]["signal_type"] == "dynamic_pacing_blocked"
    assert failed.failed_signal_count == 1
    assert failed.signals[0]["signal_type"] == "dynamic_pacing_failed"


def test_registry_imports_and_processes_dynamic_pacing() -> None:
    text = (ROOT / "core" / "unified_edit_signal_registry.py").read_text(
        encoding="utf-8"
    )

    assert "from core.dynamic_pacing_signal_adapter import" in text
    assert "adapt_dynamic_pacing_report_to_signals" in text
    assert 'SOURCE_DYNAMIC_PACING = "dynamic_pacing"' in text
    assert "dynamic_pacing_report" in text
    assert "source_counts[SOURCE_DYNAMIC_PACING]" in text


def test_registry_runtime_counts_dynamic_pacing_signals() -> None:
    job = Job.from_dict(_job_payload(dynamic_pacing_report=_report()))

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["dynamic_pacing"] >= 4
    assert result.type_counts["dynamic_pacing_ready_with_warnings"] == 1
    assert result.type_counts["dynamic_pacing_good_match"] == 1
    assert result.type_counts["dynamic_pacing_too_slow_for_energy"] == 1
    assert result.type_counts["dynamic_pacing_missing_breathing_room"] == 1


def test_dynamic_pacing_registry_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "core/dynamic_pacing_signal_adapter.py",
        "core/unified_edit_signal_registry.py",
        "tests/test_dynamic_pacing_registry_integration_smoke.py",
    ):
        content = (ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
