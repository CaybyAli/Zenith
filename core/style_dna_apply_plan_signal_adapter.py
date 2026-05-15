from __future__ import annotations

from typing import Any


STYLE_DNA_APPLY_PLAN_SIGNAL_SOURCE = "style_dna_apply_plan"
STYLE_DNA_APPLY_PLAN_ACTION_HINT = "review_style_dna_apply_plan"

SIGNAL_METADATA = {
    "style_dna_apply_plan_only": True,
    "non_writing_apply_contract": True,
    "style_dna_preview_only": True,
    "no_style_dna_file_write_in_2b_62": True,
    "no_profile_change_in_2b_62": True,
    "no_cutting_rule_activation_in_2b_62": True,
    "no_timeline_modify_in_2b_62": True,
    "no_render_trigger_in_2b_62": True,
    "no_publish_in_2b_62": True,
}


def build_style_dna_apply_plan_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="style_dna_apply_plan_waiting_for_review",
                severity="info",
                message="Style-DNA Apply Plan wartet auf Review-Daten.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "") or "").lower()

    if status == "style_dna_apply_plan_waiting_for_review":
        signals.append(
            _signal(
                signal_type="style_dna_apply_plan_waiting_for_review",
                severity="info",
                message="Style-DNA Apply Plan wartet auf Freigabe.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_apply_plan_ready":
        signals.append(
            _signal(
                signal_type="style_dna_apply_plan_ready",
                severity="info",
                message="Style-DNA Apply Plan ist als Vorschau bereit.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_apply_plan_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="style_dna_apply_plan_ready_with_warnings",
                severity="warning",
                message="Style-DNA Apply Plan ist bereit, hat aber Warnungen.",
                metadata={"status": status},
            )
        )
    elif status == "style_dna_apply_plan_blocked":
        signals.append(
            _signal(
                signal_type="style_dna_apply_plan_blocked",
                severity="blocking",
                message="Style-DNA Apply Plan ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="style_dna_apply_plan_failed",
                severity="warning",
                message="Style-DNA Apply Plan hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    plan = report.get("plan") or {}
    operations = list(plan.get("operations") or [])
    for operation in operations:
        signals.append(
            _signal(
                signal_type="style_dna_apply_operation_planned",
                severity="info",
                message="Style-DNA Operation wurde nur als Plan vorgemerkt.",
                metadata={
                    "operation_id": operation.get("operation_id"),
                    "proposal_id": operation.get("proposal_id"),
                    "parameter_name": operation.get("parameter_name"),
                    "operation_type": operation.get("operation_type"),
                    "planned_only": True,
                },
            )
        )

    if plan.get("after_preview"):
        signals.append(
            _signal(
                signal_type="style_dna_after_preview_created",
                severity="info",
                message="Style-DNA Before/After Vorschau wurde erstellt.",
                metadata={
                    "operation_count": int(report.get("operation_count", 0) or 0),
                    "preview_only": True,
                },
            )
        )

    if bool(report.get("ready_for_future_file_write", False)):
        signals.append(
            _signal(
                signal_type="style_dna_ready_for_future_file_write",
                severity="info",
                message="Style-DNA Apply Plan ist spaeter bereit fuer Datei-Schreibfreigabe.",
                metadata={"ready_for_future_file_write": True},
            )
        )

    signals.append(
        _signal(
            signal_type="style_dna_apply_still_not_allowed",
            severity="info",
            message="2B-62 darf Style-DNA noch nicht anwenden.",
            metadata={"can_apply_style_dna": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_file_write_still_not_allowed",
            severity="info",
            message="2B-62 darf keine Style-DNA-Datei speichern.",
            metadata={"can_write_style_dna": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_profile_change_still_not_allowed",
            severity="info",
            message="2B-62 darf kein Profil aendern.",
            metadata={"can_update_profile": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_timeline_modify_still_not_allowed",
            severity="info",
            message="2B-62 darf keine Timeline aendern.",
            metadata={"can_modify_timeline": False},
        )
    )
    signals.append(
        _signal(
            signal_type="style_dna_render_trigger_still_not_allowed",
            severity="info",
            message="2B-62 darf keinen Render starten.",
            metadata={"can_trigger_render": False},
        )
    )

    return signals


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("style_dna_apply_plan_report") or {}
    else:
        report = getattr(job, "style_dna_apply_plan_report", {}) or {}
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
        "source": STYLE_DNA_APPLY_PLAN_SIGNAL_SOURCE,
        "severity": severity,
        "message": message,
        "action_hint": STYLE_DNA_APPLY_PLAN_ACTION_HINT,
        "metadata": payload_metadata,
    }
