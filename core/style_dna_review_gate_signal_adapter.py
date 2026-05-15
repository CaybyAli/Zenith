from __future__ import annotations

from typing import Any


STYLE_DNA_REVIEW_GATE_SIGNAL_SOURCE = "style_dna_review_gate"
STYLE_DNA_REVIEW_GATE_ACTION_HINT = "review_style_dna_draft_approval_gate"

SIGNAL_METADATA = {
    "style_dna_review_gate_only": True,
    "human_approval_gate_only": True,
    "no_style_dna_file_write_in_2b_61": True,
    "no_profile_change_in_2b_61": True,
    "no_cutting_rule_activation_in_2b_61": True,
    "no_timeline_modify_in_2b_61": True,
    "no_render_trigger_in_2b_61": True,
    "no_publish_in_2b_61": True,
}


def build_style_dna_review_gate_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="style_dna_review_pending_review",
                severity="info",
                message="Style-DNA Review Gate wartet auf Review-Daten.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "") or "").lower()

    if status == "style_dna_review_pending_review":
        signals.append(
            _signal(
                signal_type="style_dna_review_pending_review",
                severity="info",
                message="Style-DNA Draft wartet auf menschliche Pruefung.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_review_approved":
        signals.append(
            _signal(
                signal_type="style_dna_review_approved",
                severity="info",
                message="Style-DNA Draft wurde menschlich geprueft.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_review_rejected":
        signals.append(
            _signal(
                signal_type="style_dna_review_rejected",
                severity="warning",
                message="Style-DNA Draft wurde abgelehnt.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_review_needs_manual_changes":
        signals.append(
            _signal(
                signal_type="style_dna_review_needs_manual_changes",
                severity="warning",
                message="Style-DNA Draft braucht manuelle Aenderungen.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_review_blocked":
        signals.append(
            _signal(
                signal_type="style_dna_review_blocked",
                severity="blocking",
                message="Style-DNA Review Gate ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="style_dna_review_failed",
                severity="warning",
                message="Style-DNA Review Gate hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    gate = report.get("gate") or {}
    proposal_decisions = list(gate.get("proposal_decisions") or [])
    for decision in proposal_decisions:
        decision_status = str(decision.get("status", "") or "").lower()
        proposal_id = decision.get("proposal_id")
        if decision_status == "approved":
            signals.append(
                _signal(
                    signal_type="style_dna_review_proposal_approved",
                    severity="info",
                    message="Style-DNA Vorschlag wurde fuer spaeter freigegeben.",
                    metadata={"proposal_id": proposal_id},
                )
            )
        elif decision_status == "rejected":
            signals.append(
                _signal(
                    signal_type="style_dna_review_proposal_rejected",
                    severity="warning",
                    message="Style-DNA Vorschlag wurde abgelehnt.",
                    metadata={"proposal_id": proposal_id},
                )
            )

    if bool(report.get("ready_for_later_apply", False)):
        signals.append(
            _signal(
                signal_type="style_dna_review_ready_for_later_apply",
                severity="info",
                message="Style-DNA Review ist fuer spaetere Anwendung bereit.",
                metadata={"ready_for_later_apply": True},
            )
        )

    signals.append(
        _signal(
            signal_type="style_dna_apply_still_not_allowed",
            severity="info",
            message="2B-61 darf Style-DNA noch nicht anwenden.",
            metadata={"can_apply_style_dna": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_file_write_still_not_allowed",
            severity="info",
            message="2B-61 darf keine Style-DNA-Datei speichern.",
            metadata={"can_write_style_dna": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_profile_change_still_not_allowed",
            severity="info",
            message="2B-61 darf kein Profil aendern.",
            metadata={"can_update_profile": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_timeline_modify_still_not_allowed",
            severity="info",
            message="2B-61 darf keine Timeline aendern.",
            metadata={"can_modify_timeline": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_render_trigger_still_not_allowed",
            severity="info",
            message="2B-61 darf keinen Render starten.",
            metadata={"can_trigger_render": False},
        )
    )

    return signals


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("style_dna_review_gate_report") or {}
    else:
        report = getattr(job, "style_dna_review_gate_report", {}) or {}
    return report if isinstance(report, dict) else {}


def _signal(
    *,
    signal_type: str,
    severity: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload_metadata = dict(SIGNAL_METADATA)
    payload_metadata.update(metadata or {})
    return {
        "signal_type": signal_type,
        "source": STYLE_DNA_REVIEW_GATE_SIGNAL_SOURCE,
        "severity": severity,
        "message": message,
        "action_hint": STYLE_DNA_REVIEW_GATE_ACTION_HINT,
        "metadata": payload_metadata,
    }
