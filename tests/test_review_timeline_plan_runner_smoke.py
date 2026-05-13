from core.review_timeline_plan_runner import (
    apply_review_timeline_plan_run_report_to_job,
    run_review_timeline_plan_for_job,
)
from models.final_cut_list import (
    FINAL_ACTION_CENSOR_KEEP,
    FINAL_ACTION_KEEP_HIGH_VALUE,
    FINAL_ACTION_REMOVE_REVIEW,
)
from models.job import Job
from models.review_timeline_plan import (
    REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW,
    REVIEW_TIMELINE_PLAN_STATUS_SKIPPED_NO_FINAL_ITEMS,
)


def _make_job(extra=None):
    data = {
        "job_id": "job_review_timeline_runner",
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


def _final_item(action: str, index: int):
    return {
        "final_item_id": f"final_{index}",
        "source_item_id": f"cut_{index}",
        "segment_id": f"seg_{index}",
        "start_seconds": float(index * 10),
        "end_seconds": float(index * 10 + 4),
        "duration_seconds": 4.0,
        "final_action": action,
        "final_confidence": 0.8,
        "priority": "medium",
        "reason": f"reason {action}",
        "decision_basis": {"test": True},
        "source_signal_ids": [],
    }


def test_run_review_timeline_plan_for_job_reads_final_cut_list_items():
    job = _make_job(
        {
            "final_cut_list_items": [
                _final_item(FINAL_ACTION_KEEP_HIGH_VALUE, 1),
                _final_item(FINAL_ACTION_REMOVE_REVIEW, 2),
                _final_item(FINAL_ACTION_CENSOR_KEEP, 3),
            ]
        }
    )

    report = run_review_timeline_plan_for_job(job)

    assert report.status == REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW
    assert report.total_items == 3
    assert report.total_duration_seconds == 12.0
    assert report.review_required_count >= 2
    assert report.censor_required_count == 1


def test_apply_review_timeline_plan_report_to_job_sets_job_fields():
    job = _make_job(
        {
            "final_cut_list_items": [
                _final_item(FINAL_ACTION_KEEP_HIGH_VALUE, 1),
                _final_item(FINAL_ACTION_REMOVE_REVIEW, 2),
            ]
        }
    )

    report = run_review_timeline_plan_for_job(job)
    apply_review_timeline_plan_run_report_to_job(job, report)

    assert job.review_timeline_plan_status == REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW
    assert job.review_timeline_plan_item_count == 2
    assert len(job.review_timeline_plan_items) == 2
    assert job.review_timeline_plan_review_required_count >= 1
    assert job.review_timeline_plan_id.startswith("review_timeline_plan_")
    assert job.review_timeline_plan_report["source"] == "review_timeline_plan_builder"


def test_runner_skips_safely_when_no_final_items_exist():
    job = _make_job()

    report = run_review_timeline_plan_for_job(job)

    assert report.status == REVIEW_TIMELINE_PLAN_STATUS_SKIPPED_NO_FINAL_ITEMS
    assert report.total_items == 0
    assert report.items == []
    assert "no_final_cut_list_items_available" in report.warnings
