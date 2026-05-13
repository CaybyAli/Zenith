from core.timeline_approval_gate import build_timeline_approval_gate
from models.timeline_approval_gate import (
    TIMELINE_APPROVAL_GATE_STATUS_APPROVED,
    TIMELINE_APPROVAL_GATE_STATUS_BLOCKED,
    TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
    TIMELINE_APPROVAL_REASON_CENSOR_REQUIRED,
    TIMELINE_APPROVAL_REASON_CONTINUITY_BLOCKED,
    TIMELINE_APPROVAL_REASON_MISSING_REVIEW_TIMELINE_PLAN,
    TIMELINE_APPROVAL_REASON_NEEDS_MANUAL_CHANGES,
    TIMELINE_APPROVAL_REASON_PENDING_HUMAN_REVIEW,
    TIMELINE_APPROVAL_REASON_REJECTED_BY_REVIEW,
    TIMELINE_APPROVAL_STATUS_APPROVED,
    TIMELINE_APPROVAL_STATUS_BLOCKED,
    TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES,
    TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
    TIMELINE_APPROVAL_STATUS_REJECTED,
)


def _review_plan(extra=None):
    data = {
        "plan_id": "review_timeline_plan_test",
        "job_id": "job_timeline_approval_gate",
        "status": "pending_review",
        "items": [
            {
                "timeline_item_id": "item_1",
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


def test_missing_review_timeline_plan_blocks_gate():
    gate = build_timeline_approval_gate(
        review_timeline_plan=None,
        job_id="job_missing_plan",
    )

    assert gate.approval_status == TIMELINE_APPROVAL_STATUS_BLOCKED
    assert gate.gate_status == TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
    assert gate.can_proceed_to_execution is False
    assert gate.can_render is False
    assert gate.requires_human_approval is True
    assert TIMELINE_APPROVAL_REASON_MISSING_REVIEW_TIMELINE_PLAN in gate.blocking_reasons


def test_pending_review_blocks_execution_and_render():
    gate = build_timeline_approval_gate(
        review_timeline_plan=_review_plan(),
        job_id="job_pending_review",
    )

    assert gate.approval_status == TIMELINE_APPROVAL_STATUS_PENDING_REVIEW
    assert gate.gate_status == TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW
    assert gate.can_proceed_to_execution is False
    assert gate.can_render is False
    assert gate.requires_human_approval is True
    assert TIMELINE_APPROVAL_REASON_PENDING_HUMAN_REVIEW in gate.blocking_reasons


def test_rejected_blocks_execution_and_render():
    gate = build_timeline_approval_gate(
        review_timeline_plan=_review_plan(),
        job_id="job_rejected",
        approval_status=TIMELINE_APPROVAL_STATUS_REJECTED,
        rejected_by="reviewer",
    )

    assert gate.approval_status == TIMELINE_APPROVAL_STATUS_REJECTED
    assert gate.gate_status == TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
    assert gate.can_proceed_to_execution is False
    assert gate.can_render is False
    assert gate.rejected_by == "reviewer"
    assert gate.rejected_at is not None
    assert TIMELINE_APPROVAL_REASON_REJECTED_BY_REVIEW in gate.blocking_reasons


def test_needs_manual_changes_blocks_execution_and_render():
    gate = build_timeline_approval_gate(
        review_timeline_plan=_review_plan(),
        job_id="job_manual_changes",
        approval_status=TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES,
        manual_change_reason="needs tighter review",
    )

    assert gate.approval_status == TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES
    assert gate.gate_status == TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
    assert gate.can_proceed_to_execution is False
    assert gate.can_render is False
    assert gate.manual_change_reason == "needs tighter review"
    assert TIMELINE_APPROVAL_REASON_NEEDS_MANUAL_CHANGES in gate.blocking_reasons


def test_continuity_blocked_prevents_approval():
    gate = build_timeline_approval_gate(
        review_timeline_plan=_review_plan(
            {
                "continuity_blocked_count": 1,
            }
        ),
        job_id="job_continuity_blocked",
        approval_status=TIMELINE_APPROVAL_STATUS_APPROVED,
        approved_by="reviewer",
    )

    assert gate.approval_status == TIMELINE_APPROVAL_STATUS_BLOCKED
    assert gate.gate_status == TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
    assert gate.can_proceed_to_execution is False
    assert gate.can_render is False
    assert gate.approved_by is None
    assert TIMELINE_APPROVAL_REASON_CONTINUITY_BLOCKED in gate.blocking_reasons


def test_censor_required_forces_manual_review_not_delete():
    gate = build_timeline_approval_gate(
        review_timeline_plan=_review_plan(
            {
                "censor_required_count": 1,
                "protected_count": 1,
            }
        ),
        job_id="job_censor_required",
        approval_status=TIMELINE_APPROVAL_STATUS_APPROVED,
        approved_by="reviewer",
    )

    assert gate.approval_status == TIMELINE_APPROVAL_STATUS_NEEDS_MANUAL_CHANGES
    assert gate.gate_status == TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
    assert gate.can_proceed_to_execution is False
    assert gate.can_render is False
    assert TIMELINE_APPROVAL_REASON_CENSOR_REQUIRED in gate.blocking_reasons
    assert "censor_requires_later_human_approval" in gate.safety_flags
    assert "protected_items_must_stay_preserved" in gate.safety_flags


def test_approved_allows_only_future_execution_not_render_now():
    gate = build_timeline_approval_gate(
        review_timeline_plan=_review_plan(),
        job_id="job_approved",
        approval_status=TIMELINE_APPROVAL_STATUS_APPROVED,
        approved_by="reviewer",
    )

    assert gate.approval_status == TIMELINE_APPROVAL_STATUS_APPROVED
    assert gate.gate_status == TIMELINE_APPROVAL_GATE_STATUS_APPROVED
    assert gate.can_proceed_to_execution is True
    assert gate.can_render is False
    assert gate.requires_human_approval is False
    assert gate.approved_by == "reviewer"
    assert gate.approved_at is not None
    assert gate.metadata["future_allowed_after_approval"] is True
    assert gate.metadata["can_render_in_2b_33"] is False
