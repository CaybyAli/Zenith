from pathlib import Path

from core.timeline_approval_gate_signal_adapter import (
    adapt_timeline_approval_gate_report_to_signals,
)
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job
from models.timeline_approval_gate import (
    TIMELINE_APPROVAL_GATE_STATUS_APPROVED,
    TIMELINE_APPROVAL_GATE_STATUS_BLOCKED,
    TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
    TIMELINE_APPROVAL_STATUS_APPROVED,
    TIMELINE_APPROVAL_STATUS_BLOCKED,
    TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES,
    TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
    TIMELINE_APPROVAL_STATUS_REJECTED,
)


ROOT = Path(__file__).resolve().parents[1]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _make_job(extra=None):
    data = {
        "job_id": "job_timeline_approval_registry",
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


def _gate(status: str, gate_status: str, extra=None):
    data = {
        "approval_gate_id": f"timeline_approval_gate_{status}",
        "job_id": "job_timeline_approval_registry",
        "source_review_timeline_plan_id": "review_timeline_plan_registry",
        "source_review_timeline_plan_status": "pending_review",
        "approval_status": status,
        "gate_status": gate_status,
        "can_proceed_to_execution": status == TIMELINE_APPROVAL_STATUS_APPROVED,
        "can_render": False,
        "requires_human_approval": status != TIMELINE_APPROVAL_STATUS_APPROVED,
        "total_items": 1,
        "review_required_count": 1,
        "protected_count": 0,
        "censor_required_count": 0,
        "continuity_blocked_count": 0,
        "blocking_reasons": [],
        "warnings": [],
        "safety_flags": ["media_unchanged", "approval_gate_only"],
        "metadata": {
            "review_only": True,
            "approval_gate_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_33": True,
        },
    }
    if extra:
        data.update(extra)
    return data


def test_signal_adapter_emits_timeline_approval_signal_types():
    statuses = [
        (
            TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
            TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
            "timeline_approval_pending_review",
        ),
        (
            TIMELINE_APPROVAL_STATUS_APPROVED,
            TIMELINE_APPROVAL_GATE_STATUS_APPROVED,
            "timeline_approval_approved",
        ),
        (
            TIMELINE_APPROVAL_STATUS_REJECTED,
            TIMELINE_APPROVAL_GATE_STATUS_BLOCKED,
            "timeline_approval_rejected",
        ),
        (
            TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES,
            TIMELINE_APPROVAL_GATE_STATUS_BLOCKED,
            "timeline_approval_needs_manual_changes",
        ),
        (
            TIMELINE_APPROVAL_STATUS_BLOCKED,
            TIMELINE_APPROVAL_GATE_STATUS_BLOCKED,
            "timeline_approval_blocked",
        ),
    ]

    for approval_status, gate_status, expected_signal_type in statuses:
        result = adapt_timeline_approval_gate_report_to_signals(
            {
                "timeline_approval_gate": _gate(approval_status, gate_status),
            }
        )

        assert result.signal_count == 1
        assert result.signals[0]["signal_type"] == expected_signal_type
        assert result.signals[0]["metadata"]["can_render"] is False
        assert result.signals[0]["metadata"]["approval_gate_only"] is True


def test_registry_imports_and_processes_timeline_approval_gate():
    text = _text(ROOT / "core" / "unified_edit_signal_registry.py")

    assert "from core.timeline_approval_gate_signal_adapter import" in text
    assert "adapt_timeline_approval_gate_report_to_signals" in text
    assert 'SOURCE_TIMELINE_APPROVAL_GATE = "timeline_approval_gate"' in text
    assert "timeline_approval_gate_report" in text
    assert "timeline_approval_gate" in text
    assert "source_counts[SOURCE_TIMELINE_APPROVAL_GATE]" in text


def test_registry_runtime_counts_timeline_approval_gate_signal():
    job = _make_job(
        {
            "timeline_approval_gate_report": {
                "status": TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
                "timeline_approval_gate": _gate(
                    TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
                    TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
                ),
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["timeline_approval_gate"] == 1
    assert result.type_counts["timeline_approval_pending_review"] == 1


def test_approved_signal_is_future_only_and_no_render_now():
    result = adapt_timeline_approval_gate_report_to_signals(
        {
            "timeline_approval_gate": _gate(
                TIMELINE_APPROVAL_STATUS_APPROVED,
                TIMELINE_APPROVAL_GATE_STATUS_APPROVED,
            ),
        }
    )

    signal = result.signals[0]

    assert signal["signal_type"] == "timeline_approval_approved"
    assert signal["action_hint"] == "future_execution_allowed_after_approval"
    assert signal["metadata"]["can_proceed_to_execution"] is True
    assert signal["metadata"]["can_render"] is False
    assert signal["metadata"]["no_execution_in_2b_33"] is True
