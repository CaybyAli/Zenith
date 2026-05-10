from __future__ import annotations

import os
from typing import Any

from models.silence_audio_source import SilenceAudioSourceSelection

_MANIFEST_CANDIDATES: list[tuple[str, str]] = [
    ("analysis_audio_path", "analysis_audio"),
    ("speech_audio_path", "speech_audio"),
    ("music_audio_path", "music_reference_audio"),
]

_JOB_FALLBACK_FIELDS: list[str] = [
    "raw_video_path",
    "input_file",
    "source_file",
    "video_path",
    "file_path",
]


def select_silence_audio_source(
    preprocessing_manifest: dict[str, Any] | None = None,
    fallback_source_path: str | None = None,
    require_existing_file: bool = True,
) -> SilenceAudioSourceSelection:
    checked_paths: list[str] = []
    preferred_order: list[str] = []

    preprocessed_candidates: list[tuple[str, str]] = []
    if preprocessing_manifest:
        for manifest_field, source_type in _MANIFEST_CANDIDATES:
            raw = preprocessing_manifest.get(manifest_field)
            path = str(raw or "").strip()
            if path:
                preprocessed_candidates.append((path, source_type))
                preferred_order.append(source_type)

    if fallback_source_path:
        preferred_order.append("original_source")

    if not require_existing_file:
        for path, source_type in preprocessed_candidates:
            return SilenceAudioSourceSelection(
                selected_path=path,
                source_type=source_type,
                status="missing_preprocessed_audio",
                exists=os.path.exists(path),
                checked_paths=[path],
                preferred_order=preferred_order,
                warnings=[],
                errors=[],
                recommendation="extract_audio_first",
            )
        if fallback_source_path:
            exists = os.path.exists(fallback_source_path)
            return SilenceAudioSourceSelection(
                selected_path=fallback_source_path if exists else None,
                source_type="original_source" if exists else "none",
                status="selected_fallback" if exists else "unavailable",
                exists=exists,
                checked_paths=[fallback_source_path],
                preferred_order=preferred_order,
                warnings=["original_source_used_for_silence_detection"] if exists else [],
                errors=[] if exists else ["no_silence_audio_source_available"],
                recommendation="use_fallback" if exists else "reject_or_retry",
            )
        return SilenceAudioSourceSelection(
            selected_path=None,
            source_type="none",
            status="unavailable",
            exists=False,
            checked_paths=[],
            preferred_order=preferred_order,
            warnings=[],
            errors=["no_silence_audio_source_available"],
            recommendation="reject_or_retry",
        )

    # require_existing_file=True
    preprocessed_missing_count = 0
    for path, source_type in preprocessed_candidates:
        checked_paths.append(path)
        if os.path.exists(path):
            result_warnings: list[str] = []
            if preprocessed_missing_count > 0:
                result_warnings.append("preprocessed_audio_missing")
            if source_type == "music_reference_audio":
                result_warnings.append("music_reference_audio_used_for_silence_detection")
            return SilenceAudioSourceSelection(
                selected_path=path,
                source_type=source_type,
                status="selected",
                exists=True,
                checked_paths=list(checked_paths),
                preferred_order=preferred_order,
                warnings=result_warnings,
                errors=[],
                recommendation="use_selected",
            )
        preprocessed_missing_count += 1

    if fallback_source_path:
        checked_paths.append(fallback_source_path)
        fallback_warnings: list[str] = []
        if preprocessed_missing_count > 0:
            fallback_warnings.append("preprocessed_audio_missing")
        fallback_warnings.append("original_source_used_for_silence_detection")

        if os.path.exists(fallback_source_path):
            return SilenceAudioSourceSelection(
                selected_path=fallback_source_path,
                source_type="original_source",
                status="selected_fallback",
                exists=True,
                checked_paths=list(checked_paths),
                preferred_order=preferred_order,
                warnings=fallback_warnings,
                errors=[],
                recommendation="use_fallback",
            )
        fallback_warnings.append("original_source_does_not_exist")
        return SilenceAudioSourceSelection(
            selected_path=None,
            source_type="none",
            status="unavailable",
            exists=False,
            checked_paths=list(checked_paths),
            preferred_order=preferred_order,
            warnings=fallback_warnings,
            errors=["no_silence_audio_source_available"],
            recommendation="reject_or_retry",
        )

    return SilenceAudioSourceSelection(
        selected_path=None,
        source_type="none",
        status="unavailable",
        exists=False,
        checked_paths=list(checked_paths),
        preferred_order=preferred_order,
        warnings=[],
        errors=["no_silence_audio_source_available"],
        recommendation="reject_or_retry",
    )


def select_silence_audio_source_for_job(
    job: Any,
    require_existing_file: bool = True,
) -> SilenceAudioSourceSelection:
    manifest: dict[str, Any] | None = None
    raw_manifest = getattr(job, "preprocessing_manifest", None)
    if isinstance(raw_manifest, dict) and raw_manifest:
        manifest = raw_manifest

    fallback: str | None = None
    for field_name in _JOB_FALLBACK_FIELDS:
        val = getattr(job, field_name, None)
        if val and isinstance(val, str):
            fallback = val
            break

    return select_silence_audio_source(
        preprocessing_manifest=manifest,
        fallback_source_path=fallback,
        require_existing_file=require_existing_file,
    )
