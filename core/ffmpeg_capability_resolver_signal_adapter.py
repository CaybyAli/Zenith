from __future__ import annotations

from typing import Any


FFMPEG_CAPABILITY_SIGNAL_SOURCE = "ffmpeg_capability_resolver"
FFMPEG_CAPABILITY_ACTION_HINT = "review_ffmpeg_capabilities"

SIGNAL_METADATA = {
    "phase": "2B-52",
    "block": "block8_render_export",
    "ffmpeg_capability_resolver_only": True,
    "tool_probe_only": True,
    "no_render_in_2b_52": True,
    "no_media_input_in_2b_52": True,
    "no_media_output_in_2b_52": True,
    "no_timeline_apply_in_2b_52": True,
    "controlled_tool_probe_only": True,
}


def build_ffmpeg_capability_resolver_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="ffmpeg_capability_failed",
                severity="warning",
                message="FFmpeg Capability Resolver Report fehlt.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "")).lower()

    if status == "ffmpeg_capability_ready":
        signals.append(
            _signal(
                signal_type="ffmpeg_capability_ready",
                severity="info",
                message="FFmpeg Capability Resolver ist bereit.",
                metadata={"status": status},
            )
        )
    elif status == "ffmpeg_capability_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="ffmpeg_capability_ready_with_warnings",
                severity="warning",
                message="FFmpeg Capability Resolver ist bereit, aber Warnungen muessen geprueft werden.",
                metadata={"status": status},
            )
        )
    elif status == "ffmpeg_capability_blocked":
        signals.append(
            _signal(
                signal_type="ffmpeg_capability_blocked",
                severity="blocking",
                message="FFmpeg Capability Resolver ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="ffmpeg_capability_failed",
                severity="warning",
                message="FFmpeg Capability Resolver hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    ffmpeg_path = report.get("ffmpeg_path")
    if isinstance(ffmpeg_path, dict):
        signals.append(
            _signal(
                signal_type=(
                    "ffmpeg_path_safe"
                    if ffmpeg_path.get("path_safety_status") == "safe"
                    else "ffmpeg_path_unsafe"
                ),
                severity=(
                    "info"
                    if ffmpeg_path.get("path_safety_status") == "safe"
                    else "blocking"
                ),
                message="FFmpeg Pfad-Hinweis wurde geprueft.",
                metadata={
                    "tool_name": ffmpeg_path.get("tool_name"),
                    "path_safety_status": ffmpeg_path.get("path_safety_status"),
                    "is_absolute_hint": bool(ffmpeg_path.get("is_absolute_hint")),
                    "blocking_reasons": list(ffmpeg_path.get("blocking_reasons") or []),
                },
            )
        )

    ffprobe_path = report.get("ffprobe_path")
    if isinstance(ffprobe_path, dict):
        signals.append(
            _signal(
                signal_type=(
                    "ffmpeg_path_safe"
                    if ffprobe_path.get("path_safety_status") == "safe"
                    else "ffmpeg_path_unsafe"
                ),
                severity=(
                    "info"
                    if ffprobe_path.get("path_safety_status") == "safe"
                    else "blocking"
                ),
                message="FFprobe Pfad-Hinweis wurde geprueft.",
                metadata={
                    "tool_name": ffprobe_path.get("tool_name"),
                    "path_safety_status": ffprobe_path.get("path_safety_status"),
                    "is_absolute_hint": bool(ffprobe_path.get("is_absolute_hint")),
                    "blocking_reasons": list(ffprobe_path.get("blocking_reasons") or []),
                },
            )
        )

    if bool(report.get("tool_probe_attempted")):
        signals.append(
            _signal(
                signal_type="ffmpeg_tool_probe_attempted",
                severity="info",
                message="Kontrollierte Tool-Probe wurde versucht.",
                metadata={"tool_probe_attempted": True},
            )
        )

    if bool(report.get("tool_probe_succeeded")):
        signals.append(
            _signal(
                signal_type="ffmpeg_tool_probe_succeeded",
                severity="info",
                message="Kontrollierte Tool-Probe war erfolgreich.",
                metadata={"tool_probe_succeeded": True},
            )
        )
    elif bool(report.get("tool_probe_attempted")):
        signals.append(
            _signal(
                signal_type="ffmpeg_tool_probe_failed",
                severity="warning",
                message="Kontrollierte Tool-Probe war nicht vollstaendig erfolgreich.",
                metadata={
                    "tool_probe_attempted": True,
                    "tool_probe_succeeded": False,
                },
            )
        )

    if bool(report.get("has_h264")):
        signals.append(
            _signal(
                signal_type="ffmpeg_h264_available",
                severity="info",
                message="H264 Capability ist verfuegbar.",
                metadata={"has_h264": True},
            )
        )

    if bool(report.get("has_aac")):
        signals.append(
            _signal(
                signal_type="ffmpeg_aac_available",
                severity="info",
                message="AAC Capability ist verfuegbar.",
                metadata={"has_aac": True},
            )
        )

    if bool(report.get("has_nvenc")):
        signals.append(
            _signal(
                signal_type="ffmpeg_nvenc_available",
                severity="info",
                message="NVENC Capability ist verfuegbar.",
                metadata={"has_nvenc": True},
            )
        )

    if bool(report.get("has_loudnorm_filter")):
        signals.append(
            _signal(
                signal_type="ffmpeg_loudnorm_available",
                severity="info",
                message="Loudnorm Filter ist verfuegbar.",
                metadata={"has_loudnorm_filter": True},
            )
        )

    if bool(report.get("can_prepare_real_render_tools")):
        signals.append(
            _signal(
                signal_type="ffmpeg_real_render_tools_preparable",
                severity="info",
                message="Echte Render-Tools koennen spaeter vorbereitet werden.",
                metadata={"can_prepare_real_render_tools": True},
            )
        )

    if _has_forbidden_media_permission(report):
        signals.append(
            _signal(
                signal_type="ffmpeg_render_still_not_allowed_here",
                severity="blocking",
                message="2B-52 enthaelt eine unerlaubte Render- oder Medien-Freigabe.",
                metadata={
                    "can_render": bool(report.get("can_render")),
                    "can_process_" "media": bool(report.get("can_process_" "media")),
                    "can_write_" "media": bool(report.get("can_write_" "media")),
                    "can_probe_" "media_files": bool(
                        report.get("can_probe_" "media_files")
                    ),
                },
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="ffmpeg_render_still_not_allowed_here",
                severity="info",
                message="Render, Medienverarbeitung, Medien-Schreiben und Medien-Probing bleiben in 2B-52 gesperrt.",
                metadata={
                    "can_render": False,
                    "can_process_" "media": False,
                    "can_write_" "media": False,
                    "can_probe_" "media_files": False,
                },
            )
        )

    for reason in report.get("blocking_reasons", []):
        signals.append(
            _signal(
                signal_type="ffmpeg_capability_blocked",
                severity="blocking",
                message="FFmpeg Capability Resolver blockiert wegen Safety-Grund.",
                metadata={"blocking_reason": str(reason)},
            )
        )

    return signals


def _has_forbidden_media_permission(report: dict[str, Any]) -> bool:
    return bool(
        report.get("can_render")
        or report.get("can_process_" "media")
        or report.get("can_write_" "media")
        or report.get("can_probe_" "media_files")
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
        "source": FFMPEG_CAPABILITY_SIGNAL_SOURCE,
        "signal_type": signal_type,
        "type": signal_type,
        "severity": severity,
        "message": message,
        "action_hint": FFMPEG_CAPABILITY_ACTION_HINT,
        "metadata": merged_metadata,
    }


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("ffmpeg_capability_resolver_report")
    else:
        report = getattr(job, "ffmpeg_capability_resolver_report", None)

    if isinstance(report, dict):
        return report

    if hasattr(report, "to_dict"):
        return report.to_dict()

    return {}
