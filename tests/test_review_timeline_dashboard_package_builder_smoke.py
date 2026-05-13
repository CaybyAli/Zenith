from core.review_timeline_dashboard_package_builder import (
    ReviewTimelineDashboardPackageBuilder,
)
from models.review_timeline_dashboard_package import (
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY_WITH_WARNINGS,
)


def _item(extra=None):
    data = {
        "timeline_item_id": "review_timeline_item_0",
        "source_segment_id": "segment_0",
        "start_seconds": 0.0,
        "end_seconds": 7.2,
        "source_start_seconds": 0.0,
        "source_end_seconds": 7.2,
        "duration_seconds": 7.2,
        "action": "keep_review",
        "final_decision": "keep",
        "protection_status": "normal",
        "censor_sfx_required": False,
        "continuity_blocked": False,
        "review_required": True,
        "review_reason": "needs_human_review",
        "safety_flags": ["review_only", "human_review"],
        "notes": ["check pacing"],
        "metadata": {},
    }
    if extra:
        data.update(extra)
    return data


def _plan(items=None, warnings=None):
    if items is None:
        items = [_item()]

    return {
        "plan_id": "review_timeline_plan_dashboard_test",
        "job_id": "job_dashboard_test",
        "status": "pending_review",
        "items": items,
        "total_items": len(items),
        "total_duration_seconds": sum(
            float(item.get("duration_seconds", 0.0) or 0.0)
            for item in items
        ),
        "review_required_count": sum(
            1 for item in items if item.get("review_required")
        ),
        "protected_count": sum(
            1
            for item in items
            if item.get("protection_status") in {"protected", "censor_protected"}
        ),
        "censor_required_count": sum(
            1 for item in items if item.get("censor_sfx_required")
        ),
        "continuity_blocked_count": sum(
            1 for item in items if item.get("continuity_blocked")
        ),
        "warnings": list(warnings or []),
        "errors": [],
        "metadata": {"review_only": True},
    }


def _approval_gate(**extra):
    data = {
        "approval_gate_id": "timeline_approval_gate_dashboard_test",
        "job_id": "job_dashboard_test",
        "source_review_timeline_plan_id": "review_timeline_plan_dashboard_test",
        "approval_status": "pending_review",
        "gate_status": "pending_review",
        "can_proceed_to_execution": False,
        "can_render": False,
        "requires_human_approval": True,
        "blocking_reasons": [],
        "warnings": [],
    }
    data.update(extra)
    return data


def _safety_validation(**extra):
    data = {
        "safety_validation_id": "timeline_safety_validation_dashboard_test",
        "job_id": "job_dashboard_test",
        "source_review_timeline_plan_id": "review_timeline_plan_dashboard_test",
        "source_timeline_approval_gate_id": "timeline_approval_gate_dashboard_test",
        "validation_status": "passed",
        "is_safe_for_future_execution": False,
        "is_safe_for_render": False,
        "requires_manual_review": True,
        "blocking_errors": [],
        "warnings": [],
        "item_results": [
            {
                "item_index": 0,
                "item_id": "review_timeline_item_0",
                "action": "keep_review",
                "protection_status": "normal",
                "start_seconds": 0.0,
                "end_seconds": 7.2,
                "duration_seconds": 7.2,
                "is_valid": True,
                "blocking_errors": [],
                "warnings": [],
                "metadata": {},
            }
        ],
        "total_items_checked": 1,
        "invalid_timing_count": 0,
        "overlap_count": 0,
        "gap_count": 0,
        "protected_violation_count": 0,
        "censor_violation_count": 0,
        "continuity_violation_count": 0,
        "approval_violation_count": 0,
        "future_execution_safety_status": "requires_approval_or_review",
        "metadata": {"safety_validator_only": True},
    }
    data.update(extra)
    return data


def _job(**extra):
    plan = extra.pop("review_timeline_plan", _plan())

    data = {
        "job_id": "job_dashboard_test",
        "review_timeline_plan": plan,
        "review_timeline_plan_report": {
            "status": plan.get("status"),
            "review_timeline_plan": plan,
            "items": plan.get("items", []),
        },
        "review_timeline_plan_items": plan.get("items", []),
        "review_timeline_plan_status": plan.get("status"),
        "review_timeline_plan_id": plan.get("plan_id"),
        "timeline_approval_gate": _approval_gate(),
        "timeline_approval_status": "pending_review",
        "timeline_can_proceed_to_execution": False,
        "timeline_can_render": False,
        "timeline_approval_blocking_reasons": [],
        "timeline_approval_warnings": [],
        "timeline_safety_validator": _safety_validation(),
        "timeline_safety_validation_status": "passed",
        "timeline_is_safe_for_future_execution": False,
        "timeline_is_safe_for_render": False,
        "timeline_safety_requires_manual_review": True,
        "timeline_safety_blocking_errors": [],
        "timeline_safety_warnings": [],
    }
    data.update(extra)
    return data


def _build(job):
    return ReviewTimelineDashboardPackageBuilder().build(job).dashboard_package


def test_builder_creates_ready_dashboard_package():
    package = _build(_job())

    assert package.package_status == REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY
    assert package.job_id == "job_dashboard_test"
    assert package.source_review_timeline_plan_id == "review_timeline_plan_dashboard_test"
    assert package.source_timeline_approval_gate_id == "timeline_approval_gate_dashboard_test"
    assert package.source_timeline_safety_validation_id == "timeline_safety_validation_dashboard_test"
    assert package.review_status == "pending_review"
    assert package.approval_status == "pending_review"
    assert package.safety_status == "passed"
    assert package.can_render is False
    assert package.is_safe_for_render is False
    assert package.requires_manual_review is True
    assert package.summary["total_items"] == 1
    assert package.summary["review_required_count"] == 1
    assert len(package.item_cards) == 1
    assert package.item_cards[0].label == "Keep Review"
    assert package.item_cards[0].badge == "Review Required"
    assert package.metadata["dashboard_only"] is True
    assert package.metadata["media_unchanged"] is True
    assert package.metadata["no_execution_in_2b_35"] is True


def test_builder_creates_ready_with_warnings_package():
    package = _build(
        _job(
            timeline_safety_validator=_safety_validation(
                validation_status="passed_with_warnings",
                warnings=["timeline_gap"],
            ),
            timeline_safety_validation_status="passed_with_warnings",
            timeline_safety_warnings=["timeline_gap"],
        )
    )

    assert package.package_status == (
        REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY_WITH_WARNINGS
    )
    assert package.safety_status == "passed_with_warnings"
    assert "timeline_gap" in package.warnings
    assert package.summary["warning_count"] == 1
    assert package.can_render is False


def test_builder_creates_blocked_package_when_safety_blocks():
    package = _build(
        _job(
            timeline_safety_validator=_safety_validation(
                validation_status="blocked",
                blocking_errors=["timeline_overlap"],
            ),
            timeline_safety_validation_status="blocked",
            timeline_safety_blocking_errors=["timeline_overlap"],
        )
    )

    assert package.package_status == REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED
    assert "timeline_overlap" in package.blocking_errors
    assert package.summary["blocking_error_count"] == 1
    assert package.can_proceed_to_execution is False
    assert package.can_render is False
    assert package.is_safe_for_future_execution is False
    assert package.is_safe_for_render is False


def test_builder_forces_render_false_even_when_sources_claim_render_true():
    package = _build(
        _job(
            timeline_approval_gate=_approval_gate(
                approval_status="approved",
                gate_status="approved",
                can_proceed_to_execution=True,
                can_render=True,
                requires_human_approval=False,
            ),
            timeline_approval_status="approved",
            timeline_can_proceed_to_execution=True,
            timeline_can_render=True,
            timeline_safety_validator=_safety_validation(
                validation_status="passed",
                is_safe_for_future_execution=True,
                is_safe_for_render=True,
                requires_manual_review=False,
            ),
            timeline_is_safe_for_future_execution=True,
            timeline_is_safe_for_render=True,
            timeline_safety_requires_manual_review=False,
        )
    )

    assert package.approval_status == "approved"
    assert package.can_proceed_to_execution is True
    assert package.is_safe_for_future_execution is True
    assert package.can_render is False
    assert package.is_safe_for_render is False
    assert package.metadata["can_render_forced_false_by_2b_35"] is True