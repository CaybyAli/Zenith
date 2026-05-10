from __future__ import annotations

from pathlib import Path
from typing import Any

from core.preprocessing_manager import build_cache_key, build_source_fingerprint
from models.preprocessing_cache_validation import PreprocessingCacheValidationResult
from models.preprocessing_manifest import PreprocessingManifest


REQUIRED_WORKSPACE_PATH_FIELDS = [
    "preprocessed_dir",
    "audio_dir",
    "frames_dir",
    "thumbnails_dir",
    "temp_dir",
]


def _add_unique(target: list[str], value: str) -> None:
    if value not in target:
        target.append(value)


def _target_output_path(target: dict[str, Any]) -> str | None:
    return target.get("output_path") or target.get("output_pattern")


def _is_pattern_path(path: str) -> bool:
    return "%" in path


def _validate_workspace_paths(
    manifest: PreprocessingManifest,
    missing_paths: list[str],
    existing_paths: list[str],
    errors: list[str],
) -> None:
    for field_name in REQUIRED_WORKSPACE_PATH_FIELDS:
        value = getattr(manifest, field_name, None)

        if not value:
            _add_unique(missing_paths, field_name)
            _add_unique(errors, f"{field_name}_missing")
            continue

        path = Path(value)

        if path.exists():
            _add_unique(existing_paths, str(path))
        else:
            _add_unique(missing_paths, str(path))
            _add_unique(errors, f"{field_name}_missing")


def _validate_targets(
    manifest: PreprocessingManifest,
    missing_targets: list[str],
    ready_targets: list[str],
    warnings: list[str],
) -> None:
    all_targets: list[dict[str, Any]] = []

    for target in manifest.audio_targets or []:
        item = dict(target)
        item["_kind"] = "audio"
        all_targets.append(item)

    for target in manifest.frame_targets or []:
        item = dict(target)
        item["_kind"] = "frame"
        all_targets.append(item)

    for target in all_targets:
        if target.get("enabled") is False:
            continue

        target_id = str(target.get("target_id") or "unknown_target")
        output = _target_output_path(target)

        if not output:
            _add_unique(missing_targets, target_id)
            _add_unique(warnings, "target_output_missing")
            continue

        if _is_pattern_path(output):
            parent = Path(output).parent

            if parent.exists():
                _add_unique(ready_targets, target_id)
            else:
                _add_unique(missing_targets, target_id)
                _add_unique(warnings, "target_output_directory_missing")

            continue

        if Path(output).exists():
            _add_unique(ready_targets, target_id)
        else:
            _add_unique(missing_targets, target_id)
            _add_unique(warnings, "target_output_missing")


def _finalize_result(
    manifest: PreprocessingManifest | None,
    expected_cache_key: str | None,
    missing_paths: list[str],
    existing_paths: list[str],
    missing_targets: list[str],
    ready_targets: list[str],
    warnings: list[str],
    errors: list[str],
    details: dict[str, Any],
) -> PreprocessingCacheValidationResult:
    if errors:
        status = "rebuild_required"
        severity = "error"
        reusable = False
        recommendation = "rebuild"
    elif warnings:
        status = "reusable_with_warnings"
        severity = "warning"
        reusable = True
        recommendation = "reuse_with_review"
    else:
        status = "reusable"
        severity = "ok"
        reusable = True
        recommendation = "reuse"

    return PreprocessingCacheValidationResult(
        reusable=reusable,
        status=status,
        severity=severity,
        cache_key=manifest.cache_key if manifest else None,
        expected_cache_key=expected_cache_key,
        manifest_path=manifest.manifest_path if manifest else None,
        source_path=manifest.source_path if manifest else None,
        missing_paths=missing_paths,
        existing_paths=existing_paths,
        missing_targets=missing_targets,
        ready_targets=ready_targets,
        warnings=warnings,
        errors=errors,
        recommendation=recommendation,
        details=details,
    )


def validate_preprocessing_cache(
    manifest: PreprocessingManifest | None,
) -> PreprocessingCacheValidationResult:
    missing_paths: list[str] = []
    existing_paths: list[str] = []
    missing_targets: list[str] = []
    ready_targets: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    details: dict[str, Any] = {}

    if manifest is None:
        return PreprocessingCacheValidationResult(
            reusable=False,
            status="missing_manifest",
            severity="error",
            manifest_path=None,
            errors=["manifest_missing"],
            recommendation="rebuild",
            details={"reason": "manifest_is_none"},
        )

    source_fingerprint = build_source_fingerprint(manifest.source_path)
    expected_cache_key = build_cache_key(source_fingerprint)

    details["source_fingerprint"] = source_fingerprint

    if not source_fingerprint.get("exists"):
        _add_unique(errors, "source_missing")

    if manifest.cache_key != expected_cache_key:
        _add_unique(errors, "cache_key_mismatch")

    _validate_workspace_paths(
        manifest=manifest,
        missing_paths=missing_paths,
        existing_paths=existing_paths,
        errors=errors,
    )

    if not manifest.audio_extraction_plan:
        _add_unique(warnings, "audio_extraction_plan_missing")

    if not manifest.frame_extraction_plan:
        _add_unique(warnings, "frame_extraction_plan_missing")

    _validate_targets(
        manifest=manifest,
        missing_targets=missing_targets,
        ready_targets=ready_targets,
        warnings=warnings,
    )

    return _finalize_result(
        manifest=manifest,
        expected_cache_key=expected_cache_key,
        missing_paths=missing_paths,
        existing_paths=existing_paths,
        missing_targets=missing_targets,
        ready_targets=ready_targets,
        warnings=warnings,
        errors=errors,
        details=details,
    )


def apply_cache_validation_to_manifest(
    manifest: PreprocessingManifest,
    validation: PreprocessingCacheValidationResult,
) -> PreprocessingManifest:
    manifest.cache_validation = validation.to_dict()
    manifest.cache_validation_status = validation.status
    manifest.cache_reuse_allowed = validation.reusable
    return manifest


def apply_cache_validation_to_job(
    job: Any,
    validation: PreprocessingCacheValidationResult,
) -> Any:
    job.preprocessing_cache_validation = validation.to_dict()
    job.preprocessing_cache_validation_status = validation.status
    job.preprocessing_cache_reuse_allowed = validation.reusable

    if hasattr(job, "touch"):
        job.touch()

    return job
