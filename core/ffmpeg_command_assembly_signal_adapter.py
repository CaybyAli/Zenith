from __future__ import annotations

from typing import Any


FFMPEG_COMMAND_ASSEMBLY_SIGNAL_SOURCE = "ffmpeg_command_assembly"
FFMPEG_COMMAND_ASSEMBLY_ACTION_HINT = "review_ffmpeg_command_assembly"

SIGNAL_METADATA = {
    "ffmpeg_command_assembly_only": True,
    "dry_run_only": True,
    "assembly_only": True,
    "preview_only": True,
    "no_render_in_2b_53": True,
    "no_process_spawn_in_2b_53": True,
    "no_media_read_in_2b_53": True,
    "no_media_write_in_2b_53": True,
    "no_directory_create_in_2b_53": True,
    "no_timeline_apply_in_2b_53": True,
}


def build_ffmpeg_command_assembly_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="ffmpeg_command_assembly_failed",
                severity="warning",
                message="FFmpeg Command Assembly Report fehlt.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "")).lower()

    if status == "ffmpeg_command_assembly_ready":
        signals.append(
            _signal(
                signal_type="ffmpeg_command_assembly_ready",
                severity="info",
                message="FFmpeg Command Assembly ist bereit.",
                metadata={"status": status},
            )
        )
    elif status == "ffmpeg_command_assembly_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="ffmpeg_command_assembly_ready_with_warnings",
                severity="warning",
                message="FFmpeg Command Assembly ist bereit, aber Warnungen muessen geprueft werden.",
                metadata={"status": status},
            )
        )
    elif status == "ffmpeg_command_assembly_blocked":
        signals.append(
            _signal(
                signal_type="ffmpeg_command_assembly_blocked",
                severity="blocking",
                message="FFmpeg Command Assembly ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="ffmpeg_command_assembly_failed",
                severity="warning",
                message="FFmpeg Command Assembly hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    assemblies = report.get("assemblies", [])
    if isinstance(assemblies, list):
        for assembly in assemblies:
            if not isinstance(assembly, dict):
                continue

            signals.append(
                _signal(
                    signal_type="ffmpeg_command_assembly_created",
                    severity=(
                        "blocking"
                        if assembly.get("blocking_reasons")
                        else "info"
                    ),
                    message="FFmpeg argv_preview wurde als Daten-Preview erzeugt.",
                    metadata={
                        "assembly_id": assembly.get("assembly_id"),
                        "assembly_type": assembly.get("assembly_type"),
                        "assembly_only": bool(assembly.get("assembly_only")),
                        "preview_only": bool(assembly.get("preview_only")),
                        "can_execute_command": bool(
                            assembly.get("can_execute_command")
                        ),
                        "can_spawn_process": bool(assembly.get("can_spawn_process")),
                        "can_render": bool(assembly.get("can_render")),
                        "can_write_media": bool(assembly.get("can_write_media")),
                        "blocking_reasons": list(
                            assembly.get("blocking_reasons") or []
                        ),
                    },
                )
            )

            tokens = assembly.get("argument_tokens", [])
            if isinstance(tokens, list):
                for token in tokens:
                    if not isinstance(token, dict):
                        continue
                    safe = bool(token.get("safe", False))
                    signals.append(
                        _signal(
                            signal_type=(
                                "ffmpeg_command_argument_safe"
                                if safe
                                else "ffmpeg_command_argument_blocked"
                            ),
                            severity="info" if safe else "blocking",
                            message="FFmpeg Argument Token wurde sicherheitsgeprueft.",
                            metadata={
                                "assembly_id": assembly.get("assembly_id"),
                                "token_id": token.get("token_id"),
                                "token_type": token.get("token_type"),
                                "safe": safe,
                                "warnings": list(token.get("warnings") or []),
                                "blocking_reasons": list(
                                    token.get("blocking_reasons") or []
                                ),
                            },
                        )
                    )

    if bool(report.get("preview_only")) and bool(report.get("assembly_only")):
        signals.append(
            _signal(
                signal_type="ffmpeg_command_preview_only_confirmed",
                severity="info",
                message="FFmpeg Command Assembly bleibt Preview-only und Assembly-only.",
                metadata={
                    "preview_only": True,
                    "assembly_only": True,
                },
            )
        )

    if bool(report.get("ready_for_controlled_execution_stage")):
        signals.append(
            _signal(
                signal_type="ffmpeg_command_ready_for_controlled_execution_stage",
                severity="info",
                message="FFmpeg Command Assembly darf spaeter in eine kontrollierte Execution-Stufe uebergeben werden.",
                metadata={
                    "ready_for_controlled_execution_stage": True,
                    "can_execute_commands": False,
                    "can_spawn_process": False,
                    "can_render": False,
                    "can_write_media": False,
                    "can_probe_media_files": False,
                },
            )
        )

    if _has_forbidden_permission(report):
        signals.append(
            _signal(
                signal_type="ffmpeg_command_real_execution_still_not_allowed",
                severity="blocking",
                message="FFmpeg Command Assembly enthaelt unerlaubte echte Ausfuehrungsfreigabe.",
                metadata={
                    "can_execute_commands": bool(
                        report.get("can_execute_commands")
                    ),
                    "can_spawn_process": bool(report.get("can_spawn_process")),
                    "can_render": bool(report.get("can_render")),
                    "can_write_media": bool(report.get("can_write_media")),
                    "can_probe_media_files": bool(
                        report.get("can_probe_media_files")
                    ),
                },
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="ffmpeg_command_real_execution_still_not_allowed",
                severity="info",
                message="Echte FFmpeg Ausfuehrung bleibt in 2B-53 verboten.",
                metadata={
                    "can_execute_commands": False,
                    "can_spawn_process": False,
                    "can_render": False,
                    "can_write_media": False,
                    "can_probe_media_files": False,
                },
            )
        )

    for reason in report.get("blocking_reasons", []):
        reason_text = str(reason)
        signals.append(
            _signal(
                signal_type="ffmpeg_command_assembly_blocked",
                severity="blocking",
                message="FFmpeg Command Assembly blockiert wegen Safety-Grund.",
                metadata={"blocking_reason": reason_text},
            )
        )

    return signals


def _has_forbidden_permission(report: dict[str, Any]) -> bool:
    return bool(
        report.get("can_execute_commands")
        or report.get("can_spawn_process")
        or report.get("can_render")
        or report.get("can_write_media")
        or report.get("can_probe_media_files")
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
        "source": FFMPEG_COMMAND_ASSEMBLY_SIGNAL_SOURCE,
        "signal_type": signal_type,
        "type": signal_type,
        "severity": severity,
        "message": message,
        "action_hint": FFMPEG_COMMAND_ASSEMBLY_ACTION_HINT,
        "metadata": merged_metadata,
    }


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("ffmpeg_command_assembly_report")
    else:
        report = getattr(job, "ffmpeg_command_assembly_report", None)

    if isinstance(report, dict):
        return report
    return {}
