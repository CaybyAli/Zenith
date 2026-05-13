from core.review_timeline_plan_builder import build_review_timeline_plan
from models.final_cut_list import (
    FINAL_ACTION_BLOCKED_BY_CONTINUITY,
    FINAL_ACTION_CENSOR_KEEP,
    FINAL_ACTION_KEEP_HIGH_VALUE,
    FINAL_ACTION_KEEP_REVIEW,
    FINAL_ACTION_PROTECT,
    FINAL_ACTION_REMOVE_REVIEW,
    FINAL_ACTION_TECHNICAL_REVIEW,
    FINAL_ACTION_TRIM_REVIEW,
    FINAL_ACTION_UNKNOWN_REVIEW,
)
from models.review_timeline_plan import (
    REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY,
    REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
    REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
    REVIEW_TIMELINE_ACTION_PROTECT,
    REVIEW_TIMELINE_ACTION_REMOVE_REVIEW,
    REVIEW_TIMELINE_ACTION_TECHNICAL_REVIEW,
    REVIEW_TIMELINE_ACTION_TRIM_REVIEW,
    REVIEW_TIMELINE_ACTION_UNKNOWN_REVIEW,
    REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW,
)


def _final_item(action: str, index: int, extra=None):
    data = {
        "final_item_id": f"final_item_{index}",
        "source_item_id": f"cut_item_{index}",
        "segment_id": f"seg_{index}",
        "start_seconds": float(index * 10),
        "end_seconds": float(index * 10 + 5),
        "duration_seconds": 5.0,
        "final_action": action,
        "final_confidence": 0.9,
        "priority": "high",
        "segment_type": "test",
        "murch_score": 0.8,
        "continuity_blocked": action == FINAL_ACTION_BLOCKED_BY_CONTINUITY,
        "is_protected": action == FINAL_ACTION_PROTECT,
        "is_censor_keep": action == FINAL_ACTION_CENSOR_KEEP,
        "is_review_required": action != FINAL_ACTION_KEEP_HIGH_VALUE,
        "is_keep_candidate": action
        in {
            FINAL_ACTION_KEEP_HIGH_VALUE,
            FINAL_ACTION_KEEP_REVIEW,
            FINAL_ACTION_PROTECT,
            FINAL_ACTION_CENSOR_KEEP,
        },
        "is_trim_candidate": action == FINAL_ACTION_TRIM_REVIEW,
        "is_remove_candidate": action == FINAL_ACTION_REMOVE_REVIEW,
        "reason": f"reason for {action}",
        "decision_basis": {"test": True},
        "source_signal_ids": [f"sig_{index}"],
        "metadata": {},
    }
    if extra:
        data.update(extra)
    return data


def test_build_review_timeline_plan_maps_all_final_actions_safely():
    plan = build_review_timeline_plan(
        final_cut_list_items=[
            _final_item(FINAL_ACTION_KEEP_HIGH_VALUE, 1),
            _final_item(FINAL_ACTION_KEEP_REVIEW, 2),
            _final_item(FINAL_ACTION_TRIM_REVIEW, 3),
            _final_item(FINAL_ACTION_REMOVE_REVIEW, 4),
            _final_item(FINAL_ACTION_PROTECT, 5),
            _final_item(FINAL_ACTION_CENSOR_KEEP, 6),
            _final_item(FINAL_ACTION_TECHNICAL_REVIEW, 7),
            _final_item(FINAL_ACTION_BLOCKED_BY_CONTINUITY, 8),
            _final_item(FINAL_ACTION_UNKNOWN_REVIEW, 9),
        ],
        job_id="job_review_timeline_builder",
        metadata={"test": True},
    )

    assert plan.status == REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW
    assert plan.total_items == 9
    assert plan.total_duration_seconds == 45.0

    by_final = {item.final_decision: item for item in plan.items}

    assert by_final[FINAL_ACTION_KEEP_HIGH_VALUE].action == REVIEW_TIMELINE_ACTION_KEEP_REVIEW
    assert by_final[FINAL_ACTION_KEEP_REVIEW].action == REVIEW_TIMELINE_ACTION_KEEP_REVIEW
    assert by_final[FINAL_ACTION_TRIM_REVIEW].action == REVIEW_TIMELINE_ACTION_TRIM_REVIEW
    assert by_final[FINAL_ACTION_REMOVE_REVIEW].action == REVIEW_TIMELINE_ACTION_REMOVE_REVIEW
    assert by_final[FINAL_ACTION_PROTECT].action == REVIEW_TIMELINE_ACTION_PROTECT
    assert by_final[FINAL_ACTION_CENSOR_KEEP].action == REVIEW_TIMELINE_ACTION_CENSOR_KEEP
    assert by_final[FINAL_ACTION_TECHNICAL_REVIEW].action == REVIEW_TIMELINE_ACTION_TECHNICAL_REVIEW
    assert (
        by_final[FINAL_ACTION_BLOCKED_BY_CONTINUITY].action
        == REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY
    )
    assert by_final[FINAL_ACTION_UNKNOWN_REVIEW].action == REVIEW_TIMELINE_ACTION_UNKNOWN_REVIEW


def test_review_remove_is_review_only_and_does_not_mark_media_changed():
    plan = build_review_timeline_plan(
        final_cut_list_items=[
            _final_item(FINAL_ACTION_REMOVE_REVIEW, 1),
        ],
        job_id="job_review_remove_safe",
    )

    item = plan.items[0]

    assert item.action == REVIEW_TIMELINE_ACTION_REMOVE_REVIEW
    assert item.review_required is True
    assert "human_review_remove_candidate" in item.safety_flags
    assert "review_only_plan" in item.safety_flags
    assert "media_unchanged" in item.safety_flags


def test_censor_and_protected_items_are_preserved_for_review():
    plan = build_review_timeline_plan(
        final_cut_list_items=[
            _final_item(FINAL_ACTION_CENSOR_KEEP, 1),
            _final_item(FINAL_ACTION_PROTECT, 2),
            _final_item(FINAL_ACTION_BLOCKED_BY_CONTINUITY, 3),
        ],
        job_id="job_review_timeline_safety",
    )

    assert plan.censor_required_count == 1
    assert plan.protected_count == 2
    assert plan.continuity_blocked_count == 1
    assert all(item.review_required for item in plan.items)

    censor_item = plan.items[0]
    protected_item = plan.items[1]
    blocked_item = plan.items[2]

    assert censor_item.censor_sfx_required is True
    assert censor_item.protection_status == "censor_protected"

    assert protected_item.protection_status == "protected"

    assert blocked_item.continuity_blocked is True
    assert blocked_item.protection_status == "continuity_blocked"
