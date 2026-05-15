from __future__ import annotations

from typing import Any

from core.style_dna_review_gate import build_style_dna_review_gate_report


STYLE_DNA_REVIEW_GATE_JOB_FIELDS = [
    "style_dna_review_gate_report",
    "style_dna_review_gate",
    "style_dna_review_status",
    "style_dna_review_requested_status",
    "style_dna_reviewed_by",
    "style_dna_review_comment",
    "style_dna_review_requested_at",
    "style_dna_review_proposal_decisions",
    "style_dna_review_approved_proposal_count",
    "style_dna_review_rejected_proposal_count",
    "style_dna_review_needs_changes_count",
    "style_dna_review_required",
    "style_dna_review_ready_for_later_apply",
    "style_dna_review_can_apply_style_dna",
    "style_dna_review_can_write_style_dna",
    "style_dna_review_can_update_profile",
    "style_dna_review_can_change_cutting_rules",
    "style_dna_review_can_modify_timeline",
    "style_dna_review_can_trigger_render",
    "style_dna_review_can_publish",
    "style_dna_review_warnings",
    "style_dna_review_blocking_reasons",
    "style_dna_review_recommendation",
]


class StyleDNAReviewGateRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report = build_style_dna_review_gate_report(job)
        payload = report.to_dict()
        gate = payload.get("gate") or {}

        _assign(job, "style_dna_review_gate_report", payload)
        _assign(job, "style_dna_review_gate", gate)
        _assign(job, "style_dna_review_status", payload.get("status"))
        _assign(
            job,
            "style_dna_review_requested_status",
            gate.get("requested_status", "pending_review"),
        )
        _assign(job, "style_dna_reviewed_by", gate.get("reviewed_by"))
        _assign(job, "style_dna_review_comment", gate.get("review_comment"))
        _assign(job, "style_dna_review_requested_at", gate.get("created_at"))
        _assign(
            job,
            "style_dna_review_proposal_decisions",
            list(gate.get("proposal_decisions") or []),
        )
        _assign(
            job,
            "style_dna_review_approved_proposal_count",
            int(gate.get("approved_proposal_count", 0) or 0),
        )
        _assign(
            job,
            "style_dna_review_rejected_proposal_count",
            int(gate.get("rejected_proposal_count", 0) or 0),
        )
        _assign(
            job,
            "style_dna_review_needs_changes_count",
            int(gate.get("needs_changes_count", 0) or 0),
        )
        _assign(job, "style_dna_review_required", payload.get("review_required", True))
        _assign(
            job,
            "style_dna_review_ready_for_later_apply",
            payload.get("ready_for_later_apply", False),
        )

        _assign(job, "style_dna_review_can_apply_style_dna", False)
        _assign(job, "style_dna_review_can_write_style_dna", False)
        _assign(job, "style_dna_review_can_update_profile", False)
        _assign(job, "style_dna_review_can_change_cutting_rules", False)
        _assign(job, "style_dna_review_can_modify_timeline", False)
        _assign(job, "style_dna_review_can_trigger_render", False)
        _assign(job, "style_dna_review_can_publish", False)

        _assign(job, "style_dna_review_warnings", payload.get("warnings", []))
        _assign(
            job,
            "style_dna_review_blocking_reasons",
            payload.get("blocking_reasons", []),
        )
        _assign(job, "style_dna_review_recommendation", payload.get("recommendation"))

        return payload


def run_style_dna_review_gate_for_job(job: Any) -> dict[str, Any]:
    return StyleDNAReviewGateRunner().run(job)


def _assign(job: Any, name: str, value: Any) -> None:
    if isinstance(job, dict):
        job[name] = value
        return
    setattr(job, name, value)
