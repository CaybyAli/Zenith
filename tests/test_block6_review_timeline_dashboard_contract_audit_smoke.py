from __future__ import annotations

from pathlib import Path

from core.review_timeline_dashboard_package_builder import (
    ReviewTimelineDashboardPackageBuilder,
)
from models.review_timeline_dashboard_package import (
    REVIEW_TIMELINE_DASHBOARD_ACTION_APPROVE_TIMELINE,
    REVIEW_TIMELINE_DASHBOARD_ACTION_REJECT_TIMELINE,
    REVIEW_TIMELINE_DASHBOARD_ACTION_REQUEST_CHANGES,
    REVIEW_TIMELINE_DASHBOARD_ACTION_REVIEW_TIMELINE,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
    ReviewTimelineDashboardPackage,
)
from models.review_timeline_plan import (
    REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
    REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
    REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED,
    ReviewTimelineItem,
    ReviewTimelinePlan,
)
from models.timeline_approval_gate import (
    TIMELINE_APPROVAL_GATE_STATUS_APPROVED,
    TIMELINE_APPROVAL_STATUS_APPROVED,
    TimelineApprovalGate,
)
from models.timeline_safety_validator import (
    TIMELINE_SAFETY_STATUS_BLOCKED,
    TIMELINE_SAFETY_STATUS_PASSED,
    TimelineSafetyValidation,
)


ROOT = Path(__file__).resolve().parents[1]

DASHBOARD_PRODUCT_FILES = [
    "models/review_timeline_dashboard_package.py",
    "core/review_timeline_dashboard_package_builder.py",
]


ALLOWED_DASHBOARD_ACTIONS = {
    "review_timeline",
    "approve_timeline",
    "reject_timeline",
    "request_changes",
    "inspect_safety_issues",
    "inspect_censor_items",
    "inspect_protected_items",
}


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


def _read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _safe_plan() -> ReviewTimelinePlan:
    plan = ReviewTimelinePlan(
        plan_id="dashboard_contract_plan",
        job_id="dashboard_contract_job",
        items=[
            ReviewTimelineItem(
                timeline_item_id="keep_1",
                source_segment_id="seg_keep_1",
                start_seconds=1.0,
                end_seconds=3.0,
                source_start_seconds=1.0,
                source_end_seconds=3.0,
                duration_seconds=2.0,
                action=REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
                final_decision=REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
                review_required=True,
                review_reason="dashboard_contract_keep_review",
            )
        ],
        metadata={
            "review_only": True,
            "media_unchanged": True,
        },
    )
    plan.refresh_counts()
    return plan


def _approved_gate(can_proceed: bool = True) -> TimelineApprovalGate:
    return TimelineApprovalGate(
        approval_gate_id="dashboard_contract_approval",
        job_id="dashboard_contract_job",
        source_review_timeline_plan_id="dashboard_contract_plan",
        approval_status=TIMELINE_APPROVAL_STATUS_APPROVED,
        gate_status=TIMELINE_APPROVAL_GATE_STATUS_APPROVED,
        can_proceed_to_execution=can_proceed,
        can_render=False,
        requires_human_approval=False,
        metadata={
            "approval_gate_only": True,
            "media_unchanged": True,
        },
    )


def _safety_validation(
    status: str = TIMELINE_SAFETY_STATUS_PASSED,
    safe_for_future_execution: bool = True,
    blocking_errors: list[str] | None = None,
) -> TimelineSafetyValidation:
    return TimelineSafetyValidation(
        safety_validation_id="dashboard_contract_safety",
        job_id="dashboard_contract_job",
        source_review_timeline_plan_id="dashboard_contract_plan",
        source_timeline_approval_gate_id="dashboard_contract_approval",
        validation_status=status,
        is_safe_for_future_execution=safe_for_future_execution,
        is_safe_for_render=False,
        requires_manual_review=True,
        blocking_errors=list(blocking_errors or []),
        metadata={
            "safety_validator_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_34": True,
            "no_render_in_2b_34": True,
        },
    )


def _build_job(
    plan: ReviewTimelinePlan,
    gate: TimelineApprovalGate,
    safety: TimelineSafetyValidation,
):
    class Job:
        job_id = "dashboard_contract_job"

    job = Job()
    job.review_timeline_plan = plan
    job.review_timeline_plan_status = plan.status
    job.review_timeline_plan_id = plan.plan_id
    job.review_timeline_plan_items = [item.to_dict() for item in plan.items]

    job.timeline_approval_gate = gate
    job.timeline_approval_gate_status = gate.gate_status
    job.timeline_approval_status = gate.approval_status
    job.timeline_can_proceed_to_execution = gate.can_proceed_to_execution
    job.timeline_can_render = False

    job.timeline_safety_validator = safety
    job.timeline_safety_validation_status = safety.validation_status
    job.timeline_is_safe_for_future_execution = safety.is_safe_for_future_execution
    job.timeline_is_safe_for_render = False
    job.timeline_safety_blocking_errors = list(safety.blocking_errors)

    return job


def _build_package(
    safety: TimelineSafetyValidation | None = None,
) -> ReviewTimelineDashboardPackage:
    plan = _safe_plan()
    gate = _approved_gate()
    safety = safety or _safety_validation()

    report = ReviewTimelineDashboardPackageBuilder().build(
        _build_job(plan, gate, safety)
    )

    assert report.dashboard_package is not None
    return report.dashboard_package


def test_dashboard_action_constants_are_safe_allowlisted_actions() -> None:
    dashboard_action_constants = {
        REVIEW_TIMELINE_DASHBOARD_ACTION_REVIEW_TIMELINE,
        REVIEW_TIMELINE_DASHBOARD_ACTION_APPROVE_TIMELINE,
        REVIEW_TIMELINE_DASHBOARD_ACTION_REJECT_TIMELINE,
        REVIEW_TIMELINE_DASHBOARD_ACTION_REQUEST_CHANGES,
    }

    assert dashboard_action_constants.issubset(ALLOWED_DASHBOARD_ACTIONS)
    assert dashboard_action_constants.isdisjoint(FORBIDDEN_DASHBOARD_ACTIONS)


def test_dashboard_product_files_do_not_define_forbidden_allowed_actions() -> None:
    violations: list[str] = []

    for relative_path in DASHBOARD_PRODUCT_FILES:
        text = _read_text(relative_path)

        for forbidden_action in FORBIDDEN_DASHBOARD_ACTIONS:
            double_quoted = f'"{forbidden_action}"'
            single_quoted = f"'{forbidden_action}'"

            if double_quoted in text or single_quoted in text:
                violations.append(f"{relative_path}: {forbidden_action}")

    assert violations == []


def test_dashboard_package_enforces_dashboard_only_render_safety() -> None:
    package = ReviewTimelineDashboardPackage(
        package_status=REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
        can_proceed_to_execution=True,
        can_render=True,
        is_safe_for_future_execution=True,
        is_safe_for_render=True,
        dashboard_actions=[
            REVIEW_TIMELINE_DASHBOARD_ACTION_REVIEW_TIMELINE,
            REVIEW_TIMELINE_DASHBOARD_ACTION_APPROVE_TIMELINE,
        ],
        metadata={},
    )

    payload = package.to_dict()

    assert package.can_render is False
    assert package.is_safe_for_render is False
    assert payload["can_render"] is False
    assert payload["is_safe_for_render"] is False
    assert payload["metadata"]["dashboard_only"] is True
    assert payload["metadata"]["media_unchanged"] is True
    assert payload["metadata"]["no_execution_in_2b_35"] is True
    assert payload["metadata"]["no_render_in_2b_35"] is True


def test_dashboard_builder_outputs_only_safe_dashboard_actions() -> None:
    package = _build_package()

    assert package.package_status == REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY
    assert set(package.dashboard_actions).issubset(ALLOWED_DASHBOARD_ACTIONS)
    assert set(package.dashboard_actions).isdisjoint(FORBIDDEN_DASHBOARD_ACTIONS)
    assert package.can_render is False
    assert package.is_safe_for_render is False
    assert package.metadata["dashboard_only"] is True
    assert package.metadata["media_unchanged"] is True


def test_dashboard_builder_keeps_safety_blocked_dashboard_blocked() -> None:
    package = _build_package(
        safety=_safety_validation(
            status=TIMELINE_SAFETY_STATUS_BLOCKED,
            safe_for_future_execution=False,
            blocking_errors=["safety_blocked_by_dashboard_contract_audit"],
        )
    )

    assert package.package_status == REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED
    assert package.can_proceed_to_execution is False
    assert package.can_render is False
    assert package.is_safe_for_render is False
    assert "safety_blocked_by_dashboard_contract_audit" in package.blocking_errors
    assert set(package.dashboard_actions).isdisjoint(FORBIDDEN_DASHBOARD_ACTIONS)


def test_dashboard_builder_keeps_censor_items_review_visible_and_protected() -> None:
    plan = ReviewTimelinePlan(
        plan_id="dashboard_contract_plan",
        job_id="dashboard_contract_job",
        items=[
            ReviewTimelineItem(
                timeline_item_id="censor_1",
                source_segment_id="seg_censor_1",
                start_seconds=5.0,
                end_seconds=7.0,
                source_start_seconds=5.0,
                source_end_seconds=7.0,
                duration_seconds=2.0,
                action=REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
                final_decision=REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
                protection_status=REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED,
                censor_sfx_required=True,
                review_required=True,
                review_reason="censor_item_requires_review",
                metadata={
                    "review_only": True,
                    "media_unchanged": True,
                },
            )
        ],
        metadata={
            "review_only": True,
            "media_unchanged": True,
        },
    )
    plan.refresh_counts()

    package = ReviewTimelineDashboardPackageBuilder().build(
        _build_job(
            plan=plan,
            gate=_approved_gate(can_proceed=True),
            safety=_safety_validation(),
        )
    ).dashboard_package

    assert package is not None
    assert len(package.item_cards) == 1

    card = package.item_cards[0]

    assert card.action == REVIEW_TIMELINE_ACTION_CENSOR_KEEP
    assert card.protected is True
    assert card.censor_sfx_required is True
    assert card.review_required is True
    assert "Censor" in card.badge
    assert set(package.dashboard_actions).isdisjoint(FORBIDDEN_DASHBOARD_ACTIONS)