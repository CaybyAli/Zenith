from core.timeline_safety_validator import TimelineSafetyValidator
from models.timeline_safety_validator import (
    TIMELINE_SAFETY_REASON_APPROVAL_OVERRIDDEN_BY_SAFETY_VALIDATOR,
    TIMELINE_SAFETY_REASON_CENSOR_ITEM_NOT_PROTECTED,
    TIMELINE_SAFETY_REASON_CONTINUITY_BLOCK_NOT_PRESERVED,
    TIMELINE_SAFETY_REASON_END_BEFORE_START,
    TIMELINE_SAFETY_REASON_EXECUTION_NOT_SAFE,
    TIMELINE_SAFETY_REASON_MISSING_REVIEW_TIMELINE_ITEMS,
    TIMELINE_SAFETY_REASON_MISSING_REVIEW_TIMELINE_PLAN,
    TIMELINE_SAFETY_REASON_NEGATIVE_START_TIME,
    TIMELINE_SAFETY_REASON_PROTECTED_ITEM_HAS_UNSAFE_ACTION,
    TIMELINE_SAFETY_REASON_REMOVE_REVIEW_WITHOUT_HUMAN_REVIEW_SAFETY,
    TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34,
    TIMELINE_SAFETY_REASON_TIMELINE_GAP,
    TIMELINE_SAFETY_REASON_TIMELINE_OVERLAP,
    TIMELINE_SAFETY_REASON_TRIM_REVIEW_WITHOUT_HUMAN_REVIEW_SAFETY,
    TIMELINE_SAFETY_REASON_ZERO_OR_NEGATIVE_DURATION,
    TIMELINE_SAFETY_STATUS_BLOCKED,
    TIMELINE_SAFETY_STATUS_PASSED,
    TIMELINE_SAFETY_STATUS_PASSED_WITH_WARNINGS,
)


def _item(extra=None):
    data = {
        "timeline_item_id": "item_1",
        "start_seconds": 0.0,
        "end_seconds": 5.0,
        "source_start_seconds": 0.0,
        "source_end_seconds": 5.0,
        "duration_seconds": 5.0,
        "action": "keep_review",
        "protection_status": "normal",
        "censor_sfx_required": False,
        "continuity_blocked": False,
        "review_required": True,
        "safety_flags": ["review_only", "human_review"],
        "metadata": {
            "safety_flags": ["review_only", "human_review"],
        },
    }
    if extra:
        data.update(extra)
    return data


def _plan(items=None):
    if items is None:
        items = [_item()]

    return {
        "plan_id": "review_timeline_plan_test",
        "job_id": "job_timeline_safety_validator",
        "status": "pending_review",
        "items": items,
        "total_items": len(items),
        "warnings": [],
        "errors": [],
        "metadata": {
            "review_only": True,
            "approval_required": True,
        },
    }


def _job(plan=None, **extra):
    data = {
        "job_id": "job_timeline_safety_validator",
        "review_timeline_plan": plan if plan is not None else _plan(),
        "review_timeline_plan_items": (
            plan.get("items", []) if isinstance(plan, dict) else []
        ),
        "timeline_approval_gate": {
            "approval_gate_id": "timeline_approval_gate_test",
        },
        "timeline_approval_status": "pending_review",
        "timeline_can_proceed_to_execution": False,
        "timeline_can_render": False,
        "timeline_approval_blocking_reasons": [],
    }
    data.update(extra)
    return data


def _validate(job):
    return TimelineSafetyValidator().validate(job).timeline_safety_validation


def test_missing_review_timeline_plan_blocks_validator():
    validation = _validate(
        {
            "job_id": "job_missing_plan",
            "review_timeline_plan_items": [],
        }
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert validation.is_safe_for_future_execution is False
    assert validation.is_safe_for_render is False
    assert TIMELINE_SAFETY_REASON_MISSING_REVIEW_TIMELINE_PLAN in validation.blocking_errors


def test_missing_review_timeline_items_blocks_validator():
    validation = _validate(_job(plan=_plan(items=[])))

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert validation.is_safe_for_render is False
    assert TIMELINE_SAFETY_REASON_MISSING_REVIEW_TIMELINE_ITEMS in validation.blocking_errors


def test_negative_start_time_blocks_validator():
    validation = _validate(
        _job(plan=_plan(items=[_item({"start_seconds": -1.0})]))
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert validation.negative_time_count == 1
    assert TIMELINE_SAFETY_REASON_NEGATIVE_START_TIME in validation.blocking_errors


def test_end_before_start_blocks_validator():
    validation = _validate(
        _job(
            plan=_plan(
                items=[
                    _item(
                        {
                            "start_seconds": 5.0,
                            "end_seconds": 4.0,
                            "duration_seconds": 1.0,
                        }
                    )
                ]
            )
        )
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert validation.invalid_timing_count >= 1
    assert TIMELINE_SAFETY_REASON_END_BEFORE_START in validation.blocking_errors


def test_zero_or_negative_duration_blocks_validator():
    validation = _validate(
        _job(plan=_plan(items=[_item({"duration_seconds": 0.0})]))
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert validation.zero_or_negative_duration_count == 1
    assert TIMELINE_SAFETY_REASON_ZERO_OR_NEGATIVE_DURATION in validation.blocking_errors


def test_overlap_blocks_validator():
    validation = _validate(
        _job(
            plan=_plan(
                items=[
                    _item(
                        {
                            "timeline_item_id": "item_1",
                            "start_seconds": 0.0,
                            "end_seconds": 5.0,
                            "duration_seconds": 5.0,
                        }
                    ),
                    _item(
                        {
                            "timeline_item_id": "item_2",
                            "start_seconds": 4.5,
                            "end_seconds": 8.0,
                            "duration_seconds": 3.5,
                        }
                    ),
                ]
            )
        )
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert validation.overlap_count == 1
    assert TIMELINE_SAFETY_REASON_TIMELINE_OVERLAP in validation.blocking_errors


def test_large_gap_blocks_validator():
    validation = _validate(
        _job(
            plan=_plan(
                items=[
                    _item(
                        {
                            "timeline_item_id": "item_1",
                            "start_seconds": 0.0,
                            "end_seconds": 5.0,
                            "duration_seconds": 5.0,
                        }
                    ),
                    _item(
                        {
                            "timeline_item_id": "item_2",
                            "start_seconds": 5.5,
                            "end_seconds": 9.0,
                            "duration_seconds": 3.5,
                        }
                    ),
                ]
            )
        )
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert validation.gap_count == 1
    assert TIMELINE_SAFETY_REASON_TIMELINE_GAP in validation.blocking_errors


def test_small_gap_creates_warning():
    validation = _validate(
        _job(
            plan=_plan(
                items=[
                    _item(
                        {
                            "timeline_item_id": "item_1",
                            "start_seconds": 0.0,
                            "end_seconds": 5.0,
                            "duration_seconds": 5.0,
                        }
                    ),
                    _item(
                        {
                            "timeline_item_id": "item_2",
                            "start_seconds": 5.1,
                            "end_seconds": 9.0,
                            "duration_seconds": 3.9,
                        }
                    ),
                ]
            )
        )
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_PASSED_WITH_WARNINGS
    assert validation.gap_count == 1
    assert TIMELINE_SAFETY_REASON_TIMELINE_GAP in validation.warnings
    assert validation.is_safe_for_render is False


def test_protected_remove_or_trim_blocks_validator():
    remove_validation = _validate(
        _job(
            plan=_plan(
                items=[
                    _item(
                        {
                            "action": "remove_review",
                            "protection_status": "protected",
                        }
                    )
                ]
            )
        )
    )
    trim_validation = _validate(
        _job(
            plan=_plan(
                items=[
                    _item(
                        {
                            "action": "trim_review",
                            "protection_status": "protected",
                        }
                    )
                ]
            )
        )
    )

    assert TIMELINE_SAFETY_REASON_PROTECTED_ITEM_HAS_UNSAFE_ACTION in remove_validation.blocking_errors
    assert TIMELINE_SAFETY_REASON_PROTECTED_ITEM_HAS_UNSAFE_ACTION in trim_validation.blocking_errors


def test_censor_item_without_required_safety_blocks_validator():
    validation = _validate(
        _job(
            plan=_plan(
                items=[
                    _item(
                        {
                            "action": "censor_keep",
                            "protection_status": "normal",
                            "censor_sfx_required": False,
                        }
                    )
                ]
            )
        )
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert validation.censor_violation_count == 1
    assert TIMELINE_SAFETY_REASON_CENSOR_ITEM_NOT_PROTECTED in validation.blocking_errors


def test_continuity_item_without_preserved_status_blocks_validator():
    validation = _validate(
        _job(
            plan=_plan(
                items=[
                    _item(
                        {
                            "action": "blocked_by_continuity",
                            "protection_status": "normal",
                            "continuity_blocked": False,
                        }
                    )
                ]
            )
        )
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert validation.continuity_violation_count == 1
    assert TIMELINE_SAFETY_REASON_CONTINUITY_BLOCK_NOT_PRESERVED in validation.blocking_errors


def test_remove_review_without_human_review_safety_blocks_validator():
    validation = _validate(
        _job(
            plan=_plan(
                items=[
                    _item(
                        {
                            "action": "remove_review",
                            "safety_flags": [],
                            "metadata": {},
                        }
                    )
                ]
            )
        )
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert TIMELINE_SAFETY_REASON_REMOVE_REVIEW_WITHOUT_HUMAN_REVIEW_SAFETY in validation.blocking_errors


def test_trim_review_without_human_review_safety_blocks_validator():
    validation = _validate(
        _job(
            plan=_plan(
                items=[
                    _item(
                        {
                            "action": "trim_review",
                            "safety_flags": [],
                            "metadata": {},
                        }
                    )
                ]
            )
        )
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert TIMELINE_SAFETY_REASON_TRIM_REVIEW_WITHOUT_HUMAN_REVIEW_SAFETY in validation.blocking_errors


def test_approval_approved_is_overridden_when_safety_finds_error():
    validation = _validate(
        _job(
            plan=_plan(items=[_item({"start_seconds": -1.0})]),
            timeline_approval_status="approved",
        )
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert validation.approval_violation_count >= 1
    assert TIMELINE_SAFETY_REASON_APPROVAL_OVERRIDDEN_BY_SAFETY_VALIDATOR in validation.blocking_errors


def test_timeline_can_render_true_blocks_immediately():
    validation = _validate(_job(timeline_can_render=True))

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert validation.is_safe_for_render is False
    assert TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34 in validation.blocking_errors


def test_execution_true_with_errors_is_not_safe():
    validation = _validate(
        _job(
            plan=_plan(items=[_item({"duration_seconds": 0.0})]),
            timeline_can_proceed_to_execution=True,
        )
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert validation.approval_violation_count >= 1
    assert TIMELINE_SAFETY_REASON_EXECUTION_NOT_SAFE in validation.blocking_errors


def test_valid_approved_timeline_passes_future_execution_but_never_render():
    validation = _validate(
        _job(
            timeline_approval_status="approved",
            timeline_can_proceed_to_execution=True,
        )
    )

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_PASSED
    assert validation.is_safe_for_future_execution is True
    assert validation.is_safe_for_render is False
    assert validation.requires_manual_review is False
