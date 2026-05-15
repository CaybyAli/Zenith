from __future__ import annotations

from typing import Any


STYLE_DNA_PERSISTENCE_GATE_SIGNAL_SOURCE = "style_dna_persistence_gate"
STYLE_DNA_PERSISTENCE_GATE_ACTION_HINT = "review_style_dna_persistence_gate"

SIGNAL_METADATA = {
    "style_dna_persistence_gate_only": True,
    "final_human_write_permission_gate": True,
    "write_intent_only": True,
    "no_style_dna_file_write_in_2b_63": True,
    "no_backup_write_in_2b_63": True,
    "no_profile_change_in_2b_63": True,
    "no_cutting_rule_activation_in_2b_63": True,
    "no_timeline_modify_in_2b_63": True,
    "no_render_trigger_in_2b_63": True,
    "no_publish_in_2b_63": True,
}


def build_style_dna_persistence_gate_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="style_dna_persistence_pending_write_review",
                severity="info",
                message="Style-DNA Persistence Gate wartet auf Apply-Plan-Daten.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "") or "").lower()

    if status == "style_dna_persistence_pending_write_review":
        signals.append(
            _signal(
                signal_type="style_dna_persistence_pending_write_review",
                severity="info",
                message="Style-DNA Persistence Gate wartet auf finale Schreibfreigabe.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_persistence_approved_write":
        signals.append(
            _signal(
                signal_type="style_dna_persistence_approved_write",
                severity="info",
                message="Style-DNA Schreibfreigabe wurde nur als Zukunfts-Erlaubnis vorgemerkt.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_persistence_rejected_write":
        signals.append(
            _signal(
                signal_type="style_dna_persistence_rejected_write",
                severity="warning",
                message="Style-DNA Schreibfreigabe wurde abgelehnt.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_persistence_needs_manual_changes":
        signals.append(
            _signal(
                signal_type="style_dna_persistence_needs_manual_changes",
                severity="warning",
                message="Style-DNA Persistence Gate braucht manuelle Anpassungen.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_persistence_blocked":
        signals.append(
            _signal(
                signal_type="style_dna_persistence_blocked",
                severity="blocking",
                message="Style-DNA Persistence Gate ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="style_dna_persistence_failed",
                severity="warning",
                message="Style-DNA Persistence Gate hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    gate = dict(report.get("gate") or {})
    write_intent = dict(gate.get("write_intent") or {})

    if write_intent:
        signals.append(
            _signal(
                signal_type="style_dna_write_intent_created",
                severity="info",
                message="Style-DNA Write Intent wurde nur als Daten-Vorschau erstellt.",
                metadata={
                    "intent_id": write_intent.get("intent_id"),
                    "target_path_hint": write_intent.get("target_path_hint"),
                    "planned_only": True,
                    "no_file_write_performed": True,
                },
            )
        )

    if write_intent.get("write_preview_hash"):
        signals.append(
            _signal(
                signal_type="style_dna_write_preview_hash_created",
                severity="info",
                message="Style-DNA Write Preview Hash wurde als Vergleichswert erstellt.",
                metadata={
                    "write_preview_hash": write_intent.get("write_preview_hash"),
                    "hash_only": True,
                },
            )
        )

    if bool(report.get("write_permission_ready_for_future", False)):
        signals.append(
            _signal(
                signal_type="style_dna_write_permission_ready_for_future",
                severity="info",
                message="Style-DNA Schreibfreigabe ist nur fuer spaetere Verarbeitung bereit.",
                metadata={"write_permission_ready_for_future": True},
            )
        )

    signals.append(
        _signal(
            signal_type="style_dna_file_write_still_not_allowed",
            severity="info",
            message="2B-63 darf keine Style-DNA-Datei speichern.",
            metadata={"can_write_style_dna": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_backup_write_still_not_allowed",
            severity="info",
            message="2B-63 darf kein Backup speichern.",
            metadata={"backup_write_allowed": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_apply_still_not_allowed",
            severity="info",
            message="2B-63 darf Style-DNA noch nicht anwenden.",
            metadata={"can_apply_style_dna": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_profile_change_still_not_allowed",
            severity="info",
            message="2B-63 darf kein Profil aendern.",
            metadata={"can_update_profile": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_timeline_modify_still_not_allowed",
            severity="info",
            message="2B-63 darf keine Timeline aendern.",
            metadata={"can_modify_timeline": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_render_trigger_still_not_allowed",
            severity="info",
            message="2B-63 darf keinen Render ausloesen.",
            metadata={"can_trigger_render": False},
        )
    )

    return signals


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("style_dna_persistence_gate_report") or {}
    else:
        report = getattr(job, "style_dna_persistence_gate_report", {}) or {}
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
        "source": STYLE_DNA_PERSISTENCE_GATE_SIGNAL_SOURCE,
        "severity": severity,
        "message": message,
        "action_hint": STYLE_DNA_PERSISTENCE_GATE_ACTION_HINT,
        "metadata": payload_metadata,
    }
