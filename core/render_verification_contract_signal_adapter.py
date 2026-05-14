from __future__ import annotations

from typing import Any


RENDER_VERIFICATION_SIGNAL_SOURCE = "render_verification_contract"
RENDER_VERIFICATION_ACTION_HINT = "review_render_verification_contract"

SIGNAL_METADATA = {
    "render_verification_contract_only": True,
    "dry_run_only": True,
    "probe_plan_only": True,
    "no_" "full_" "render_in_2b_56": True,
    "no_" "ff" "probe_execution_in_2b_56": True,
    "no_project_" "output_probe_in_2b_56": True,
    "no_user_media_" "input_in_2b_56": True,
    "no_project_" "output_write_in_2b_56": True,
    "no_timeline_" "apply_in_2b_56": True,
}


def build_render_verification_contract_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="render_verification_contract_failed",
                severity="warning",
                message="Render Verification Contract Report fehlt.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "") or "").lower()

    if status == "render_verification_contract_ready":
        signals.append(
            _signal(
                signal_type="render_verification_contract_ready",
                severity="info",
                message="Render Verification Contract ist bereit.",
                metadata={"status": status},
            )
        )
    elif status == "render_verification_contract_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="render_verification_contract_ready_with_warnings",
                severity="warning",
                message="Render Verification Contract ist bereit, aber Warnungen muessen geprueft werden.",
                metadata={"status": status},
            )
        )
    elif status == "render_verification_contract_smoke_probe_ready":
        signals.append(
            _signal(
                signal_type="render_verification_contract_smoke_probe_ready",
                severity="info",
                message="Render Verification Smoke-Probe-Plan ist bereit.",
                metadata={"status": status},
            )
        )
    elif status == "render_verification_contract_blocked":
        signals.append(
            _signal(
                signal_type="render_verification_contract_blocked",
                severity="blocking",
                message="Render Verification Contract ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="render_verification_contract_failed",
                severity="warning",
                message="Render Verification Contract hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    expected_spec = report.get("expected_spec", {})
    if isinstance(expected_spec, dict) and expected_spec:
        signals.append(
            _signal(
                signal_type="render_verification_expected_spec_planned",
                severity="info",
                message="Render Verification Expected Spec wurde geplant.",
                metadata={
                    "container": expected_spec.get("container"),
                    "video_codec": expected_spec.get("video_codec"),
                    "audio_codec": expected_spec.get("audio_codec"),
                    "width": expected_spec.get("width"),
                    "height": expected_spec.get("height"),
                    "fps": expected_spec.get("fps"),
                    "expected_duration_seconds": expected_spec.get(
                        "expected_duration_seconds"
                    ),
                    "duration_tolerance_seconds": expected_spec.get(
                        "duration_tolerance_seconds"
                    ),
                },
            )
        )

    checks = report.get("checks", [])
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, dict):
                continue
            signals.append(
                _signal(
                    signal_type="render_verification_check_planned",
                    severity=str(check.get("severity") or "info"),
                    message="Render Verification Check wurde geplant.",
                    metadata={
                        "check_id": check.get("check_id"),
                        "check_type": check.get("check_type"),
                        "status": check.get("status"),
                        "planned_only": bool(check.get("planned_only", True)),
                        "can_run_now": bool(check.get("can_run_now", False)),
                    },
                )
            )

    probe_plan = report.get("probe_plan", {})
    if isinstance(probe_plan, dict) and probe_plan:
        signals.append(
            _signal(
                signal_type="render_verification_probe_plan_created",
                severity="info",
                message="Render Verification Probe Plan wurde als Preview erstellt.",
                metadata={
                    "tool": probe_plan.get("tool"),
                    "path_hint": probe_plan.get("path_hint"),
                    "target_path_hint": probe_plan.get("target_path_hint"),
                    "argv_preview_count": len(probe_plan.get("argv_preview", []) or []),
                    "can_execute_probe": bool(probe_plan.get("can_execute_probe")),
                    "can_probe_project_" "output": bool(
                        probe_plan.get("can_probe_project_" "output")
                    ),
                },
            )
        )

    if bool(report.get("can_verify_smoke_output")):
        signals.append(
            _signal(
                signal_type="render_verification_smoke_probe_available",
                severity="info",
                message="Smoke Output kann spaeter gezielt verifiziert werden.",
                metadata={
                    "smoke_probe_allowed": bool(report.get("smoke_probe_allowed")),
                    "can_verify_smoke_output": True,
                },
            )
        )

    signals.append(
        _signal(
            signal_type="render_verification_project_output_still_not_allowed",
            severity="info",
            message="Projekt-Output-Probe bleibt in 2B-56 gesperrt.",
            metadata={
                "project_" "output_probe_allowed": False,
                "can_verify_project_" "output": False,
                "can_write_media": False,
            },
        )
    )

    signals.append(
        _signal(
            signal_type="render_verification_media_probe_still_not_allowed",
            severity="info",
            message="Medien-Probe und Render-Rechte bleiben in 2B-56 gesperrt.",
            metadata={
                "can_probe_media_files": False,
                "can_render": False,
                "can_write_media": False,
            },
        )
    )

    for reason in report.get("blocking_reasons", []):
        signals.append(
            _signal(
                signal_type="render_verification_contract_blocked",
                severity="blocking",
                message="Render Verification Contract ist durch einen Blocking Reason blockiert.",
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
        "source": RENDER_VERIFICATION_SIGNAL_SOURCE,
        "signal_type": signal_type,
        "type": signal_type,
        "severity": severity,
        "message": message,
        "action_hint": RENDER_VERIFICATION_ACTION_HINT,
        "metadata": merged_metadata,
    }


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("render_verification_contract_report") or job.get(
            "render_verification_contract"
        )
    else:
        report = getattr(job, "render_verification_contract_report", None) or getattr(
            job,
            "render_verification_contract",
            None,
        )

    if isinstance(report, dict):
        return report
    return {}
