from pathlib import Path

from core.review_timeline_plan_signal_adapter import (
    adapt_review_timeline_plan_report_to_signals,
)
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _make_job(extra=None):
    data = {
        "job_id": "job_review_timeline_registry",
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
    if extra:
        data.update(extra)
    return Job.from_dict(data)


def _timeline_item(action: str, index: int, extra=None):
    data = {
        "timeline_item_id": f"review_timeline_item_{index}",
        "source_segment_id": f"seg_{index}",
        "start_seconds": float(index * 5),
        "end_seconds": float(index * 5 + 5),
        "source_start_seconds": float(index * 10),
        "source_end_seconds": float(index * 10 + 5),
        "duration_seconds": 5.0,
        "action": action,
        "final_decision": f"FINAL_{action.upper()}",
        "protection_status": "normal",
        "censor_sfx_required": action == "censor_keep",
        "continuity_blocked": action == "blocked_by_continuity",
        "review_required": True,
        "review_reason": f"reason {action}",
        "safety_flags": ["review_only_plan", "approval_required_before_changes"],
        "notes": ["safe_review_timeline_item"],
        "metadata": {},
    }
    if extra:
        data.update(extra)
    return data


def test_signal_adapter_emits_review_timeline_signal_types():
    result = adapt_review_timeline_plan_report_to_signals(
        {
            "items": [
                _timeline_item("keep_review", 1),
                _timeline_item("trim_review", 2),
                _timeline_item("remove_review", 3),
                _timeline_item("protect", 4, {"protection_status": "protected"}),
                _timeline_item(
                    "censor_keep",
                    5,
                    {"protection_status": "censor_protected"},
                ),
                _timeline_item("technical_review", 6),
                _timeline_item("blocked_by_continuity", 7),
                _timeline_item("unknown_review", 8),
            ]
        }
    )

    types = {signal["signal_type"] for signal in result.signals}

    assert "review_timeline_keep_review" in types
    assert "review_timeline_trim_review" in types
    assert "review_timeline_remove_review" in types
    assert "review_timeline_protect" in types
    assert "review_timeline_censor_keep" in types
    assert "review_timeline_technical_review" in types
    assert "review_timeline_blocked_by_continuity" in types
    assert "review_timeline_unknown_review" in types


def test_registry_imports_and_processes_review_timeline_plan():
    text = _text(ROOT / "core" / "unified_edit_signal_registry.py")

    assert (
        "from core.review_timeline_plan_signal_adapter import"
        in text
    )
    assert "adapt_review_timeline_plan_report_to_signals" in text
    assert 'SOURCE_REVIEW_TIMELINE_PLAN = "review_timeline_plan"' in text
    assert "review_timeline_plan_report" in text
    assert "review_timeline_plan_items" in text
    assert "source_counts[SOURCE_REVIEW_TIMELINE_PLAN]" in text


def test_registry_runtime_counts_review_timeline_plan_signals():
    job = _make_job(
        {
            "review_timeline_plan_report": {
                "status": "pending_review",
                "items": [
                    _timeline_item("keep_review", 1),
                    _timeline_item("remove_review", 2),
                    _timeline_item("censor_keep", 3),
                    _timeline_item("blocked_by_continuity", 4),
                ],
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["review_timeline_plan"] == 4
    assert result.type_counts["review_timeline_keep_review"] == 1
    assert result.type_counts["review_timeline_remove_review"] == 1
    assert result.type_counts["review_timeline_censor_keep"] == 1
    assert result.type_counts["review_timeline_blocked_by_continuity"] == 1


def test_review_remove_and_censor_signals_stay_safe():
    result = adapt_review_timeline_plan_report_to_signals(
        {
            "items": [
                _timeline_item("remove_review", 1),
                _timeline_item("censor_keep", 2),
            ]
        }
    )

    by_type = {signal["signal_type"]: signal for signal in result.signals}

    assert (
        by_type["review_timeline_remove_review"]["action_hint"]
        == "human_review_remove_candidate"
    )
    assert (
        by_type["review_timeline_censor_keep"]["action_hint"]
        == "preserve_censor_item_for_later_approval"
    )
    assert by_type["review_timeline_remove_review"]["metadata"]["review_only"] is True
    assert by_type["review_timeline_censor_keep"]["metadata"]["approval_required"] is True
