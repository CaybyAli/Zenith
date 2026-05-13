from core.timeline_approval_gate_runner import (
    apply_timeline_approval_gate_run_report_to_job,
    run_timeline_approval_gate_for_job,
)
from models.job import Job
from models.timeline_approval_gate import (
    TIMELINE_APPROVAL_GATE_STATUS_APPROVED,
    TIMELINE_APPROVAL_GATE_STATUS_BLOCKED,
    TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
    TIMELINE_APPROVAL_REASON_MISSING_REVIEW_TIMELINE_PLAN,
    TIMELINE_APPROVAL_STATUS_APPROVED,
    TIMELINE_APPROVAL_STATUS_BLOCKED,
    TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
)


def _make_job(extra=None):
    data = {
        "job_id": "job_timeline_approval_runner",
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


def _review_timeline_plan(extra=None):
    data = {
        "plan_id": "review_timeline_plan_runner_test",
        "job_id": "job_timeline_approval_runner",
        "status": "pending_review",
        "items": [
            {
                "timeline_item_id": "item_1",
                "source_segment_id": "seg_1",
                "action": "keep_review",
                "protection_status": "normal",
                "review_required": True,
                "censor_sfx_required": False,
                "continuity_blocked": False,
            }
        ],
        "total_items": 1,
        "review_required_count": 1,
        "protected_count": 0,
        "censor_required_count": 0,
        "continuity_blocked_count": 0,
        "warnings": [],
        "metadata": {
            "review_only": True,
            "approval_required": True,
        },
    }
    if extra:
        data.update(extra)
    return data


def test_runner_blocks_when_review_timeline_plan_missing():
    job = _make_job()

    report = run_timeline_approval_gate_for_job(job)

    assert report.gate_status == TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
    assert report.approval_status == TIMELINE_APPROVAL_STATUS_BLOCKED
    assert report.can_proceed_to_execution is False
    assert report.can_render is False
    assert TIMELINE_APPROVAL_REASON_MISSING_REVIEW_TIMELINE_PLAN in report.blocking_reasons


def test_runner_keeps_pending_review_safe_by_default():
    job = _make_job(
        {
            "review_timeline_plan": _review_timeline_plan(),
        }
    )

    report = run_timeline_approval_gate_for_job(job)

    assert report.gate_status == TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW
    assert report.approval_status == TIMELINE_APPROVAL_STATUS_PENDING_REVIEW
    assert report.can_proceed_to_execution is False
    assert report.can_render is False
    assert report.requires_human_approval is True


def test_runner_approved_sets_safe_gate_but_no_render():
    job = _make_job(
        {
            "review_timeline_plan": _review_timeline_plan(),
            "timeline_approval_requested_status": TIMELINE_APPROVAL_STATUS_APPROVED,
            "timeline_approved_by": "reviewer",
        }
    )

    report = run_timeline_approval_gate_for_job(job)

    assert report.gate_status == TIMELINE_APPROVAL_GATE_STATUS_APPROVED
    assert report.approval_status == TIMELINE_APPROVAL_STATUS_APPROVED
    assert report.can_proceed_to_execution is True
    assert report.can_render is False
    assert report.requires_human_approval is False


def test_apply_timeline_approval_gate_report_to_job_sets_job_fields():
    job = _make_job(
        {
            "review_timeline_plan": _review_timeline_plan(),
            "timeline_approval_requested_status": TIMELINE_APPROVAL_STATUS_APPROVED,
            "timeline_approved_by": "reviewer",
        }
    )

    report = run_timeline_approval_gate_for_job(job)
    apply_timeline_approval_gate_run_report_to_job(job, report)

    assert job.timeline_approval_gate_status == TIMELINE_APPROVAL_GATE_STATUS_APPROVED
    assert job.timeline_approval_status == TIMELINE_APPROVAL_STATUS_APPROVED
    assert job.timeline_can_proceed_to_execution is True
    assert job.timeline_can_render is False
    assert job.timeline_requires_human_approval is False
    assert job.timeline_approval_gate_id.startswith("timeline_approval_gate_")
    assert job.timeline_approval_gate_report["source"] == "timeline_approval_gate"
    assert job.timeline_approval_gate["approval_status"] == TIMELINE_APPROVAL_STATUS_APPROVED
