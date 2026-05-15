from __future__ import annotations

from copy import deepcopy
from typing import Any

from models.style_dna_apply_plan import (
    OPERATION_TYPE_INCREMENT_VALUE,
    OPERATION_TYPE_MANUAL_REVIEW_REQUIRED,
    OPERATION_TYPE_MARK_REVIEW_REQUIRED,
    OPERATION_TYPE_SET_VALUE,
    OPERATION_TYPE_STABILIZE_VALUE,
    PHASE_METADATA,
    STYLE_DNA_APPLY_PLAN_STATUS_BLOCKED,
    STYLE_DNA_APPLY_PLAN_STATUS_FAILED,
    STYLE_DNA_APPLY_PLAN_STATUS_READY,
    STYLE_DNA_APPLY_PLAN_STATUS_READY_WITH_WARNINGS,
    STYLE_DNA_APPLY_PLAN_STATUS_WAITING_FOR_REVIEW,
    StyleDNAApplyOperation,
    StyleDNAApplyPlan,
    StyleDNAApplyPlanReport,
    utc_now_iso,
)


REVIEW_STATUS_APPROVED = "style_dna_review_approved"
REVIEW_STATUS_BLOCKED = "style_dna_review_blocked"
REVIEW_STATUS_FAILED = "style_dna_review_failed"
REVIEW_STATUS_PENDING = "style_dna_review_pending_review"
REVIEW_STATUS_REJECTED = "style_dna_review_rejected"
REVIEW_STATUS_NEEDS_CHANGES = "style_dna_review_needs_manual_changes"

PROPOSAL_DECISION_APPROVED = "approved"
PROPOSAL_DECISION_REJECTED = "rejected"
PROPOSAL_DECISION_NEEDS_CHANGES = "needs_manual_changes"
PROPOSAL_DECISION_PENDING = "pending_review"

RECOMMENDATION_REVIEW_PLAN = "review_style_dna_apply_plan"
RECOMMENDATION_WAIT_FOR_REVIEW = "wait_for_style_dna_review_approval"
RECOMMENDATION_FIX_BLOCKERS = "resolve_style_dna_apply_plan_blockers"

BLOCKING_REVIEW_STATUS_MISSING = "style_dna_review_status_missing"
BLOCKING_REVIEW_BLOCKED_OR_FAILED = "style_dna_review_gate_blocked_or_failed"
BLOCKING_REVIEW_HAS_BLOCKERS = "style_dna_review_gate_has_blocking_reasons"
BLOCKING_UNSAFE_REVIEW_PERMISSION = "style_dna_review_gate_contains_unsafe_permission"
BLOCKING_FILE_WRITE_REQUESTED = "style_dna_file_write_not_allowed_in_2b_62"

WARNING_REVIEW_NOT_APPROVED = "style_dna_review_not_approved_yet"
WARNING_NO_APPROVED_PROPOSALS = "no_approved_style_dna_proposals_for_apply_plan"
WARNING_FILE_WRITE_REQUEST_IGNORED = "style_dna_file_write_not_allowed_in_2b_62"
WARNING_SKIPPED_NON_APPROVED_PROPOSALS = "non_approved_style_dna_proposals_skipped"
WARNING_EMPTY_PARAMETER_NAME = "style_dna_proposal_missing_parameter_name"


UNSAFE_REVIEW_FLAGS = [
    "style_dna_review_can_apply_style_dna",
    "style_dna_review_can_write_style_dna",
    "style_dna_review_can_update_profile",
    "style_dna_review_can_change_cutting_rules",
    "style_dna_review_can_modify_timeline",
    "style_dna_review_can_trigger_render",
    "style_dna_review_can_publish",
]


def build_style_dna_apply_plan_report(job: Any) -> dict[str, Any]:
    job_id = _text(_get(job, "job_id") or _get(job, "id") or "unknown_job")
    profile = _resolve_profile(job)
    review_status = _text(_get(job, "style_dna_review_status"))

    warnings: list[str] = []
    blocking_reasons: list[str] = []

    review_blocking_reasons = _text_list(
        _get(job, "style_dna_review_blocking_reasons")
    )
    if not review_status:
        blocking_reasons.append(BLOCKING_REVIEW_STATUS_MISSING)
    if review_status in {REVIEW_STATUS_BLOCKED, REVIEW_STATUS_FAILED}:
        blocking_reasons.append(BLOCKING_REVIEW_BLOCKED_OR_FAILED)
    if review_blocking_reasons:
        blocking_reasons.append(BLOCKING_REVIEW_HAS_BLOCKERS)

    unsafe_flags = [
        flag for flag in UNSAFE_REVIEW_FLAGS if bool(_get(job, flag, False))
    ]
    if unsafe_flags:
        blocking_reasons.append(BLOCKING_UNSAFE_REVIEW_PERMISSION)

    allow_file_write = bool(_get(job, "style_dna_apply_allow_file_write", False))
    if allow_file_write:
        warnings.append(WARNING_FILE_WRITE_REQUEST_IGNORED)
        blocking_reasons.append(BLOCKING_FILE_WRITE_REQUESTED)

    before_snapshot = _dict(_get(job, "existing_style_dna_snapshot"))
    decisions = _list(_get(job, "style_dna_review_proposal_decisions"))
    proposals = _list(_get(job, "style_dna_update_proposals"))

    approved_decision_ids = _approved_proposal_ids(decisions)
    skipped_operation_count = max(0, len(decisions) - len(approved_decision_ids))

    if decisions and skipped_operation_count > 0:
        warnings.append(WARNING_SKIPPED_NON_APPROVED_PROPOSALS)

    if review_status != REVIEW_STATUS_APPROVED:
        warnings.append(WARNING_REVIEW_NOT_APPROVED)

    if review_status in {
        REVIEW_STATUS_PENDING,
        REVIEW_STATUS_REJECTED,
        REVIEW_STATUS_NEEDS_CHANGES,
    }:
        status = STYLE_DNA_APPLY_PLAN_STATUS_WAITING_FOR_REVIEW
        if not approved_decision_ids:
            warnings.append(WARNING_NO_APPROVED_PROPOSALS)
        return _report(
            job_id=job_id,
            profile=profile,
            source_review_status=review_status,
            status=status,
            warnings=warnings,
            blocking_reasons=[],
            before_snapshot=before_snapshot,
            operations=[],
            skipped_operation_count=skipped_operation_count,
            ready_for_future_file_write=False,
            source_review_gate_id=_source_review_gate_id(job),
            source_draft_id=_source_draft_id(job),
            recommendation=RECOMMENDATION_WAIT_FOR_REVIEW,
        )

    if blocking_reasons:
        return _report(
            job_id=job_id,
            profile=profile,
            source_review_status=review_status,
            status=STYLE_DNA_APPLY_PLAN_STATUS_BLOCKED,
            warnings=warnings,
            blocking_reasons=blocking_reasons,
            before_snapshot=before_snapshot,
            operations=[],
            skipped_operation_count=skipped_operation_count,
            ready_for_future_file_write=False,
            source_review_gate_id=_source_review_gate_id(job),
            source_draft_id=_source_draft_id(job),
            recommendation=RECOMMENDATION_FIX_BLOCKERS,
        )

    operations = _build_operations(
        job_id=job_id,
        decisions=decisions,
        proposals=proposals,
        approved_decision_ids=approved_decision_ids,
        has_blockers=bool(blocking_reasons),
    )

    if not operations:
        warnings.append(WARNING_NO_APPROVED_PROPOSALS)

    if any(not operation.parameter_name for operation in operations):
        warnings.append(WARNING_EMPTY_PARAMETER_NAME)

    if review_status == REVIEW_STATUS_APPROVED and operations:
        status = STYLE_DNA_APPLY_PLAN_STATUS_READY_WITH_WARNINGS
        if not warnings:
            status = STYLE_DNA_APPLY_PLAN_STATUS_READY
    else:
        status = STYLE_DNA_APPLY_PLAN_STATUS_WAITING_FOR_REVIEW

    ready_for_future_file_write = (
        status
        in {
            STYLE_DNA_APPLY_PLAN_STATUS_READY,
            STYLE_DNA_APPLY_PLAN_STATUS_READY_WITH_WARNINGS,
        }
        and bool(operations)
        and not blocking_reasons
    )

    return _report(
        job_id=job_id,
        profile=profile,
        source_review_status=review_status,
        status=status,
        warnings=warnings,
        blocking_reasons=blocking_reasons,
        before_snapshot=before_snapshot,
        operations=operations,
        skipped_operation_count=skipped_operation_count,
        ready_for_future_file_write=ready_for_future_file_write,
        source_review_gate_id=_source_review_gate_id(job),
        source_draft_id=_source_draft_id(job),
        recommendation=RECOMMENDATION_REVIEW_PLAN,
    )


def _build_operations(
    *,
    job_id: str,
    decisions: list[Any],
    proposals: list[Any],
    approved_decision_ids: set[str],
    has_blockers: bool,
) -> list[StyleDNAApplyOperation]:
    proposal_by_id = {
        _text(_dict(proposal).get("proposal_id")): _dict(proposal)
        for proposal in proposals
        if _text(_dict(proposal).get("proposal_id"))
    }

    operations: list[StyleDNAApplyOperation] = []
    operation_index = 1

    for decision in decisions:
        decision_data = _dict(decision)
        proposal_id = _text(decision_data.get("proposal_id"))
        decision_status = _text(decision_data.get("status"))

        if decision_status != PROPOSAL_DECISION_APPROVED:
            continue
        if proposal_id not in approved_decision_ids:
            continue

        proposal = proposal_by_id.get(proposal_id, {})
        parameter_name = _text(
            proposal.get("parameter_name")
            or decision_data.get("parameter_name")
        )
        current_value = proposal.get("current_value")
        proposed_value = proposal.get("proposed_value")
        delta = proposal.get("delta")

        operation_warnings: list[str] = []
        operation_blocking_reasons: list[str] = []

        if not parameter_name:
            operation_warnings.append(WARNING_EMPTY_PARAMETER_NAME)

        operation = StyleDNAApplyOperation(
            operation_id=f"{job_id}_style_dna_apply_op_{operation_index:03d}",
            proposal_id=proposal_id,
            parameter_name=parameter_name,
            current_value=current_value,
            proposed_value=proposed_value,
            delta=delta,
            operation_type=_operation_type(delta, proposed_value),
            approved=True,
            planned_only=True,
            safe_to_apply_later=not has_blockers and bool(parameter_name),
            warnings=operation_warnings,
            blocking_reasons=operation_blocking_reasons,
            metadata={
                **PHASE_METADATA,
                "reason": proposal.get("reason"),
                "source_tags": list(proposal.get("source_tags") or []),
                "confidence": proposal.get("confidence"),
                "decision_status": decision_status,
                "planned_from_proposal": True,
            },
        )
        operations.append(operation)
        operation_index += 1

    return operations


def _report(
    *,
    job_id: str,
    profile: str | None,
    source_review_status: str | None,
    status: str,
    warnings: list[str],
    blocking_reasons: list[str],
    before_snapshot: dict[str, Any],
    operations: list[StyleDNAApplyOperation],
    skipped_operation_count: int,
    ready_for_future_file_write: bool,
    source_review_gate_id: str | None,
    source_draft_id: str | None,
    recommendation: str,
) -> dict[str, Any]:
    clean_warnings = _unique(warnings)
    clean_blocking_reasons = _unique(blocking_reasons)
    after_preview = _build_after_preview(before_snapshot, operations)

    operation_count = len(operations)
    approved_operation_count = len(
        [operation for operation in operations if operation.approved]
    )

    plan = StyleDNAApplyPlan(
        plan_id=f"{job_id}_style_dna_apply_plan",
        job_id=job_id,
        profile=profile,
        source_review_gate_id=source_review_gate_id,
        source_draft_id=source_draft_id,
        operations=operations,
        operation_count=operation_count,
        approved_operation_count=approved_operation_count,
        skipped_operation_count=skipped_operation_count,
        before_snapshot=before_snapshot,
        after_preview=after_preview,
        planned_only=True,
        non_writing=True,
        safe_to_review=not clean_blocking_reasons,
        warnings=clean_warnings,
        blocking_reasons=clean_blocking_reasons,
        metadata={
            **PHASE_METADATA,
            "operation_ids": [operation.operation_id for operation in operations],
        },
    )

    report = StyleDNAApplyPlanReport(
        report_id=f"{job_id}_style_dna_apply_plan_report",
        job_id=job_id,
        status=status,
        profile=profile,
        source_review_status=source_review_status,
        plan=plan,
        operation_count=operation_count,
        approved_operation_count=approved_operation_count,
        skipped_operation_count=skipped_operation_count,
        ready_for_future_file_write=bool(ready_for_future_file_write),
        can_write_style_dna=False,
        can_apply_style_dna=False,
        can_update_profile=False,
        can_change_cutting_rules=False,
        can_modify_timeline=False,
        can_trigger_render=False,
        can_publish=False,
        warnings=clean_warnings,
        blocking_reasons=clean_blocking_reasons,
        recommendation=recommendation,
        created_at=utc_now_iso(),
        metadata={
            **PHASE_METADATA,
            "allow_file_write_ignored": True,
            "operation_count": operation_count,
            "approved_operation_count": approved_operation_count,
            "skipped_operation_count": skipped_operation_count,
        },
    )
    return report.to_dict()


def _build_after_preview(
    before_snapshot: dict[str, Any],
    operations: list[StyleDNAApplyOperation],
) -> dict[str, Any]:
    after_preview = deepcopy(before_snapshot)
    for operation in operations:
        if not operation.parameter_name:
            continue
        after_preview[operation.parameter_name] = operation.proposed_value
    return after_preview


def _approved_proposal_ids(decisions: list[Any]) -> set[str]:
    approved: set[str] = set()
    for decision in decisions:
        decision_data = _dict(decision)
        if _text(decision_data.get("status")) == PROPOSAL_DECISION_APPROVED:
            proposal_id = _text(decision_data.get("proposal_id"))
            if proposal_id:
                approved.add(proposal_id)
    return approved


def _operation_type(delta: Any, proposed_value: Any) -> str:
    if isinstance(delta, (int, float)) and not isinstance(delta, bool):
        if delta == 0:
            return OPERATION_TYPE_STABILIZE_VALUE
        return OPERATION_TYPE_INCREMENT_VALUE
    if isinstance(proposed_value, bool):
        return OPERATION_TYPE_MARK_REVIEW_REQUIRED
    if proposed_value is None:
        return OPERATION_TYPE_MANUAL_REVIEW_REQUIRED
    return OPERATION_TYPE_SET_VALUE


def _source_review_gate_id(job: Any) -> str | None:
    report = _dict(_get(job, "style_dna_review_gate_report"))
    gate = _dict(_get(job, "style_dna_review_gate"))
    return _text(report.get("report_id") or gate.get("gate_id")) or None


def _source_draft_id(job: Any) -> str | None:
    draft = _dict(_get(job, "style_dna_update_draft"))
    report = _dict(_get(job, "style_dna_feedback_update_report"))
    return _text(draft.get("draft_id") or report.get("draft_id")) or None


def _resolve_profile(job: Any) -> str | None:
    explicit_profile = _text(_get(job, "style_dna_profile_name"))
    if explicit_profile:
        return explicit_profile

    update_report = _dict(_get(job, "style_dna_feedback_update_report"))
    review_report = _dict(_get(job, "style_dna_review_gate_report"))

    profile = _text(
        update_report.get("profile")
        or review_report.get("profile")
        or _get(job, "profile")
    )
    return profile or None


def _get(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    return []


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = _text(item)
        if text and text not in result:
            result.append(text)
    return result


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in result:
            result.append(text)
    return result
