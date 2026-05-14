from __future__ import annotations

from typing import Any


CONTROLLED_FFMPEG_EXECUTION_SIGNAL_SOURCE = "controlled_ffmpeg_execution"
CONTROLLED_FFMPEG_EXECUTION_ACTION_HINT = "review_controlled_ffmpeg_execution"

SIGNAL_METADATA = {
    "phase": "2B-54",
    "block": "block8_render_export",
    "controlled_ffmpeg_execution_gate": True,
    "default_dry_run": True,
    "smoke_test_only_when_explicitly_allowed": True,
    "no_full_render_in_2b_54": True,
    "no_user_media_input_in_2b_54": True,
    "no_project_output_in_2b_54": True,
    "no_timeline_apply_in_2b_54": True,
}


def build_controlled_ffmpeg_execution_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="controlled_ffmpeg_execution_failed",
                severity="warning",
                message="Controlled FFmpeg Execution Report fehlt.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "")).lower()

    if status == "controlled_ffmpeg_execution_dry_run_ready":
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_execution_dry_run_ready",
                severity="info",
                message="Controlled FFmpeg Execution bleibt im sicheren Dry-Run.",
                metadata={"status": status, "dry_run_only": True},
            )
        )
    elif status == "controlled_ffmpeg_execution_smoke_ready":
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_execution_smoke_ready",
                severity="warning",
                message="Controlled FFmpeg Smoke-Test ist explizit vorbereitet.",
                metadata={"status": status, "smoke_test_only": True},
            )
        )
    elif status == "controlled_ffmpeg_execution_smoke_succeeded":
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_execution_smoke_succeeded",
                severity="info",
                message="Controlled FFmpeg Smoke-Test war erfolgreich.",
                metadata={
                    "status": status,
                    "output_created": bool(report.get("output_created")),
                    "output_path": report.get("output_path"),
                },
            )
        )
    elif status == "controlled_ffmpeg_execution_smoke_failed":
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_execution_smoke_failed",
                severity="blocking",
                message="Controlled FFmpeg Smoke-Test ist fehlgeschlagen.",
                metadata={"status": status},
            )
        )
    elif status == "controlled_ffmpeg_execution_blocked":
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_execution_blocked",
                severity="blocking",
                message="Controlled FFmpeg Execution ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_execution_failed",
                severity="warning",
                message="Controlled FFmpeg Execution hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    if bool(report.get("output_created")):
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_smoke_output_created",
                severity="info",
                message="Controlled FFmpeg Smoke-Test hat eine temporäre Testdatei erzeugt.",
                metadata={
                    "output_created": True,
                    "output_path": report.get("output_path"),
                    "smoke_test_only": True,
                },
            )
        )

    if _has_forbidden_full_render_permission(report):
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_full_render_still_not_allowed",
                severity="blocking",
                message="2B-54 enthält eine unerlaubte Full-Render-Freigabe.",
                metadata={
                    "can_execute_full_render": bool(
                        report.get("can_execute_full_render")
                    ),
                    "can_render_timeline": bool(report.get("can_render_timeline")),
                },
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_full_render_still_not_allowed",
                severity="info",
                message="Full Render und Timeline Render bleiben in 2B-54 verboten.",
                metadata={
                    "can_execute_full_render": False,
                    "can_render_timeline": False,
                },
            )
        )

    if bool(report.get("can_process_user_media")):
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_user_media_still_not_allowed",
                severity="blocking",
                message="2B-54 enthält eine unerlaubte User-Media-Freigabe.",
                metadata={"can_process_user_media": True},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_user_media_still_not_allowed",
                severity="info",
                message="User-Media-Verarbeitung bleibt in 2B-54 verboten.",
                metadata={"can_process_user_media": False},
            )
        )

    if bool(report.get("can_write_project_output")):
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_project_output_still_not_allowed",
                severity="blocking",
                message="2B-54 enthält eine unerlaubte Projekt-Output-Freigabe.",
                metadata={"can_write_project_output": True},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_project_output_still_not_allowed",
                severity="info",
                message="Projekt-Output-Schreiben bleibt in 2B-54 verboten.",
                metadata={"can_write_project_output": False},
            )
        )

    for reason in report.get("blocking_reasons", []):
        signals.append(
            _signal(
                signal_type="controlled_ffmpeg_execution_blocked",
                severity="blocking",
                message="Controlled FFmpeg Execution blockiert wegen Safety-Grund.",
                metadata={"blocking_reason": str(reason)},
            )
        )

    return signals


def _has_forbidden_full_render_permission(report: dict[str, Any]) -> bool:
    return bool(
        report.get("can_execute_full_render")
        or report.get("can_render_timeline")
    )


def _signal(
    signal_type: str,
    severity: str,
    message: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    merged_metadata = dict(SIGNAL_METADATA)
    merged_metadata.update(metadata)

    return {
        "source": CONTROLLED_FFMPEG_EXECUTION_SIGNAL_SOURCE,
        "signal_type": signal_type,
        "type": signal_type,
        "severity": severity,
        "message": message,
        "action_hint": CONTROLLED_FFMPEG_EXECUTION_ACTION_HINT,
        "metadata": merged_metadata,
    }


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("controlled_ffmpeg_execution_report")
    else:
        report = getattr(job, "controlled_ffmpeg_execution_report", None)

    if isinstance(report, dict):
        return report

    if hasattr(report, "to_dict"):
        return report.to_dict()

    return {}

