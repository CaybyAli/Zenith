from __future__ import annotations

from types import SimpleNamespace

from core.review_timeline_dashboard_package_builder import (
    ReviewTimelineDashboardPackageBuilder,
)
from models.review_timeline_dashboard_package import (
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
)
from models.review_timeline_plan import (
    REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY,
    REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
    REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
    REVIEW_TIMELINE_ACTION_PROTECT,
    REVIEW_TIMELINE_ACTION_REMOVE_REVIEW,
    REVIEW_TIMELINE_ACTION_TRIM_REVIEW,
    REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW,
    REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED,
    REVIEW_TIMELINE_PROTECTION_CONTINUITY_BLOCKED,
    REVIEW_TIMELINE_PROTECTION_NORMAL,
    REVIEW_TIMELINE_PROTECTION_PROTECTED,
    ReviewTimelineItem,
    ReviewTimelinePlan,
)
from models.timeline_approval_gate import (
    TIMELINE_APPROVAL_GATE_STATUS_APPROVED,
    TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
    TIMELINE_APPROVAL_STATUS_APPROVED,
    TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
    TimelineApprovalGate,
)
from models.timeline_safety_validator import (
    TIMELINE_SAFETY_STATUS_BLOCKED,
    TIMELINE_SAFETY_STATUS_PASSED,
    TimelineSafetyItemResult,
    TimelineSafetyValidation,
)


FORBIDDEN_DASHBOARD_ACTIONS = {
    "render",
    "execute",
    "apply",
    "cut",
    "trim_now",
    "delete",
    "mute",
    "censor_now",
    "apply_timeline",
    "execute_timeline",
}


def _item(
    item_id: str,
    action: str,
    protection_status: str = REVIEW_TIMELINE_PROTECTION_NORMAL,
    review_required: bool = True,
    censor_sfx_required: bool = False,
    continuity_blocked: bool = False,
) -> ReviewTimelineItem:
    return ReviewTimelineItem(
        timeline_item_id=item_id,
        source_segment_id=f"segment_{item_id}",
        start_seconds=10.0,
        end_seconds=20.0,
        source_start_seconds=10.0,
        source_end_seconds=20.0,
        duration_seconds=10.0,
        action=action,
        final_decision=action,
        protection_status=protection_status,
        review_required=review_required,
        review_reason=f"{action}_requires_review",
        censor_sfx_required=censor_sfx_required,
        continuity_blocked=continuity_blocked,
        safety_flags=[],
        notes=[],
        metadata={"audit": "block6_safety_contract"},
    )


def _plan(items: list[ReviewTimelineItem]) -> ReviewTimelinePlan:
    plan = ReviewTimelinePlan(
        plan_id="review_timeline_plan_audit",
        job_id="block6_safety_contract_job",
        items=items,
        status=REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW,
        metadata={
            "review_only": True,
            "media_unchanged": True,
        },
    )
    plan.refresh_counts()
    return plan


def _approval_gate(
    approval_status: str,
    gate_status: str,
    can_proceed_to_execution: bool,
) -> TimelineApprovalGate:
    return TimelineApprovalGate(
        approval_gate_id="timeline_approval_gate_audit",
        job_id="block6_safety_contract_job",
        source_review_timeline_plan_id="review_timeline_plan_audit",
        approval_status=approval_status,
        gate_status=gate_status,
        can_proceed_to_execution=can_proceed_to_execution,
        can_render=False,
        requires_human_approval=(approval_status != TIMELINE_APPROVAL_STATUS_APPROVED),
        metadata={
            "approval_gate_only": True,
            "media_unchanged": True,
        },
    )


def _safety_validation(
    validation_status: str,
    is_safe_for_future_execution: bool,
    blocking_errors: list[str] | None = None,
    item_results: list[TimelineSafetyItemResult] | None = None,
) -> TimelineSafetyValidation:
    return TimelineSafetyValidation(
        safety_validation_id="timeline_safety_validation_audit",
        job_id="block6_safety_contract_job",
        source_review_timeline_plan_id="review_timeline_plan_audit",
        source_timeline_approval_gate_id="timeline_approval_gate_audit",
        validation_status=validation_status,
        is_safe_for_future_execution=is_safe_for_future_execution,
        is_safe_for_render=False,
        requires_manual_review=True,
        blocking_errors=list(blocking_errors or []),
        warnings=[],
        item_results=list(item_results or []),
        total_items_checked=len(item_results or []),
        future_execution_safety_status=(
            "safe"
            if is_safe_for_future_execution and not blocking_errors
            else "blocked"
        ),
        metadata={
            "safety_validator_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_34": True,
            "no_render_in_2b_34": True,
        },
    )


def _job(
    plan: ReviewTimelinePlan,
    approval_gate: TimelineApprovalGate,
    safety_validation: TimelineSafetyValidation,
) -> SimpleNamespace:
    return SimpleNamespace(
        job_id="block6_safety_contract_job",
        review_timeline_plan=plan,
        review_timeline_plan_status=plan.status,
        review_timeline_plan_id=plan.plan_id,
        review_timeline_plan_items=[item.to_dict() for item in plan.items],
        timeline_approval_gate=approval_gate,
        timeline_approval_gate_status=approval_gate.gate_status,
        timeline_approval_status=approval_gate.approval_status,
        timeline_can_proceed_to_execution=approval_gate.can_proceed_to_execution,
        timeline_can_render=False,
        timeline_safety_validator=safety_validation,
        timeline_safety_validation_status=safety_validation.validation_status,
        timeline_is_safe_for_future_execution=(
            safety_validation.is_safe_for_future_execution
        ),
        timeline_is_safe_for_render=False,
        timeline_safety_blocking_errors=list(safety_validation.blocking_errors),
        timeline_safety_item_results=[
            item_result.to_dict()
            for item_result in safety_validation.item_results
        ],
    )


def _dashboard_package_for_job(job: SimpleNamespace):
    report = ReviewTimelineDashboardPackageBuilder().build(job)
    assert report.can_render is False

    package = report.dashboard_package
    assert package is not None
    assert package.can_render is False
    assert package.is_safe_for_render is False

    return package


def _assert_no_dangerous_dashboard_actions(actions: list[str]) -> None:
    found_forbidden_actions = [
        action
        for action in actions
        if action in FORBIDDEN_DASHBOARD_ACTIONS
    ]

    assert found_forbidden_actions == []


def test_case_a_pending_approval_safety_passed_dashboard_ready_but_not_renderable() -> None:
    plan = _plan([
        _item("keep_1", REVIEW_TIMELINE_ACTION_KEEP_REVIEW),
    ])
    approval_gate = _approval_gate(
        approval_status=TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
        gate_status=TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
        can_proceed_to_execution=False,
    )
    safety_validation = _safety_validation(
        validation_status=TIMELINE_SAFETY_STATUS_PASSED,
        is_safe_for_future_execution=True,
    )

    package = _dashboard_package_for_job(
        _job(plan, approval_gate, safety_validation)
    )

    assert package.package_status == REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY
    assert package.approval_status == TIMELINE_APPROVAL_STATUS_PENDING_REVIEW
    assert package.safety_status == TIMELINE_SAFETY_STATUS_PASSED
    assert package.can_proceed_to_execution is False
    assert package.can_render is False
    assert package.is_safe_for_render is False
    assert package.requires_manual_review is True
    _assert_no_dangerous_dashboard_actions(package.dashboard_actions)


def test_case_b_approved_and_safety_passed_can_proceed_but_still_not_renderable() -> None:
    plan = _plan([
        _item("keep_1", REVIEW_TIMELINE_ACTION_KEEP_REVIEW),
    ])
    approval_gate = _approval_gate(
        approval_status=TIMELINE_APPROVAL_STATUS_APPROVED,
        gate_status=TIMELINE_APPROVAL_GATE_STATUS_APPROVED,
        can_proceed_to_execution=True,
    )
    safety_validation = _safety_validation(
        validation_status=TIMELINE_SAFETY_STATUS_PASSED,
        is_safe_for_future_execution=True,
    )

    package = _dashboard_package_for_job(
        _job(plan, approval_gate, safety_validation)
    )

    assert package.package_status == REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY
    assert package.can_proceed_to_execution is True
    assert package.can_render is False
    assert package.is_safe_for_render is False
    _assert_no_dangerous_dashboard_actions(package.dashboard_actions)


def test_case_c_approved_but_safety_blocked_forces_dashboard_blocked() -> None:
    plan = _plan([
        _item("keep_1", REVIEW_TIMELINE_ACTION_KEEP_REVIEW),
    ])
    approval_gate = _approval_gate(
        approval_status=TIMELINE_APPROVAL_STATUS_APPROVED,
        gate_status=TIMELINE_APPROVAL_GATE_STATUS_APPROVED,
        can_proceed_to_execution=True,
    )
    safety_validation = _safety_validation(
        validation_status=TIMELINE_SAFETY_STATUS_BLOCKED,
        is_safe_for_future_execution=False,
        blocking_errors=["blocked_by_safety_validator"],
    )

    package = _dashboard_package_for_job(
        _job(plan, approval_gate, safety_validation)
    )

    assert package.package_status == REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED
    assert package.safety_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert package.can_proceed_to_execution is False
    assert package.can_render is False
    assert package.is_safe_for_render is False
    assert "blocked_by_safety_validator" in package.blocking_errors
    _assert_no_dangerous_dashboard_actions(package.dashboard_actions)


def test_case_d_censor_item_stays_protected_and_only_reviewable() -> None:
    item = _item(
        "censor_1",
        REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
        protection_status=REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED,
        censor_sfx_required=True,
    )
    plan = _plan([item])
    approval_gate = _approval_gate(
        approval_status=TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
        gate_status=TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
        can_proceed_to_execution=False,
    )
    safety_validation = _safety_validation(
        validation_status=TIMELINE_SAFETY_STATUS_PASSED,
        is_safe_for_future_execution=True,
        item_results=[
            TimelineSafetyItemResult(
                item_index=0,
                item_id="censor_1",
                action=REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
                protection_status=REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED,
                is_valid=True,
            )
        ],
    )

    package = _dashboard_package_for_job(
        _job(plan, approval_gate, safety_validation)
    )
    card = package.item_cards[0]

    assert card.action == REVIEW_TIMELINE_ACTION_CENSOR_KEEP
    assert card.protected is True
    assert card.censor_sfx_required is True
    assert "Censor" in card.badge
    assert card.review_required is True
    _assert_no_dangerous_dashboard_actions(package.dashboard_actions)


def test_case_e_protected_item_stays_protected_without_execution_action() -> None:
    item = _item(
        "protected_1",
        REVIEW_TIMELINE_ACTION_PROTECT,
        protection_status=REVIEW_TIMELINE_PROTECTION_PROTECTED,
    )
    plan = _plan([item])
    approval_gate = _approval_gate(
        approval_status=TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
        gate_status=TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
        can_proceed_to_execution=False,
    )
    safety_validation = _safety_validation(
        validation_status=TIMELINE_SAFETY_STATUS_PASSED,
        is_safe_for_future_execution=True,
    )

    package = _dashboard_package_for_job(
        _job(plan, approval_gate, safety_validation)
    )
    card = package.item_cards[0]

    assert card.action == REVIEW_TIMELINE_ACTION_PROTECT
    assert card.protected is True
    assert card.protection_status == REVIEW_TIMELINE_PROTECTION_PROTECTED
    assert "remove_file" not in package.dashboard_actions
    assert "trim_now" not in package.dashboard_actions
    _assert_no_dangerous_dashboard_actions(package.dashboard_actions)


def test_case_f_remove_review_item_is_only_review_candidate() -> None:
    item = _item(
        "remove_1",
        REVIEW_TIMELINE_ACTION_REMOVE_REVIEW,
        protection_status=REVIEW_TIMELINE_PROTECTION_NORMAL,
        review_required=True,
    )
    plan = _plan([item])
    approval_gate = _approval_gate(
        approval_status=TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
        gate_status=TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
        can_proceed_to_execution=False,
    )
    safety_validation = _safety_validation(
        validation_status=TIMELINE_SAFETY_STATUS_PASSED,
        is_safe_for_future_execution=True,
    )

    package = _dashboard_package_for_job(
        _job(plan, approval_gate, safety_validation)
    )
    card = package.item_cards[0]

    assert card.action == REVIEW_TIMELINE_ACTION_REMOVE_REVIEW
    assert card.review_required is True
    assert card.final_decision == REVIEW_TIMELINE_ACTION_REMOVE_REVIEW
    assert "delete" not in package.dashboard_actions
    assert "apply_timeline" not in package.dashboard_actions
    _assert_no_dangerous_dashboard_actions(package.dashboard_actions)


def test_case_g_trim_review_item_is_only_review_candidate() -> None:
    item = _item(
        "trim_1",
        REVIEW_TIMELINE_ACTION_TRIM_REVIEW,
        protection_status=REVIEW_TIMELINE_PROTECTION_NORMAL,
        review_required=True,
    )
    plan = _plan([item])
    approval_gate = _approval_gate(
        approval_status=TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
        gate_status=TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
        can_proceed_to_execution=False,
    )
    safety_validation = _safety_validation(
        validation_status=TIMELINE_SAFETY_STATUS_PASSED,
        is_safe_for_future_execution=True,
    )

    package = _dashboard_package_for_job(
        _job(plan, approval_gate, safety_validation)
    )
    card = package.item_cards[0]

    assert card.action == REVIEW_TIMELINE_ACTION_TRIM_REVIEW
    assert card.review_required is True
    assert card.final_decision == REVIEW_TIMELINE_ACTION_TRIM_REVIEW
    assert "trim_now" not in package.dashboard_actions
    assert "apply_timeline" not in package.dashboard_actions
    _assert_no_dangerous_dashboard_actions(package.dashboard_actions)


def test_continuity_blocked_item_stays_blocked() -> None:
    item = _item(
        "continuity_1",
        REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY,
        protection_status=REVIEW_TIMELINE_PROTECTION_CONTINUITY_BLOCKED,
        review_required=True,
        continuity_blocked=True,
    )
    plan = _plan([item])
    approval_gate = _approval_gate(
        approval_status=TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
        gate_status=TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
        can_proceed_to_execution=False,
    )
    safety_validation = _safety_validation(
        validation_status=TIMELINE_SAFETY_STATUS_BLOCKED,
        is_safe_for_future_execution=False,
        blocking_errors=["continuity_blocked_items_require_manual_review"],
    )

    package = _dashboard_package_for_job(
        _job(plan, approval_gate, safety_validation)
    )
    card = package.item_cards[0]

    assert package.package_status == REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED
    assert card.action == REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY
    assert card.continuity_blocked is True
    assert card.protected is True
    assert "Continuity" in card.badge
    _assert_no_dangerous_dashboard_actions(package.dashboard_actions)