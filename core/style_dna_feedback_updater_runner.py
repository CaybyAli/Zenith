from __future__ import annotations

from typing import Any

from core.style_dna_feedback_updater import build_style_dna_feedback_update_report


STYLE_DNA_FEEDBACK_UPDATE_JOB_FIELDS = [
    "style_dna_feedback_update_report",
    "style_dna_feedback_update_status",
    "style_dna_update_draft",
    "style_dna_update_proposals",
    "style_dna_update_proposal_count",
    "style_dna_update_confidence",
    "style_dna_update_overfitting_risk",
    "style_dna_update_ready_for_human_review",
    "style_dna_update_ready_for_later_apply",
    "style_dna_update_can_write_style_dna",
    "style_dna_update_can_update_profile",
    "style_dna_update_can_change_cutting_rules",
    "style_dna_update_can_modify_timeline",
    "style_dna_update_can_trigger_render",
    "style_dna_update_can_publish",
    "style_dna_update_warnings",
    "style_dna_update_blocking_reasons",
    "style_dna_update_recommendation",
]


class StyleDNAFeedbackUpdaterRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report = build_style_dna_feedback_update_report(job)
        payload = report.to_dict()

        draft = payload.get("draft") or {}
        proposals = list(draft.get("proposals") or [])

        _assign(job, "style_dna_feedback_update_report", payload)
        _assign(job, "style_dna_feedback_update_status", payload.get("status"))
        _assign(job, "style_dna_update_draft", draft)
        _assign(job, "style_dna_update_proposals", proposals)
        _assign(job, "style_dna_update_proposal_count", payload.get("proposal_count", 0))
        _assign(job, "style_dna_update_confidence", payload.get("confidence", 0.0))
        _assign(
            job,
            "style_dna_update_overfitting_risk",
            draft.get("overfitting_risk") if draft else None,
        )
        _assign(
            job,
            "style_dna_update_ready_for_human_review",
            payload.get("ready_for_human_review", False),
        )
        _assign(
            job,
            "style_dna_update_ready_for_later_apply",
            payload.get("ready_for_later_apply", False),
        )

        _assign(job, "style_dna_update_can_write_style_dna", False)
        _assign(job, "style_dna_update_can_update_profile", False)
        _assign(job, "style_dna_update_can_change_cutting_rules", False)
        _assign(job, "style_dna_update_can_modify_timeline", False)
        _assign(job, "style_dna_update_can_trigger_render", False)
        _assign(job, "style_dna_update_can_publish", False)

        _assign(job, "style_dna_update_warnings", payload.get("warnings", []))
        _assign(
            job,
            "style_dna_update_blocking_reasons",
            payload.get("blocking_reasons", []),
        )
        _assign(job, "style_dna_update_recommendation", payload.get("recommendation"))

        return payload


def run_style_dna_feedback_updater_for_job(job: Any) -> dict[str, Any]:
    return StyleDNAFeedbackUpdaterRunner().run(job)


def _assign(job: Any, name: str, value: Any) -> None:
    if isinstance(job, dict):
        job[name] = value
        return
    setattr(job, name, value)
