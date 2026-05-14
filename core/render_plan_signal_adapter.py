from __future__ import annotations

from typing import Any


RENDER_PLAN_SIGNAL_SOURCE = "render_plan"
RENDER_PLAN_ACTION_HINT = "review_render_plan"

SIGNAL_METADATA = {
    "render_plan_only": True,
    "dry_run_only": True,
    "renderer_contract_only": True,
    "media_unchanged": True,
    "no_execution_in_2b_46": True,
    "no_render_in_2b_46": True,
    "no_ff" "mpeg_in_2b_46": True,
    "no_media_write_in_2b_46": True,
    "no_timeline_" "apply_in_2b_46": True,
    "no_exec_commands_in_2b_46": True,
}


def build_render_plan_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="render_plan_failed",
                severity="warning",
                message="Render Plan Report fehlt.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "")).lower()

    if status == "render_plan_ready":
        signals.append(
            _signal(
                signal_type="render_plan_ready",
                severity="info",
                message="Render Plan ist als Dry-Run-Vertrag bereit.",
                metadata={"status": status},
            )
        )
    elif status == "render_plan_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="render_plan_ready_with_warnings",
                severity="warning",
                message="Render Plan ist bereit, aber Warnungen müssen geprüft werden.",
                metadata={"status": status},
            )
        )
    elif status == "render_plan_blocked":
        signals.append(
            _signal(
                signal_type="render_plan_blocked",
                severity="blocking",
                message="Render Plan ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="render_plan_failed",
                severity="warning",
                message="Render Plan hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    if bool(report.get("ready_for_renderer_contract")):
        signals.append(
            _signal(
                signal_type="render_plan_contract_ready",
                severity="info",
                message="Render Plan Contract ist bereit für die spätere Renderer-Phase.",
                metadata={"ready_for_renderer_contract": True},
            )
        )

    for segment in report.get("segments", []):
        if isinstance(segment, dict):
            signals.append(_segment_signal(segment))
            if segment.get("blocking_reasons"):
                signals.append(
                    _signal(
                        signal_type="render_plan_invalid_timing",
                        severity="blocking",
                        message="Render Plan Segment hat Timing-Probleme.",
                        metadata={
                            "segment_id": segment.get("segment_id"),
                            "blocking_reasons": segment.get("blocking_reasons", []),
                        },
                    )
                )

    for target in report.get("output_targets", []):
        if isinstance(target, dict):
            signals.append(_output_target_signal(target))

    for intent in report.get("operation_intents", []):
        if isinstance(intent, dict):
            signals.append(_operation_intent_signal(intent))

    for warning in report.get("warnings", []):
        warning_text = str(warning)
        if "source_hint" in warning_text:
            signals.append(
                _signal(
                    signal_type="render_plan_missing_source_hint",
                    severity="warning",
                    message="Render Plan hat keinen sicheren Source-Hinweis.",
                    metadata={"warning": warning_text},
                )
            )

    for reason in report.get("blocking_reasons", []):
        reason_text = str(reason)
        if "guard" in reason_text:
            signals.append(
                _signal(
                    signal_type="render_plan_guard_not_ready",
                    severity="blocking",
                    message="Render Readiness Guard ist für den Render Plan nicht ready.",
                    metadata={"blocking_reason": reason_text},
                )
            )
        if "no_timeline_items" in reason_text or "timeline_items_missing" in reason_text:
            signals.append(
                _signal(
                    signal_type="render_plan_no_timeline_items",
                    severity="blocking",
                    message="Render Plan kann ohne Timeline Items nicht gebaut werden.",
                    metadata={"blocking_reason": reason_text},
                )
            )

    return signals


def _segment_signal(segment: dict[str, Any]) -> dict[str, Any]:
    return _signal(
        signal_type="render_plan_segment_planned",
        severity="info",
        message="Render Plan Segment wurde geplant.",
        metadata={
            "segment_id": segment.get("segment_id"),
            "source_start_seconds": segment.get("source_start_seconds"),
            "source_end_seconds": segment.get("source_end_seconds"),
            "output_start_seconds": segment.get("output_start_seconds"),
            "output_end_seconds": segment.get("output_end_seconds"),
            "duration_seconds": segment.get("duration_seconds"),
        },
    )


def _output_target_signal(target: dict[str, Any]) -> dict[str, Any]:
    return _signal(
        signal_type="render_plan_output_target_planned",
        severity="info",
        message="Render Plan Output Target wurde geplant.",
        metadata={
            "target_id": target.get("target_id"),
            "target_format": target.get("target_format"),
            "container": target.get("container"),
            "platform": target.get("platform"),
        },
    )


def _operation_intent_signal(intent: dict[str, Any]) -> dict[str, Any]:
    severity = "warning" if bool(intent.get("can_execute_now")) else "info"
    return _signal(
        signal_type="render_plan_operation_intent",
        severity=severity,
        message="Render Plan Operation Intent wurde geplant.",
        metadata={
            "intent_id": intent.get("intent_id"),
            "intent_type": intent.get("intent_type"),
            "can_execute_now": bool(intent.get("can_execute_now")),
            "requires_later_renderer": bool(intent.get("requires_later_renderer")),
        },
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
        "source": RENDER_PLAN_SIGNAL_SOURCE,
        "signal_type": signal_type,
        "type": signal_type,
        "severity": severity,
        "message": message,
        "action_hint": RENDER_PLAN_ACTION_HINT,
        "metadata": merged_metadata,
    }


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("render_plan_report") or job.get("render_plan")
    else:
        report = getattr(job, "render_plan_report", None) or getattr(
            job,
            "render_plan",
            None,
        )

    if isinstance(report, dict):
        return report

    if hasattr(report, "to_dict"):
        return report.to_dict()

    return {}
