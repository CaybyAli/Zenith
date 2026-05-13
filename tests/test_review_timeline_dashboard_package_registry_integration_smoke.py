from pathlib import Path

from core.review_timeline_dashboard_package_signal_adapter import (
    adapt_review_timeline_dashboard_package_report_to_signals,
)
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job
from models.review_timeline_dashboard_package import (
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY_WITH_WARNINGS,
)


ROOT = Path(__file__).resolve().parents[1]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _make_job(extra=None):
    data = {
        "job_id": "job_dashboard_registry",
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


def _package(status: str, extra=None):
    data = {
        "dashboard_package_id": f"review_timeline_dashboard_package_{status}",
        "job_id": "job_dashboard_registry",
        "package_status": status,
        "source_review_timeline_plan_id": "review_timeline_plan_registry",
        "source_timeline_approval_gate_id": "timeline_approval_gate_registry",
        "source_timeline_safety_validation_id": "timeline_safety_validation_registry",
        "review_status": "pending_review",
        "approval_status": "pending_review",
        "safety_status": "passed",
        "can_proceed_to_execution": False,
        "can_render": False,
        "is_safe_for_future_execution": False,
        "is_safe_for_render": False,
        "requires_manual_review": True,
        "summary": {
            "total_items": 1,
            "total_duration_seconds": 5.0,
            "review_required_count": 1,
            "blocking_error_count": 0,
            "warning_count": 0,
        },
        "counters": {
            "total_items": 1,
            "warning_count": 0,
            "blocking_error_count": 0,
        },
        "timeline_items": [],
        "item_cards": [
            {
                "item_id": "review_timeline_item_registry_0",
                "source_segment_id": "segment_registry_0",
                "start_seconds": 0.0,
                "end_seconds": 5.0,
                "duration_seconds": 5.0,
                "action": "keep_review",
                "label": "Keep Review",
                "badge": "Review Required",
                "severity": "medium",
                "review_required": True,
                "protected": False,
                "censor_sfx_required": False,
                "continuity_blocked": False,
                "safety_status": "ok",
                "warnings": [],
                "blocking_errors": [],
            }
        ],
        "approval_panel": {
            "approval_status": "pending_review",
            "gate_status": "pending_review",
            "can_proceed_to_execution": False,
            "can_render": False,
            "blocking_reasons": [],
        },
        "safety_panel": {
            "validation_status": "passed",
            "is_safe_for_future_execution": False,
            "is_safe_for_render": False,
            "blocking_errors": [],
            "warnings": [],
        },
        "warnings": [],
        "blocking_errors": [],
        "dashboard_actions": [
            "review_timeline",
            "approve_timeline",
            "request_changes",
            "reject_timeline",
        ],
        "metadata": {
            "dashboard_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_35": True,
            "no_render_in_2b_35": True,
        },
    }
    if extra:
        data.update(extra)
    return data


def test_signal_adapter_emits_dashboard_package_status_signal_types():
    statuses = [
        (
            REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
            "review_timeline_dashboard_package_ready",
        ),
        (
            REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY_WITH_WARNINGS,
            "review_timeline_dashboard_package_ready_with_warnings",
        ),
        (
            REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED,
            "review_timeline_dashboard_package_blocked",
        ),
        (
            REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED,
            "review_timeline_dashboard_package_failed",
        ),
    ]

    for package_status, expected_signal_type in statuses:
        result = adapt_review_timeline_dashboard_package_report_to_signals(
            {
                "dashboard_package": _package(package_status),
            }
        )

        signal_types = {signal["signal_type"] for signal in result.signals}

        assert expected_signal_type in signal_types
        assert result.signals[0]["metadata"]["can_render"] is False
        assert result.signals[0]["metadata"]["is_safe_for_render"] is False
        assert result.signals[0]["metadata"]["dashboard_only"] is True
        assert result.signals[0]["metadata"]["media_unchanged"] is True
        assert result.signals[0]["metadata"]["no_execution_in_2b_35"] is True
        assert result.signals[0]["metadata"]["no_render_in_2b_35"] is True


def test_signal_adapter_emits_item_warning_and_blocking_error_signals():
    package = _package(
        REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED,
        {
            "warnings": ["timeline_gap"],
            "blocking_errors": ["timeline_overlap"],
            "item_cards": [
                {
                    "item_id": "review_timeline_item_registry_0",
                    "start_seconds": 1.0,
                    "end_seconds": 4.0,
                    "duration_seconds": 3.0,
                    "action": "keep_review",
                    "label": "Keep Review",
                    "badge": "Blocked",
                    "severity": "blocking",
                    "review_required": True,
                    "protected": False,
                    "censor_sfx_required": False,
                    "continuity_blocked": False,
                    "safety_status": "blocked",
                    "warnings": ["timeline_gap"],
                    "blocking_errors": ["timeline_overlap"],
                }
            ],
        },
    )

    result = adapt_review_timeline_dashboard_package_report_to_signals(
        {"dashboard_package": package}
    )

    signal_types = {signal["signal_type"] for signal in result.signals}

    assert "review_timeline_dashboard_package_blocked" in signal_types
    assert "review_timeline_dashboard_item_card" in signal_types
    assert "review_timeline_dashboard_warning" in signal_types
    assert "review_timeline_dashboard_blocking_error" in signal_types
    assert result.item_card_signal_count == 1
    assert result.warning_signal_count == 1
    assert result.blocking_error_signal_count == 1


def test_registry_imports_and_processes_dashboard_package():
    text = _text(ROOT / "core" / "unified_edit_signal_registry.py")

    assert "from core.review_timeline_dashboard_package_signal_adapter import" in text
    assert "adapt_review_timeline_dashboard_package_report_to_signals" in text
    assert (
        'SOURCE_REVIEW_TIMELINE_DASHBOARD_PACKAGE = '
        '"review_timeline_dashboard_package"'
    ) in text
    assert "review_timeline_dashboard_package_report" in text
    assert "source_counts[SOURCE_REVIEW_TIMELINE_DASHBOARD_PACKAGE]" in text


def test_registry_runtime_counts_dashboard_package_signal():
    package = _package(
        REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED,
        {
            "blocking_errors": ["timeline_overlap"],
        },
    )

    job = _make_job(
        {
            "review_timeline_dashboard_package_report": {
                "status": REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED,
                "dashboard_package": package,
            },
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["review_timeline_dashboard_package"] >= 1
    assert result.type_counts["review_timeline_dashboard_package_blocked"] == 1
    assert result.type_counts["review_timeline_dashboard_item_card"] == 1
    assert result.type_counts["review_timeline_dashboard_blocking_error"] == 1


def test_dashboard_package_signals_are_dashboard_only_and_no_render():
    result = adapt_review_timeline_dashboard_package_report_to_signals(
        {
            "dashboard_package": _package(
                REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
            ),
        }
    )

    signal = result.signals[0]

    assert signal["signal_type"] == "review_timeline_dashboard_package_ready"
    assert signal["action_hint"] == "show_review_timeline_dashboard_package"
    assert signal["metadata"]["dashboard_only"] is True
    assert signal["metadata"]["media_unchanged"] is True
    assert signal["metadata"]["can_render"] is False
    assert signal["metadata"]["is_safe_for_render"] is False
    assert signal["metadata"]["no_execution_in_2b_35"] is True
    assert signal["metadata"]["no_render_in_2b_35"] is True