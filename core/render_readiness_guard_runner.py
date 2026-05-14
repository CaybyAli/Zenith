from __future__ import annotations

from typing import Any

from core.render_readiness_guard import evaluate_render_readiness


RENDER_READINESS_SAFE_FALSE_FIELDS = {
    "render_readiness_can_render": False,
    "render_readiness_can_run_ffmpeg": False,
    "render_readiness_can_execute_media_operations": False,
    "render_readiness_can_apply_timeline": False,
    "render_readiness_can_modify_media": False,
}


class RenderReadinessGuardRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report = evaluate_render_readiness(job)
        report_data = report.to_dict()

        self._set(job, "render_readiness_guard_report", report_data)
        self._set(job, "render_readiness_guard", report_data)
        self._set(job, "render_readiness_status", report_data["status"])
        self._set(job, "render_readiness_checks", report_data["checks"])

        self._set(job, "render_readiness_total_checks", report_data["total_checks"])
        self._set(job, "render_readiness_passed_count", report_data["passed_count"])
        self._set(job, "render_readiness_warning_count", report_data["warning_count"])
        self._set(job, "render_readiness_blocking_count", report_data["blocking_count"])

        self._set(job, "render_readiness_review_required", report_data["review_required"])
        self._set(
            job,
            "render_readiness_ready_for_next_render_stage",
            report_data["ready_for_next_render_stage"],
        )
        self._set(
            job,
            "render_readiness_can_start_render_pipeline",
            report_data["can_start_render_pipeline"],
        )

        for key, value in RENDER_READINESS_SAFE_FALSE_FIELDS.items():
            self._set(job, key, value)

        self._set(job, "render_readiness_blocking_reasons", report_data["blocking_reasons"])
        self._set(job, "render_readiness_warnings", report_data["warnings"])
        self._set(job, "render_readiness_recommendation", report_data["recommendation"])

        return report_data

    def _set(self, job: Any, key: str, value: Any) -> None:
        if isinstance(job, dict):
            job[key] = value
            return
        setattr(job, key, value)


def run_render_readiness_guard(job: Any) -> dict[str, Any]:
    return RenderReadinessGuardRunner().run(job)
