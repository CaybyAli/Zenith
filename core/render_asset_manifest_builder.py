from __future__ import annotations

import re
from typing import Any

from models.render_asset_manifest import (
    RenderAssetReference,
    RenderOutputPathPlan,
    build_render_asset_manifest_report,
)


ASSET_METADATA = {
    "phase": "2B-48",
    "block": "block8_render_export",
    "render_asset_manifest_only": True,
    "dry_run_only": True,
    "paths_are_hints_only": True,
    "media_unchanged": True,
    "no_execution_in_2b_48": True,
    "no_render_in_2b_48": True,
    "no_ff" "mpeg_in_2b_48": True,
    "no_media_read_in_2b_48": True,
    "no_media_write_in_2b_48": True,
    "no_directory_create_in_2b_48": True,
    "no_timeline_" "apply_in_2b_48": True,
}

READY_PLAN_STATUSES = {
    "render_plan_ready",
    "render_plan_ready_with_warnings",
}

READY_BLUEPRINT_STATUSES = {
    "render_blueprint_ready",
    "render_blueprint_ready_with_warnings",
}

DANGER_JOB_FLAGS = (
    "can_render",
    "can_run_ff" "mpeg",
    "can_write_media",
    "render_plan_can_render",
    "render_plan_can_run_ff" "mpeg",
    "render_plan_can_write_media",
    "render_blueprint_can_render",
    "render_blueprint_can_run_ff" "mpeg",
    "render_blueprint_can_write_media",
)

SHELL_MARKERS = ("&", "|", ";", ">", "<")
URL_MARKERS = ("://", "http:", "https:", "file:")
DEVICE_NAMES = {"CON", "PRN", "AUX", "NUL"}
ROOT_HINTS = {"/", "\\", "C:\\", "D:\\", "E:\\"}


class RenderAssetManifestBuilder:
    def build(self, job: Any) -> dict[str, Any]:
        job_id = str(self._get(job, "job_id", self._get(job, "id", "unknown")))

        warnings: list[str] = []
        blocking_reasons: list[str] = []

        plan = self._dict(self._get(job, "render_plan_report") or self._get(job, "render_plan"))
        blueprint = self._dict(
            self._get(job, "render_command_blueprint_report")
            or self._get(job, "render_command_blueprint")
        )

        self._check_preconditions(job, plan, blueprint, warnings, blocking_reasons)

        asset_references = self._build_asset_references(job, plan, blueprint, warnings)
        output_path_plans = self._build_output_path_plans(job, plan, blueprint, warnings)

        self._check_asset_paths(asset_references)
        self._check_output_paths(output_path_plans)

        for asset in asset_references:
            warnings.extend([f"{asset.asset_id}:{item}" for item in asset.warnings])
            blocking_reasons.extend([f"{asset.asset_id}:{item}" for item in asset.blocking_reasons])

        for output in output_path_plans:
            warnings.extend([f"{output.output_id}:{item}" for item in output.warnings])
            blocking_reasons.extend([f"{output.output_id}:{item}" for item in output.blocking_reasons])

        report = build_render_asset_manifest_report(
            job_id=job_id,
            asset_references=asset_references,
            output_path_plans=output_path_plans,
            warnings=self._unique(warnings),
            blocking_reasons=self._unique(blocking_reasons),
            metadata=dict(ASSET_METADATA),
        )
        return report.to_dict()

    def _check_preconditions(
        self,
        job: Any,
        plan: dict[str, Any],
        blueprint: dict[str, Any],
        warnings: list[str],
        blocking_reasons: list[str],
    ) -> None:
        if not plan:
            blocking_reasons.append("render_asset_manifest_render_plan_missing")
        else:
            plan_status = self._status(self._get(job, "render_plan_status") or plan.get("status"))
            if plan_status not in READY_PLAN_STATUSES:
                blocking_reasons.append("render_asset_manifest_render_plan_not_ready")

            plan_blocking = self._string_list(
                self._get(job, "render_plan_blocking_reasons") or plan.get("blocking_reasons")
            )
            if plan_blocking:
                blocking_reasons.append("render_asset_manifest_render_plan_has_blocking_reasons")
                blocking_reasons.extend([f"render_plan_blocking:{item}" for item in plan_blocking])

        if not blueprint:
            blocking_reasons.append("render_asset_manifest_blueprint_missing")
        else:
            blueprint_status = self._status(
                self._get(job, "render_blueprint_status") or blueprint.get("status")
            )
            if blueprint_status not in READY_BLUEPRINT_STATUSES:
                blocking_reasons.append("render_asset_manifest_blueprint_not_ready")

            non_executable = self._truthy(
                self._get(job, "render_blueprint_non_executable")
                if self._get(job, "render_blueprint_non_executable") is not None
                else blueprint.get("non_executable")
            )
            if not non_executable:
                blocking_reasons.append("render_asset_manifest_blueprint_not_non_executable")

            ready_for_renderer = self._truthy(
                self._get(job, "render_blueprint_ready_for_renderer_implementation")
                if self._get(job, "render_blueprint_ready_for_renderer_implementation") is not None
                else blueprint.get("ready_for_renderer_implementation")
            )
            if not ready_for_renderer:
                blocking_reasons.append("render_asset_manifest_blueprint_not_ready_for_renderer")

            blueprint_blocking = self._string_list(
                self._get(job, "render_blueprint_blocking_reasons")
                or blueprint.get("blocking_reasons")
            )
            if blueprint_blocking:
                blocking_reasons.append("render_asset_manifest_blueprint_has_blocking_reasons")
                blocking_reasons.extend(
                    [f"render_blueprint_blocking:{item}" for item in blueprint_blocking]
                )

        for flag_name in DANGER_JOB_FLAGS:
            if self._truthy(self._get(job, flag_name)):
                blocking_reasons.append(f"render_asset_manifest_dangerous_flag:{flag_name}")

        if not self._truthy(self._get(job, "render_plan_dry_run_only", True), default=True):
            blocking_reasons.append("render_asset_manifest_plan_not_dry_run_only")

        if not self._truthy(self._get(job, "render_blueprint_dry_run_only", True), default=True):
            blocking_reasons.append("render_asset_manifest_blueprint_not_dry_run_only")

        plan_warnings = self._string_list(
            self._get(job, "render_plan_warnings") or plan.get("warnings")
        )
        blueprint_warnings = self._string_list(
            self._get(job, "render_blueprint_warnings") or blueprint.get("warnings")
        )
        warnings.extend([f"render_plan_warning:{item}" for item in plan_warnings])
        warnings.extend([f"render_blueprint_warning:{item}" for item in blueprint_warnings])

    def _build_asset_references(
        self,
        job: Any,
        plan: dict[str, Any],
        blueprint: dict[str, Any],
        warnings: list[str],
    ) -> list[RenderAssetReference]:
        assets: list[RenderAssetReference] = []

        sources = self._list(self._get(job, "render_plan_sources") or plan.get("sources"))
        if not sources:
            fallback_path = self._first_text(
                self._get(job, "input_file"),
                self._get(job, "source_file"),
                self._get(job, "media_path"),
                self._get(job, "raw_video_path"),
                self._get(job, "video_path"),
            )
            assets.append(
                RenderAssetReference(
                    asset_id="render_source_primary_media_fallback",
                    asset_type="primary_media",
                    path_hint=fallback_path,
                    required=True,
                    available_hint=bool(fallback_path),
                    safety_status="hint_only",
                    warnings=[] if fallback_path else ["render_source_path_hint_missing"],
                    metadata={**ASSET_METADATA, "source": "job_fallback"},
                )
            )
        else:
            for index, source in enumerate(sources, start=1):
                source_type = str(
                    source.get("source_type")
                    or source.get("asset_type")
                    or source.get("type")
                    or "primary_media"
                )
                path_hint = self._first_text(
                    source.get("path_hint"),
                    source.get("source_path"),
                    source.get("path"),
                    source.get("file_path"),
                )
                required = self._truthy(source.get("required"), default=True)
                assets.append(
                    RenderAssetReference(
                        asset_id=f"render_source_{index}_{self._safe_id(source_type)}",
                        asset_type=source_type,
                        path_hint=path_hint,
                        required=required,
                        available_hint=bool(path_hint),
                        safety_status="hint_only",
                        warnings=[] if path_hint else ["render_source_path_hint_missing"],
                        metadata={**ASSET_METADATA, "source": "render_plan_sources"},
                    )
                )

        steps = self._list(
            self._get(job, "render_blueprint_steps") or blueprint.get("blueprint_steps")
        )
        for index, step in enumerate(steps, start=1):
            step_type = str(step.get("step_type") or "").strip().lower()

            if step_type == "censor_sfx":
                path_hint = self._first_text(
                    step.get("censor_sfx_path_hint"),
                    self._get(job, "censor_sfx_asset_path_hint"),
                    "assets/sfx/censor/censor_sfx_manifest.json",
                )
                assets.append(
                    RenderAssetReference(
                        asset_id=f"render_blueprint_step_{index}_censor_sfx_asset",
                        asset_type="censor_sfx_asset",
                        path_hint=path_hint,
                        required=True,
                        available_hint=bool(path_hint),
                        safety_status="hint_only",
                        warnings=["censor_sfx_asset_is_hint_only"],
                        metadata={**ASSET_METADATA, "source": "render_blueprint_steps"},
                    )
                )

            elif step_type == "subtitle":
                path_hint = self._first_text(
                    step.get("subtitle_asset_path_hint"),
                    self._get(job, "subtitle_asset_path_hint"),
                    self._get(job, "subtitle_intent"),
                )
                assets.append(
                    RenderAssetReference(
                        asset_id=f"render_blueprint_step_{index}_subtitle_asset",
                        asset_type="subtitle_asset",
                        path_hint=path_hint,
                        required=False,
                        available_hint=bool(path_hint),
                        safety_status="hint_only",
                        warnings=["subtitle_asset_is_planned_hint_only"],
                        metadata={**ASSET_METADATA, "source": "render_blueprint_steps"},
                    )
                )

            elif step_type == "audio_mix":
                path_hint = self._first_text(
                    step.get("audio_mix_asset_path_hint"),
                    self._get(job, "audio_mix_asset_path_hint"),
                    self._get(job, "audio_mix_intent"),
                )
                assets.append(
                    RenderAssetReference(
                        asset_id=f"render_blueprint_step_{index}_audio_mix_asset",
                        asset_type="audio_mix_asset",
                        path_hint=path_hint,
                        required=False,
                        available_hint=bool(path_hint),
                        safety_status="hint_only",
                        warnings=["audio_mix_asset_is_planned_hint_only"],
                        metadata={**ASSET_METADATA, "source": "render_blueprint_steps"},
                    )
                )

            elif step_type == "encode":
                warnings.append("render_encode_step_output_target_required")

        if self._truthy(self._get(job, "censor_sfx_required")):
            already_present = any(asset.asset_type == "censor_sfx_asset" for asset in assets)
            if not already_present:
                assets.append(
                    RenderAssetReference(
                        asset_id="render_job_censor_sfx_required_asset",
                        asset_type="censor_sfx_asset",
                        path_hint="assets/sfx/censor/censor_sfx_manifest.json",
                        required=True,
                        available_hint=True,
                        safety_status="hint_only",
                        warnings=["censor_sfx_required_from_job_field"],
                        metadata={**ASSET_METADATA, "source": "job_censor_sfx_required"},
                    )
                )

        return assets

    def _build_output_path_plans(
        self,
        job: Any,
        plan: dict[str, Any],
        blueprint: dict[str, Any],
        warnings: list[str],
    ) -> list[RenderOutputPathPlan]:
        outputs: list[RenderOutputPathPlan] = []

        output_targets = self._list(
            self._get(job, "render_plan_output_targets")
            or plan.get("output_targets")
            or self._get(job, "output_targets")
        )

        if not output_targets:
            target_platforms = self._string_list(self._get(job, "target_platforms"))
            if not target_platforms:
                target_platforms = ["default"]
            for platform in target_platforms:
                filename_hint = f"{self._safe_id(self._get(job, 'job_id', 'job'))}_{platform}.mp4"
                output_targets.append(
                    {
                        "output_id": f"fallback_output_{platform}",
                        "output_type": "planned_video",
                        "filename_hint": filename_hint,
                        "directory_hint": None,
                        "container": "mp4",
                        "platform": platform,
                        "fallback_generated": True,
                    }
                )
                warnings.append(f"render_output_target_generated_for_platform:{platform}")

        for index, target in enumerate(output_targets, start=1):
            filename_hint = self._first_text(
                target.get("filename_hint"),
                target.get("filename"),
                target.get("name"),
            )
            full_path_hint = self._first_text(
                target.get("output_path_hint"),
                target.get("full_path_hint"),
                target.get("path_hint"),
                target.get("path"),
            )
            directory_hint = self._first_text(
                target.get("directory_hint"),
                target.get("output_dir_hint"),
                target.get("folder_hint"),
            )
            platform = self._first_text(target.get("platform"), target.get("target_platform"))
            container = self._first_text(target.get("container"), target.get("extension")) or "mp4"

            if not filename_hint:
                filename_hint = f"{self._safe_id(self._get(job, 'job_id', 'job'))}_{index}.mp4"
                warnings.append(f"render_output_filename_generated:{index}")

            outputs.append(
                RenderOutputPathPlan(
                    output_id=str(target.get("output_id") or f"render_output_{index}"),
                    output_type=str(target.get("output_type") or target.get("type") or "planned_video"),
                    filename_hint=filename_hint,
                    directory_hint=directory_hint,
                    full_path_hint=full_path_hint,
                    container=container.strip("."),
                    platform=platform,
                    safe_filename=self._safe_filename(filename_hint, container),
                    path_safety_status="hint_only",
                    warnings=["render_output_path_is_hint_only"],
                    metadata={**ASSET_METADATA, "source": "render_plan_output_targets"},
                )
            )

        _ = blueprint
        return outputs

    def _check_asset_paths(self, assets: list[RenderAssetReference]) -> None:
        for asset in assets:
            self._apply_path_safety(
                path_hint=asset.path_hint,
                required=asset.required,
                warnings=asset.warnings,
                blocking_reasons=asset.blocking_reasons,
            )
            if asset.blocking_reasons:
                asset.safety_status = "unsafe"
            elif asset.warnings:
                asset.safety_status = "hint_only_with_warnings"
            else:
                asset.safety_status = "hint_only"

    def _check_output_paths(self, outputs: list[RenderOutputPathPlan]) -> None:
        for output in outputs:
            for hint in (output.filename_hint, output.directory_hint, output.full_path_hint):
                self._apply_path_safety(
                    path_hint=hint,
                    required=False,
                    warnings=output.warnings,
                    blocking_reasons=output.blocking_reasons,
                )
            if output.blocking_reasons:
                output.path_safety_status = "unsafe"
            elif output.warnings:
                output.path_safety_status = "hint_only_with_warnings"
            else:
                output.path_safety_status = "hint_only"

    def _apply_path_safety(
        self,
        *,
        path_hint: str | None,
        required: bool,
        warnings: list[str],
        blocking_reasons: list[str],
    ) -> None:
        if not path_hint:
            if required:
                blocking_reasons.append("path_hint_missing_for_required_asset")
            else:
                warnings.append("path_hint_missing_optional")
            return

        text = str(path_hint).strip()
        if not text:
            if required:
                blocking_reasons.append("path_hint_empty_for_required_asset")
            else:
                warnings.append("path_hint_empty_optional")
            return

        lowered = text.lower()
        if any(marker in lowered for marker in URL_MARKERS):
            blocking_reasons.append("path_hint_url_not_allowed")

        if ".." in text:
            blocking_reasons.append("path_hint_traversal_not_allowed")

        if any(marker in text for marker in SHELL_MARKERS):
            blocking_reasons.append("path_hint_shell_marker_not_allowed")

        if text in ROOT_HINTS or re.fullmatch(r"[A-Za-z]:[\\/]", text):
            blocking_reasons.append("path_hint_root_not_allowed")

        filename = re.split(r"[\\/]+", text)[-1].strip()
        stem = filename.split(".")[0].upper() if filename else ""
        if stem in DEVICE_NAMES:
            blocking_reasons.append("path_hint_device_name_not_allowed")

        commandish_tokens = ("&&", "||", "$(", "`", " powershell ", " cmd ", " bash ")
        padded = f" {lowered} "
        if any(token in padded for token in commandish_tokens):
            blocking_reasons.append("path_hint_command_like_not_allowed")

    def _safe_filename(self, filename_hint: str | None, container: str | None = "mp4") -> str:
        raw = str(filename_hint or "render_output").strip()
        raw = re.split(r"[\\/]+", raw)[-1]
        raw = raw.replace(" ", "_")
        raw = re.sub(r"[&|;><`$]+", "", raw)
        raw = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)
        raw = raw.strip("._-") or "render_output"

        extension = (container or "mp4").strip(".").lower() or "mp4"
        if "." not in raw:
            raw = f"{raw}.{extension}"
        elif not raw.lower().endswith(f".{extension}"):
            raw = f"{raw}.{extension}"

        stem = raw.split(".")[0].upper()
        if stem in DEVICE_NAMES:
            raw = f"safe_{raw}"

        return raw

    def _safe_id(self, value: Any) -> str:
        text = str(value or "item").strip().lower()
        text = re.sub(r"[^a-z0-9_-]+", "_", text)
        return text.strip("_") or "item"

    def _get(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _dict(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _list(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, dict)]

    def _status(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().lower()

    def _truthy(self, value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {
                "true",
                "1",
                "yes",
                "ready",
                "safe",
                "passed",
                "approved",
            }
        return bool(value)

    def _first_text(self, *values: Any) -> str | None:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item)]
        if isinstance(value, tuple):
            return [str(item) for item in value if str(item)]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _unique(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result


def build_render_asset_manifest(job: Any) -> dict[str, Any]:
    return RenderAssetManifestBuilder().build(job)
