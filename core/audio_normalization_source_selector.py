from __future__ import annotations

import json
import pathlib
from typing import Any

from models.audio_normalization_source import AudioNormalizationSourceSelection

_SOURCE_PRIORITY = [
    "analysis_audio",
    "speech_audio",
    "music_reference_audio",
    "original_wav",
]

_MANIFEST_DIRECT_FIELD_MAP: list[tuple[str, str]] = [
    ("analysis_audio_path", "analysis_audio"),
    ("speech_audio_path", "speech_audio"),
    ("music_reference_audio_path", "music_reference_audio"),
    ("music_audio_path", "music_reference_audio"),
    ("audio_main_path", "analysis_audio"),
    ("audio_speech_path", "speech_audio"),
    ("audio_music_path", "music_reference_audio"),
]

_VALID_TARGET_TYPES = frozenset({"analysis_audio", "speech_audio", "music_reference_audio"})

_JOB_ORIGINAL_SOURCE_FIELDS: list[str] = [
    "raw_video_path",
    "source_path",
    "input_path",
    "video_path",
    "original_source_path",
]


def is_wav_path(path: Any) -> bool:
    try:
        if not path:
            return False
        return str(path).lower().endswith(".wav")
    except Exception:
        return False


def path_exists(path: Any) -> bool:
    try:
        if not path:
            return False
        return pathlib.Path(str(path)).exists()
    except Exception:
        return False


def _extract_plan_targets(plan: Any, result: dict[str, str]) -> None:
    targets: Any = None
    if isinstance(plan, dict):
        targets = plan.get("targets")
    else:
        try:
            targets = getattr(plan, "targets", None)
        except Exception:
            return

    if not isinstance(targets, list):
        return

    for target in targets:
        if isinstance(target, dict):
            tt = str(target.get("target_type", "")).strip()
            if tt not in _VALID_TARGET_TYPES or tt in result:
                continue
            path = str(
                target.get("output_path")
                or target.get("path")
                or target.get("target_path")
                or ""
            ).strip()
            if path:
                result[tt] = path
        else:
            try:
                tt = str(getattr(target, "target_type", "")).strip()
                if tt not in _VALID_TARGET_TYPES or tt in result:
                    continue
                path = str(getattr(target, "output_path", "") or "").strip()
                if path:
                    result[tt] = path
            except Exception:
                continue


def extract_manifest_audio_targets(manifest: Any) -> dict[str, str]:
    result: dict[str, str] = {}

    if manifest is None:
        return result

    manifest_dict: dict[str, Any] | None = None
    if isinstance(manifest, dict):
        manifest_dict = manifest
    else:
        try:
            d = manifest.to_dict()
            if isinstance(d, dict):
                manifest_dict = d
        except Exception:
            pass

    if manifest_dict is not None:
        for field_name, target_type in _MANIFEST_DIRECT_FIELD_MAP:
            if target_type in result:
                continue
            raw = manifest_dict.get(field_name)
            path = str(raw or "").strip()
            if path:
                result[target_type] = path

        plan = manifest_dict.get("audio_extraction_plan")
        if plan is not None:
            _extract_plan_targets(plan, result)

    # Check object attributes for non-dict manifests (or as supplement)
    for field_name, target_type in _MANIFEST_DIRECT_FIELD_MAP:
        if target_type in result:
            continue
        try:
            val = getattr(manifest, field_name, None)
            path = str(val or "").strip()
            if path:
                result[target_type] = path
        except Exception:
            pass

    # Check audio_extraction_plan attribute on objects
    if not isinstance(manifest, dict):
        try:
            plan_attr = getattr(manifest, "audio_extraction_plan", None)
            if plan_attr is not None:
                _extract_plan_targets(plan_attr, result)
        except Exception:
            pass

    # Check audio_targets attribute (list on objects)
    try:
        audio_targets_attr = getattr(manifest, "audio_targets", None)
        if isinstance(audio_targets_attr, list):
            _extract_plan_targets({"targets": audio_targets_attr}, result)
    except Exception:
        pass

    return result


def select_audio_normalization_source(
    preprocessing_manifest: Any | None = None,
    original_source_path: str | None = None,
    require_existing_file: bool = True,
    allow_original_wav_fallback: bool = True,
    metadata: dict[str, Any] | None = None,
) -> AudioNormalizationSourceSelection:
    checked_sources: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
    meta = metadata or {}

    audio_targets: dict[str, str] = {}
    if preprocessing_manifest is not None:
        try:
            audio_targets = extract_manifest_audio_targets(preprocessing_manifest)
        except Exception:
            pass

    def _make(
        status: str,
        selected_path: str | None = None,
        selected_type: str | None = None,
        requires_extraction: bool = False,
        is_wav_source: bool = False,
        source_exists: bool = False,
        recommendation: str = "review",
    ) -> AudioNormalizationSourceSelection:
        return AudioNormalizationSourceSelection(
            status=status,
            selected_path=selected_path,
            selected_type=selected_type,
            source_priority=list(_SOURCE_PRIORITY),
            checked_sources=list(checked_sources),
            requires_extraction=requires_extraction,
            require_existing_file=require_existing_file,
            is_wav_source=is_wav_source,
            source_exists=source_exists,
            original_source_path=original_source_path,
            recommendation=recommendation,
            warnings=list(warnings),
            errors=list(errors),
            metadata=dict(meta),
        )

    # 1. analysis_audio
    analysis_path = audio_targets.get("analysis_audio")
    if analysis_path:
        is_wav = is_wav_path(analysis_path)
        exists = path_exists(analysis_path)
        if not is_wav:
            checked_sources.append({
                "type": "analysis_audio",
                "path": analysis_path,
                "exists": exists,
                "is_wav": False,
                "usable": False,
                "reason": "non_wav_preprocessed_audio",
            })
            # not WAV — fall through to speech_audio
        elif exists:
            checked_sources.append({
                "type": "analysis_audio",
                "path": analysis_path,
                "exists": True,
                "is_wav": True,
                "usable": True,
                "reason": "ok",
            })
            return _make(
                status="selected",
                selected_path=analysis_path,
                selected_type="analysis_audio",
                is_wav_source=True,
                source_exists=True,
                recommendation="analyze_selected_wav",
            )
        else:
            # WAV but missing — block for preprocessing
            checked_sources.append({
                "type": "analysis_audio",
                "path": analysis_path,
                "exists": False,
                "is_wav": True,
                "usable": False,
                "reason": "file_not_found",
            })
            return _make(
                status="missing_preprocessed_audio",
                selected_path=analysis_path,
                selected_type="planned_analysis_audio",
                requires_extraction=True,
                is_wav_source=True,
                source_exists=False,
                recommendation="generate_preprocessed_audio",
            )

    # 2. speech_audio
    speech_path = audio_targets.get("speech_audio")
    if speech_path:
        is_wav = is_wav_path(speech_path)
        exists = path_exists(speech_path)
        if not is_wav:
            checked_sources.append({
                "type": "speech_audio",
                "path": speech_path,
                "exists": exists,
                "is_wav": False,
                "usable": False,
                "reason": "non_wav_preprocessed_audio",
            })
            # not WAV — fall through to music_reference
        elif exists:
            checked_sources.append({
                "type": "speech_audio",
                "path": speech_path,
                "exists": True,
                "is_wav": True,
                "usable": True,
                "reason": "ok",
            })
            return _make(
                status="selected",
                selected_path=speech_path,
                selected_type="speech_audio",
                is_wav_source=True,
                source_exists=True,
                recommendation="analyze_selected_wav",
            )
        else:
            # WAV but missing — block for preprocessing
            checked_sources.append({
                "type": "speech_audio",
                "path": speech_path,
                "exists": False,
                "is_wav": True,
                "usable": False,
                "reason": "file_not_found",
            })
            return _make(
                status="missing_preprocessed_audio",
                selected_path=speech_path,
                selected_type="planned_speech_audio",
                requires_extraction=True,
                is_wav_source=True,
                source_exists=False,
                recommendation="generate_preprocessed_audio",
            )

    # 3. music_reference_audio (fallback with warning)
    music_path = audio_targets.get("music_reference_audio")
    if music_path:
        is_wav = is_wav_path(music_path)
        exists = path_exists(music_path)
        if is_wav and exists:
            checked_sources.append({
                "type": "music_reference_audio",
                "path": music_path,
                "exists": True,
                "is_wav": True,
                "usable": True,
                "reason": "music_reference_last_resort",
            })
            warnings.append("music_reference_audio_used_for_normalization")
            return _make(
                status="selected_fallback",
                selected_path=music_path,
                selected_type="music_reference_audio",
                is_wav_source=True,
                source_exists=True,
                recommendation="review_warning",
            )
        else:
            checked_sources.append({
                "type": "music_reference_audio",
                "path": music_path,
                "exists": exists,
                "is_wav": is_wav,
                "usable": False,
                "reason": "file_not_found" if is_wav else "non_wav_preprocessed_audio",
            })
            # Don't block — continue to original_wav fallback

    # 4. original_source_path fallback
    if allow_original_wav_fallback and original_source_path:
        is_wav = is_wav_path(original_source_path)
        exists = path_exists(original_source_path)
        if is_wav and exists:
            checked_sources.append({
                "type": "original_wav",
                "path": original_source_path,
                "exists": True,
                "is_wav": True,
                "usable": True,
                "reason": "original_wav_fallback",
            })
            warnings.append("original_wav_used_for_normalization")
            return _make(
                status="selected_fallback",
                selected_path=original_source_path,
                selected_type="original_wav",
                is_wav_source=True,
                source_exists=True,
                recommendation="review_warning",
            )
        elif not is_wav:
            checked_sources.append({
                "type": "original_source",
                "path": original_source_path,
                "exists": exists,
                "is_wav": False,
                "usable": False,
                "reason": "not_wav_requires_extraction",
            })
            return _make(
                status="skipped_unsupported_source",
                selected_path=original_source_path,
                selected_type="unsupported_original_source",
                requires_extraction=True,
                is_wav_source=False,
                source_exists=exists,
                recommendation="extract_audio_first",
            )
        else:
            # WAV but missing
            checked_sources.append({
                "type": "original_wav",
                "path": original_source_path,
                "exists": False,
                "is_wav": True,
                "usable": False,
                "reason": "file_not_found",
            })

    # Nothing usable found
    errors.append("no_audio_normalization_source_available")
    return _make(
        status="unavailable",
        selected_path=None,
        selected_type="none",
        recommendation="no_audio_source_available",
    )


def select_audio_normalization_source_for_job(
    job: Any,
    require_existing_file: bool = True,
    allow_original_wav_fallback: bool = True,
    metadata: dict[str, Any] | None = None,
) -> AudioNormalizationSourceSelection:
    manifest: Any = None
    manifest_path_str: str | None = None

    # 1. job.preprocessing_manifest (dict or object)
    try:
        raw = getattr(job, "preprocessing_manifest", None)
        if raw is not None:
            manifest = raw
    except Exception:
        pass

    # 2. job.preprocessing_manifest_path → load JSON file
    if manifest is None:
        try:
            mp = getattr(job, "preprocessing_manifest_path", None)
            if mp and isinstance(mp, str):
                p = pathlib.Path(mp)
                if p.is_file():
                    manifest_path_str = mp
                    manifest = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 3. job.manifest
    if manifest is None:
        try:
            m = getattr(job, "manifest", None)
            if m is not None:
                manifest = m
        except Exception:
            pass

    # 4. job.metadata["preprocessing_manifest"]
    if manifest is None:
        try:
            meta_dict = getattr(job, "metadata", None)
            if isinstance(meta_dict, dict):
                m = meta_dict.get("preprocessing_manifest")
                if m is not None:
                    manifest = m
        except Exception:
            pass

    # Find original source path
    original_source: str | None = None
    for field_name in _JOB_ORIGINAL_SOURCE_FIELDS:
        try:
            val = getattr(job, field_name, None)
            if val and isinstance(val, str):
                original_source = val
                break
        except Exception:
            pass

    if original_source is None:
        try:
            meta_dict = getattr(job, "metadata", None)
            if isinstance(meta_dict, dict):
                for key in ("raw_video_path", "source_path"):
                    val = meta_dict.get(key)
                    if val and isinstance(val, str):
                        original_source = val
                        break
        except Exception:
            pass

    result = select_audio_normalization_source(
        preprocessing_manifest=manifest,
        original_source_path=original_source,
        require_existing_file=require_existing_file,
        allow_original_wav_fallback=allow_original_wav_fallback,
        metadata=metadata,
    )

    if manifest_path_str is not None:
        result.preprocessing_manifest_path = manifest_path_str

    return result
