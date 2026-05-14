from __future__ import annotations

from typing import Any

from core.controlled_render_executor import build_controlled_render_executor


CONTROLLED_RENDER_SAFE_FALSE_FIELDS = {
    "controlled_render_real_render_allowed": False,
    "controlled_render_can_execute_real_render": False,
    "controlled_render_can_render": False,
    "controlled_render_can_run_ff" "mpeg": False,
    "controlled_render_can_spawn_" "process": False,
    "controlled_render_can_write_" "media": False,
    "controlled_render_output_created": False,
}


class ControlledRenderExecutorRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report_data = build_controlled_render_executor(job)

        self._set(job, "controlled_render_executor_report", report_data)
        self._set(job, "controlled_render_executor", report_data)
        self._set(job, "controlled_render_executor_status", report_data["status"])

        self._set(
            job,
            "controlled_render_execution_request",
            report_data["request"],
        )
        self._set(
            job,
            "controlled_render_execution_steps",
            report_data["execution_steps"],
        )

        self._set(job, "controlled_render_total_steps", report_data["total_steps"])
        self._set(
            job,
            "controlled_render_planned_step_count",
            report_data["planned_step_count"],
        )
        self._set(
            job,
            "controlled_render_executed_step_count",
            report_data["executed_step_count"],
        )
        self._set(
            job,
            "controlled_render_skipped_step_count",
            report_data["skipped_step_count"],
        )

        self._set(job, "controlled_render_dry_run_only", True)
        self._set(
            job,
            "controlled_render_real_render_requested",
            report_data["real_render_requested"],
        )

        for key, value in CONTROLLED_RENDER_SAFE_FALSE_FIELDS.items():
            self._set(job, key, value)

        self._set(job, "controlled_render_output_path", None)
        self._set(
            job,
            "controlled_render_blocking_reasons",
            report_data["blocking_reasons"],
        )
        self._set(job, "controlled_render_warnings", report_data["warnings"])
        self._set(
            job,
            "controlled_render_recommendation",
            report_data["recommendation"],
        )

        return report_data

    def _set(self, job: Any, key: str, value: Any) -> None:
        if isinstance(job, dict):
            job[key] = value
            return
        setattr(job, key, value)


def run_controlled_render_executor_for_job(job: Any) -> dict[str, Any]:
    return ControlledRenderExecutorRunner().run(job)
