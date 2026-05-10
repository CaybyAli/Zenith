from __future__ import annotations

from typing import Any

from models.frame_extraction_plan import FrameExtractionPlan, FrameExtractionTarget
from models.preprocessing_manifest import PreprocessingManifest


def _fps_filter(interval_seconds: float | None) -> str | None:
    if interval_seconds is None or interval_seconds <= 0:
        return None
    return f"fps=1/{interval_seconds}"


def _scale_filter(width: int | None, height: int | None) -> str | None:
    if width is None and height is None:
        return None

    resolved_width = width if width is not None else -1
    resolved_height = height if height is not None else -1

    return f"scale={resolved_width}:{resolved_height}"


def _build_command_preview(
    source_path: str,
    output_pattern: str,
    interval_seconds: float | None = None,
    width: int | None = None,
    height: int | None = None,
) -> list[str]:
    filters: list[str] = []

    fps_filter = _fps_filter(interval_seconds)
    if fps_filter:
        filters.append(fps_filter)

    scale_filter = _scale_filter(width, height)
    if scale_filter:
        filters.append(scale_filter)

    command = ["ffmpeg", "-i", source_path]

    if filters:
        command.extend(["-vf", ",".join(filters)])

    command.append(output_pattern)
    return command


def build_default_frame_targets(
    manifest: PreprocessingManifest,
) -> list[FrameExtractionTarget]:
    motion_pattern = str(manifest.frame_pattern).replace("frame_%06d", "motion_%06d")

    return [
        FrameExtractionTarget(
            target_id="analysis_frames",
            purpose="analysis",
            output_pattern=manifest.frame_pattern,
            format="jpg",
            interval_seconds=1.0,
            enabled=True,
            command_preview=_build_command_preview(
                manifest.source_path,
                manifest.frame_pattern,
                interval_seconds=1.0,
            ),
        ),
        FrameExtractionTarget(
            target_id="preview_thumbnails",
            purpose="preview_thumbnail",
            output_pattern=manifest.thumbnail_pattern,
            format="jpg",
            interval_seconds=10.0,
            width=640,
            height=None,
            enabled=True,
            command_preview=_build_command_preview(
                manifest.source_path,
                manifest.thumbnail_pattern,
                interval_seconds=10.0,
                width=640,
                height=None,
            ),
        ),
        FrameExtractionTarget(
            target_id="dense_motion_frames",
            purpose="motion_analysis",
            output_pattern=motion_pattern,
            format="jpg",
            interval_seconds=0.5,
            enabled=False,
            status="planned_disabled",
            warnings=["disabled_by_default"],
            command_preview=_build_command_preview(
                manifest.source_path,
                motion_pattern,
                interval_seconds=0.5,
            ),
        ),
    ]


def build_frame_extraction_plan(
    manifest: PreprocessingManifest,
    metadata: dict[str, Any] | None = None,
) -> FrameExtractionPlan:
    targets = build_default_frame_targets(manifest)

    warnings: list[str] = []
    errors: list[str] = []

    if manifest.status == "missing_source":
        errors.append("source_missing")

    status = "planned" if not errors else "blocked"

    return FrameExtractionPlan(
        job_id=manifest.job_id,
        source_path=manifest.source_path,
        frames_dir=manifest.frames_dir,
        thumbnails_dir=manifest.thumbnails_dir,
        targets=targets,
        status=status,
        warnings=warnings,
        errors=errors,
        metadata=dict(metadata or {}),
    )


def apply_frame_extraction_plan_to_manifest(
    manifest: PreprocessingManifest,
    plan: FrameExtractionPlan,
) -> PreprocessingManifest:
    plan_dict = plan.to_dict()
    manifest.frame_extraction_plan = plan_dict
    manifest.frame_targets = plan_dict.get("targets", [])
    return manifest


def apply_frame_extraction_plan_to_job(
    job: Any,
    plan: FrameExtractionPlan,
) -> Any:
    plan_dict = plan.to_dict()
    job.frame_extraction_plan = plan_dict
    job.frame_targets = plan_dict.get("targets", [])

    if hasattr(job, "touch"):
        job.touch()

    return job
