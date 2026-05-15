from __future__ import annotations

from typing import Any


STYLE_DNA_FEEDBACK_UPDATE_SIGNAL_SOURCE = "style_dna_feedback_update"
STYLE_DNA_FEEDBACK_UPDATE_ACTION_HINT = "review_style_dna_update_draft"

SIGNAL_METADATA = {
    "style_dna_update_proposal_only": True,
    "style_dna_draft_only": True,
    "no_style_dna_file_write_in_2b_60": True,
    "no_profile_change_in_2b_60": True,
    "no_cutting_rule_activation_in_2b_60": True,
    "no_timeline_modify_in_2b_60": True,
    "no_render_trigger_in_2b_60": True,
    "no_publish_in_2b_60": True,
}


def build_style_dna_feedback_update_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="style_dna_update_waiting_for_feedback",
                severity="info",
                message="Style-DNA Update wartet auf Feedback-Daten.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "") or "").lower()

    if status == "style_dna_update_waiting_for_feedback":
        signals.append(
            _signal(
                signal_type="style_dna_update_waiting_for_feedback",
                severity="info",
                message="Style-DNA Update wartet auf nutzbares Feedback.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_update_draft_ready":
        signals.append(
            _signal(
                signal_type="style_dna_update_draft_ready",
                severity="info",
                message="Style-DNA Update Draft ist bereit.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_update_draft_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="style_dna_update_draft_ready_with_warnings",
                severity="warning",
                message="Style-DNA Update Draft ist bereit, aber Warnungen muessen geprueft werden.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_update_blocked":
        signals.append(
            _signal(
                signal_type="style_dna_update_blocked",
                severity="blocking",
                message="Style-DNA Update ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="style_dna_update_failed",
                severity="warning",
                message="Style-DNA Update hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    proposal_count = int(report.get("proposal_count", 0) or 0)
    if proposal_count:
        signals.append(
            _signal(
                signal_type="style_dna_proposal_created",
                severity="info",
                message="Style-DNA Parameter-Vorschlaege wurden erstellt.",
                metadata={"proposal_count": proposal_count},
            )
        )

    draft = report.get("draft") or {}
    overfitting_risk = str(draft.get("overfitting_risk", "") or "").lower()
    if overfitting_risk in {"medium", "high"}:
        signals.append(
            _signal(
                signal_type="style_dna_overfitting_risk_detected",
                severity="warning" if overfitting_risk == "medium" else "blocking",
                message="Style-DNA Draft hat Overfitting-Risiko.",
                metadata={"overfitting_risk": overfitting_risk},
            )
        )

    if bool(report.get("ready_for_human_review", False)):
        signals.append(
            _signal(
                signal_type="style_dna_ready_for_human_review",
                severity="info",
                message="Style-DNA Draft ist bereit fuer menschliche Pruefung.",
                metadata={"ready_for_human_review": True},
            )
        )

    if bool(report.get("ready_for_later_apply", False)):
        signals.append(
            _signal(
                signal_type="style_dna_ready_for_later_apply",
                severity="info",
                message="Style-DNA Draft ist spaeter anwendbar, aber noch nicht automatisch.",
                metadata={"ready_for_later_apply": True},
            )
        )

    signals.append(
        _signal(
            signal_type="style_dna_file_write_still_not_allowed",
            severity="info",
            message="2B-60 darf keine Style-DNA-Datei schreiben.",
            metadata={"can_write_style_dna": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_profile_change_still_not_allowed",
            severity="info",
            message="2B-60 darf kein Profil aendern.",
            metadata={"can_update_profile": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_timeline_modify_still_not_allowed",
            severity="info",
            message="2B-60 darf keine Timeline aendern.",
            metadata={"can_modify_timeline": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_render_trigger_still_not_allowed",
            severity="info",
            message="2B-60 darf keinen Render starten.",
            metadata={"can_trigger_render": False},
        )
    )

    return signals


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("style_dna_feedback_update_report") or {}
    else:
        report = getattr(job, "style_dna_feedback_update_report", {}) or {}
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
        "source": STYLE_DNA_FEEDBACK_UPDATE_SIGNAL_SOURCE,
        "severity": severity,
        "message": message,
        "action_hint": STYLE_DNA_FEEDBACK_UPDATE_ACTION_HINT,
        "metadata": payload_metadata,
    }
