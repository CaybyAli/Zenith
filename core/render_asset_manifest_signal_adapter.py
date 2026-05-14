from __future__ import annotations

from typing import Any


RENDER_ASSET_SIGNAL_SOURCE = "render_asset_manifest"
RENDER_ASSET_ACTION_HINT = "review_render_asset_manifest"

SIGNAL_METADATA = {
    "render_asset_manifest_only": True,
    "dry_run_only": True,
    "paths_are_hints_only": True,
    "media_unchanged": True,
    "no_execution_in_2b_48": True,
    "no_render_in_2b_48": True,
    "no_ff" "mpeg_in_2b_48": True,
    "no_media_read_in_2b_48": True,
    "no_media_write_in_2b_48": True,
    "no_directory_create_in_2b_48": True,
    "no_timeline_" "apply_in_2b_48": True,
}


def build_render_asset_manifest_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="render_asset_manifest_failed",
                severity="warning",
                message="Render Asset Manifest Report fehlt.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "")).lower()

    if status == "render_asset_manifest_ready":
        signals.append(
            _signal(
                signal_type="render_asset_manifest_ready",
                severity="info",
                message="Render Asset Manifest ist bereit.",
                metadata={"status": status},
            )
        )
    elif status == "render_asset_manifest_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="render_asset_manifest_ready_with_warnings",
                severity="warning",
                message="Render Asset Manifest ist bereit, aber Warnungen muessen geprueft werden.",
                metadata={"status": status},
            )
        )
    elif status == "render_asset_manifest_blocked":
        signals.append(
            _signal(
                signal_type="render_asset_manifest_blocked",
                severity="blocking",
                message="Render Asset Manifest ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="render_asset_manifest_failed",
                severity="warning",
                message="Render Asset Manifest hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    if bool(report.get("manifest_only")):
        signals.append(
            _signal(
                signal_type="render_asset_manifest_only_confirmed",
                severity="info",
                message="Render Asset Manifest ist ausdruecklich nur ein Manifest.",
                metadata={"manifest_only": True},
            )
        )

    if bool(report.get("paths_are_hints_only")):
        signals.append(
            _signal(
                signal_type="render_asset_paths_hint_only_confirmed",
                severity="info",
                message="Render Asset Manifest behandelt Pfade nur als Hinweise.",
                metadata={"paths_are_hints_only": True},
            )
        )

    if (
        bool(report.get("can_render"))
        or bool(report.get("can_run_ff" "mpeg"))
        or bool(report.get("can_write_files"))
    ):
        signals.append(
            _signal(
                signal_type="render_asset_render_not_allowed",
                severity="blocking",
                message="Render Asset Manifest enthaelt eine unerlaubte Render- oder Schreibfreigabe.",
                metadata={
                    "can_render": bool(report.get("can_render")),
                    "can_run_ffmpeg": bool(report.get("can_run_ff" "mpeg")),
                    "can_write_files": bool(report.get("can_write_files")),
                },
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="render_asset_render_not_allowed",
                severity="info",
                message="Rendern, Medienzugriff und Datei-Schreiben bleiben in 2B-48 gesperrt.",
                metadata={
                    "can_render": False,
                    "can_run_ffmpeg": False,
                    "can_write_files": False,
                },
            )
        )

    for asset in report.get("asset_references", []):
        if not isinstance(asset, dict):
            continue

        signals.append(
            _signal(
                signal_type="render_asset_reference_planned",
                severity="info",
                message="Render Asset Reference wurde geplant.",
                metadata={
                    "asset_id": asset.get("asset_id"),
                    "asset_type": asset.get("asset_type"),
                    "required": bool(asset.get("required")),
                    "safety_status": asset.get("safety_status"),
                },
            )
        )

        if asset.get("asset_type") == "censor_sfx_asset":
            signals.append(
                _signal(
                    signal_type="render_asset_censor_sfx_required",
                    severity="warning" if asset.get("required") else "info",
                    message="Censor-SFX Asset-Hinweis wurde eingeplant.",
                    metadata={
                        "asset_id": asset.get("asset_id"),
                        "required": bool(asset.get("required")),
                    },
                )
            )

        if bool(asset.get("required")) and not asset.get("path_hint"):
            signals.append(
                _signal(
                    signal_type="render_asset_missing_required_hint",
                    severity="blocking",
                    message="Ein erforderlicher Asset-Pfad-Hinweis fehlt.",
                    metadata={
                        "asset_id": asset.get("asset_id"),
                        "asset_type": asset.get("asset_type"),
                    },
                )
            )

        if asset.get("blocking_reasons"):
            signals.append(
                _signal(
                    signal_type="render_asset_unsafe_path",
                    severity="blocking",
                    message="Ein Asset-Pfad-Hinweis ist unsicher.",
                    metadata={
                        "asset_id": asset.get("asset_id"),
                        "asset_type": asset.get("asset_type"),
                        "blocking_reasons": list(asset.get("blocking_reasons") or []),
                    },
                )
            )

    for output in report.get("output_path_plans", []):
        if not isinstance(output, dict):
            continue

        signals.append(
            _signal(
                signal_type="render_output_path_planned",
                severity="info",
                message="Render Output Path Plan wurde geplant.",
                metadata={
                    "output_id": output.get("output_id"),
                    "output_type": output.get("output_type"),
                    "platform": output.get("platform"),
                    "safe_filename": output.get("safe_filename"),
                    "path_safety_status": output.get("path_safety_status"),
                },
            )
        )

        if output.get("blocking_reasons"):
            signals.append(
                _signal(
                    signal_type="render_asset_unsafe_path",
                    severity="blocking",
                    message="Ein Output-Pfad-Hinweis ist unsicher.",
                    metadata={
                        "output_id": output.get("output_id"),
                        "blocking_reasons": list(output.get("blocking_reasons") or []),
                    },
                )
            )

    for reason in report.get("blocking_reasons", []):
        reason_text = str(reason)
        if "missing_required" in reason_text:
            signals.append(
                _signal(
                    signal_type="render_asset_missing_required_hint",
                    severity="blocking",
                    message="Render Asset Manifest blockiert wegen fehlendem Pflicht-Hinweis.",
                    metadata={"blocking_reason": reason_text},
                )
            )
        if "unsafe" in reason_text or "path_hint" in reason_text:
            signals.append(
                _signal(
                    signal_type="render_asset_unsafe_path",
                    severity="blocking",
                    message="Render Asset Manifest blockiert wegen unsicherem Pfad-Hinweis.",
                    metadata={"blocking_reason": reason_text},
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
        "source": RENDER_ASSET_SIGNAL_SOURCE,
        "signal_type": signal_type,
        "type": signal_type,
        "severity": severity,
        "message": message,
        "action_hint": RENDER_ASSET_ACTION_HINT,
        "metadata": merged_metadata,
    }


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("render_asset_manifest_report") or job.get("render_asset_manifest")
    else:
        report = getattr(job, "render_asset_manifest_report", None) or getattr(
            job,
            "render_asset_manifest",
            None,
        )

    if isinstance(report, dict):
        return report

    if hasattr(report, "to_dict"):
        return report.to_dict()

    return {}
