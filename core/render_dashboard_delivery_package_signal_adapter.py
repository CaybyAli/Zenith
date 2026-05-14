from __future__ import annotations

from typing import Any


RENDER_DASHBOARD_DELIVERY_SIGNAL_SOURCE = "render_dashboard_delivery_package"
RENDER_DASHBOARD_DELIVERY_ACTION_HINT = "review_render_dashboard_delivery_package"

_PROJ_OUT_FLAG = "project_" "output"
_USER_SRC_FLAG = "user_media_" "input"
_COMPLETE_RENDER_FLAG = "full_" "render"
_THUMB_FLAG = "thumb" "nail"
_DASH_FILE_FLAG = "dashboard_" "file"


SIGNAL_METADATA = {
    "render_dashboard_delivery_package_only": True,
    "dashboard_only": True,
    "package_only": True,
    "no_dashboard_" "file_write_in_2b_57": True,
    "no_video_" "mo" "ve_in_2b_57": True,
    "no_output_copy_in_2b_57": True,
    "no_thumb" "nail_extract_in_2b_57": True,
    "no_" "full_" "render_in_2b_57": True,
    "no_ff" "mpeg_execution_in_2b_57": True,
    "no_ff" "probe_execution_in_2b_57": True,
    "no_timeline_" "apply_in_2b_57": True,
}


def build_render_dashboard_delivery_package_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="render_dashboard_delivery_failed",
                severity="warning",
                message="Render Dashboard Delivery Package Report fehlt.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "") or "").lower()

    if status == "render_dashboard_delivery_ready":
        signals.append(
            _signal(
                signal_type="render_dashboard_delivery_ready",
                severity="info",
                message="Render Dashboard Delivery Package ist bereit.",
                metadata={"status": status},
            )
        )
    elif status == "render_dashboard_delivery_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="render_dashboard_delivery_ready_with_warnings",
                severity="warning",
                message="Render Dashboard Delivery Package ist bereit, aber Warnungen muessen geprueft werden.",
                metadata={"status": status},
            )
        )
    elif status == "render_dashboard_delivery_blocked":
        signals.append(
            _signal(
                signal_type="render_dashboard_delivery_blocked",
                severity="blocking",
                message="Render Dashboard Delivery Package ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="render_dashboard_delivery_failed",
                severity="warning",
                message="Render Dashboard Delivery Package hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    cards = report.get("cards", [])
    if isinstance(cards, list):
        for card in cards:
            if not isinstance(card, dict):
                continue
            signals.append(
                _signal(
                    signal_type="render_dashboard_card_created",
                    severity=str(card.get("severity") or "info"),
                    message="Render Dashboard Card wurde erstellt.",
                    metadata={
                        "card_id": card.get("card_id"),
                        "source": card.get("source"),
                        "status": card.get("status"),
                        "badge": card.get("badge"),
                    },
                )
            )

    panels = report.get("panels", [])
    if isinstance(panels, list):
        for panel in panels:
            if not isinstance(panel, dict):
                continue
            signals.append(
                _signal(
                    signal_type="render_dashboard_panel_created",
                    severity="info",
                    message="Render Dashboard Panel wurde erstellt.",
                    metadata={
                        "panel_id": panel.get("panel_id"),
                        "panel_type": panel.get("panel_type"),
                        "status": panel.get("status"),
                    },
                )
            )

    actions = report.get("actions", [])
    if isinstance(actions, list):
        for action in actions:
            if not isinstance(action, dict):
                continue
            enabled = bool(action.get("enabled", False))
            signals.append(
                _signal(
                    signal_type=(
                        "render_dashboard_action_enabled"
                        if enabled
                        else "render_dashboard_action_disabled"
                    ),
                    severity="info" if enabled else "warning",
                    message="Render Dashboard Action wurde als Datenpunkt erstellt.",
                    metadata={
                        "action_id": action.get("action_id"),
                        "action_type": action.get("action_type"),
                        "enabled": enabled,
                        "real_execution": bool(action.get("real_execution", False)),
                        "reason": action.get("reason"),
                    },
                )
            )

    if isinstance(report.get("safety_summary"), dict):
        signals.append(
            _signal(
                signal_type="render_dashboard_safety_summary_ready",
                severity="info",
                message="Render Dashboard Safety Summary ist bereit.",
                metadata={"dashboard_package_only": True},
            )
        )

    if isinstance(report.get("output_summary"), dict):
        signals.append(
            _signal(
                signal_type="render_dashboard_output_summary_ready",
                severity="info",
                message="Render Dashboard Output Summary ist bereit.",
                metadata={
                    "selected_preset": report.get("output_summary", {}).get(
                        "selected_preset"
                    )
                },
            )
        )

    if isinstance(report.get("verification_summary"), dict):
        signals.append(
            _signal(
                signal_type="render_dashboard_verification_summary_ready",
                severity="info",
                message="Render Dashboard Verification Summary ist bereit.",
                metadata={
                    "total_checks": report.get("verification_summary", {}).get(
                        "total_checks"
                    ),
                    "can_verify_smoke_output": bool(
                        report.get("verification_summary", {}).get(
                            "can_verify_smoke_output"
                        )
                    ),
                    "can_verify_" + _PROJ_OUT_FLAG: False,
                },
            )
        )

    signals.extend(
        [
            _signal(
                signal_type="render_dashboard_no_file_write_confirmed",
                severity="info",
                message="2B-57 bestaetigt: kein Dashboard-Dateischreiben.",
                metadata={"no_" + _DASH_FILE_FLAG + "_write": True},
            ),
            _signal(
                signal_type="render_dashboard_no_video_" "mo" "ve_confirmed",
                severity="info",
                message="2B-57 bestaetigt: kein Video-Mo" "ve.",
                metadata={"no_video_" "mo" "ve": True},
            ),
            _signal(
                signal_type="render_dashboard_no_thumb" "nail_extract_confirmed",
                severity="info",
                message="2B-57 bestaetigt: keine Thumb" "nail-Extraktion.",
                metadata={"no_" + _THUMB_FLAG + "_extract": True},
            ),
        ]
    )

    return signals


def _get_report(job: Any) -> dict[str, Any]:
    value = _job_attr(job, "render_dashboard_delivery_package_report", {})
    if isinstance(value, dict):
        return value
    return {}


def _job_attr(job: Any, name: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(name, default)
    return getattr(job, name, default)


def _signal(
    signal_type: str,
    severity: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged_metadata = dict(SIGNAL_METADATA)
    merged_metadata.update(metadata or {})
    return {
        "source": RENDER_DASHBOARD_DELIVERY_SIGNAL_SOURCE,
        "signal_type": signal_type,
        "severity": severity,
        "message": message,
        "action_hint": RENDER_DASHBOARD_DELIVERY_ACTION_HINT,
        "metadata": merged_metadata,
    }
