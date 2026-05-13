from __future__ import annotations

from pathlib import Path

from core.review_timeline_dashboard_package_signal_adapter import (
    adapt_review_timeline_dashboard_package_report_to_signals,
)
from core.review_timeline_plan_signal_adapter import (
    adapt_review_timeline_plan_report_to_signals,
)
from core.timeline_approval_gate_signal_adapter import (
    adapt_timeline_approval_gate_report_to_signals,
)
from core.timeline_safety_validator_signal_adapter import (
    adapt_timeline_safety_validator_report_to_signals,
)
from core.unified_edit_signal_registry import build_unified_edit_signal_result
from models.review_timeline_dashboard_package import (
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY_WITH_WARNINGS,
)
from models.review_timeline_plan import (
    REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY,
    REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
    REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
    REVIEW_TIMELINE_ACTION_REMOVE_REVIEW,
    REVIEW_TIMELINE_ACTION_TRIM_REVIEW,
)
from models.timeline_approval_gate import (
    TIMELINE_APPROVAL_STATUS_APPROVED,
    TIMELINE_APPROVAL_STATUS_BLOCKED,
    TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES,
    TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
    TIMELINE_APPROVAL_STATUS_REJECTED,
)
from models.timeline_safety_validator import (
    TIMELINE_SAFETY_STATUS_BLOCKED,
    TIMELINE_SAFETY_STATUS_FAILED,
    TIMELINE_SAFETY_STATUS_PASSED,
    TIMELINE_SAFETY_STATUS_PASSED_WITH_WARNINGS,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "core" / "unified_edit_signal_registry.py"


EXPECTED_BLOCK6_SOURCES = {
    "review_timeline_plan",
    "timeline_approval_gate",
    "timeline_safety_validator",
    "review_timeline_dashboard_package",
}


EXPECTED_REVIEW_TIMELINE_SIGNAL_TYPES = {
    "review_timeline_keep_review",
    "review_timeline_trim_review",
    "review_timeline_remove_review",
    "review_timeline_censor_keep",
    "review_timeline_blocked_by_continuity",
}


EXPECTED_APPROVAL_SIGNAL_TYPES = {
    "timeline_approval_pending_review",
    "timeline_approval_approved",
    "timeline_approval_rejected",
    "timeline_approval_needs_manual_changes",
    "timeline_approval_blocked",
}


EXPECTED_SAFETY_SIGNAL_TYPES = {
    "timeline_safety_passed",
    "timeline_safety_passed_with_warnings",
    "timeline_safety_blocked",
    "timeline_safety_failed",
}


EXPECTED_DASHBOARD_SIGNAL_TYPES = {
    "review_timeline_dashboard_package_ready",
    "review_timeline_dashboard_package_ready_with_warnings",
    "review_timeline_dashboard_package_blocked",
    "review_timeline_dashboard_package_failed",
    "review_timeline_dashboard_item_card",
}


def _signal_types(result) -> set[str]:
    return {
        str(signal.get("signal_type"))
        for signal in list(result.signals or [])
    }


def _sources(result) -> set[str]:
    return {
        str(signal.get("source"))
        for signal in list(result.signals or [])
    }


def test_block6_registry_contains_all_block6_sources() -> None:
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    missing_sources = [
        source
        for source in sorted(EXPECTED_BLOCK6_SOURCES)
        if source not in text
    ]

    assert missing_sources == []


def test_block6_registry_imports_all_block6_signal_adapters() -> None:
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    expected_adapter_names = [
        "adapt_review_timeline_plan_report_to_signals",
        "adapt_timeline_approval_gate_report_to_signals",
        "adapt_timeline_safety_validator_report_to_signals",
        "adapt_review_timeline_dashboard_package_report_to_signals",
    ]

    missing_adapters = [
        adapter_name
        for adapter_name in expected_adapter_names
        if adapter_name not in text
    ]

    assert missing_adapters == []


def test_block6_review_timeline_plan_adapter_emits_required_signal_types() -> None:
    report = {
        "items": [
            {
                "timeline_item_id": "keep_1",
                "source_segment_id": "seg_keep_1",
                "source_start_seconds": 1.0,
                "source_end_seconds": 3.0,
                "duration_seconds": 2.0,
                "action": REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
                "final_decision": REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
                "review_required": True,
                "review_reason": "audit_keep_review",
            },
            {
                "timeline_item_id": "trim_1",
                "source_segment_id": "seg_trim_1",
                "source_start_seconds": 4.0,
                "source_end_seconds": 7.0,
                "duration_seconds": 3.0,
                "action": REVIEW_TIMELINE_ACTION_TRIM_REVIEW,
                "final_decision": REVIEW_TIMELINE_ACTION_TRIM_REVIEW,
                "review_required": True,
                "review_reason": "audit_trim_review",
            },
            {
                "timeline_item_id": "remove_1",
                "source_segment_id": "seg_remove_1",
                "source_start_seconds": 8.0,
                "source_end_seconds": 9.0,
                "duration_seconds": 1.0,
                "action": REVIEW_TIMELINE_ACTION_REMOVE_REVIEW,
                "final_decision": REVIEW_TIMELINE_ACTION_REMOVE_REVIEW,
                "review_required": True,
                "review_reason": "audit_remove_review",
            },
            {
                "timeline_item_id": "censor_1",
                "source_segment_id": "seg_censor_1",
                "source_start_seconds": 10.0,
                "source_end_seconds": 12.0,
                "duration_seconds": 2.0,
                "action": REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
                "final_decision": REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
                "protection_status": "censor_protected",
                "censor_sfx_required": True,
                "review_required": True,
                "review_reason": "audit_censor_keep",
            },
            {
                "timeline_item_id": "continuity_1",
                "source_segment_id": "seg_continuity_1",
                "source_start_seconds": 13.0,
                "source_end_seconds": 14.0,
                "duration_seconds": 1.0,
                "action": REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY,
                "final_decision": REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY,
                "protection_status": "continuity_blocked",
                "continuity_blocked": True,
                "review_required": True,
                "review_reason": "audit_continuity_blocked",
            },
        ]
    }

    result = adapt_review_timeline_plan_report_to_signals(report)

    assert result.status == "ok"
    assert EXPECTED_REVIEW_TIMELINE_SIGNAL_TYPES.issubset(_signal_types(result))
    assert _sources(result) == {"review_timeline_plan"}


def test_block6_timeline_approval_adapter_emits_required_signal_types() -> None:
    approval_statuses = [
        TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
        TIMELINE_APPROVAL_STATUS_APPROVED,
        TIMELINE_APPROVAL_STATUS_REJECTED,
        TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES,
        TIMELINE_APPROVAL_STATUS_BLOCKED,
    ]

    found_signal_types: set[str] = set()

    for approval_status in approval_statuses:
        result = adapt_timeline_approval_gate_report_to_signals(
            {
                "timeline_approval_gate": {
                    "approval_gate_id": f"approval_{approval_status}",
                    "approval_status": approval_status,
                    "gate_status": approval_status,
                    "can_proceed_to_execution": (
                        approval_status == TIMELINE_APPROVAL_STATUS_APPROVED
                    ),
                    "can_render": False,
                    "requires_human_approval": (
                        approval_status != TIMELINE_APPROVAL_STATUS_APPROVED
                    ),
                    "metadata": {
                        "approval_gate_only": True,
                        "media_unchanged": True,
                    },
                }
            }
        )
        assert result.status == "ok"
        assert _sources(result) == {"timeline_approval_gate"}
        found_signal_types.update(_signal_types(result))

    assert EXPECTED_APPROVAL_SIGNAL_TYPES.issubset(found_signal_types)


def test_block6_timeline_safety_adapter_emits_required_signal_types() -> None:
    safety_statuses = [
        TIMELINE_SAFETY_STATUS_PASSED,
        TIMELINE_SAFETY_STATUS_PASSED_WITH_WARNINGS,
        TIMELINE_SAFETY_STATUS_BLOCKED,
        TIMELINE_SAFETY_STATUS_FAILED,
    ]

    found_signal_types: set[str] = set()

    for safety_status in safety_statuses:
        result = adapt_timeline_safety_validator_report_to_signals(
            {
                "timeline_safety_validation": {
                    "safety_validation_id": f"safety_{safety_status}",
                    "validation_status": safety_status,
                    "is_safe_for_future_execution": (
                        safety_status == TIMELINE_SAFETY_STATUS_PASSED
                    ),
                    "is_safe_for_render": False,
                    "requires_manual_review": True,
                    "blocking_errors": (
                        ["blocked_by_audit"]
                        if safety_status
                        in {
                            TIMELINE_SAFETY_STATUS_BLOCKED,
                            TIMELINE_SAFETY_STATUS_FAILED,
                        }
                        else []
                    ),
                    "warnings": (
                        ["warning_by_audit"]
                        if safety_status == TIMELINE_SAFETY_STATUS_PASSED_WITH_WARNINGS
                        else []
                    ),
                    "metadata": {
                        "safety_validator_only": True,
                        "media_unchanged": True,
                    },
                }
            }
        )
        assert result.status == "ok"
        assert _sources(result) == {"timeline_safety_validator"}
        found_signal_types.update(_signal_types(result))

    assert EXPECTED_SAFETY_SIGNAL_TYPES.issubset(found_signal_types)


def test_block6_dashboard_package_adapter_emits_required_signal_types() -> None:
    package_statuses = [
        REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
        REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY_WITH_WARNINGS,
        REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED,
        REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED,
    ]

    found_signal_types: set[str] = set()

    for package_status in package_statuses:
        result = adapt_review_timeline_dashboard_package_report_to_signals(
            {
                "dashboard_package": {
                    "dashboard_package_id": f"dashboard_{package_status}",
                    "package_status": package_status,
                    "review_status": "pending_review",
                    "approval_status": "pending_review",
                    "safety_status": "passed",
                    "can_proceed_to_execution": False,
                    "can_render": False,
                    "is_safe_for_future_execution": False,
                    "is_safe_for_render": False,
                    "requires_manual_review": True,
                    "item_cards": [
                        {
                            "item_id": "card_1",
                            "start_seconds": 1.0,
                            "end_seconds": 2.0,
                            "duration_seconds": 1.0,
                            "action": "keep_review",
                            "label": "Keep Review",
                            "badge": "Review Required",
                            "severity": "medium",
                            "review_required": True,
                            "protected": False,
                            "censor_sfx_required": False,
                            "continuity_blocked": False,
                            "safety_status": "ok",
                        }
                    ],
                    "warnings": (
                        ["dashboard_warning"]
                        if package_status
                        == REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY_WITH_WARNINGS
                        else []
                    ),
                    "blocking_errors": (
                        ["dashboard_blocked"]
                        if package_status
                        == REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED
                        else []
                    ),
                    "metadata": {
                        "dashboard_only": True,
                        "media_unchanged": True,
                    },
                }
            }
        )
        assert result.status == "ok"
        assert _sources(result) == {"review_timeline_dashboard_package"}
        found_signal_types.update(_signal_types(result))

    assert EXPECTED_DASHBOARD_SIGNAL_TYPES.issubset(found_signal_types)


def test_block6_unified_registry_collects_signals_from_all_block6_sources() -> None:
    class Job:
        review_timeline_plan_report = {
            "items": [
                {
                    "timeline_item_id": "keep_1",
                    "source_segment_id": "seg_keep_1",
                    "source_start_seconds": 1.0,
                    "source_end_seconds": 2.0,
                    "duration_seconds": 1.0,
                    "action": REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
                    "review_required": True,
                    "review_reason": "audit_keep_review",
                }
            ]
        }
        timeline_approval_gate_report = {
            "timeline_approval_gate": {
                "approval_gate_id": "approval_1",
                "approval_status": TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
                "gate_status": "pending_review",
                "can_proceed_to_execution": False,
                "can_render": False,
                "requires_human_approval": True,
            }
        }
        timeline_safety_validator_report = {
            "timeline_safety_validation": {
                "safety_validation_id": "safety_1",
                "validation_status": TIMELINE_SAFETY_STATUS_PASSED,
                "is_safe_for_future_execution": True,
                "is_safe_for_render": False,
                "requires_manual_review": True,
            }
        }
        review_timeline_dashboard_package_report = {
            "dashboard_package": {
                "dashboard_package_id": "dashboard_1",
                "package_status": REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
                "review_status": "pending_review",
                "approval_status": "pending_review",
                "safety_status": "passed",
                "can_proceed_to_execution": False,
                "can_render": False,
                "is_safe_for_future_execution": False,
                "is_safe_for_render": False,
                "requires_manual_review": True,
                "item_cards": [
                    {
                        "item_id": "card_1",
                        "start_seconds": 1.0,
                        "end_seconds": 2.0,
                        "duration_seconds": 1.0,
                        "action": "keep_review",
                        "label": "Keep Review",
                        "badge": "Review Required",
                        "severity": "medium",
                        "review_required": True,
                        "protected": False,
                        "censor_sfx_required": False,
                        "continuity_blocked": False,
                        "safety_status": "ok",
                    }
                ],
            }
        }

    result = build_unified_edit_signal_result(Job())

    found_sources = {
        str(signal.get("source"))
        for signal in list(result.signals or [])
    }
    found_signal_types = {
        str(signal.get("signal_type"))
        for signal in list(result.signals or [])
    }

    assert EXPECTED_BLOCK6_SOURCES.issubset(found_sources)
    assert "review_timeline_keep_review" in found_signal_types
    assert "timeline_approval_pending_review" in found_signal_types
    assert "timeline_safety_passed" in found_signal_types
    assert "review_timeline_dashboard_package_ready" in found_signal_types
    assert "review_timeline_dashboard_item_card" in found_signal_types