from core.timeline_safety_validator_runner import (
    apply_timeline_safety_validator_run_report_to_job,
    run_timeline_safety_validator_for_job,
)
from models.job import Job
from models.timeline_safety_validator import (
    TIMELINE_SAFETY_REASON_MISSING_REVIEW_TIMELINE_PLAN,
    TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34,
    TIMELINE_SAFETY_STATUS_BLOCKED,
    TIMELINE_SAFETY_STATUS_PASSED,
)


def _make_job(extra=None):
    data = {
        "job_id": "job_timeline_safety_runner",
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


def _review_timeline_plan():
    return {
        "plan_id": "review_timeline_plan_runner_test",
        "job_id": "job_timeline_safety_runner",
        "status": "pending_review",
        "items": [
            {
                "timeline_item_id": "item_1",
                "source_segment_id": "seg_1",
                "start_seconds": 0.0,
                "end_seconds": 5.0,
                "source_start_seconds": 0.0,
                "source_end_seconds": 5.0,
                "duration_seconds": 5.0,
                "action": "keep_review",
                "protection_status": "normal",
                "review_required": True,
                "censor_sfx_required": False,
                "continuity_blocked": False,
                "safety_flags": ["review_only", "human_review"],
                "metadata": {
                    "safety_flags": ["review_only", "human_review"],
                },
            }
        ],
        "total_items": 1,
        "warnings": [],
        "errors": [],
        "metadata": {
            "review_only": True,
            "approval_required": True,
        },
    }


def test_runner_blocks_when_review_timeline_plan_missing():
    job = _make_job()

    report = run_timeline_safety_validator_for_job(job)

    assert report.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert report.is_safe_for_future_execution is False
    assert report.is_safe_for_render is False
    assert report.requires_manual_review is True
    assert TIMELINE_SAFETY_REASON_MISSING_REVIEW_TIMELINE_PLAN in report.blocking_errors


def test_runner_passes_valid_approved_timeline_but_never_render():
    job = _make_job(
        {
            "review_timeline_plan": _review_timeline_plan(),
            "review_timeline_plan_items": _review_timeline_plan()["items"],
            "timeline_approval_status": "approved",
            "timeline_can_proceed_to_execution": True,
            "timeline_can_render": False,
        }
    )

    report = run_timeline_safety_validator_for_job(job)

    assert report.validation_status == TIMELINE_SAFETY_STATUS_PASSED
    assert report.is_safe_for_future_execution is True
    assert report.is_safe_for_render is False
    assert report.requires_manual_review is False


def test_runner_blocks_if_timeline_can_render_is_true():
    job = _make_job(
        {
            "review_timeline_plan": _review_timeline_plan(),
            "review_timeline_plan_items": _review_timeline_plan()["items"],
            "timeline_approval_status": "approved",
            "timeline_can_proceed_to_execution": True,
            "timeline_can_render": True,
        }
    )

    report = run_timeline_safety_validator_for_job(job)

    assert report.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert report.is_safe_for_render is False
    assert TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34 in report.blocking_errors


def test_apply_timeline_safety_validator_report_to_job_sets_job_fields():
    job = _make_job(
        {
            "review_timeline_plan": _review_timeline_plan(),
            "review_timeline_plan_items": _review_timeline_plan()["items"],
            "timeline_approval_status": "approved",
            "timeline_can_proceed_to_execution": True,
            "timeline_can_render": False,
        }
    )

    report = run_timeline_safety_validator_for_job(job)
    apply_timeline_safety_validator_run_report_to_job(job, report)

    assert job.timeline_safety_validation_status == TIMELINE_SAFETY_STATUS_PASSED
    assert job.timeline_is_safe_for_future_execution is True
    assert job.timeline_is_safe_for_render is False
    assert job.timeline_safety_requires_manual_review is False
    assert job.timeline_safety_validation_id.startswith(
        "timeline_safety_validation_"
    )
    assert job.timeline_safety_validator_report["source"] == (
        "timeline_safety_validator"
    )
    assert job.timeline_safety_validator["validation_status"] == (
        TIMELINE_SAFETY_STATUS_PASSED
    )
    assert isinstance(job.timeline_safety_item_results, list)
    assert job.timeline_safety_invalid_timing_count == 0
    assert job.timeline_safety_overlap_count == 0
    assert job.timeline_safety_gap_count == 0
