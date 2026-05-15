from __future__ import annotations

from typing import Any

from core.style_dna_apply_plan_builder import build_style_dna_apply_plan_report


class StyleDNAApplyPlanRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report = build_style_dna_apply_plan_report(job)
        plan = dict(report.get("plan") or {})
        operations = list(plan.get("operations") or [])

        _assign(job, "style_dna_apply_plan_report", report)
        _assign(job, "style_dna_apply_plan", plan)
        _assign(job, "style_dna_apply_plan_status", report.get("status"))
        _assign(job, "style_dna_apply_operations", operations)
        _assign(
            job,
            "style_dna_apply_operation_count",
            int(report.get("operation_count", 0) or 0),
        )
        _assign(
            job,
            "style_dna_apply_approved_operation_count",
            int(report.get("approved_operation_count", 0) or 0),
        )
        _assign(
            job,
            "style_dna_apply_skipped_operation_count",
            int(report.get("skipped_operation_count", 0) or 0),
        )
        _assign(
            job,
            "style_dna_apply_before_snapshot",
            dict(plan.get("before_snapshot") or {}),
        )
        _assign(
            job,
            "style_dna_apply_after_preview",
            dict(plan.get("after_preview") or {}),
        )
        _assign(
            job,
            "style_dna_apply_ready_for_future_file_write",
            bool(report.get("ready_for_future_file_write", False)),
        )

        _assign(job, "style_dna_apply_can_write_style_dna", False)
        _assign(job, "style_dna_apply_can_apply_style_dna", False)
        _assign(job, "style_dna_apply_can_update_profile", False)
        _assign(job, "style_dna_apply_can_change_cutting_rules", False)
        _assign(job, "style_dna_apply_can_modify_timeline", False)
        _assign(job, "style_dna_apply_can_trigger_render", False)
        _assign(job, "style_dna_apply_can_publish", False)

        _assign(job, "style_dna_apply_warnings", list(report.get("warnings") or []))
        _assign(
            job,
            "style_dna_apply_blocking_reasons",
            list(report.get("blocking_reasons") or []),
        )
        _assign(job, "style_dna_apply_recommendation", report.get("recommendation"))

        return report


def run_style_dna_apply_plan_for_job(job: Any) -> dict[str, Any]:
    return StyleDNAApplyPlanRunner().run(job)


def _assign(job: Any, key: str, value: Any) -> None:
    if isinstance(job, dict):
        job[key] = value
        return
    setattr(job, key, value)
