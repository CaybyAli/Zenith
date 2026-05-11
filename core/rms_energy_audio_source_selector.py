from __future__ import annotations

import os
from typing import Any

from models.rms_energy_audio_source import RmsEnergyAudioSourceSelection

_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".ts", ".m2ts"}

_MANIFEST_DIRECT_FIELDS: list[tuple[str, str]] = [
    ("analysis_audio_path", "analysis_audio"),
    ("speech_audio_path", "speech_audio"),
    ("audio_main_path", "analysis_audio"),
    ("audio_speech_path", "speech_audio"),
    ("music_reference_audio_path", "music_reference_audio"),
    ("music_audio_path", "music_reference_audio"),
    ("audio_music_path", "music_reference_audio"),
]

_JOB_FALLBACK_FIELDS: list[str] = [
    "raw_video_path",
    "input_file",
    "source_file",
    "video_path",
    "file_path",
]

_PLAN_TYPE_MAP: dict[str, str] = {
    "analysis_audio": "analysis_audio",
    "speech_audio": "speech_audio",
    "music_reference_audio": "music_reference_audio",
}


def _is_wav_path(path: str) -> bool:
    return path.lower().endswith(".wav")


def _path_exists(path: str) -> bool:
    try:
        return os.path.exists(path)
    except Exception:
        return False


def _is_video_path(path: str) -> bool:
    ext = os.path.splitext(path.lower())[1]
    return ext in _VIDEO_EXTENSIONS


def _collect_manifest_candidates(
    manifest: dict[str, Any],
) -> list[tuple[str, str]]:
    """Return (path, source_type) candidates in priority order, deduped by path."""
    seen: set[str] = set()
    candidates: list[tuple[str, str]] = []

    # Direct manifest fields (in priority order)
    for field_name, source_type in _MANIFEST_DIRECT_FIELDS:
        raw = manifest.get(field_name)
        path = str(raw or "").strip()
        if path and path not in seen:
            seen.add(path)
            candidates.append((path, source_type))

    # audio_extraction_plan targets
    plan = manifest.get("audio_extraction_plan")
    if isinstance(plan, dict):
        targets = plan.get("targets") or []
        if isinstance(targets, list):
            for target in targets:
                if not isinstance(target, dict):
                    continue
                target_type = str(target.get("target_type", "")).strip()
                mapped_type = _PLAN_TYPE_MAP.get(target_type)
                if not mapped_type:
                    continue
                path = str(
                    target.get("output_path")
                    or target.get("path")
                    or target.get("target_path")
                    or ""
                ).strip()
                if path and path not in seen:
                    seen.add(path)
                    candidates.append((path, mapped_type))

    return candidates


def select_rms_energy_audio_source(
    preprocessing_manifest: dict[str, Any] | None = None,
    fallback_source_path: str | None = None,
    require_existing_file: bool = True,
    allow_original_wav_fallback: bool = True,
) -> RmsEnergyAudioSourceSelection:
    checked_sources: list[dict[str, Any]] = []
    source_priority: list[str] = []

    # Gather manifest candidates
    manifest_candidates: list[tuple[str, str]] = []
    if preprocessing_manifest and isinstance(preprocessing_manifest, dict):
        manifest_candidates = _collect_manifest_candidates(preprocessing_manifest)

    for _, source_type in manifest_candidates:
        if source_type not in source_priority:
            source_priority.append(source_type)

    if fallback_source_path and allow_original_wav_fallback:
        if "original_wav" not in source_priority:
            source_priority.append("original_wav")

    # Split by type for planned-fallback tracking
    planned_analysis: str | None = None
    planned_speech: str | None = None

    for path, source_type in manifest_candidates:
        if source_type == "analysis_audio" and planned_analysis is None:
            planned_analysis = path
        if source_type == "speech_audio" and planned_speech is None:
            planned_speech = path

    if not require_existing_file:
        # Accept first WAV manifest candidate even if missing
        for path, source_type in manifest_candidates:
            is_wav = _is_wav_path(path)
            exists = _path_exists(path)
            if not is_wav:
                checked_sources.append({
                    "source_type": source_type,
                    "path": path,
                    "exists": exists,
                    "is_wav": False,
                    "accepted": False,
                    "reason": "not_wav",
                })
                continue
            if source_type == "music_reference_audio":
                checked_sources.append({
                    "source_type": source_type,
                    "path": path,
                    "exists": exists,
                    "is_wav": True,
                    "accepted": False,
                    "reason": "music_reference_skipped_in_planned_mode",
                })
                continue
            planned_type = (
                "planned_analysis_audio"
                if source_type == "analysis_audio"
                else "planned_speech_audio"
            )
            checked_sources.append({
                "source_type": source_type,
                "path": path,
                "exists": exists,
                "is_wav": True,
                "accepted": True,
                "reason": "planned_preprocessed_audio",
            })
            return RmsEnergyAudioSourceSelection(
                status="missing_preprocessed_audio",
                selected_path=path,
                selected_type=planned_type,
                exists=exists,
                is_wav=True,
                source_priority=list(source_priority),
                checked_sources=checked_sources,
                allow_original_wav_fallback=allow_original_wav_fallback,
                requires_extraction=True,
                warnings=[],
                errors=[],
                recommendation="generate_preprocessed_audio",
            )

        # No planned manifest WAV found — check fallback
        if fallback_source_path and allow_original_wav_fallback:
            is_wav = _is_wav_path(fallback_source_path)
            exists = _path_exists(fallback_source_path)
            is_video = _is_video_path(fallback_source_path)
            if is_video or not is_wav:
                checked_sources.append({
                    "source_type": "original_source",
                    "path": fallback_source_path,
                    "exists": exists,
                    "is_wav": is_wav,
                    "accepted": False,
                    "reason": "not_wav_video_source",
                })
                return RmsEnergyAudioSourceSelection(
                    status="unsupported_original_source",
                    selected_path=None,
                    selected_type=None,
                    exists=False,
                    is_wav=False,
                    source_priority=list(source_priority),
                    checked_sources=checked_sources,
                    allow_original_wav_fallback=allow_original_wav_fallback,
                    requires_extraction=True,
                    warnings=["original_source_not_wav"],
                    errors=[],
                    recommendation="extract_audio_first",
                )
            checked_sources.append({
                "source_type": "original_wav",
                "path": fallback_source_path,
                "exists": exists,
                "is_wav": True,
                "accepted": True,
                "reason": "original_wav_fallback_planned_mode",
            })
            return RmsEnergyAudioSourceSelection(
                status="selected_fallback",
                selected_path=fallback_source_path,
                selected_type="original_wav",
                exists=exists,
                is_wav=True,
                source_priority=list(source_priority),
                checked_sources=checked_sources,
                allow_original_wav_fallback=allow_original_wav_fallback,
                requires_extraction=False,
                warnings=["original_wav_used_for_rms_energy"],
                errors=[],
                recommendation="analyze_wav",
            )

        return RmsEnergyAudioSourceSelection(
            status="unavailable",
            selected_path=None,
            selected_type=None,
            exists=False,
            is_wav=False,
            source_priority=list(source_priority),
            checked_sources=checked_sources,
            allow_original_wav_fallback=allow_original_wav_fallback,
            requires_extraction=False,
            warnings=[],
            errors=["no_rms_energy_audio_source_available"],
            recommendation="no_audio_source_available",
        )

    # require_existing_file=True — walk candidates in priority order
    # Separate music_reference candidates so they are only used as last resort
    primary_candidates = [
        (p, t) for p, t in manifest_candidates if t != "music_reference_audio"
    ]
    music_candidates = [
        (p, t) for p, t in manifest_candidates if t == "music_reference_audio"
    ]

    # Try primary preprocessed candidates first
    for path, source_type in primary_candidates:
        is_wav = _is_wav_path(path)
        exists = _path_exists(path)

        if not is_wav:
            checked_sources.append({
                "source_type": source_type,
                "path": path,
                "exists": exists,
                "is_wav": False,
                "accepted": False,
                "reason": "not_wav",
            })
            continue

        if not exists:
            checked_sources.append({
                "source_type": source_type,
                "path": path,
                "exists": False,
                "is_wav": True,
                "accepted": False,
                "reason": "file_not_found",
            })
            continue

        checked_sources.append({
            "source_type": source_type,
            "path": path,
            "exists": True,
            "is_wav": True,
            "accepted": True,
            "reason": "ok",
        })
        return RmsEnergyAudioSourceSelection(
            status="selected",
            selected_path=path,
            selected_type=source_type,
            exists=True,
            is_wav=True,
            source_priority=list(source_priority),
            checked_sources=checked_sources,
            allow_original_wav_fallback=allow_original_wav_fallback,
            requires_extraction=False,
            warnings=[],
            errors=[],
            recommendation="analyze_wav",
        )

    # Try original WAV fallback before music_reference
    if fallback_source_path and allow_original_wav_fallback:
        is_wav = _is_wav_path(fallback_source_path)
        exists = _path_exists(fallback_source_path)
        is_video = _is_video_path(fallback_source_path)

        if is_video or not is_wav:
            checked_sources.append({
                "source_type": "original_source",
                "path": fallback_source_path,
                "exists": exists,
                "is_wav": is_wav,
                "accepted": False,
                "reason": "not_wav_video_source",
            })
            # Don't return yet — still try music_reference below
        elif exists:
            checked_sources.append({
                "source_type": "original_wav",
                "path": fallback_source_path,
                "exists": True,
                "is_wav": True,
                "accepted": True,
                "reason": "original_wav_fallback",
            })
            return RmsEnergyAudioSourceSelection(
                status="selected_fallback",
                selected_path=fallback_source_path,
                selected_type="original_wav",
                exists=True,
                is_wav=True,
                source_priority=list(source_priority),
                checked_sources=checked_sources,
                allow_original_wav_fallback=allow_original_wav_fallback,
                requires_extraction=False,
                warnings=["original_wav_used_for_rms_energy"],
                errors=[],
                recommendation="analyze_wav",
            )
        else:
            checked_sources.append({
                "source_type": "original_wav",
                "path": fallback_source_path,
                "exists": False,
                "is_wav": True,
                "accepted": False,
                "reason": "file_not_found",
            })

    # Try music_reference as last-resort fallback
    for path, source_type in music_candidates:
        is_wav = _is_wav_path(path)
        exists = _path_exists(path)

        if not is_wav:
            checked_sources.append({
                "source_type": source_type,
                "path": path,
                "exists": exists,
                "is_wav": False,
                "accepted": False,
                "reason": "not_wav",
            })
            continue

        if not exists:
            checked_sources.append({
                "source_type": source_type,
                "path": path,
                "exists": False,
                "is_wav": True,
                "accepted": False,
                "reason": "file_not_found",
            })
            continue

        checked_sources.append({
            "source_type": source_type,
            "path": path,
            "exists": True,
            "is_wav": True,
            "accepted": True,
            "reason": "music_reference_last_resort",
        })
        return RmsEnergyAudioSourceSelection(
            status="selected_fallback",
            selected_path=path,
            selected_type="music_reference_audio",
            exists=True,
            is_wav=True,
            source_priority=list(source_priority),
            checked_sources=checked_sources,
            allow_original_wav_fallback=allow_original_wav_fallback,
            requires_extraction=False,
            warnings=["music_reference_audio_used_for_rms_energy"],
            errors=[],
            recommendation="review_warnings",
        )

    # Nothing found — determine best status/recommendation
    has_planned_wav = any(
        _is_wav_path(p)
        for p, t in manifest_candidates
        if t in ("analysis_audio", "speech_audio")
    )

    if has_planned_wav:
        # Pick the first planned WAV to surface as the planned path
        planned_path: str | None = None
        planned_sel_type: str | None = None
        for path, source_type in manifest_candidates:
            if source_type in ("analysis_audio", "speech_audio") and _is_wav_path(path):
                planned_path = path
                planned_sel_type = (
                    "planned_analysis_audio"
                    if source_type == "analysis_audio"
                    else "planned_speech_audio"
                )
                break
        return RmsEnergyAudioSourceSelection(
            status="missing_preprocessed_audio",
            selected_path=planned_path,
            selected_type=planned_sel_type,
            exists=False,
            is_wav=True,
            source_priority=list(source_priority),
            checked_sources=checked_sources,
            allow_original_wav_fallback=allow_original_wav_fallback,
            requires_extraction=True,
            warnings=[],
            errors=[],
            recommendation="generate_preprocessed_audio",
        )

    # Check if only a non-WAV video fallback was rejected
    if fallback_source_path and not allow_original_wav_fallback:
        pass  # fallback disabled entirely, fall through
    elif fallback_source_path and _is_video_path(fallback_source_path):
        return RmsEnergyAudioSourceSelection(
            status="unsupported_original_source",
            selected_path=None,
            selected_type=None,
            exists=False,
            is_wav=False,
            source_priority=list(source_priority),
            checked_sources=checked_sources,
            allow_original_wav_fallback=allow_original_wav_fallback,
            requires_extraction=True,
            warnings=["original_source_not_wav"],
            errors=[],
            recommendation="extract_audio_first",
        )

    return RmsEnergyAudioSourceSelection(
        status="unavailable",
        selected_path=None,
        selected_type=None,
        exists=False,
        is_wav=False,
        source_priority=list(source_priority),
        checked_sources=checked_sources,
        allow_original_wav_fallback=allow_original_wav_fallback,
        requires_extraction=False,
        warnings=[],
        errors=["no_rms_energy_audio_source_available"],
        recommendation="no_audio_source_available",
    )


def select_rms_energy_audio_source_for_job(
    job: Any,
    require_existing_file: bool = True,
    allow_original_wav_fallback: bool = True,
) -> RmsEnergyAudioSourceSelection:
    manifest: dict[str, Any] | None = None
    try:
        raw_manifest = getattr(job, "preprocessing_manifest", None)
        if isinstance(raw_manifest, dict) and raw_manifest:
            manifest = raw_manifest
    except Exception:
        pass

    fallback: str | None = None
    for field_name in _JOB_FALLBACK_FIELDS:
        try:
            val = getattr(job, field_name, None)
            if val and isinstance(val, str):
                fallback = val
                break
        except Exception:
            pass

    return select_rms_energy_audio_source(
        preprocessing_manifest=manifest,
        fallback_source_path=fallback,
        require_existing_file=require_existing_file,
        allow_original_wav_fallback=allow_original_wav_fallback,
    )
