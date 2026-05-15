from __future__ import annotations

from typing import Any

from models.style_dna_review_gate import (
    PHASE_METADATA,
    PROPOSAL_DECISION_APPROVED,
    PROPOSAL_DECISION_NEEDS_CHANGES,
    PROPOSAL_DECISION_PENDING,
    PROPOSAL_DECISION_REJECTED,
    STYLE_DNA_REVIEW_STATUS_APPROVED,
    STYLE_DNA_REVIEW_STATUS_BLOCKED,
    STYLE_DNA_REVIEW_STATUS_FAILED,
    STYLE_DNA_REVIEW_STATUS_NEEDS_CHANGES,
    STYLE_DNA_REVIEW_STATUS_PENDING,
    STYLE_DNA_REVIEW_STATUS_REJECTED,
    StyleDNAProposalReviewDecision,
    StyleDNAReviewGate,
    StyleDNAReviewGateReport,
    utc_now_iso,
)


ALLOWED_REQUESTED_STATUSES = {
    "pending_review",
    "approved",
    "rejected",
    "needs_manual_changes",
}

SOURCE_BLOCKED_STATUSES = {
    "style_dna_update_blocked",
    "style_dna_update_failed",
    "blocked",
    "failed",
}

UNSAFE_SOURCE_FLAG_NAMES = [
    "style_dna_update_can_write_style_dna",
    "style_dna_update_can_update_profile",
    "style_dna_update_can_change_cutting_rules",
    "style_dna_update_can_modify_timeline",
    "style_dna_update_can_trigger_render",
    "style_dna_update_can_publish",
]


def build_style_dna_review_gate_report(job: Any) -> StyleDNAReviewGateReport:
    job_id = _text(_get(job, "job_id"))
    warnings: list[str] = []
    blocking_reasons: list[str] = []

    source_report = _dict(_get(job, "style_dna_feedback_update_report"))
    source_update_status = _text(_get(job, "style_dna_feedback_update_status"))
    if not source_update_status and source_report:
        source_update_status = _text(source_report.get("status"))

    source_draft = _dict(_get(job, "style_dna_update_draft"))
    if not source_draft and source_report:
        source_draft = _dict(source_report.get("draft"))

    proposals = _list(_get(job, "style_dna_update_proposals"))
    if not proposals and source_draft:
        proposals = _list(source_draft.get("proposals"))

    source_proposal_count = int(
        _get(job, "style_dna_update_proposal_count")
        or source_report.get("proposal_count")
        or len(proposals)
        or 0
    )

    requested_status = _normalize_requested_status(
        _get(job, "style_dna_review_requested_status")
    )
    reviewed_by = _text(_get(job, "style_dna_reviewed_by"))
    review_comment = _text(_get(job, "style_dna_review_comment"))
    manual_change_notes = _list(_get(job, "style_dna_review_manual_change_notes"))

    approved_ids = set(_text_list(_get(job, "style_dna_review_approved_proposal_ids")))
    rejected_ids = set(_text_list(_get(job, "style_dna_review_rejected_proposal_ids")))

    if not source_update_status:
        blocking_reasons.append("style_dna_feedback_update_status_missing")

    if source_update_status in SOURCE_BLOCKED_STATUSES:
        blocking_reasons.append("style_dna_feedback_update_source_blocked_or_failed")

    if not source_draft:
        blocking_reasons.append("style_dna_update_draft_missing")

    if source_proposal_count <= 0:
        blocking_reasons.append("style_dna_update_proposal_count_missing")

    if not bool(_get(job, "style_dna_update_ready_for_human_review")):
        blocking_reasons.append("style_dna_update_not_ready_for_human_review")

    source_blocking_reasons = _list(_get(job, "style_dna_update_blocking_reasons"))
    if not source_blocking_reasons and source_report:
        source_blocking_reasons = _list(source_report.get("blocking_reasons"))
    if source_blocking_reasons:
        blocking_reasons.append("source_style_dna_update_has_blocking_reasons")

    for flag_name in UNSAFE_SOURCE_FLAG_NAMES:
        if bool(_get(job, flag_name)):
            blocking_reasons.append(f"unsafe_source_flag_true:{flag_name}")

    if bool(_get(job, "style_dna_update_allow_file_write")):
        warnings.append("style_dna_file_write_still_not_allowed_in_2b_61")

    if requested_status not in ALLOWED_REQUESTED_STATUSES:
        warnings.append("style_dna_review_requested_status_unknown")
        blocking_reasons.append("style_dna_review_requested_status_unknown")

    if requested_status == "approved" and not reviewed_by:
        blocking_reasons.append("style_dna_review_approved_requires_reviewed_by")

    if requested_status == "rejected" and not reviewed_by:
        blocking_reasons.append("style_dna_review_rejected_requires_reviewed_by")

    if requested_status == "needs_manual_changes" and not reviewed_by:
        warnings.append("style_dna_review_needs_manual_changes_reviewed_by_recommended")

    if (
        requested_status == "needs_manual_changes"
        and not review_comment
        and not manual_change_notes
    ):
        warnings.append("style_dna_review_manual_change_notes_recommended")

    if blocking_reasons:
        status = STYLE_DNA_REVIEW_STATUS_BLOCKED
        review_required = True
        ready_for_later_apply = False
        recommendation = "fix_style_dna_review_gate_blockers"
        decision_status = PROPOSAL_DECISION_PENDING
    elif requested_status == "approved":
        status = STYLE_DNA_REVIEW_STATUS_APPROVED
        review_required = False
        ready_for_later_apply = True
        recommendation = "style_dna_draft_human_approved_for_later_apply_only"
        decision_status = PROPOSAL_DECISION_APPROVED
    elif requested_status == "rejected":
        status = STYLE_DNA_REVIEW_STATUS_REJECTED
        review_required = False
        ready_for_later_apply = False
        recommendation = "style_dna_draft_rejected"
        decision_status = PROPOSAL_DECISION_REJECTED
    elif requested_status == "needs_manual_changes":
        status = STYLE_DNA_REVIEW_STATUS_NEEDS_CHANGES
        review_required = True
        ready_for_later_apply = False
        recommendation = "style_dna_draft_needs_manual_changes"
        decision_status = PROPOSAL_DECISION_NEEDS_CHANGES
    else:
        status = STYLE_DNA_REVIEW_STATUS_PENDING
        review_required = True
        ready_for_later_apply = False
        recommendation = "review_style_dna_draft_approval_gate"
        decision_status = PROPOSAL_DECISION_PENDING

    proposal_decisions = _build_proposal_decisions(
        proposals=proposals,
        requested_status=requested_status,
        default_status=decision_status,
        reviewed_by=reviewed_by,
        review_comment=review_comment,
        approved_ids=approved_ids,
        rejected_ids=rejected_ids,
        blocked=bool(blocking_reasons),
    )

    approved_count = _count_decisions(proposal_decisions, PROPOSAL_DECISION_APPROVED)
    rejected_count = _count_decisions(proposal_decisions, PROPOSAL_DECISION_REJECTED)
    needs_changes_count = _count_decisions(
        proposal_decisions,
        PROPOSAL_DECISION_NEEDS_CHANGES,
    )

    source_draft_id = _text(source_draft.get("draft_id")) if source_draft else None
    source_update_report_id = (
        _text(source_report.get("report_id")) if source_report else None
    )

    gate = StyleDNAReviewGate(
        gate_id=f"style_dna_review_gate_{job_id or 'unknown_job'}",
        job_id=job_id,
        source_draft_id=source_draft_id,
        source_update_report_id=source_update_report_id,
        requested_status=requested_status,
        status=status,
        reviewed_by=reviewed_by,
        review_comment=review_comment,
        proposal_decisions=[decision.to_dict() for decision in proposal_decisions],
        approved_proposal_count=approved_count,
        rejected_proposal_count=rejected_count,
        needs_changes_count=needs_changes_count,
        ready_for_later_apply=ready_for_later_apply,
        can_apply_style_dna=False,
        can_write_style_dna=False,
        can_update_profile=False,
        can_change_cutting_rules=False,
        can_modify_timeline=False,
        can_trigger_render=False,
        can_publish=False,
        warnings=_unique(warnings),
        blocking_reasons=_unique(blocking_reasons),
        recommendation=recommendation,
        metadata=dict(PHASE_METADATA),
    )

    return StyleDNAReviewGateReport(
        report_id=f"style_dna_review_gate_report_{job_id or 'unknown_job'}",
        job_id=job_id,
        status=status,
        gate=gate.to_dict(),
        source_update_status=source_update_status,
        source_proposal_count=source_proposal_count,
        review_required=review_required,
        ready_for_later_apply=ready_for_later_apply,
        can_apply_style_dna=False,
        can_write_style_dna=False,
        can_update_profile=False,
        can_change_cutting_rules=False,
        can_modify_timeline=False,
        can_trigger_render=False,
        can_publish=False,
        warnings=_unique(warnings),
        blocking_reasons=_unique(blocking_reasons),
        recommendation=recommendation,
        created_at=utc_now_iso(),
        metadata=dict(PHASE_METADATA),
    )


def _build_proposal_decisions(
    *,
    proposals: list[Any],
    requested_status: str,
    default_status: str,
    reviewed_by: str | None,
    review_comment: str | None,
    approved_ids: set[str],
    rejected_ids: set[str],
    blocked: bool,
) -> list[StyleDNAProposalReviewDecision]:
    decisions: list[StyleDNAProposalReviewDecision] = []

    for index, proposal in enumerate(proposals, start=1):
        proposal_data = _dict(proposal)
        proposal_id = _text(proposal_data.get("proposal_id")) or f"proposal_{index}"

        status = default_status
        if blocked:
            status = PROPOSAL_DECISION_PENDING
        elif requested_status == "approved":
            if approved_ids:
                status = (
                    PROPOSAL_DECISION_APPROVED
                    if proposal_id in approved_ids
                    else PROPOSAL_DECISION_PENDING
                )
            if proposal_id in rejected_ids:
                status = PROPOSAL_DECISION_REJECTED
        elif requested_status == "rejected":
            if rejected_ids:
                status = (
                    PROPOSAL_DECISION_REJECTED
                    if proposal_id in rejected_ids
                    else PROPOSAL_DECISION_PENDING
                )
            else:
                status = PROPOSAL_DECISION_REJECTED
            if proposal_id in approved_ids:
                status = PROPOSAL_DECISION_APPROVED
        elif requested_status == "needs_manual_changes":
            status = PROPOSAL_DECISION_NEEDS_CHANGES

        decisions.append(
            StyleDNAProposalReviewDecision(
                decision_id=f"style_dna_review_decision_{index}",
                proposal_id=proposal_id,
                status=status,
                reviewed_by=reviewed_by,
                comment=review_comment,
                safe_for_later_apply=bool(status == PROPOSAL_DECISION_APPROVED),
                warnings=[],
                blocking_reasons=[],
                metadata={
                    **PHASE_METADATA,
                    "source_proposal_index": index,
                    "human_review_decision_only": True,
                },
            )
        )

    return decisions


def _normalize_requested_status(value: Any) -> str:
    text = _text(value)
    if not text:
        return "pending_review"
    return text.lower()


def _count_decisions(
    decisions: list[StyleDNAProposalReviewDecision],
    status: str,
) -> int:
    return sum(1 for decision in decisions if decision.status == status)


def _get(source: Any, name: str) -> Any:
    if isinstance(source, dict):
        return source.get(name)
    return getattr(source, name, None)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in (_text(entry) for entry in value) if item]


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
