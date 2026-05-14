from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


RENDER_ASSET_MANIFEST_STATUS_READY = "render_asset_manifest_ready"
RENDER_ASSET_MANIFEST_STATUS_READY_WITH_WARNINGS = "render_asset_manifest_ready_with_warnings"
RENDER_ASSET_MANIFEST_STATUS_BLOCKED = "render_asset_manifest_blocked"
RENDER_ASSET_MANIFEST_STATUS_FAILED = "render_asset_manifest_failed"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class RenderAssetReference:
    asset_id: str
    asset_type: str
    path_hint: str | None = None
    required: bool = False
    available_hint: bool = False
    safety_status: str = "hint_only"
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RenderOutputPathPlan:
    output_id: str
    output_type: str
    filename_hint: str | None = None
    directory_hint: str | None = None
    full_path_hint: str | None = None
    container: str = "mp4"
    platform: str | None = None
    safe_filename: str = "render_output.mp4"
    path_safety_status: str = "hint_only"
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RenderAssetManifestReport:
    report_id: str
    job_id: str
    status: str

    asset_references: list[RenderAssetReference] = field(default_factory=list)
    output_path_plans: list[RenderOutputPathPlan] = field(default_factory=list)

    total_assets: int = 0
    required_asset_count: int = 0
    missing_required_hint_count: int = 0
    unsafe_path_count: int = 0
    output_plan_count: int = 0

    dry_run_only: bool = True
    manifest_only: bool = True
    paths_are_hints_only: bool = True

    can_create_directories: bool = False
    can_write_files: bool = False
    can_open_media: bool = False
    can_render: bool = False
    can_run_ffmpeg: bool = False

    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)

        data["asset_references"] = [
            asset.to_dict() if hasattr(asset, "to_dict") else dict(asset)
            for asset in self.asset_references
        ]
        data["output_path_plans"] = [
            output.to_dict() if hasattr(output, "to_dict") else dict(output)
            for output in self.output_path_plans
        ]

        data["total_assets"] = len(data["asset_references"])
        data["required_asset_count"] = sum(
            1 for asset in data["asset_references"] if asset.get("required") is True
        )
        data["missing_required_hint_count"] = sum(
            1
            for asset in data["asset_references"]
            if asset.get("required") is True and not asset.get("path_hint")
        )
        data["unsafe_path_count"] = sum(
            1
            for item in [*data["asset_references"], *data["output_path_plans"]]
            if item.get("blocking_reasons")
        )
        data["output_plan_count"] = len(data["output_path_plans"])

        data["dry_run_only"] = True
        data["manifest_only"] = True
        data["paths_are_hints_only"] = True

        data["can_create_directories"] = False
        data["can_write_files"] = False
        data["can_open_media"] = False
        data["can_render"] = False
        data["can_run_ffmpeg"] = False

        return data


def build_render_asset_manifest_report(
    *,
    job_id: str,
    asset_references: list[RenderAssetReference] | None = None,
    output_path_plans: list[RenderOutputPathPlan] | None = None,
    warnings: list[str] | None = None,
    blocking_reasons: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> RenderAssetManifestReport:
    safe_assets = list(asset_references or [])
    safe_outputs = list(output_path_plans or [])
    safe_warnings = list(warnings or [])
    safe_blocking_reasons = list(blocking_reasons or [])

    missing_required_hint_count = sum(
        1 for asset in safe_assets if asset.required is True and not asset.path_hint
    )
    unsafe_path_count = sum(
        1
        for item in [*safe_assets, *safe_outputs]
        if item.blocking_reasons
    )

    if missing_required_hint_count:
        _append_once(safe_blocking_reasons, "render_asset_missing_required_hint")

    if unsafe_path_count:
        _append_once(safe_blocking_reasons, "render_asset_unsafe_path")

    if safe_blocking_reasons:
        status = RENDER_ASSET_MANIFEST_STATUS_BLOCKED
        recommendation = "Render Asset Manifest blockiert. Pfad-Hinweise und Blocking Reasons pruefen."
    elif safe_warnings:
        status = RENDER_ASSET_MANIFEST_STATUS_READY_WITH_WARNINGS
        recommendation = "Render Asset Manifest ist bereit, aber Warnungen pruefen."
    else:
        status = RENDER_ASSET_MANIFEST_STATUS_READY
        recommendation = "Render Asset Manifest ist bereit als sichere Hinweis-Sammlung."

    return RenderAssetManifestReport(
        report_id=f"render_asset_manifest_{job_id}",
        job_id=job_id,
        status=status,
        asset_references=safe_assets,
        output_path_plans=safe_outputs,
        total_assets=len(safe_assets),
        required_asset_count=sum(1 for asset in safe_assets if asset.required is True),
        missing_required_hint_count=missing_required_hint_count,
        unsafe_path_count=unsafe_path_count,
        output_plan_count=len(safe_outputs),
        dry_run_only=True,
        manifest_only=True,
        paths_are_hints_only=True,
        can_create_directories=False,
        can_write_files=False,
        can_open_media=False,
        can_render=False,
        can_run_ffmpeg=False,
        warnings=safe_warnings,
        blocking_reasons=safe_blocking_reasons,
        recommendation=recommendation,
        metadata=dict(metadata or {}),
    )


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)
