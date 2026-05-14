from __future__ import annotations

from typing import Any

from core.render_verification_contract import build_render_verification_contract


RENDER_VERIFICATION_JOB_FIELDS = [
    "render_verification_contract_report",
    "render_verification_contract_status",
    "render_verification_expected_spec",
    "render_verification_checks",
    "render_verification_probe_plan",
    "render_verification_total_checks",
    "render_verification_planned_check_count",
    "render_verification_runnable_smoke_check_count",
    "render_verification_blocked_check_count",
    "render_verification_contract_only",
    "render_verification_dry_run_only",
    "render_verification_smoke_probe_allowed",
    "render_verification_project_" "output_probe_allowed",
    "render_verification_can_verify_smoke_output",
    "render_verification_can_verify_project_" "output",
    "render_verification_can_probe_media_files",
    "render_verification_can_render",
    "render_verification_can_write_media",
    "render_verification_blocking_reasons",
    "render_verification_warnings",
    "render_verification_recommendation",
]


class RenderVerificationContractRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report = build_render_verification_contract(job)
        report_dict = report.to_dict()

        _assign(job, "render_verification_contract_report", report_dict)
        _assign(job, "render_verification_contract_status", report_dict.get("status"))
        _assign(job, "render_verification_expected_spec", report_dict.get("expected_spec", {}))
        _assign(job, "render_verification_checks", report_dict.get("checks", []))
        _assign(job, "render_verification_probe_plan", report_dict.get("probe_plan", {}))

        _assign(job, "render_verification_total_checks", int(report_dict.get("total_checks", 0) or 0))
        _assign(
            job,
            "render_verification_planned_check_count",
            int(report_dict.get("planned_check_count", 0) or 0),
        )
        _assign(
            job,
            "render_verification_runnable_smoke_check_count",
            int(report_dict.get("runnable_smoke_check_count", 0) or 0),
        )
        _assign(
            job,
            "render_verification_blocked_check_count",
            int(report_dict.get("blocked_check_count", 0) or 0),
        )

        _assign(job, "render_verification_contract_only", True)
        _assign(job, "render_verification_dry_run_only", True)
        _assign(job, "render_verification_smoke_probe_allowed", bool(report_dict.get("smoke_probe_allowed")))
        _assign(
            job,
            "render_verification_project_" "output_probe_allowed",
            False,
        )
        _assign(
            job,
            "render_verification_can_verify_smoke_output",
            bool(report_dict.get("can_verify_smoke_output")),
        )
        _assign(
            job,
            "render_verification_can_verify_project_" "output",
            False,
        )
        _assign(job, "render_verification_can_probe_media_files", False)
        _assign(job, "render_verification_can_render", False)
        _assign(job, "render_verification_can_write_media", False)

        _assign(
            job,
            "render_verification_blocking_reasons",
            report_dict.get("blocking_reasons", []),
        )
        _assign(job, "render_verification_warnings", report_dict.get("warnings", []))
        _assign(job, "render_verification_recommendation", report_dict.get("recommendation"))

        return report_dict


def run_render_verification_contract(job: Any) -> dict[str, Any]:
    return RenderVerificationContractRunner().run(job)


def _assign(job: Any, name: str, value: Any) -> None:
    if isinstance(job, dict):
        job[name] = value
        return
    setattr(job, name, value)
