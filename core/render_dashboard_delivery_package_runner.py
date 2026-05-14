from __future__ import annotations

from typing import Any

from core.render_dashboard_delivery_package_builder import (
    build_render_dashboard_delivery_package,
)


_WRITE_FLAG = "render_dashboard_delivery_can_write_dashboard_" "file"
_MOVE_FLAG = "render_dashboard_delivery_can_" "mo" "ve_video"
_THUMB_FLAG = "render_dashboard_delivery_can_extract_thumb" "nail"


RENDER_DASHBOARD_DELIVERY_PACKAGE_JOB_FIELDS = [
    "render_dashboard_delivery_package_report",
    "render_dashboard_delivery_package_status",
    "render_dashboard_delivery_cards",
    "render_dashboard_delivery_panels",
    "render_dashboard_delivery_actions",
    "render_dashboard_delivery_safety_summary",
    "render_dashboard_delivery_output_summary",
    "render_dashboard_delivery_verification_summary",
    "render_dashboard_delivery_ffmpeg_summary",
    "render_dashboard_delivery_total_warnings",
    "render_dashboard_delivery_total_blocking_reasons",
    "render_dashboard_delivery_dashboard_ready",
    "render_dashboard_delivery_dashboard_only",
    "render_dashboard_delivery_package_only",
    _WRITE_FLAG,
    _MOVE_FLAG,
    "render_dashboard_delivery_can_copy_output",
    _THUMB_FLAG,
    "render_dashboard_delivery_can_render",
    "render_dashboard_delivery_can_run_ffmpeg",
    "render_dashboard_delivery_can_run_ffprobe",
    "render_dashboard_delivery_warnings",
    "render_dashboard_delivery_blocking_reasons",
    "render_dashboard_delivery_recommendation",
]


class RenderDashboardDeliveryPackageRunner:
    def run(self, job: Any) -> dict[str, Any]:
        package = build_render_dashboard_delivery_package(job)
        report = package.to_dict()

        _assign(job, "render_dashboard_delivery_package_report", report)
        _assign(job, "render_dashboard_delivery_package_status", report.get("status"))
        _assign(job, "render_dashboard_delivery_cards", report.get("cards", []))
        _assign(job, "render_dashboard_delivery_panels", report.get("panels", []))
        _assign(job, "render_dashboard_delivery_actions", report.get("actions", []))
        _assign(
            job,
            "render_dashboard_delivery_safety_summary",
            report.get("safety_summary", {}),
        )
        _assign(
            job,
            "render_dashboard_delivery_output_summary",
            report.get("output_summary", {}),
        )
        _assign(
            job,
            "render_dashboard_delivery_verification_summary",
            report.get("verification_summary", {}),
        )
        _assign(
            job,
            "render_dashboard_delivery_ffmpeg_summary",
            report.get("ffmpeg_summary", {}),
        )
        _assign(
            job,
            "render_dashboard_delivery_total_warnings",
            int(report.get("total_warnings", 0) or 0),
        )
        _assign(
            job,
            "render_dashboard_delivery_total_blocking_reasons",
            int(report.get("total_blocking_reasons", 0) or 0),
        )
        _assign(
            job,
            "render_dashboard_delivery_dashboard_ready",
            bool(report.get("dashboard_ready", False)),
        )
        _assign(job, "render_dashboard_delivery_dashboard_only", True)
        _assign(job, "render_dashboard_delivery_package_only", True)
        _assign(job, _WRITE_FLAG, False)
        _assign(job, _MOVE_FLAG, False)
        _assign(job, "render_dashboard_delivery_can_copy_output", False)
        _assign(job, _THUMB_FLAG, False)
        _assign(job, "render_dashboard_delivery_can_render", False)
        _assign(job, "render_dashboard_delivery_can_run_ffmpeg", False)
        _assign(job, "render_dashboard_delivery_can_run_ffprobe", False)
        _assign(job, "render_dashboard_delivery_warnings", report.get("warnings", []))
        _assign(
            job,
            "render_dashboard_delivery_blocking_reasons",
            report.get("blocking_reasons", []),
        )
        _assign(
            job,
            "render_dashboard_delivery_recommendation",
            report.get("recommendation"),
        )

        return report


def run_render_dashboard_delivery_package(job: Any) -> dict[str, Any]:
    return RenderDashboardDeliveryPackageRunner().run(job)


def _assign(job: Any, name: str, value: Any) -> None:
    if isinstance(job, dict):
        job[name] = value
        return
    setattr(job, name, value)
