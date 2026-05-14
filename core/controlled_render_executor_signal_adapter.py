from __future__ import annotations

from typing import Any


CONTROLLED_RENDER_EXECUTOR_SIGNAL_SOURCE = "controlled_render_executor"
CONTROLLED_RENDER_EXECUTOR_ACTION_HINT = "review_controlled_render_executor"

SIGNAL_METADATA = {
    "controlled_render_executor_foundation": True,
    "dry_run_only": True,
    "media_unchanged": True,
    "no_real_render_in_2b_50": True,
    "no_ff" "mpeg_in_2b_50": True,
    "no_process_" "spawn_in_2b_50": True,
    "no_media_read_in_2b_50": True,
    "no_media_write_in_2b_50": True,
    "no_directory_create_in_2b_50": True,
    "no_timeline_" "apply_in_2b_50": True,
    "execution_steps_are_dry_run_only": True,
}


def build_controlled_render_executor_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="controlled_render_executor_failed",
                severity="warning",
                message="Controlled Render Executor Report fehlt.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "")).lower()

    if status == "controlled_render_executor_dry_run_ready":
        signals.append(
            _signal(
                signal_type="controlled_render_executor_dry_run_ready",
                severity="info",
                message="Controlled Render Executor Dry-Run ist bereit.",
                metadata={"status": status},
            )
        )
    elif status == "controlled_render_executor_dry_run_with_warnings":
        signals.append(
            _signal(
                signal_type="controlled_render_executor_dry_run_with_warnings",
                severity="warning",
                message="Controlled Render Executor Dry-Run ist bereit, aber Warnungen muessen geprueft werden.",
                metadata={"status": status},
            )
        )
    elif status == "controlled_render_executor_blocked":
        signals.append(
            _signal(
                signal_type="controlled_render_executor_blocked",
                severity="blocking",
                message="Controlled Render Executor ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="controlled_render_executor_failed",
                severity="warning",
                message="Controlled Render Executor hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    steps = report.get("execution_steps", [])
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, dict):
                continue
            signals.append(
                _signal(
                    signal_type="controlled_render_execution_step_planned",
                    severity="info",
                    message="Controlled Render Dry-Run Step ist geplant und bleibt nicht ausgefuehrt.",
                    metadata={
                        "step_id": step.get("step_id"),
                        "source_blueprint_step_id": step.get("source_blueprint_step_id"),
                        "step_type": step.get("step_type"),
                        "executed": False,
                        "skipped_reason": step.get("skipped_reason"),
                        "safety_status": step.get("safety_status"),
                    },
                )
            )

    if bool(report.get("dry_run_only")):
        signals.append(
            _signal(
                signal_type="controlled_render_dry_run_only_confirmed",
                severity="info",
                message="Controlled Render Executor ist strikt Dry-Run only.",
                metadata={"dry_run_only": True},
            )
        )

    if bool(report.get("real_render_requested")):
        signals.append(
            _signal(
                signal_type="controlled_render_real_render_requested_blocked",
                severity="blocking",
                message="Echte Render-Anfrage wurde in 2B-50 blockiert.",
                metadata={
                    "real_render_requested": True,
                    "real_render_allowed": False,
                },
            )
        )

    if not bool(report.get("real_render_allowed")):
        signals.append(
            _signal(
                signal_type="controlled_render_real_render_not_allowed_here",
                severity="info",
                message="Echter Render bleibt in 2B-50 nicht erlaubt.",
                metadata={"real_render_allowed": False},
            )
        )

    if _has_forbidden_permission(report):
        signals.append(
            _signal(
                signal_type="controlled_render_real_render_requested_blocked",
                severity="blocking",
                message="Controlled Render Report enthaelt unerlaubte echte Ausfuehrungsfreigabe.",
                metadata={
                    "can_execute_real_render": bool(report.get("can_execute_real_render")),
                    "can_render": bool(report.get("can_render")),
                    "can_run_ff" "mpeg": bool(report.get("can_run_ff" "mpeg")),
                    "can_spawn_" "process": bool(report.get("can_spawn_" "process")),
                    "can_write_" "media": bool(report.get("can_write_" "media")),
                    "output_created": bool(report.get("output_created")),
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
                message="Controlled Render Executor blockiert wegen Safety-Grund.",
                metadata={"blocking_reason": reason_text},
            )
        )

    return signals


def _has_forbidden_permission(report: dict[str, Any]) -> bool:
    return bool(
        report.get("real_render_allowed")
        or report.get("can_execute_real_render")
        or report.get("can_render")
        or report.get("can_run_ff" "mpeg")
        or report.get("can_spawn_" "process")
        or report.get("can_write_" "media")
        or report.get("output_created")
    )


def _signal_type_for_reason(reason_text: str) -> str | None:
    if "permission_gate" in reason_text:
        return "controlled_render_permission_gate_not_ready"
    if "blueprint" in reason_text:
        return "controlled_render_blueprint_missing"
    if "asset_manifest" in reason_text or "dangerous_asset_flag" in reason_text:
        return "controlled_render_asset_manifest_not_ready"
    if "real_render_execution_not_implemented_in_2b_50" in reason_text:
        return "controlled_render_real_render_requested_blocked"
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
        "source": CONTROLLED_RENDER_EXECUTOR_SIGNAL_SOURCE,
        "signal_type": signal_type,
        "type": signal_type,
        "severity": severity,
        "message": message,
        "action_hint": CONTROLLED_RENDER_EXECUTOR_ACTION_HINT,
        "metadata": merged_metadata,
    }


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("controlled_render_executor_report") or job.get(
            "controlled_render_executor"
        )
    else:
        report = getattr(job, "controlled_render_executor_report", None) or getattr(
            job,
            "controlled_render_executor",
            None,
        )

    if isinstance(report, dict):
        return report

    if hasattr(report, "to_dict"):
        return report.to_dict()

    return {}
