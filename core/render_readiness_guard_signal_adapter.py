from __future__ import annotations

from typing import Any


RENDER_READINESS_SIGNAL_SOURCE = "render_readiness_guard"
RENDER_READINESS_ACTION_HINT = "review_render_readiness"

SIGNAL_METADATA = {
    "render_readiness_guard_only": True,
    "media_unchanged": True,
    "no_execution_in_2b_45": True,
    "no_render_in_2b_45": True,
    "no_ffmpeg_in_2b_45": True,
    "no_media_write_in_2b_45": True,
    "no_timeline_apply_in_2b_45": True,
}


def build_render_readiness_guard_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="render_readiness_failed",
                severity="warning",
                message="Render Readiness Guard Report fehlt.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "")).lower()

    if status == "render_readiness_ready":
        signals.append(
            _signal(
                signal_type="render_readiness_ready",
                severity="info",
                message="Render Readiness Guard ist ready f?r die n?chste Render-Stufe.",
                metadata={"status": status},
            )
        )
        signals.append(
            _signal(
                signal_type="render_readiness_ready_for_next_stage",
                severity="info",
                message="N?chste Render-Stufe darf geplant werden. 2B-45 rendert nicht.",
                metadata={"status": status},
            )
        )
    elif status == "render_readiness_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="render_readiness_ready_with_warnings",
                severity="warning",
                message="Render Readiness Guard ist ready mit Warnungen.",
                metadata={"status": status},
            )
        )
        signals.append(
            _signal(
                signal_type="render_readiness_ready_for_next_stage",
                severity="warning",
                message="N?chste Render-Stufe darf geplant werden, aber Warnungen pr?fen.",
                metadata={"status": status},
            )
        )
    elif status == "render_readiness_blocked":
        signals.append(
            _signal(
                signal_type="render_readiness_blocked",
                severity="blocking",
                message="Render Readiness Guard blockiert die n?chste Render-Stufe.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="render_readiness_failed",
                severity="warning",
                message="Render Readiness Guard hat keinen klaren Ready-Status.",
                metadata={"status": status},
            )
        )

    for check in report.get("checks", []):
        if isinstance(check, dict):
            signals.extend(_signals_for_check(check))

    return signals


def _signals_for_check(check: dict[str, Any]) -> list[dict[str, Any]]:
    status = str(check.get("status", "")).lower()
    check_id = str(check.get("check_id", "")).lower()
    message = str(check.get("message", ""))

    if status not in {"warning", "blocked", "failed"}:
        return []

    severity = "blocking" if status in {"blocked", "failed"} else "warning"

    mapping = {
        "timeline_approval_approved": "render_readiness_approval_missing",
        "timeline_safety_passed": "render_readiness_safety_blocked",
        "final_quality_not_blocked": "render_readiness_final_quality_blocked",
        "no_render_permission_leaked": "render_readiness_render_permission_leak",
        "no_execution_permission_leaked": "render_readiness_execution_permission_leak",
        "dashboard_package_ready": "render_readiness_dashboard_not_ready",
    }

    signal_type = mapping.get(check_id)
    if not signal_type:
        return []

    return [
        _signal(
            signal_type=signal_type,
            severity=severity,
            message=message,
            metadata={
                "check_id": check_id,
                "check_status": status,
            },
        )
    ]


def _signal(
    signal_type: str,
    severity: str,
    message: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    merged_metadata = dict(SIGNAL_METADATA)
    merged_metadata.update(metadata)
    return {
        "source": RENDER_READINESS_SIGNAL_SOURCE,
        "signal_type": signal_type,
        "type": signal_type,
        "severity": severity,
        "message": message,
        "action_hint": RENDER_READINESS_ACTION_HINT,
        "metadata": merged_metadata,
    }


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("render_readiness_guard_report") or job.get("render_readiness_guard")
    else:
        report = getattr(job, "render_readiness_guard_report", None) or getattr(
            job,
            "render_readiness_guard",
            None,
        )

    if isinstance(report, dict):
        return report

    if hasattr(report, "to_dict"):
        return report.to_dict()

    return {}
