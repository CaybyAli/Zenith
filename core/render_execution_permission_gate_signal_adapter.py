from __future__ import annotations

from typing import Any


RENDER_EXECUTION_PERMISSION_SIGNAL_SOURCE = "render_execution_permission_gate"
RENDER_EXECUTION_PERMISSION_ACTION_HINT = "review_render_execution_permission"

SIGNAL_METADATA = {
    "render_execution_permission_gate_only": True,
    "final_human_approval_gate": True,
    "media_unchanged": True,
    "no_execution_in_2b_49": True,
    "no_render_in_2b_49": True,
    "no_ff" "mpeg_in_2b_49": True,
    "no_process_" "spawn_in_2b_49": True,
    "no_media_read_in_2b_49": True,
    "no_media_write_in_2b_49": True,
    "no_directory_create_in_2b_49": True,
    "no_timeline_" "apply_in_2b_49": True,
}


def build_render_execution_permission_gate_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="render_execution_permission_failed",
                severity="warning",
                message="Render Execution Permission Report fehlt.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "")).lower()

    if status == "render_execution_permission_ready":
        signals.append(
            _signal(
                signal_type="render_execution_permission_ready",
                severity="info",
                message="Render Execution Permission Gate ist bereit.",
                metadata={"status": status},
            )
        )
    elif status == "render_execution_permission_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="render_execution_permission_ready_with_warnings",
                severity="warning",
                message="Render Execution Permission Gate ist bereit, aber Warnungen muessen geprueft werden.",
                metadata={"status": status},
            )
        )
    elif status == "render_execution_permission_blocked":
        signals.append(
            _signal(
                signal_type="render_execution_permission_blocked",
                severity="blocking",
                message="Render Execution Permission Gate ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="render_execution_permission_failed",
                severity="warning",
                message="Render Execution Permission Gate hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    if bool(report.get("human_approved")):
        signals.append(
            _signal(
                signal_type="render_execution_human_approval_present",
                severity="info",
                message="Finale menschliche Render-Freigabe ist vorhanden.",
                metadata={
                    "approved_by": report.get("approved_by"),
                    "approved_at": report.get("approved_at"),
                },
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="render_execution_human_approval_missing",
                severity="blocking",
                message="Finale menschliche Render-Freigabe fehlt.",
                metadata={"human_approved": False},
            )
        )

    if bool(report.get("ready_for_real_render_stage")):
        signals.append(
            _signal(
                signal_type="render_execution_ready_for_real_render_stage",
                severity="info",
                message="Naechster Block darf kontrollierte echte Render-Vorbereitung starten.",
                metadata={
                    "ready_for_real_render_stage": True,
                    "can_prepare_real_render_execution": bool(
                        report.get("can_prepare_real_render_execution")
                    ),
                },
            )
        )

    if (
        bool(report.get("can_render"))
        or bool(report.get("can_run_ff" "mpeg"))
        or bool(report.get("can_spawn_" "process"))
        or bool(report.get("can_write_" "media"))
        or bool(report.get("can_apply_" "timeline"))
    ):
        signals.append(
            _signal(
                signal_type="render_execution_permission_leak_blocked",
                severity="blocking",
                message="2B-49 enthaelt eine unerlaubte echte Ausfuehrungsfreigabe.",
                metadata={
                    "can_render": bool(report.get("can_render")),
                    "can_run_ff" "mpeg": bool(report.get("can_run_ff" "mpeg")),
                    "can_spawn_" "process": bool(report.get("can_spawn_" "process")),
                    "can_write_" "media": bool(report.get("can_write_" "media")),
                    "can_apply_" "timeline": bool(report.get("can_apply_" "timeline")),
                },
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="render_execution_real_render_still_not_allowed_here",
                severity="info",
                message="Echter Render, Tool-Start, Medien-Schreiben und Timeline-Anwendung bleiben in 2B-49 gesperrt.",
                metadata={
                    "can_render": False,
                    "can_run_ff" "mpeg": False,
                    "can_spawn_" "process": False,
                    "can_write_" "media": False,
                    "can_apply_" "timeline": False,
                },
            )
        )

    for check in report.get("checks", []):
        if not isinstance(check, dict):
            continue

        check_id = str(check.get("check_id") or "")
        status_text = str(check.get("status") or "")
        severity = "blocking" if bool(check.get("blocking")) else str(check.get("severity") or "info")

        signal_type = _signal_type_for_check(check_id=check_id, status_text=status_text)
        if not signal_type:
            continue

        signals.append(
            _signal(
                signal_type=signal_type,
                severity=severity,
                message=str(check.get("message") or check_id),
                metadata={
                    "check_id": check_id,
                    "check_status": status_text,
                    "category": check.get("category"),
                    "evidence": check.get("evidence") if isinstance(check.get("evidence"), dict) else {},
                },
            )
        )

    for reason in report.get("blocking_reasons", []):
        reason_text = str(reason)
        mapped = _signal_type_for_reason(reason_text)
        if not mapped:
            continue
        signals.append(
            _signal(
                signal_type=mapped,
                severity="blocking",
                message="Render Execution Permission Gate blockiert wegen Safety- oder Approval-Grund.",
                metadata={"blocking_reason": reason_text},
            )
        )

    return signals


def _signal_type_for_check(check_id: str, status_text: str) -> str | None:
    if status_text == "passed":
        if check_id == "human_approval_present":
            return "render_execution_human_approval_present"
        return None

    mapping = {
        "render_execution_human_approval_missing": "render_execution_human_approval_missing",
        "human_approval_present": "render_execution_human_approval_missing",
        "render_execution_approval_rejected": "render_execution_approval_rejected",
        "approval_not_rejected": "render_execution_approval_rejected",
        "render_readiness_ready": "render_execution_readiness_not_ready",
        "render_plan_ready": "render_execution_plan_not_ready",
        "render_blueprint_ready": "render_execution_blueprint_not_ready",
        "render_blueprint_non_executable": "render_execution_blueprint_not_ready",
        "render_asset_manifest_ready": "render_execution_asset_manifest_not_ready",
        "render_asset_manifest_safe": "render_execution_asset_manifest_unsafe",
        "no_render_permission_leak": "render_execution_permission_leak_blocked",
        "no_process_or_write_permission_leak": "render_execution_permission_leak_blocked",
        "no_timeline_apply_permission_leak": "render_execution_permission_leak_blocked",
    }
    return mapping.get(check_id)


def _signal_type_for_reason(reason_text: str) -> str | None:
    if "human_approval_missing" in reason_text:
        return "render_execution_human_approval_missing"
    if "approval_rejected" in reason_text:
        return "render_execution_approval_rejected"
    if "readiness" in reason_text:
        return "render_execution_readiness_not_ready"
    if "plan" in reason_text:
        return "render_execution_plan_not_ready"
    if "blueprint" in reason_text:
        return "render_execution_blueprint_not_ready"
    if "asset_manifest" in reason_text or "unsafe" in reason_text:
        return "render_execution_asset_manifest_unsafe"
    if "permission_leak" in reason_text:
        return "render_execution_permission_leak_blocked"
    return None


def _signal(
    signal_type: str,
    severity: str,
    message: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    merged_metadata = dict(SIGNAL_METADATA)
    merged_metadata.update(metadata)

    return {
        "source": RENDER_EXECUTION_PERMISSION_SIGNAL_SOURCE,
        "signal_type": signal_type,
        "type": signal_type,
        "severity": severity,
        "message": message,
        "action_hint": RENDER_EXECUTION_PERMISSION_ACTION_HINT,
        "metadata": merged_metadata,
    }


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("render_execution_permission_report") or job.get(
            "render_execution_permission_gate"
        )
    else:
        report = getattr(job, "render_execution_permission_report", None) or getattr(
            job,
            "render_execution_permission_gate",
            None,
        )

    if isinstance(report, dict):
        return report

    if hasattr(report, "to_dict"):
        return report.to_dict()

    return {}
