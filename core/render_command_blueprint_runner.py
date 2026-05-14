from __future__ import annotations

from typing import Any

from core.render_command_blueprint_builder import build_render_command_blueprint


RENDER_BLUEPRINT_SAFE_FALSE_FIELDS = {
    "render_blueprint_can_execute_contract": False,
    "render_blueprint_can_render": False,
    "render_blueprint_can_run_ff" "mpeg": False,
    "render_blueprint_can_spawn_process": False,
    "render_blueprint_can_write_media": False,
}


class RenderCommandBlueprintRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report_data = build_render_command_blueprint(job)

        self._set(job, "render_command_blueprint_report", report_data)
        self._set(job, "render_command_blueprint", report_data)
        self._set(job, "render_blueprint_status", report_data["status"])

        self._set(job, "render_blueprint_steps", report_data["blueprint_steps"])
        self._set(job, "render_blueprint_total_steps", report_data["total_steps"])

        self._set(
            job,
            "render_blueprint_trim_step_count",
            report_data["trim_step_count"],
        )
        self._set(
            job,
            "render_blueprint_concat_step_count",
            report_data["concat_step_count"],
        )
        self._set(
            job,
            "render_blueprint_transition_step_count",
            report_data["transition_step_count"],
        )
        self._set(
            job,
            "render_blueprint_audio_mix_step_count",
            report_data["audio_mix_step_count"],
        )
        self._set(
            job,
            "render_blueprint_censor_sfx_step_count",
            report_data["censor_sfx_step_count"],
        )
        self._set(
            job,
            "render_blueprint_subtitle_step_count",
            report_data["subtitle_step_count"],
        )
        self._set(
            job,
            "render_blueprint_encode_step_count",
            report_data["encode_step_count"],
        )

        self._set(job, "render_blueprint_dry_run_only", True)
        self._set(job, "render_blueprint_non_executable", True)
        self._set(
            job,
            "render_blueprint_ready_for_renderer_implementation",
            report_data["ready_for_renderer_implementation"],
        )

        for key, value in RENDER_BLUEPRINT_SAFE_FALSE_FIELDS.items():
            self._set(job, key, value)

        self._set(
            job,
            "render_blueprint_blocking_reasons",
            report_data["blocking_reasons"],
        )
        self._set(job, "render_blueprint_warnings", report_data["warnings"])
        self._set(
            job,
            "render_blueprint_recommendation",
            report_data["recommendation"],
        )

        return report_data

    def _set(self, job: Any, key: str, value: Any) -> None:
        if isinstance(job, dict):
            job[key] = value
            return
        setattr(job, key, value)


def run_render_command_blueprint_for_job(job: Any) -> dict[str, Any]:
    return RenderCommandBlueprintRunner().run(job)
