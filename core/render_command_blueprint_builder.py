from __future__ import annotations

from typing import Any

from models.render_command_blueprint import (
    RenderBlueprintStep,
    build_render_blueprint_contract,
)


BLUEPRINT_METADATA = {
    "phase": "2B-47",
    "block": "block8_render_export",
    "render_blueprint_only": True,
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

READY_PLAN_STATUSES = {
    "render_plan_ready",
    "render_plan_ready_with_warnings",
}

DANGER_PLAN_FLAGS = (
    "render_plan_can_execute_plan",
    "render_plan_can_render",
    "render_plan_can_run_ff" "mpeg",
    "render_plan_can_write_media",
    "render_plan_can_apply_timeline",
)

INTENT_TO_STEP_TYPE = {
    "trim_intent": "trim",
    "concat_intent": "concat",
    "transition_intent": "transition",
    "audio_mix_intent": "audio_mix",
    "censor_sfx_intent": "censor_sfx",
    "subtitle_intent": "subtitle",
    "output_encode_intent": "encode",
}


class RenderCommandBlueprintBuilder:
    def build(self, job: Any) -> dict[str, Any]:
        job_id = str(self._get(job, "job_id", self._get(job, "id", "unknown")))

        warnings: list[str] = []
        blocking_reasons: list[str] = []

        plan = self._plan(job)
        self._check_plan(job, plan, warnings, blocking_reasons)

        intents = self._list(
            self._get(job, "render_plan_operation_intents")
            or plan.get("operation_intents")
        )
        if not intents:
            blocking_reasons.append("render_blueprint_operation_intents_missing")

        steps = self._build_steps(intents, warnings, blocking_reasons)
        self._check_steps(steps, blocking_reasons)

        contract = build_render_blueprint_contract(
            job_id=job_id,
            blueprint_steps=steps,
            warnings=self._unique(warnings),
            blocking_reasons=self._unique(blocking_reasons),
            metadata=dict(BLUEPRINT_METADATA),
        )
        return contract.to_dict()

    def _plan(self, job: Any) -> dict[str, Any]:
        return self._dict(
            self._get(job, "render_plan_report")
            or self._get(job, "render_plan")
        )

    def _check_plan(
        self,
        job: Any,
        plan: dict[str, Any],
        warnings: list[str],
        blocking_reasons: list[str],
    ) -> None:
        if not plan:
            blocking_reasons.append("render_blueprint_render_plan_missing")
            return

        status = self._status(self._get(job, "render_plan_status") or plan.get("status"))
        if status not in READY_PLAN_STATUSES:
            blocking_reasons.append("render_blueprint_render_plan_not_ready")

        dry_run_only = self._truthy(
            self._get(job, "render_plan_dry_run_only")
            if self._get(job, "render_plan_dry_run_only") is not None
            else plan.get("dry_run_only")
        )
        if not dry_run_only:
            blocking_reasons.append("render_blueprint_plan_not_dry_run_only")

        ready_for_contract = self._truthy(
            self._get(job, "render_plan_ready_for_renderer_contract")
            if self._get(job, "render_plan_ready_for_renderer_contract") is not None
            else plan.get("ready_for_renderer_contract")
        )
        if not ready_for_contract:
            blocking_reasons.append("render_blueprint_plan_not_ready_for_contract")

        plan_blocking = self._string_list(
            self._get(job, "render_plan_blocking_reasons")
            or plan.get("blocking_reasons")
        )
        if plan_blocking:
            blocking_reasons.append("render_blueprint_plan_has_blocking_reasons")
            blocking_reasons.extend([f"render_plan_blocking:{item}" for item in plan_blocking])

        plan_warnings = self._string_list(
            self._get(job, "render_plan_warnings")
            or plan.get("warnings")
        )
        warnings.extend([f"render_plan_warning:{item}" for item in plan_warnings])

        for flag_name in DANGER_PLAN_FLAGS:
            value = self._get(job, flag_name)
            if value is None:
                key = flag_name.replace("render_plan_", "")
                value = plan.get(key)
            if self._truthy(value):
                blocking_reasons.append(f"render_blueprint_dangerous_plan_flag:{flag_name}")

    def _build_steps(
        self,
        intents: list[dict[str, Any]],
        warnings: list[str],
        blocking_reasons: list[str],
    ) -> list[RenderBlueprintStep]:
        steps: list[RenderBlueprintStep] = []

        for index, intent in enumerate(intents, start=1):
            intent_type = str(intent.get("intent_type") or "").strip()
            step_type = INTENT_TO_STEP_TYPE.get(intent_type)

            if not step_type:
                warnings.append(f"render_blueprint_unknown_intent_type:{intent_type or 'missing'}")
                continue

            if self._truthy(intent.get("can_execute_now")):
                blocking_reasons.append("render_blueprint_intent_marked_executable")

            if not self._truthy(intent.get("requires_later_renderer"), default=True):
                blocking_reasons.append("render_blueprint_intent_missing_later_renderer_flag")

            step = RenderBlueprintStep(
                step_id=f"render_blueprint_step_{index}",
                step_type=step_type,
                order_index=index,
                description=str(
                    intent.get("description")
                    or f"Plan later renderer implementation for {step_type} step."
                ),
                source_segment_id=self._optional_text(intent.get("source_segment_id")),
                target_segment_id=self._optional_text(intent.get("target_segment_id")),
                planned_inputs=[
                    {
                        "input_type": "render_plan_intent",
                        "intent_id": intent.get("intent_id"),
                        "intent_type": intent_type,
                        "planned_only": True,
                    }
                ],
                planned_outputs=[
                    {
                        "output_type": "blueprint_step",
                        "step_type": step_type,
                        "planned_only": True,
                    }
                ],
                filter_intents=[
                    {
                        "intent_type": intent_type,
                        "step_type": step_type,
                        "planned_only": True,
                        "requires_renderer_implementation": True,
                        "metadata": dict(intent.get("metadata") or {}),
                    }
                ],
                safety_notes=[
                    "non_executable_blueprint_only",
                    "no_media_access",
                    "no_process_spawn",
                    "future_renderer_required",
                ],
                can_execute_now=False,
                requires_renderer_implementation=True,
                warnings=self._string_list(intent.get("warnings")),
                blocking_reasons=[],
                metadata={
                    **BLUEPRINT_METADATA,
                    "source_intent_id": intent.get("intent_id"),
                    "source_intent_type": intent_type,
                },
            )
            steps.append(step)

        return steps

    def _check_steps(
        self,
        steps: list[RenderBlueprintStep],
        blocking_reasons: list[str],
    ) -> None:
        if not steps:
            blocking_reasons.append("render_blueprint_steps_missing")
            return

        for step in steps:
            if step.can_execute_now:
                blocking_reasons.append("render_blueprint_step_marked_executable")
            if not step.requires_renderer_implementation:
                blocking_reasons.append("render_blueprint_step_missing_renderer_flag")

    def _get(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _dict(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _list(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, dict)]

    def _status(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().lower()

    def _truthy(self, value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {
                "true",
                "1",
                "yes",
                "ready",
                "safe",
                "passed",
                "approved",
            }
        return bool(value)

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item)]
        if isinstance(value, tuple):
            return [str(item) for item in value if str(item)]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _unique(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result


def build_render_command_blueprint(job: Any) -> dict[str, Any]:
    return RenderCommandBlueprintBuilder().build(job)
