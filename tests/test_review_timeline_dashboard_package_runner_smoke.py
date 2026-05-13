from core.review_timeline_dashboard_package_runner import (
    apply_review_timeline_dashboard_package_run_report_to_job,
    run_review_timeline_dashboard_package_for_job,
)
from models.review_timeline_dashboard_package import (
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
)


def _item():
    return {
        "timeline_item_id": "review_timeline_item_runner_0",
        "source_segment_id": "segment_runner_0",
        "start_seconds": 0.0,
        "end_seconds": 5.0,
        "source_start_seconds": 0.0,
        "source_end_seconds": 5.0,
        "duration_seconds": 5.0,
        "action": "keep_review",
        "final_decision": "keep",
        "protection_status": "normal",
        "censor_sfx_required": False,
        "continuity_blocked": False,
        "review_required": True,
        "review_reason": "needs_human_review",
        "safety_flags": ["review_only", "human_review"],
        "notes": [],
        "metadata": {},
    }


def _job():
    item = _item()

    plan = {
        "plan_id": "review_timeline_plan_runner_test",
        "job_id": "job_dashboard_runner_test",
        "status": "pending_review",
        "items": [item],
        "total_items": 1,
        "total_duration_seconds": 5.0,
        "review_required_count": 1,
        "protected_count": 0,
        "censor_required_count": 0,
        "continuity_blocked_count": 0,
        "warnings": [],
        "errors": [],
        "metadata": {"review_only": True},
    }

    return {
        "job_id": "job_dashboard_runner_test",
        "review_timeline_plan": plan,
        "review_timeline_plan_report": {
            "status": "pending_review",
            "review_timeline_plan": plan,
            "items": [item],
        },
        "review_timeline_plan_items": [item],
        "review_timeline_plan_status": "pending_review",
        "review_timeline_plan_id": "review_timeline_plan_runner_test",
        "timeline_approval_gate": {
            "approval_gate_id": "timeline_approval_gate_runner_test",
            "job_id": "job_dashboard_runner_test",
            "approval_status": "pending_review",
            "gate_status": "pending_review",
            "can_proceed_to_execution": False,
            "can_render": False,
            "requires_human_approval": True,
            "blocking_reasons": [],
            "warnings": [],
        },
        "timeline_approval_gate_id": "timeline_approval_gate_runner_test",
        "timeline_approval_status": "pending_review",
        "timeline_can_proceed_to_execution": False,
        "timeline_can_render": False,
        "timeline_approval_blocking_reasons": [],
        "timeline_approval_warnings": [],
        "timeline_safety_validator": {
            "safety_validation_id": "timeline_safety_validation_runner_test",
            "job_id": "job_dashboard_runner_test",
            "source_review_timeline_plan_id": "review_timeline_plan_runner_test",
            "source_timeline_approval_gate_id": "timeline_approval_gate_runner_test",
            "validation_status": "passed",
            "is_safe_for_future_execution": False,
            "is_safe_for_render": False,
            "requires_manual_review": True,
            "blocking_errors": [],
            "warnings": [],
            "item_results": [
                {
                    "item_index": 0,
                    "item_id": "review_timeline_item_runner_0",
                    "action": "keep_review",
                    "protection_status": "normal",
                    "start_seconds": 0.0,
                    "end_seconds": 5.0,
                    "duration_seconds": 5.0,
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
        },
        "timeline_safety_validation_id": "timeline_safety_validation_runner_test",
        "timeline_safety_validation_status": "passed",
        "timeline_is_safe_for_future_execution": False,
        "timeline_is_safe_for_render": False,
        "timeline_safety_requires_manual_review": True,
        "timeline_safety_blocking_errors": [],
        "timeline_safety_warnings": [],
    }


def test_runner_builds_dashboard_package_report():
    job = _job()

    report = run_review_timeline_dashboard_package_for_job(
        job,
        metadata={"test_marker": "runner_smoke"},
    )

    assert report.status == REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY
    assert report.dashboard_package is not None
    assert report.dashboard_package.job_id == "job_dashboard_runner_test"
    assert report.dashboard_package.can_render is False
    assert report.dashboard_package.is_safe_for_render is False
    assert report.metadata["test_marker"] == "runner_smoke"


def test_runner_applies_dashboard_package_to_job_dict():
    job = _job()
    report = run_review_timeline_dashboard_package_for_job(job)

    updated_job = apply_review_timeline_dashboard_package_run_report_to_job(
        job,
        report,
    )

    assert updated_job["review_timeline_dashboard_package_status"] == (
        REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY
    )
    assert updated_job["review_timeline_dashboard_package_id"]
    assert updated_job["review_timeline_dashboard_package"]
    assert updated_job["review_timeline_dashboard_package_report"]
    assert updated_job["review_timeline_dashboard_summary"]["total_items"] == 1
    assert len(updated_job["review_timeline_dashboard_item_cards"]) == 1
    assert updated_job["review_timeline_dashboard_can_render"] is False
    assert updated_job["review_timeline_dashboard_is_safe_for_render"] is False
    assert "review_timeline" in updated_job["review_timeline_dashboard_actions"]