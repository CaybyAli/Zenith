from __future__ import annotations

from typing import Any

from core.learning_pattern_recognition import build_learning_pattern_recognition_report


class LearningPatternRecognitionRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report = build_learning_pattern_recognition_report(job)

        _assign(job, "learning_pattern_recognition_report", report)
        _assign(job, "learning_pattern_status", report.get("status"))
        _assign(job, "learning_pattern_profile", report.get("profile"))
        _assign(
            job,
            "learning_pattern_feedback_sample_count",
            int(report.get("feedback_sample_count", 0) or 0),
        )
        _assign(job, "learning_pattern_trends", list(report.get("trends") or []))
        _assign(job, "learning_pattern_clusters", list(report.get("clusters") or []))
        _assign(
            job,
            "learning_pattern_trend_count",
            int(report.get("trend_count", 0) or 0),
        )
        _assign(
            job,
            "learning_pattern_cluster_count",
            int(report.get("cluster_count", 0) or 0),
        )
        _assign(
            job,
            "learning_pattern_top_positive_patterns",
            list(report.get("top_positive_patterns") or []),
        )
        _assign(
            job,
            "learning_pattern_top_negative_patterns",
            list(report.get("top_negative_patterns") or []),
        )
        _assign(
            job,
            "learning_pattern_repeated_issue_count",
            int(report.get("repeated_issue_count", 0) or 0),
        )
        _assign(
            job,
            "learning_pattern_repeated_success_count",
            int(report.get("repeated_success_count", 0) or 0),
        )
        _assign(
            job,
            "learning_pattern_confidence",
            float(report.get("confidence", 0.0) or 0.0),
        )
        _assign(
            job,
            "learning_pattern_overfitting_risk",
            report.get("overfitting_risk"),
        )
        _assign(
            job,
            "learning_pattern_ready_for_future_style_dna_proposal",
            bool(report.get("ready_for_future_style_dna_proposal", False)),
        )

        _assign(job, "learning_pattern_can_update_style_dna", False)
        _assign(job, "learning_pattern_can_write_style_dna", False)
        _assign(job, "learning_pattern_can_change_profile", False)
        _assign(job, "learning_pattern_can_change_cutting_rules", False)
        _assign(job, "learning_pattern_can_modify_timeline", False)
        _assign(job, "learning_pattern_can_trigger_render", False)
        _assign(job, "learning_pattern_can_publish", False)

        _assign(job, "learning_pattern_warnings", list(report.get("warnings") or []))
        _assign(
            job,
            "learning_pattern_blocking_reasons",
            list(report.get("blocking_reasons") or []),
        )
        _assign(job, "learning_pattern_recommendation", report.get("recommendation"))

        return report


def run_learning_pattern_recognition_for_job(job: Any) -> dict[str, Any]:
    return LearningPatternRecognitionRunner().run(job)


def _assign(job: Any, key: str, value: Any) -> None:
    if isinstance(job, dict):
        job[key] = value
        return
    setattr(job, key, value)
