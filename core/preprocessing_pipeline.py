from __future__ import annotations

from pathlib import Path
from typing import Any

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
    )

    errors = _collect_unique(
        list(manifest_dict.get("errors") or []),
        list(audio_plan_dict.get("errors") or []),
        list(frame_plan_dict.get("errors") or []),
        list(cache_validation_dict.get("errors") or []),
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
) -> dict[str, Any]:
    report = build_preprocessing_pipeline_report(
        job_id=getattr(job, "job_id"),
        source_path=source_path,
        root_dir=root_dir,
        metadata=metadata,
    )
    apply_preprocessing_pipeline_report_to_job(job, report)
    return report
