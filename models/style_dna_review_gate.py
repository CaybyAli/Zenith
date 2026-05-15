from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


STYLE_DNA_REVIEW_STATUS_PENDING = "style_dna_review_pending_review"
STYLE_DNA_REVIEW_STATUS_APPROVED = "style_dna_review_approved"
STYLE_DNA_REVIEW_STATUS_REJECTED = "style_dna_review_rejected"
STYLE_DNA_REVIEW_STATUS_NEEDS_CHANGES = "style_dna_review_needs_manual_changes"
STYLE_DNA_REVIEW_STATUS_BLOCKED = "style_dna_review_blocked"
STYLE_DNA_REVIEW_STATUS_FAILED = "style_dna_review_failed"

PROPOSAL_DECISION_PENDING = "pending_review"
PROPOSAL_DECISION_APPROVED = "approved"
PROPOSAL_DECISION_REJECTED = "rejected"
PROPOSAL_DECISION_NEEDS_CHANGES = "needs_manual_changes"

PHASE_METADATA = {
    "phase": "2B-61",
    "block": "block9_learning_feedback",
    "style_dna_review_gate_only": True,
    "human_approval_gate_only": True,
    "no_style_dna_file_write_in_2b_61": True,
    "no_profile_change_in_2b_61": True,
    "no_cutting_rule_activation_in_2b_61": True,
    "no_timeline_modify_in_2b_61": True,
    "no_render_trigger_in_2b_61": True,
    "no_publish_in_2b_61": True,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StyleDNAProposalReviewDecision:
    decision_id: str
    proposal_id: str
    status: str = PROPOSAL_DECISION_PENDING
    reviewed_by: str | None = None
    comment: str | None = None
    safe_for_later_apply: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["metadata"] = {**PHASE_METADATA, **dict(self.metadata or {})}
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StyleDNAProposalReviewDecision":
        return cls(
            decision_id=str(data.get("decision_id") or ""),
            proposal_id=str(data.get("proposal_id") or ""),
            status=str(data.get("status") or PROPOSAL_DECISION_PENDING),
            reviewed_by=data.get("reviewed_by"),
            comment=data.get("comment"),
            safe_for_later_apply=bool(data.get("safe_for_later_apply", False)),
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class StyleDNAReviewGate:
    gate_id: str
    job_id: str | None
    source_draft_id: str | None
    source_update_report_id: str | None
    requested_status: str = "pending_review"
    status: str = STYLE_DNA_REVIEW_STATUS_PENDING
    reviewed_by: str | None = None
    review_comment: str | None = None
    proposal_decisions: list[dict[str, Any]] = field(default_factory=list)
    approved_proposal_count: int = 0
    rejected_proposal_count: int = 0
    needs_changes_count: int = 0
    ready_for_later_apply: bool = False
    can_apply_style_dna: bool = False
    can_write_style_dna: bool = False
    can_update_profile: bool = False
    can_change_cutting_rules: bool = False
    can_modify_timeline: bool = False
    can_trigger_render: bool = False
    can_publish: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str = "review_style_dna_draft_approval_gate"
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["can_apply_style_dna"] = False
        payload["can_write_style_dna"] = False
        payload["can_update_profile"] = False
        payload["can_change_cutting_rules"] = False
        payload["can_modify_timeline"] = False
        payload["can_trigger_render"] = False
        payload["can_publish"] = False
        payload["metadata"] = {**PHASE_METADATA, **dict(self.metadata or {})}
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StyleDNAReviewGate":
        return cls(
            gate_id=str(data.get("gate_id") or ""),
            job_id=data.get("job_id"),
            source_draft_id=data.get("source_draft_id"),
            source_update_report_id=data.get("source_update_report_id"),
            requested_status=str(data.get("requested_status") or "pending_review"),
            status=str(data.get("status") or STYLE_DNA_REVIEW_STATUS_PENDING),
            reviewed_by=data.get("reviewed_by"),
            review_comment=data.get("review_comment"),
            proposal_decisions=list(data.get("proposal_decisions") or []),
            approved_proposal_count=int(data.get("approved_proposal_count", 0) or 0),
            rejected_proposal_count=int(data.get("rejected_proposal_count", 0) or 0),
            needs_changes_count=int(data.get("needs_changes_count", 0) or 0),
            ready_for_later_apply=bool(data.get("ready_for_later_apply", False)),
            can_apply_style_dna=False,
            can_write_style_dna=False,
            can_update_profile=False,
            can_change_cutting_rules=False,
            can_modify_timeline=False,
            can_trigger_render=False,
            can_publish=False,
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            recommendation=str(
                data.get("recommendation") or "review_style_dna_draft_approval_gate"
            ),
            created_at=str(data.get("created_at") or utc_now_iso()),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class StyleDNAReviewGateReport:
    report_id: str
    job_id: str | None
    status: str
    gate: dict[str, Any] | None = None
    source_update_status: str | None = None
    source_proposal_count: int = 0
    review_required: bool = True
    ready_for_later_apply: bool = False
    can_apply_style_dna: bool = False
    can_write_style_dna: bool = False
    can_update_profile: bool = False
    can_change_cutting_rules: bool = False
    can_modify_timeline: bool = False
    can_trigger_render: bool = False
    can_publish: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str = "review_style_dna_draft_approval_gate"
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["can_apply_style_dna"] = False
        payload["can_write_style_dna"] = False
        payload["can_update_profile"] = False
        payload["can_change_cutting_rules"] = False
        payload["can_modify_timeline"] = False
        payload["can_trigger_render"] = False
        payload["can_publish"] = False
        payload["metadata"] = {**PHASE_METADATA, **dict(self.metadata or {})}
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StyleDNAReviewGateReport":
        return cls(
            report_id=str(data.get("report_id") or ""),
            job_id=data.get("job_id"),
            status=str(data.get("status") or STYLE_DNA_REVIEW_STATUS_PENDING),
            gate=dict(data.get("gate") or {}),
            source_update_status=data.get("source_update_status"),
            source_proposal_count=int(data.get("source_proposal_count", 0) or 0),
            review_required=bool(data.get("review_required", True)),
            ready_for_later_apply=bool(data.get("ready_for_later_apply", False)),
            can_apply_style_dna=False,
            can_write_style_dna=False,
            can_update_profile=False,
            can_change_cutting_rules=False,
            can_modify_timeline=False,
            can_trigger_render=False,
            can_publish=False,
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            recommendation=str(
                data.get("recommendation") or "review_style_dna_draft_approval_gate"
            ),
            created_at=str(data.get("created_at") or utc_now_iso()),
            metadata=dict(data.get("metadata") or {}),
        )
