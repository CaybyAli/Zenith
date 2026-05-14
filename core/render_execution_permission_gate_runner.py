from __future__ import annotations

from typing import Any

from core.render_execution_permission_gate import build_render_execution_permission_gate


RENDER_EXECUTION_SAFE_FALSE_FIELDS = {
    "render_execution_can_render": False,
    "render_execution_can_run_ff" "mpeg": False,
    "render_execution_can_spawn_" "process": False,
    "render_execution_can_write_" "media": False,
    "render_execution_can_apply_" "timeline": False,
}


class RenderExecutionPermissionGateRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report_data = build_render_execution_permission_gate(job)

        self._set(job, "render_execution_permission_report", report_data)
        self._set(job, "render_execution_permission_gate", report_data)
        self._set(job, "render_execution_permission_status", report_data["status"])
        self._set(job, "render_execution_permission_checks", report_data["checks"])

        self._set(
            job,
            "render_execution_permission_total_checks",
            report_data["total_checks"],
        )
        self._set(
            job,
            "render_execution_permission_passed_count",
            report_data["passed_count"],
        )
        self._set(
            job,
            "render_execution_permission_warning_count",
            report_data["warning_count"],
        )
        self._set(
            job,
            "render_execution_permission_blocking_count",
            report_data["blocking_count"],
        )
        self._set(
            job,
            "render_execution_permission_review_required",
            report_data["review_required"],
        )

        self._set(
            job,
            "render_execution_ready_for_real_render_stage",
            report_data["ready_for_real_render_stage"],
        )
        self._set(
            job,
            "render_execution_can_prepare_real_render_execution",
            report_data["can_prepare_real_render_execution"],
        )

        for key, value in RENDER_EXECUTION_SAFE_FALSE_FIELDS.items():
            self._set(job, key, value)

        self._set(
            job,
            "render_execution_human_approved",
            report_data["human_approved"],
        )
        self._set(job, "render_execution_approved_by", report_data["approved_by"])
        self._set(job, "render_execution_approved_at", report_data["approved_at"])
        self._set(
            job,
            "render_execution_approval_reason",
            report_data["approval_reason"],
        )

        self._set(
            job,
            "render_execution_blocking_reasons",
            report_data["blocking_reasons"],
        )
        self._set(job, "render_execution_warnings", report_data["warnings"])
        self._set(
            job,
            "render_execution_recommendation",
            report_data["recommendation"],
        )

        return report_data

    def _set(self, job: Any, key: str, value: Any) -> None:
        if isinstance(job, dict):
            job[key] = value
            return
        setattr(job, key, value)


def run_render_execution_permission_gate_for_job(job: Any) -> dict[str, Any]:
    return RenderExecutionPermissionGateRunner().run(job)
