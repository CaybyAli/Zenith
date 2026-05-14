from __future__ import annotations

from typing import Any, Dict

from core.final_quality_validator import validate_final_quality


FINAL_QUALITY_JOB_DEFAULTS = {
    "final_quality_can_apply_fixes": False,
    "final_quality_can_render": False,
    "final_quality_can_execute_timeline": False,
    "final_quality_can_reorder_timeline": False,
    "final_quality_can_trim": False,
    "final_quality_can_extend": False,
    "final_quality_can_insert_effects": False,
}


class FinalQualityValidatorRunner:
    def run(self, job: Any) -> Dict[str, Any]:
        report = validate_final_quality(job)
        report_data = report.to_dict()

        self._set(job, "final_quality_validation_report", report_data)
        self._set(job, "final_quality_validator", report_data)
        self._set(job, "final_quality_validation_status", report_data["status"])
        self._set(job, "final_quality_checks", report_data["checks"])
        self._set(job, "final_quality_suggestions", report_data["suggestions"])

        self._set(job, "final_quality_audio_score", report_data["audio_score"])
        self._set(job, "final_quality_video_score", report_data["video_score"])
        self._set(job, "final_quality_story_score", report_data["story_score"])
        self._set(job, "final_quality_pacing_score", report_data["pacing_score"])
        self._set(job, "final_quality_safety_score", report_data["safety_score"])
        self._set(job, "final_quality_overall_score", report_data["overall_quality_score"])

        self._set(job, "final_quality_passed_count", report_data["passed_count"])
        self._set(job, "final_quality_warning_count", report_data["warning_count"])
        self._set(job, "final_quality_blocking_count", report_data["blocking_count"])
        self._set(job, "final_quality_review_required", True)

        for key, value in FINAL_QUALITY_JOB_DEFAULTS.items():
            self._set(job, key, value)

        self._set(job, "final_quality_blocking_reasons", report_data["blocking_reasons"])
        self._set(job, "final_quality_warnings", report_data["warnings"])
        self._set(job, "final_quality_recommendation", report_data["recommendation"])

        return report_data

    def _set(self, job: Any, key: str, value: Any) -> None:
        if isinstance(job, dict):
            job[key] = value
            return
        setattr(job, key, value)


def run_final_quality_validator(job: Any) -> Dict[str, Any]:
    return FinalQualityValidatorRunner().run(job)
