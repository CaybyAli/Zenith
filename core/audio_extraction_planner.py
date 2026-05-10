from __future__ import annotations

from typing import Any

from models.audio_extraction_plan import AudioExtractionPlan, AudioExtractionTarget
from models.preprocessing_manifest import PreprocessingManifest


def _build_command_preview(
    source_path: str,
    output_path: str,
    sample_rate: int | None,
    channels: int | None,
    source_stream_index: int | None = None,
) -> list[str]:
    command = ["ffmpeg", "-i", source_path, "-vn"]

    if source_stream_index is not None:
        command.extend(["-map", f"0:{source_stream_index}"])

    if channels is not None:
        command.extend(["-ac", str(channels)])

    if sample_rate is not None:
        command.extend(["-ar", str(sample_rate)])

    command.append(output_path)
    return command


def build_default_audio_targets(
    manifest: PreprocessingManifest,
    source_stream_index: int | None = None,
) -> list[AudioExtractionTarget]:
    return [
        AudioExtractionTarget(
            target_id="analysis_audio",
            purpose="analysis",
            output_path=manifest.analysis_audio_path,
            sample_rate=44100,
            channels=2,
            source_stream_index=source_stream_index,
            command_preview=_build_command_preview(
                manifest.source_path,
                manifest.analysis_audio_path,
                44100,
                2,
                source_stream_index,
            ),
        ),
        AudioExtractionTarget(
            target_id="speech_audio",
            purpose="speech",
            output_path=manifest.speech_audio_path,
            sample_rate=16000,
            channels=1,
            source_stream_index=source_stream_index,
            command_preview=_build_command_preview(
                manifest.source_path,
                manifest.speech_audio_path,
                16000,
                1,
                source_stream_index,
            ),
        ),
        AudioExtractionTarget(
            target_id="music_reference_audio",
            purpose="music_reference",
            output_path=manifest.music_audio_path,
            sample_rate=44100,
            channels=2,
            source_stream_index=source_stream_index,
            command_preview=_build_command_preview(
                manifest.source_path,
                manifest.music_audio_path,
                44100,
                2,
                source_stream_index,
            ),
        ),
    ]


def build_audio_extraction_plan(
    manifest: PreprocessingManifest,
    source_stream_index: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AudioExtractionPlan:
    targets = build_default_audio_targets(
        manifest=manifest,
        source_stream_index=source_stream_index,
    )

    warnings: list[str] = []
    errors: list[str] = []

    if manifest.status == "missing_source":
        errors.append("source_missing")

    status = "planned" if not errors else "blocked"

    return AudioExtractionPlan(
        job_id=manifest.job_id,
        source_path=manifest.source_path,
        audio_dir=manifest.audio_dir,
        targets=targets,
        status=status,
        warnings=warnings,
        errors=errors,
        metadata=dict(metadata or {}),
    )


def apply_audio_extraction_plan_to_manifest(
    manifest: PreprocessingManifest,
    plan: AudioExtractionPlan,
) -> PreprocessingManifest:
    plan_dict = plan.to_dict()
    manifest.audio_extraction_plan = plan_dict
    manifest.audio_targets = plan_dict.get("targets", [])
    return manifest


def apply_audio_extraction_plan_to_job(
    job: Any,
    plan: AudioExtractionPlan,
) -> Any:
    plan_dict = plan.to_dict()
    job.audio_extraction_plan = plan_dict
    job.audio_targets = plan_dict.get("targets", [])

    if hasattr(job, "touch"):
        job.touch()

    return job
