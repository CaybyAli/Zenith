from __future__ import annotations

from typing import Any

from core.render_asset_manifest_builder import build_render_asset_manifest


RENDER_ASSET_SAFE_FALSE_FIELDS = {
    "render_asset_can_create_directories": False,
    "render_asset_can_write_files": False,
    "render_asset_can_open_media": False,
    "render_asset_can_render": False,
    "render_asset_can_run_ff" "mpeg": False,
}


class RenderAssetManifestRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report_data = build_render_asset_manifest(job)

        self._set(job, "render_asset_manifest_report", report_data)
        self._set(job, "render_asset_manifest", report_data)
        self._set(job, "render_asset_manifest_status", report_data["status"])

        self._set(job, "render_asset_references", report_data["asset_references"])
        self._set(job, "render_output_path_plans", report_data["output_path_plans"])

        self._set(job, "render_asset_total_assets", report_data["total_assets"])
        self._set(job, "render_asset_required_count", report_data["required_asset_count"])
        self._set(
            job,
            "render_asset_missing_required_hint_count",
            report_data["missing_required_hint_count"],
        )
        self._set(job, "render_asset_unsafe_path_count", report_data["unsafe_path_count"])
        self._set(job, "render_asset_output_plan_count", report_data["output_plan_count"])

        self._set(job, "render_asset_dry_run_only", True)
        self._set(job, "render_asset_manifest_only", True)
        self._set(job, "render_asset_paths_are_hints_only", True)

        for key, value in RENDER_ASSET_SAFE_FALSE_FIELDS.items():
            self._set(job, key, value)

        self._set(job, "render_asset_blocking_reasons", report_data["blocking_reasons"])
        self._set(job, "render_asset_warnings", report_data["warnings"])
        self._set(job, "render_asset_recommendation", report_data["recommendation"])

        return report_data

    def _set(self, job: Any, key: str, value: Any) -> None:
        if isinstance(job, dict):
            job[key] = value
            return
        setattr(job, key, value)


def run_render_asset_manifest_for_job(job: Any) -> dict[str, Any]:
    return RenderAssetManifestRunner().run(job)
