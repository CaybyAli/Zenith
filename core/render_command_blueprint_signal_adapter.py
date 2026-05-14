from __future__ import annotations

from typing import Any


RENDER_BLUEPRINT_SIGNAL_SOURCE = "render_command_blueprint"
RENDER_BLUEPRINT_ACTION_HINT = "review_render_command_blueprint"

SIGNAL_METADATA = {
    "render_command_blueprint_only": True,
    "dry_run_only": True,
    "non_executable": True,
    "renderer_contract_only": True,
    "media_unchanged": True,
    "no_execution_in_2b_47": True,
    "no_render_in_2b_47": True,
    "no_ff" "mpeg_in_2b_47": True,
    "no_process_spawn_in_2b_47": True,
    "no_media_write_in_2b_47": True,
    "no_timeline_" "apply_in_2b_47": True,
    "no_exec_key_payloads_in_2b_47": True,
}

STEP_SIGNAL_TYPES = {
    "trim": "render_blueprint_trim_step",
    "concat": "render_blueprint_concat_step",
    "transition": "render_blueprint_transition_step",
    "audio_mix": "render_blueprint_audio_mix_step",
    "censor_sfx": "render_blueprint_censor_sfx_step",
    "subtitle": "render_blueprint_subtitle_step",
    "encode": "render_blueprint_encode_step",
}


def build_render_command_blueprint_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="render_blueprint_failed",
                severity="warning",
                message="Render Blueprint Report fehlt.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "")).lower()

    if status == "render_blueprint_ready":
        signals.append(
            _signal(
                signal_type="render_blueprint_ready",
                severity="info",
                message="Render Blueprint ist bereit.",
                metadata={"status": status},
            )
        )
    elif status == "render_blueprint_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="render_blueprint_ready_with_warnings",
                severity="warning",
                message="Render Blueprint ist bereit, aber Warnungen m?ssen gepr?ft werden.",
                metadata={"status": status},
            )
        )
    elif status == "render_blueprint_blocked":
        signals.append(
            _signal(
                signal_type="render_blueprint_blocked",
                severity="blocking",
                message="Render Blueprint ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="render_blueprint_failed",
                severity="warning",
                message="Render Blueprint hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    if bool(report.get("ready_for_renderer_implementation")):
        signals.append(
            _signal(
                signal_type="render_blueprint_contract_ready",
                severity="info",
                message="Render Blueprint Contract ist bereit f?r sp?tere Renderer-Implementierung.",
                metadata={"ready_for_renderer_implementation": True},
            )
        )

    if bool(report.get("non_executable")):
        signals.append(
            _signal(
                signal_type="render_blueprint_non_executable_confirmed",
                severity="info",
                message="Render Blueprint ist ausdr?cklich nicht ausf?hrbar.",
                metadata={"non_executable": True},
            )
        )

    for step in report.get("blueprint_steps", []):
        if not isinstance(step, dict):
            continue

        signals.append(_step_signal(step))

        step_type = str(step.get("step_type") or "")
        signal_type = STEP_SIGNAL_TYPES.get(step_type)
        if signal_type:
            signals.append(
                _signal(
                    signal_type=signal_type,
                    severity="info",
                    message=f"Render Blueprint Step geplant: {step_type}.",
                    metadata={
                        "step_id": step.get("step_id"),
                        "step_type": step_type,
                        "order_index": step.get("order_index"),
                    },
                )
            )

        if bool(step.get("can_execute_now")):
            signals.append(
                _signal(
                    signal_type="render_blueprint_command_key_blocked",
                    severity="blocking",
                    message="Render Blueprint Step wurde als ausf?hrbar markiert und ist blockiert.",
                    metadata={
                        "step_id": step.get("step_id"),
                        "step_type": step_type,
                        "can_execute_now": True,
                    },
                )
            )

    for reason in report.get("blocking_reasons", []):
        reason_text = str(reason)
        if "render_plan" in reason_text or "plan" in reason_text:
            signals.append(
                _signal(
                    signal_type="render_blueprint_render_plan_not_ready",
                    severity="blocking",
                    message="Render Blueprint ist durch Render Plan Zustand blockiert.",
                    metadata={"blocking_reason": reason_text},
                )
            )
        if "key" in reason_text or "executable" in reason_text:
            signals.append(
                _signal(
                    signal_type="render_blueprint_command_key_blocked",
                    severity="blocking",
                    message="Render Blueprint enth?lt eine gesperrte ausf?hrbare Markierung.",
                    metadata={"blocking_reason": reason_text},
                )
            )

    return signals


def _step_signal(step: dict[str, Any]) -> dict[str, Any]:
    return _signal(
        signal_type="render_blueprint_step_planned",
        severity="info",
        message="Render Blueprint Step wurde geplant.",
        metadata={
            "step_id": step.get("step_id"),
            "step_type": step.get("step_type"),
            "order_index": step.get("order_index"),
            "source_segment_id": step.get("source_segment_id"),
            "target_segment_id": step.get("target_segment_id"),
            "can_execute_now": bool(step.get("can_execute_now")),
            "requires_renderer_implementation": bool(
                step.get("requires_renderer_implementation")
            ),
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
        "source": RENDER_BLUEPRINT_SIGNAL_SOURCE,
        "signal_type": signal_type,
        "type": signal_type,
        "severity": severity,
        "message": message,
        "action_hint": RENDER_BLUEPRINT_ACTION_HINT,
        "metadata": merged_metadata,
    }


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("render_command_blueprint_report") or job.get(
            "render_command_blueprint"
        )
    else:
        report = getattr(job, "render_command_blueprint_report", None) or getattr(
            job,
            "render_command_blueprint",
            None,
        )

    if isinstance(report, dict):
        return report

    if hasattr(report, "to_dict"):
        return report.to_dict()

    return {}
