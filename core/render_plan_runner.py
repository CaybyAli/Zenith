from __future__ import annotations

from typing import Any

from core.render_plan_builder import build_render_plan


RENDER_PLAN_SAFE_FALSE_FIELDS = {
    "render_plan_can_execute_plan": False,
    "render_plan_can_render": False,
    "render_plan_can_run_ffmpeg": False,
    "render_plan_can_write_media": False,
    "render_plan_can_apply_timeline": False,
}


class RenderPlanRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report_data = build_render_plan(job)

        self._set(job, "render_plan_report", report_data)
        self._set(job, "render_plan", report_data)
        self._set(job, "render_plan_status", report_data["status"])

        self._set(job, "render_plan_sources", report_data["sources"])
        self._set(job, "render_plan_segments", report_data["segments"])
        self._set(job, "render_plan_output_targets", report_data["output_targets"])
        self._set(job, "render_plan_operation_intents", report_data["operation_intents"])

        self._set(job, "render_plan_total_segments", report_data["total_segments"])
        self._set(
            job,
            "render_plan_total_duration_seconds",
            report_data["total_duration_seconds"],
        )
        self._set(
            job,
            "render_plan_estimated_output_duration_seconds",
            report_data["estimated_output_duration_seconds"],
        )

        self._set(job, "render_plan_dry_run_only", True)
        self._set(
            job,
            "render_plan_ready_for_renderer_contract",
            report_data["ready_for_renderer_contract"],
        )

        for key, value in RENDER_PLAN_SAFE_FALSE_FIELDS.items():
            self._set(job, key, value)

        self._set(job, "render_plan_blocking_reasons", report_data["blocking_reasons"])
        self._set(job, "render_plan_warnings", report_data["warnings"])
        self._set(job, "render_plan_recommendation", report_data["recommendation"])

        return report_data

    def _set(self, job: Any, key: str, value: Any) -> None:
        if isinstance(job, dict):
            job[key] = value
            return
        setattr(job, key, value)


def run_render_plan_for_job(job: Any) -> dict[str, Any]:
    return RenderPlanRunner().run(job)
