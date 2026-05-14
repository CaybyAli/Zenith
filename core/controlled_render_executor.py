from __future__ import annotations

from typing import Any

from models.controlled_render_executor import (
    CONTROLLED_RENDER_EXECUTOR_METADATA,
    CONTROLLED_RENDER_EXECUTOR_STATUS_BLOCKED,
    CONTROLLED_RENDER_EXECUTOR_STATUS_DRY_RUN_READY,
    CONTROLLED_RENDER_EXECUTOR_STATUS_DRY_RUN_WITH_WARNINGS,
    ControlledRenderExecutionStep,
    build_controlled_render_execution_report,
    build_controlled_render_execution_request,
)


READY_PERMISSION_STATUSES = {
    "render_execution_permission_ready",
    "render_execution_permission_ready_with_warnings",
}

READY_ASSET_STATUSES = {
    "render_asset_manifest_ready",
    "render_asset_manifest_ready_with_warnings",
}

DANGEROUS_ASSET_FLAGS = (
    "render_asset_can_write_files",
    "render_asset_can_open_media",
    "render_asset_can_render",
    "render_asset_can_run_ff" "mpeg",
)


class ControlledRenderExecutor:
    def build(self, job: Any) -> dict[str, Any]:
        job_id = str(self._get(job, "job_id", self._get(job, "id", "unknown")))

        warnings: list[str] = []
        blocking_reasons: list[str] = []

        self._check_permission_gate(job, blocking_reasons, warnings)
        self._check_blueprint(job, blocking_reasons)
        self._check_asset_manifest(job, blocking_reasons)

        request = self._build_request(job, job_id)
        request_data = request.to_dict()

        real_render_requested = bool(
            request_data.get("requested_mode") == "real_render"
            or request_data.get("allow_real_render") is True
        )
        if real_render_requested:
            self._append_once(
                blocking_reasons,
                "real_render_execution_not_implemented_in_2b_50",
            )

        steps = self._build_steps(job)

        if blocking_reasons:
            status = CONTROLLED_RENDER_EXECUTOR_STATUS_BLOCKED
            recommendation = "Controlled Render Executor blockiert. Dry-Run Eingaben pruefen."
        elif warnings:
            status = CONTROLLED_RENDER_EXECUTOR_STATUS_DRY_RUN_WITH_WARNINGS
            recommendation = "Controlled Render Executor Dry-Run ist bereit, aber Warnungen pruefen."
        else:
            status = CONTROLLED_RENDER_EXECUTOR_STATUS_DRY_RUN_READY
            recommendation = "Controlled Render Executor Dry-Run ist bereit. Keine echte Ausfuehrung in 2B-50."

        report = build_controlled_render_execution_report(
            job_id=job_id,
            status=status,
            request=request,
            execution_steps=steps,
            warnings=warnings,
            blocking_reasons=blocking_reasons,
            recommendation=recommendation,
            metadata=dict(CONTROLLED_RENDER_EXECUTOR_METADATA),
        )
        return report.to_dict()

    def _check_permission_gate(
        self,
        job: Any,
        blocking_reasons: list[str],
        warnings: list[str],
    ) -> None:
        report = self._get(job, "render_execution_permission_report")
        status = self._status(self._get(job, "render_execution_permission_status"))

        if not isinstance(report, dict) or not report:
            self._append_once(blocking_reasons, "render_execution_permission_gate_missing")

        if status not in READY_PERMISSION_STATUSES:
            self._append_once(blocking_reasons, "render_execution_permission_gate_not_ready")

        if not self._truthy(self._get(job, "render_execution_ready_for_real_render_stage")):
            self._append_once(blocking_reasons, "render_execution_stage_not_ready")

        if not self._truthy(
            self._get(job, "render_execution_can_prepare_real_render_execution")
        ):
            self._append_once(blocking_reasons, "render_execution_prepare_not_allowed")

        if not self._truthy(self._get(job, "render_execution_human_approved")):
            self._append_once(blocking_reasons, "render_execution_human_approval_missing")

        approval_name = self._first_text(self._get(job, "render_execution_approved_by"))
        if self._truthy(self._get(job, "render_execution_human_approved")) and not approval_name:
            self._append_once(warnings, "render_execution_approval_identity_missing")

        for reason in self._string_list(self._get(job, "render_execution_blocking_reasons")):
            self._append_once(blocking_reasons, f"permission_gate:{reason}")

    def _check_blueprint(self, job: Any, blocking_reasons: list[str]) -> None:
        blueprint = self._get(job, "render_command_blueprint")
        blueprint_report = self._get(job, "render_command_blueprint_report")
        steps = self._blueprint_steps(job)

        if (
            not isinstance(blueprint, dict)
            or not blueprint
            or not isinstance(blueprint_report, dict)
            or not blueprint_report
        ):
            self._append_once(blocking_reasons, "render_blueprint_missing")

        if not steps:
            self._append_once(blocking_reasons, "render_blueprint_steps_missing")

        if not self._truthy(self._get(job, "render_blueprint_non_executable")):
            self._append_once(blocking_reasons, "render_blueprint_not_non_executable")

        if not self._truthy(
            self._get(job, "render_blueprint_ready_for_renderer_implementation")
        ):
            self._append_once(blocking_reasons, "render_blueprint_not_ready_for_renderer")

    def _check_asset_manifest(self, job: Any, blocking_reasons: list[str]) -> None:
        report = self._get(job, "render_asset_manifest_report")
        status = self._status(self._get(job, "render_asset_manifest_status"))

        if not isinstance(report, dict) or not report:
            self._append_once(blocking_reasons, "render_asset_manifest_missing")

        if status not in READY_ASSET_STATUSES:
            self._append_once(blocking_reasons, "render_asset_manifest_not_ready")

        for field_name in DANGEROUS_ASSET_FLAGS:
            if self._truthy(self._get(job, field_name)):
                self._append_once(
                    blocking_reasons,
                    f"dangerous_asset_flag_enabled:{field_name}",
                )

    def _build_request(self, job: Any, job_id: str):
        return build_controlled_render_execution_request(
            job_id=job_id,
            requested_mode=self._requested_mode(
                self._get(job, "render_execution_requested_mode", "dry_run")
            ),
            allow_real_render=self._truthy(
                self._get(job, "render_execution_allow_real_render")
            ),
            allow_tool=self._truthy(self._get(job, "render_execution_allow_ff" "mpeg")),
            allow_proc_spawn=self._truthy(
                self._get(job, "render_execution_allow_process_" "spawn")
            ),
            allow_media_out=self._truthy(
                self._get(job, "render_execution_allow_media_" "write")
            ),
            human_approved=self._truthy(self._get(job, "render_execution_human_approved")),
            approved_by=self._first_text(self._get(job, "render_execution_approved_by")),
            metadata=dict(CONTROLLED_RENDER_EXECUTOR_METADATA),
        )

    def _build_steps(self, job: Any) -> list[ControlledRenderExecutionStep]:
        steps: list[ControlledRenderExecutionStep] = []
        for index, blueprint_step in enumerate(self._blueprint_steps(job), start=1):
            step_data = dict(blueprint_step or {})
            source_step_id = self._first_text(
                step_data.get("step_id")
                or step_data.get("id")
                or step_data.get("blueprint_step_id")
            )
            step_type = self._first_text(
                step_data.get("step_type")
                or step_data.get("type")
                or step_data.get("action")
            ) or "blueprint_step"
            description = self._first_text(
                step_data.get("description")
                or step_data.get("summary")
                or step_data.get("label")
            )

            steps.append(
                ControlledRenderExecutionStep(
                    step_id=f"controlled_render_step_{index}",
                    step_type=step_type,
                    order_index=index,
                    source_blueprint_step_id=source_step_id,
                    description=description,
                    execution_mode="dry_run",
                    would_execute=True,
                    executed=False,
                    skipped_reason="dry_run_only_in_2b_50",
                    safety_status="dry_run_only",
                    warnings=[],
                    blocking_reasons=[],
                    metadata={
                        **dict(CONTROLLED_RENDER_EXECUTOR_METADATA),
                        "source_blueprint_step": step_data,
                    },
                )
            )
        return steps

    def _blueprint_steps(self, job: Any) -> list[dict[str, Any]]:
        direct_steps = self._list_of_dicts(self._get(job, "render_blueprint_steps"))
        if direct_steps:
            return direct_steps

        blueprint = self._get(job, "render_command_blueprint")
        if isinstance(blueprint, dict):
            nested_steps = self._list_of_dicts(blueprint.get("steps"))
            if nested_steps:
                return nested_steps

        report = self._get(job, "render_command_blueprint_report")
        if isinstance(report, dict):
            report_steps = self._list_of_dicts(report.get("steps"))
            if report_steps:
                return report_steps
            report_steps = self._list_of_dicts(report.get("blueprint_steps"))
            if report_steps:
                return report_steps

        return []

    def _requested_mode(self, value: Any) -> str:
        mode = self._status(value)
        if mode in {"real_render", "dry_run"}:
            return mode
        return "dry_run"

    def _get(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

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

    def _first_text(self, value: Any) -> str | None:
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

    def _list_of_dicts(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        result: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                result.append(dict(item))
        return result

    def _append_once(self, items: list[str], value: str) -> None:
        text = str(value).strip()
        if text and text not in items:
            items.append(text)


def build_controlled_render_executor(job: Any) -> dict[str, Any]:
    return ControlledRenderExecutor().build(job)
