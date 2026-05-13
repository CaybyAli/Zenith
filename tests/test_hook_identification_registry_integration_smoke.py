from __future__ import annotations

from pathlib import Path

from core.hook_identification_signal_adapter import (
    adapt_hook_identification_report_to_signals,
)
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]


def _job_payload(**overrides) -> dict:
    data = {
        "job_id": "job_hook_registry",
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


def _report(status: str = "hook_candidate_found") -> dict:
    selected = {
        "candidate_id": "hook_candidate_registry",
        "source_item_id": "item_registry",
        "source_segment_id": "seg_registry",
        "start_seconds": 4.0,
        "end_seconds": 9.0,
        "duration_seconds": 5.0,
        "hook_score": 0.86,
        "energy_peak_score": 0.9,
        "surprise_factor_score": 0.8,
        "emotional_value_score": 0.85,
        "content_value_score": 0.82,
        "confidence": 0.9,
        "reason": "strong_hook_candidate_review_only",
        "review_required": True,
        "safety_flags": [],
        "warnings": [],
        "blocking_reasons": [],
        "metadata": {},
    }
    return {
        "report_id": "hook_identification_report_registry",
        "job_id": "job_hook_registry",
        "status": status,
        "selected_candidate": selected if status == "hook_candidate_found" else None,
        "candidates": [selected],
        "total_candidates": 1,
        "best_hook_score": 0.86,
        "review_required": True,
        "can_apply_hook": False,
        "can_reorder_timeline": False,
        "can_render": False,
        "warnings": [],
        "blocking_reasons": [],
        "recommendation": "review_hook_candidate",
        "metadata": {
            "review_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_37": True,
            "no_render_in_2b_37": True,
            "no_timeline_reorder_in_2b_37": True,
        },
    }


def test_signal_adapter_emits_hook_candidate_review_signals() -> None:
    result = adapt_hook_identification_report_to_signals(_report())
    signal_types = {signal["signal_type"] for signal in result.signals}

    assert "hook_candidate_found" in signal_types
    assert "hook_candidate_review_required" in signal_types
    assert "hook_candidate_high_score" in signal_types

    first_signal = result.signals[0]
    assert first_signal["source"] == "hook_identification"
    assert first_signal["action_hint"] == "review_hook_candidate"
    assert first_signal["metadata"]["review_only"] is True
    assert first_signal["metadata"]["media_unchanged"] is True
    assert first_signal["metadata"]["no_execution_in_2b_37"] is True
    assert first_signal["metadata"]["no_render_in_2b_37"] is True
    assert first_signal["metadata"]["no_timeline_reorder_in_2b_37"] is True
    assert first_signal["metadata"]["can_apply_hook"] is False
    assert first_signal["metadata"]["can_reorder_timeline"] is False
    assert first_signal["metadata"]["can_render"] is False


def test_signal_adapter_emits_missing_safe_candidate_signal() -> None:
    report = _report(status="no_safe_hook_candidate")
    report["candidates"] = []
    report["best_hook_score"] = 0.0

    result = adapt_hook_identification_report_to_signals(report)

    assert result.missing_safe_candidate_signal_count == 1
    assert result.signals[0]["signal_type"] == "hook_candidate_missing_safe_candidate"
    assert result.signals[0]["action_hint"] == "review_hook_candidate"


def test_registry_imports_and_processes_hook_identification() -> None:
    text = (ROOT / "core" / "unified_edit_signal_registry.py").read_text(
        encoding="utf-8"
    )

    assert "from core.hook_identification_signal_adapter import" in text
    assert "adapt_hook_identification_report_to_signals" in text
    assert 'SOURCE_HOOK_IDENTIFICATION = "hook_identification"' in text
    assert "hook_identification_report" in text
    assert "source_counts[SOURCE_HOOK_IDENTIFICATION]" in text


def test_registry_runtime_counts_hook_identification_signals() -> None:
    job = Job.from_dict(
        _job_payload(
            hook_identification_report=_report(),
        )
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["hook_identification"] >= 3
    assert result.type_counts["hook_candidate_found"] == 1
    assert result.type_counts["hook_candidate_review_required"] == 1
    assert result.type_counts["hook_candidate_high_score"] == 1


def test_hook_registry_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "core/hook_identification_signal_adapter.py",
        "core/unified_edit_signal_registry.py",
        "tests/test_hook_identification_registry_integration_smoke.py",
    ):
        content = (ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
