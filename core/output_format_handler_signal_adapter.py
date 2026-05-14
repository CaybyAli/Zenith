from __future__ import annotations

from typing import Any


OUTPUT_FORMAT_SIGNAL_SOURCE = "output_format_contract"
OUTPUT_FORMAT_ACTION_HINT = "review_output_format_contract"

SIGNAL_METADATA = {
    "output_format_contract_only": True,
    "render_preset_contract_only": True,
    "dry_run_only": True,
    "no_" "full_" "render_in_2b_55": True,
    "no_" "ff" "mpeg_execution_in_2b_55": True,
    "no_user_media_" "input_in_2b_55": True,
    "no_project_" "output_in_2b_55": True,
    "no_timeline_" "apply_in_2b_55": True,
}


def build_output_format_contract_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="output_format_contract_failed",
                severity="warning",
                message="Output Format Contract Report fehlt.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "")).lower()

    if status == "output_format_contract_ready":
        signals.append(
            _signal(
                signal_type="output_format_contract_ready",
                severity="info",
                message="Output Format Contract ist bereit.",
                metadata={"status": status},
            )
        )
    elif status == "output_format_contract_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="output_format_contract_ready_with_warnings",
                severity="warning",
                message="Output Format Contract ist bereit, aber Warnungen muessen geprueft werden.",
                metadata={"status": status},
            )
        )
    elif status == "output_format_contract_blocked":
        signals.append(
            _signal(
                signal_type="output_format_contract_blocked",
                severity="blocking",
                message="Output Format Contract ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="output_format_contract_failed",
                severity="warning",
                message="Output Format Contract hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    preset = report.get("preset", {})
    if isinstance(preset, dict):
        signals.append(
            _signal(
                signal_type="output_format_preset_selected",
                severity="info",
                message="Output Format Preset wurde ausgewaehlt.",
                metadata={
                    "preset_id": preset.get("preset_id"),
                    "profile": preset.get("profile"),
                    "platform": preset.get("platform"),
                    "target_format": preset.get("target_format"),
                    "safe_filename_hint": preset.get("safe_filename_hint"),
                },
            )
        )

        video = preset.get("video", {})
        if isinstance(video, dict):
            signals.append(
                _signal(
                    signal_type="output_format_video_spec_planned",
                    severity="info",
                    message="Output Video Spec wurde geplant.",
                    metadata={
                        "codec": video.get("codec"),
                        "encoder_intent": video.get("encoder_intent"),
                        "resolution_width": video.get("resolution_width"),
                        "resolution_height": video.get("resolution_height"),
                        "fps": video.get("fps"),
                        "crf": video.get("crf"),
                        "preset": video.get("preset"),
                        "pix_fmt": video.get("pix_fmt"),
                    },
                )
            )

            if video.get("encoder_intent") == "h264_nvenc":
                signals.append(
                    _signal(
                        signal_type="output_format_nvenc_available",
                        severity="info",
                        message="NVENC ist verfuegbar und als Encoder-Intent geplant.",
                        metadata={"encoder_intent": "h264_nvenc"},
                    )
                )
            else:
                signals.append(
                    _signal(
                        signal_type="output_format_nvenc_fallback",
                        severity="warning",
                        message="NVENC ist nicht verfuegbar oder nicht gewaehlt; libx264 wird als Intent genutzt.",
                        metadata={"encoder_intent": video.get("encoder_intent")},
                    )
                )

        audio = preset.get("audio", {})
        if isinstance(audio, dict):
            signals.append(
                _signal(
                    signal_type="output_format_audio_spec_planned",
                    severity="info",
                    message="Output Audio Spec wurde geplant.",
                    metadata={
                        "codec": audio.get("codec"),
                        "bitrate_kbps": audio.get("bitrate_kbps"),
                        "target_lufs": audio.get("target_lufs"),
                        "true_peak_db": audio.get("true_peak_db"),
                        "loudnorm_required": bool(audio.get("loudnorm_required")),
                    },
                )
            )

        container = preset.get("container", {})
        if isinstance(container, dict):
            signals.append(
                _signal(
                    signal_type="output_format_container_spec_planned",
                    severity="info",
                    message="Output Container Spec wurde geplant.",
                    metadata={
                        "container": container.get("container"),
                        "extension": container.get("extension"),
                        "faststart": bool(container.get("faststart")),
                        "movflags": container.get("movflags"),
                    },
                )
            )

    for warning in report.get("warnings", []):
        warning_text = str(warning)
        if "nvenc_missing" in warning_text:
            signals.append(
                _signal(
                    signal_type="output_format_nvenc_fallback",
                    severity="warning",
                    message="NVENC fehlt; libx264 bleibt als sicherer Fallback geplant.",
                    metadata={"warning": warning_text},
                )
            )
        if "loudnorm" in warning_text:
            signals.append(
                _signal(
                    signal_type="output_format_loudnorm_missing",
                    severity="warning",
                    message="Loudnorm-Filter fehlt oder ist nicht bestaetigt.",
                    metadata={"warning": warning_text},
                )
            )

    if (
        bool(report.get("can_render"))
        or bool(report.get("can_write_project_" "output"))
        or bool(report.get("can_process_user_" "media"))
        or bool(report.get("can_execute_ff" "mpeg"))
    ):
        signals.append(
            _signal(
                signal_type="output_format_render_still_not_allowed",
                severity="blocking",
                message="Output Format Contract enthaelt eine unerlaubte Ausfuehrungsfreigabe.",
                metadata={
                    "can_render": bool(report.get("can_render")),
                    "can_write_project_" "output": bool(report.get("can_write_project_" "output")),
                    "can_process_user_" "media": bool(report.get("can_process_user_" "media")),
                    "can_execute_ff" "mpeg": bool(report.get("can_execute_ff" "mpeg")),
                },
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="output_format_render_still_not_allowed",
                severity="info",
                message="Rendern, Medienverarbeitung, Tool-Ausfuehrung und Projekt-Ausgabe bleiben in 2B-55 gesperrt.",
                metadata={
                    "can_render": False,
                    "can_write_project_" "output": False,
                    "can_process_user_" "media": False,
                    "can_execute_ff" "mpeg": False,
                },
            )
        )

    for reason in report.get("blocking_reasons", []):
        signals.append(
            _signal(
                signal_type="output_format_contract_blocked",
                severity="blocking",
                message="Output Format Contract ist durch einen Blocking Reason blockiert.",
                metadata={"blocking_reason": str(reason)},
            )
        )

    return signals


def _signal(
    signal_type: str,
    severity: str,
    message: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    merged_metadata = dict(SIGNAL_METADATA)
    merged_metadata.update(metadata)
    return {
        "source": OUTPUT_FORMAT_SIGNAL_SOURCE,
        "signal_type": signal_type,
        "type": signal_type,
        "severity": severity,
        "message": message,
        "action_hint": OUTPUT_FORMAT_ACTION_HINT,
        "metadata": merged_metadata,
    }


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("output_format_contract_report") or job.get("output_format_contract")
    else:
        report = getattr(job, "output_format_contract_report", None) or getattr(
            job,
            "output_format_contract",
            None,
        )

    if isinstance(report, dict):
        return report

    if hasattr(report, "to_dict"):
        return report.to_dict()

    return {}
