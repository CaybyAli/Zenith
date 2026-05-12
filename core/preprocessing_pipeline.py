from __future__ import annotations

from pathlib import Path
from typing import Any

from core.audio_extraction_executor import (
    apply_audio_extraction_result_to_manifest,
    execute_audio_extraction_plan,
)
from core.audio_extraction_planner import (
    apply_audio_extraction_plan_to_manifest,
    build_audio_extraction_plan,
)
from core.frame_extraction_planner import (
    apply_frame_extraction_plan_to_manifest,
    build_frame_extraction_plan,
)
from core.preprocessing_cache_validator import (
    apply_cache_validation_to_manifest,
    validate_preprocessing_cache,
)
from core.preprocessing_manager import (
    prepare_preprocessing_workspace,
    write_preprocessing_manifest,
)
from models.audio_extraction_plan import AudioExtractionPlan


def _collect_unique(*values: list[str]) -> list[str]:
    result: list[str] = []

    for items in values:
        for item in items or []:
            if item not in result:
                result.append(item)

    return result


def build_preprocessing_pipeline_report(
    job_id: str,
    source_path: str | Path,
    root_dir: str | Path = "preprocessed",
    metadata: dict[str, Any] | None = None,
    execute_audio_extraction: bool = True,
    audio_extraction_overwrite_existing: bool = False,
) -> dict[str, Any]:
    manifest = prepare_preprocessing_workspace(
        job_id=job_id,
        source_path=source_path,
        root_dir=root_dir,
        metadata=metadata,
    )

    audio_plan = build_audio_extraction_plan(
        manifest=manifest,
        metadata={"stage": "2B-05-E"},
    )
    apply_audio_extraction_plan_to_manifest(manifest, audio_plan)

    frame_plan = build_frame_extraction_plan(
        manifest=manifest,
        metadata={"stage": "2B-05-E"},
    )
    apply_frame_extraction_plan_to_manifest(manifest, frame_plan)

    audio_extraction_result_dict: dict[str, Any] = {}
    audio_extraction_warnings: list[str] = []
    audio_extraction_errors: list[str] = []

    if execute_audio_extraction:
        audio_result = _execute_audio_extraction(
            manifest_source_missing=manifest.status == "missing_source",
            audio_plan=audio_plan,
            manifest=manifest,
            overwrite_existing=audio_extraction_overwrite_existing,
        )
        apply_audio_extraction_result_to_manifest(manifest, audio_result)
        audio_extraction_result_dict = audio_result.to_dict()
        audio_extraction_warnings = list(audio_result.warnings)
        audio_extraction_errors = list(audio_result.errors)

    cache_validation = validate_preprocessing_cache(manifest)
    apply_cache_validation_to_manifest(manifest, cache_validation)

    write_preprocessing_manifest(manifest)

    manifest_dict = manifest.to_dict()
    audio_plan_dict = audio_plan.to_dict()
    frame_plan_dict = frame_plan.to_dict()
    cache_validation_dict = cache_validation.to_dict()

    warnings = _collect_unique(
        list(manifest_dict.get("warnings") or []),
        list(audio_plan_dict.get("warnings") or []),
        list(frame_plan_dict.get("warnings") or []),
        list(cache_validation_dict.get("warnings") or []),
        audio_extraction_warnings,
    )

    errors = _collect_unique(
        list(manifest_dict.get("errors") or []),
        list(audio_plan_dict.get("errors") or []),
        list(frame_plan_dict.get("errors") or []),
        list(cache_validation_dict.get("errors") or []),
        audio_extraction_errors,
    )

    if errors:
        status = "failed"
        recommendation = "fix_or_rebuild"
    elif warnings:
        status = "ready_with_warnings"
        recommendation = "continue_with_review"
    else:
        status = "ready"
        recommendation = "continue"

    return {
        "preprocessing_manifest": manifest_dict,
        "audio_extraction_plan": audio_plan_dict,
        "audio_targets": list(audio_plan_dict.get("targets") or []),
        "audio_extraction_result": audio_extraction_result_dict,
        "audio_extraction_status": manifest.audio_extraction_status,
        "ready_audio_targets": list(manifest.ready_audio_targets),
        "missing_audio_targets": list(manifest.missing_audio_targets),
        "failed_audio_targets": list(manifest.failed_audio_targets),
        "frame_extraction_plan": frame_plan_dict,
        "frame_targets": list(frame_plan_dict.get("targets") or []),
        "cache_validation": cache_validation_dict,
        "preprocessing_dir": manifest.preprocessed_dir,
        "manifest_path": manifest.manifest_path,
        "status": status,
        "cache_reuse_allowed": bool(cache_validation.reusable),
        "reused_cache": bool(manifest.reused_cache),
        "warnings": warnings,
        "errors": errors,
        "recommendation": recommendation,
    }


def _execute_audio_extraction(
    manifest_source_missing: bool,
    audio_plan: AudioExtractionPlan,
    manifest: Any,
    overwrite_existing: bool,
) -> Any:
    if manifest_source_missing:
        return execute_audio_extraction_plan(
            plan=AudioExtractionPlan(
                job_id=audio_plan.job_id,
                source_path=audio_plan.source_path,
                audio_dir=audio_plan.audio_dir,
                targets=audio_plan.targets,
                status=audio_plan.status,
                warnings=list(audio_plan.warnings),
                errors=list(audio_plan.errors),
                metadata=dict(audio_plan.metadata),
            ),
            overwrite_existing=overwrite_existing,
            metadata={"stage": "3-A"},
        )

    return execute_audio_extraction_plan(
        plan=audio_plan,
        overwrite_existing=overwrite_existing,
        metadata={"stage": "3-A"},
    )


def apply_preprocessing_pipeline_report_to_job(
    job: Any,
    report: dict[str, Any],
) -> Any:
    manifest_dict = dict(report.get("preprocessing_manifest") or {})

    job.preprocessing_dir = report.get("preprocessing_dir")
    job.preprocessing_manifest_path = report.get("manifest_path")
    job.preprocessing_manifest = manifest_dict
    job.preprocessing_status = report.get("status")
    job.preprocessing_cache_key = manifest_dict.get("cache_key")
    job.preprocessing_reused_cache = bool(report.get("reused_cache", False))

    job.audio_extraction_plan = dict(report.get("audio_extraction_plan") or {})
    job.audio_targets = list(report.get("audio_targets") or [])

    job.audio_extraction_result = dict(report.get("audio_extraction_result") or {})
    job.audio_extraction_status = report.get("audio_extraction_status")
    job.ready_audio_targets = list(report.get("ready_audio_targets") or [])
    job.missing_audio_targets = list(report.get("missing_audio_targets") or [])
    job.failed_audio_targets = list(report.get("failed_audio_targets") or [])

    job.frame_extraction_plan = dict(report.get("frame_extraction_plan") or {})
    job.frame_targets = list(report.get("frame_targets") or [])

    job.preprocessing_cache_validation = dict(report.get("cache_validation") or {})
    job.preprocessing_cache_validation_status = job.preprocessing_cache_validation.get("status")
    job.preprocessing_cache_reuse_allowed = bool(
        report.get("cache_reuse_allowed", False)
    )

    if hasattr(job, "touch"):
        job.touch()

    return job


def run_preprocessing_pipeline_for_job(
    job: Any,
    source_path: str | Path,
    root_dir: str | Path = "preprocessed",
    metadata: dict[str, Any] | None = None,
    execute_audio_extraction: bool = True,
    audio_extraction_overwrite_existing: bool = False,
) -> dict[str, Any]:
    report = build_preprocessing_pipeline_report(
        job_id=getattr(job, "job_id"),
        source_path=source_path,
        root_dir=root_dir,
        metadata=metadata,
        execute_audio_extraction=execute_audio_extraction,
        audio_extraction_overwrite_existing=audio_extraction_overwrite_existing,
    )
    apply_preprocessing_pipeline_report_to_job(job, report)
    return report
