from __future__ import annotations

from typing import Any

from core.output_format_handler import build_output_format_contract


OUTPUT_FORMAT_JOB_FIELDS = [
    "output_format_contract_report",
    "output_format_contract_status",
    "output_format_selected_preset",
    "output_format_available_presets",
    "output_format_selected_profile",
    "output_format_selected_platform",
    "output_format_selected_target_format",
    "output_video_spec",
    "output_audio_spec",
    "output_container_spec",
    "output_filename_hint",
    "output_safe_filename_hint",
    "output_path_hint",
    "output_can_prepare_output_format",
    "output_can_render",
    "output_can_write_project_" "output",
    "output_can_process_user_" "media",
    "output_can_execute_ff" "mpeg",
    "output_dry_run_only",
    "output_contract_only",
    "output_format_blocking_reasons",
    "output_format_warnings",
    "output_format_recommendation",
]


class OutputFormatHandlerRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report = build_output_format_contract(job)
        report_dict = report.to_dict()
        preset = report_dict.get("preset", {})
        video = preset.get("video", {}) if isinstance(preset, dict) else {}
        audio = preset.get("audio", {}) if isinstance(preset, dict) else {}
        container = preset.get("container", {}) if isinstance(preset, dict) else {}

        _assign(job, "output_format_contract_report", report_dict)
        _assign(job, "output_format_contract_status", report_dict.get("status"))
        _assign(job, "output_format_selected_preset", preset.get("preset_id"))
        _assign(job, "output_format_available_presets", report_dict.get("available_presets", []))
        _assign(job, "output_format_selected_profile", report_dict.get("selected_profile"))
        _assign(job, "output_format_selected_platform", report_dict.get("selected_platform"))
        _assign(job, "output_format_selected_target_format", report_dict.get("selected_target_format"))

        _assign(job, "output_video_spec", video)
        _assign(job, "output_audio_spec", audio)
        _assign(job, "output_container_spec", container)

        _assign(job, "output_filename_hint", preset.get("filename_hint"))
        _assign(job, "output_safe_filename_hint", preset.get("safe_filename_hint"))
        _assign(job, "output_path_hint", preset.get("output_path_hint"))

        _assign(job, "output_can_prepare_output_format", bool(report_dict.get("can_prepare_output_format")))
        _assign(job, "output_can_render", False)
        _assign(job, "output_can_write_project_" "output", False)
        _assign(job, "output_can_process_user_" "media", False)
        _assign(job, "output_can_execute_ff" "mpeg", False)
        _assign(job, "output_dry_run_only", True)
        _assign(job, "output_contract_only", True)

        _assign(job, "output_format_blocking_reasons", report_dict.get("blocking_reasons", []))
        _assign(job, "output_format_warnings", report_dict.get("warnings", []))
        _assign(job, "output_format_recommendation", report_dict.get("recommendation"))

        return report_dict


def run_output_format_handler(job: Any) -> dict[str, Any]:
    return OutputFormatHandlerRunner().run(job)


def _assign(job: Any, name: str, value: Any) -> None:
    if isinstance(job, dict):
        job[name] = value
        return
    setattr(job, name, value)
