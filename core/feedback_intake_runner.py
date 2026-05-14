from __future__ import annotations

from typing import Any

from core.feedback_intake import build_feedback_intake_report


FEEDBACK_INTAKE_JOB_FIELDS = [
    "feedback_intake_report",
    "feedback_intake_status",
    "feedback_submissions",
    "feedback_submission_count",
    "feedback_timestamp_feedback_count",
    "feedback_positive_feedback_count",
    "feedback_negative_feedback_count",
    "feedback_neutral_feedback_count",
    "feedback_average_video_score",
    "feedback_tags_summary",
    "feedback_category_summary",
    "feedback_review_required",
    "feedback_ready_for_style_dna_update",
    "feedback_can_update_style_dna",
    "feedback_can_change_profile",
    "feedback_can_change_cutting_rules",
    "feedback_can_modify_timeline",
    "feedback_can_trigger_render",
    "feedback_can_publish",
    "feedback_warnings",
    "feedback_blocking_reasons",
    "feedback_recommendation",
]


class FeedbackIntakeRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report = build_feedback_intake_report(job)
        payload = report.to_dict()

        _assign(job, "feedback_intake_report", payload)
        _assign(job, "feedback_intake_status", payload.get("status"))
        _assign(job, "feedback_submissions", payload.get("submissions", []))
        _assign(job, "feedback_submission_count", payload.get("submission_count", 0))
        _assign(
            job,
            "feedback_timestamp_feedback_count",
            payload.get("timestamp_feedback_count", 0),
        )
        _assign(
            job,
            "feedback_positive_feedback_count",
            payload.get("positive_feedback_count", 0),
        )
        _assign(
            job,
            "feedback_negative_feedback_count",
            payload.get("negative_feedback_count", 0),
        )
        _assign(
            job,
            "feedback_neutral_feedback_count",
            payload.get("neutral_feedback_count", 0),
        )
        _assign(job, "feedback_average_video_score", payload.get("average_video_score"))
        _assign(job, "feedback_tags_summary", payload.get("tags_summary", {}))
        _assign(job, "feedback_category_summary", payload.get("category_summary", {}))
        _assign(job, "feedback_review_required", payload.get("review_required", True))
        _assign(
            job,
            "feedback_ready_for_style_dna_update",
            payload.get("ready_for_style_dna_update", False),
        )

        _assign(job, "feedback_can_update_style_dna", False)
        _assign(job, "feedback_can_change_profile", False)
        _assign(job, "feedback_can_change_cutting_rules", False)
        _assign(job, "feedback_can_modify_timeline", False)
        _assign(job, "feedback_can_trigger_render", False)
        _assign(job, "feedback_can_publish", False)

        _assign(job, "feedback_warnings", payload.get("warnings", []))
        _assign(job, "feedback_blocking_reasons", payload.get("blocking_reasons", []))
        _assign(job, "feedback_recommendation", payload.get("recommendation"))

        return payload


def run_feedback_intake_for_job(job: Any) -> dict[str, Any]:
    return FeedbackIntakeRunner().run(job)


def _assign(job: Any, name: str, value: Any) -> None:
    if isinstance(job, dict):
        job[name] = value
        return
    setattr(job, name, value)
