from pathlib import Path

from core.timeline_safety_validator_signal_adapter import (
    adapt_timeline_safety_validator_report_to_signals,
)
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job
from models.timeline_safety_validator import (
    TIMELINE_SAFETY_REASON_CENSOR_ITEM_NOT_PROTECTED,
    TIMELINE_SAFETY_REASON_CONTINUITY_BLOCK_NOT_PRESERVED,
    TIMELINE_SAFETY_REASON_END_BEFORE_START,
    TIMELINE_SAFETY_REASON_PROTECTED_ITEM_HAS_UNSAFE_ACTION,
    TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34,
    TIMELINE_SAFETY_REASON_TIMELINE_GAP,
    TIMELINE_SAFETY_REASON_TIMELINE_OVERLAP,
    TIMELINE_SAFETY_STATUS_BLOCKED,
    TIMELINE_SAFETY_STATUS_FAILED,
    TIMELINE_SAFETY_STATUS_PASSED,
    TIMELINE_SAFETY_STATUS_PASSED_WITH_WARNINGS,
)


ROOT = Path(__file__).resolve().parents[1]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _make_job(extra=None):
    data = {
        "job_id": "job_timeline_safety_registry",
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


def _validation(status: str, extra=None):
    data = {
        "safety_validation_id": f"timeline_safety_validation_{status}",
        "job_id": "job_timeline_safety_registry",
        "source_review_timeline_plan_id": "review_timeline_plan_registry",
        "source_timeline_approval_gate_id": "timeline_approval_gate_registry",
        "validation_status": status,
        "is_safe_for_future_execution": status == TIMELINE_SAFETY_STATUS_PASSED,
        "is_safe_for_render": False,
        "requires_manual_review": status != TIMELINE_SAFETY_STATUS_PASSED,
        "blocking_errors": [],
        "warnings": [],
        "item_results": [],
        "total_items_checked": 1,
        "invalid_timing_count": 0,
        "overlap_count": 0,
        "gap_count": 0,
        "protected_violation_count": 0,
        "censor_violation_count": 0,
        "continuity_violation_count": 0,
        "approval_violation_count": 0,
        "future_execution_safety_status": "safe_after_approval",
        "metadata": {
            "review_only": True,
            "safety_validator_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_34": True,
            "no_render_in_2b_34": True,
        },
    }
    if extra:
        data.update(extra)
    return data


def test_signal_adapter_emits_timeline_safety_status_signal_types():
    statuses = [
        (TIMELINE_SAFETY_STATUS_PASSED, "timeline_safety_passed"),
        (
            TIMELINE_SAFETY_STATUS_PASSED_WITH_WARNINGS,
            "timeline_safety_passed_with_warnings",
        ),
        (TIMELINE_SAFETY_STATUS_BLOCKED, "timeline_safety_blocked"),
        (TIMELINE_SAFETY_STATUS_FAILED, "timeline_safety_failed"),
    ]

    for validation_status, expected_signal_type in statuses:
        result = adapt_timeline_safety_validator_report_to_signals(
            {
                "timeline_safety_validation": _validation(validation_status),
            }
        )

        assert result.signal_count == 1
        assert result.signals[0]["signal_type"] == expected_signal_type
        assert result.signals[0]["metadata"]["is_safe_for_render"] is False
        assert result.signals[0]["metadata"]["safety_validator_only"] is True
        assert result.signals[0]["metadata"]["no_render_in_2b_34"] is True


def test_signal_adapter_emits_timeline_safety_reason_signal_types():
    validation = _validation(
        TIMELINE_SAFETY_STATUS_BLOCKED,
        {
            "blocking_errors": [
                TIMELINE_SAFETY_REASON_END_BEFORE_START,
                TIMELINE_SAFETY_REASON_TIMELINE_OVERLAP,
                TIMELINE_SAFETY_REASON_PROTECTED_ITEM_HAS_UNSAFE_ACTION,
                TIMELINE_SAFETY_REASON_CENSOR_ITEM_NOT_PROTECTED,
                TIMELINE_SAFETY_REASON_CONTINUITY_BLOCK_NOT_PRESERVED,
                TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34,
            ],
            "warnings": [
                TIMELINE_SAFETY_REASON_TIMELINE_GAP,
            ],
        },
    )

    result = adapt_timeline_safety_validator_report_to_signals(
        {
            "timeline_safety_validation": validation,
        }
    )

    signal_types = {signal["signal_type"] for signal in result.signals}

    assert "timeline_safety_blocked" in signal_types
    assert "timeline_safety_invalid_timing" in signal_types
    assert "timeline_safety_overlap" in signal_types
    assert "timeline_safety_gap" in signal_types
    assert "timeline_safety_protected_violation" in signal_types
    assert "timeline_safety_censor_violation" in signal_types
    assert "timeline_safety_continuity_violation" in signal_types
    assert "timeline_safety_approval_violation" in signal_types


def test_registry_imports_and_processes_timeline_safety_validator():
    text = _text(ROOT / "core" / "unified_edit_signal_registry.py")

    assert "from core.timeline_safety_validator_signal_adapter import" in text
    assert "adapt_timeline_safety_validator_report_to_signals" in text
    assert 'SOURCE_TIMELINE_SAFETY_VALIDATOR = "timeline_safety_validator"' in text
    assert "timeline_safety_validator_report" in text
    assert "timeline_safety_validator" in text
    assert "source_counts[SOURCE_TIMELINE_SAFETY_VALIDATOR]" in text


def test_registry_runtime_counts_timeline_safety_validator_signal():
    job = _make_job(
        {
            "timeline_safety_validator_report": {
                "status": TIMELINE_SAFETY_STATUS_BLOCKED,
                "timeline_safety_validation": _validation(
                    TIMELINE_SAFETY_STATUS_BLOCKED,
                    {
                        "blocking_errors": [
                            TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34,
                        ],
                    },
                ),
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["timeline_safety_validator"] >= 1
    assert result.type_counts["timeline_safety_blocked"] == 1
    assert result.type_counts["timeline_safety_approval_violation"] == 1


def test_passed_signal_is_future_only_and_no_render_now():
    result = adapt_timeline_safety_validator_report_to_signals(
        {
            "timeline_safety_validation": _validation(
                TIMELINE_SAFETY_STATUS_PASSED,
            ),
        }
    )

    signal = result.signals[0]

    assert signal["signal_type"] == "timeline_safety_passed"
    assert signal["action_hint"] == "timeline_safety_validated_for_future_review_flow"
    assert signal["metadata"]["is_safe_for_future_execution"] is True
    assert signal["metadata"]["is_safe_for_render"] is False
    assert signal["metadata"]["no_execution_in_2b_34"] is True
    assert signal["metadata"]["no_render_in_2b_34"] is True
