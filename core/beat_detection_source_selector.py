from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.beat_detection_source import BeatDetectionSourceSelection


SOURCE_PRIORITY = [
    "music_reference_audio",
    "analysis_audio",
    "original_wav",
]

MUSIC_DIRECT_FIELDS = [
    "music_reference_audio_path",
    "music_audio_path",
    "beat_audio_path",
]

ANALYSIS_DIRECT_FIELDS = [
    "analysis_audio_path",
    "audio_main_path",
]

ORIGINAL_SOURCE_FIELDS = [
    "raw_video_path",
    "source_path",
    "input_path",
    "video_path",
    "original_source_path",
]


def _safe_text(value: Any) -> str | None:
    if value is None:
        return None

    try:
        text = str(value).strip()
    except Exception:
        return None

    if not text:
        return None

    return text


def _get_value(source: Any, key: str) -> Any:
    if source is None:
        return None

    if isinstance(source, dict):
        return source.get(key)

    return getattr(source, key, None)


def _first_text_from_keys(source: Any, keys: list[str]) -> str | None:
    for key in keys:
        value = _safe_text(_get_value(source, key))
        if value:
            return value

    return None


def is_wav_path(path: Any) -> bool:
    text = _safe_text(path)

    if not text:
        return False

    try:
        return Path(text).suffix.lower() == ".wav"
    except Exception:
        return False


def path_exists(path: Any) -> bool:
    text = _safe_text(path)

    if not text:
        return False

    try:
        return Path(text).exists()
    except Exception:
        return False


def _target_path_from_value(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, (str, Path)):
        return _safe_text(value)

    if isinstance(value, dict):
        for key in ["output_path", "path", "target_path"]:
            text = _safe_text(value.get(key))
            if text:
                return text
        return None

    for key in ["output_path", "path", "target_path"]:
        text = _safe_text(getattr(value, key, None))
        if text:
            return text

    return None


def _target_type_from_value(value: Any, fallback_type: str | None = None) -> str | None:
    target_type = None

    if isinstance(value, dict):
        target_type = _safe_text(value.get("target_type"))
    else:
        target_type = _safe_text(getattr(value, "target_type", None))

    if target_type:
        return target_type

    return fallback_type


def _record_target(
    result: dict[str, str],
    target_type: str | None,
    target_path: str | None,
) -> None:
    if target_type not in {"music_reference_audio", "analysis_audio"}:
        return

    if not target_path:
        return

    result[target_type] = target_path


def _extract_targets_from_container(container: Any, result: dict[str, str]) -> None:
    if container is None:
        return

    if isinstance(container, dict):
        for key, value in container.items():
            key_text = _safe_text(key)
            target_type = _target_type_from_value(value, key_text)
            target_path = _target_path_from_value(value)
            _record_target(result, target_type, target_path)
        return

    if isinstance(container, list) or isinstance(container, tuple):
        for item in container:
            target_type = _target_type_from_value(item)
            target_path = _target_path_from_value(item)
            _record_target(result, target_type, target_path)
        return

    target_type = _target_type_from_value(container)
    target_path = _target_path_from_value(container)
    _record_target(result, target_type, target_path)


def extract_manifest_beat_audio_targets(manifest: Any) -> dict[str, str]:
    result: dict[str, str] = {}

    if manifest is None:
        return result

    music_path = _first_text_from_keys(manifest, MUSIC_DIRECT_FIELDS)
    analysis_path = _first_text_from_keys(manifest, ANALYSIS_DIRECT_FIELDS)

    if music_path:
        result["music_reference_audio"] = music_path

    if analysis_path:
        result["analysis_audio"] = analysis_path

    audio_targets = _get_value(manifest, "audio_targets")
    _extract_targets_from_container(audio_targets, result)

    audio_extraction_plan = _get_value(manifest, "audio_extraction_plan")
    if audio_extraction_plan is not None:
        _extract_targets_from_container(audio_extraction_plan, result)

        plan_targets = _get_value(audio_extraction_plan, "targets")
        _extract_targets_from_container(plan_targets, result)

    direct_targets = _get_value(manifest, "targets")
    _extract_targets_from_container(direct_targets, result)

    return result


def _checked_source(
    source_type: str,
    source_path: str | None,
    exists: bool,
    is_wav: bool,
    usable: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "type": source_type,
        "path": source_path,
        "exists": exists,
        "is_wav": is_wav,
        "usable": usable,
        "reason": reason,
    }


def _selection(
    status: str,
    selected_path: str | None,
    selected_type: str | None,
    checked_sources: list[dict[str, Any]],
    require_existing_file: bool,
    original_source_path: str | None,
    preprocessing_manifest_path: str | None,
    recommendation: str,
    requires_extraction: bool = False,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> BeatDetectionSourceSelection:
    return BeatDetectionSourceSelection(
        status=status,
        selected_path=selected_path,
        selected_type=selected_type,
        source_priority=list(SOURCE_PRIORITY),
        checked_sources=checked_sources,
        requires_extraction=requires_extraction,
        require_existing_file=require_existing_file,
        is_wav_source=is_wav_path(selected_path),
        source_exists=path_exists(selected_path),
        original_source_path=original_source_path,
        preprocessing_manifest_path=preprocessing_manifest_path,
        recommendation=recommendation,
        warnings=list(warnings or []),
        errors=list(errors or []),
        metadata=dict(metadata or {}),
    )


def select_beat_detection_source(
    preprocessing_manifest: Any | None = None,
    original_source_path: str | None = None,
    require_existing_file: bool = True,
    allow_original_wav_fallback: bool = True,
    metadata: dict[str, Any] | None = None,
) -> BeatDetectionSourceSelection:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    checked_sources: list[dict[str, Any]] = []
    targets = extract_manifest_beat_audio_targets(preprocessing_manifest)

    manifest_path = _safe_text(safe_metadata.get("preprocessing_manifest_path"))
    original_path = _safe_text(original_source_path)

    for source_type in ["music_reference_audio", "analysis_audio"]:
        candidate_path = _safe_text(targets.get(source_type))

        if not candidate_path:
            checked_sources.append(
                _checked_source(
                    source_type=source_type,
                    source_path=None,
                    exists=False,
                    is_wav=False,
                    usable=False,
                    reason="source_not_declared",
                )
            )
            continue

        candidate_is_wav = is_wav_path(candidate_path)
        candidate_exists = path_exists(candidate_path)
        candidate_usable = candidate_is_wav and (candidate_exists or not require_existing_file)

        if candidate_usable:
            checked_sources.append(
                _checked_source(
                    source_type=source_type,
                    source_path=candidate_path,
                    exists=candidate_exists,
                    is_wav=candidate_is_wav,
                    usable=True,
                    reason="selected_wav_source",
                )
            )

            if source_type == "music_reference_audio":
                return _selection(
                    status="selected",
                    selected_path=candidate_path,
                    selected_type="music_reference_audio",
                    checked_sources=checked_sources,
                    require_existing_file=require_existing_file,
                    original_source_path=original_path,
                    preprocessing_manifest_path=manifest_path,
                    recommendation="analyze_selected_wav",
                    metadata=safe_metadata,
                )

            return _selection(
                status="selected_fallback",
                selected_path=candidate_path,
                selected_type="analysis_audio",
                checked_sources=checked_sources,
                require_existing_file=require_existing_file,
                original_source_path=original_path,
                preprocessing_manifest_path=manifest_path,
                recommendation="review_warning",
                warnings=["analysis_audio_used_for_beat_detection"],
                metadata=safe_metadata,
            )

        if not candidate_is_wav:
            checked_sources.append(
                _checked_source(
                    source_type=source_type,
                    source_path=candidate_path,
                    exists=candidate_exists,
                    is_wav=False,
                    usable=False,
                    reason="non_wav_preprocessed_audio",
                )
            )
            continue

        checked_sources.append(
            _checked_source(
                source_type=source_type,
                source_path=candidate_path,
                exists=False,
                is_wav=True,
                usable=False,
                reason="preprocessed_wav_missing",
            )
        )

        planned_type = (
            "planned_music_reference_audio"
            if source_type == "music_reference_audio"
            else "planned_analysis_audio"
        )

        return _selection(
            status="missing_preprocessed_audio",
            selected_path=candidate_path,
            selected_type=planned_type,
            checked_sources=checked_sources,
            require_existing_file=require_existing_file,
            original_source_path=original_path,
            preprocessing_manifest_path=manifest_path,
            recommendation="generate_preprocessed_audio",
            requires_extraction=True,
            metadata=safe_metadata,
        )

    if original_path:
        original_is_wav = is_wav_path(original_path)
        original_exists = path_exists(original_path)

        if allow_original_wav_fallback and original_is_wav and (
            original_exists or not require_existing_file
        ):
            checked_sources.append(
                _checked_source(
                    source_type="original_wav",
                    source_path=original_path,
                    exists=original_exists,
                    is_wav=True,
                    usable=True,
                    reason="selected_original_wav_fallback",
                )
            )

            return _selection(
                status="selected_fallback",
                selected_path=original_path,
                selected_type="original_wav",
                checked_sources=checked_sources,
                require_existing_file=require_existing_file,
                original_source_path=original_path,
                preprocessing_manifest_path=manifest_path,
                recommendation="review_warning",
                warnings=["original_wav_used_for_beat_detection"],
                metadata=safe_metadata,
            )

        if original_exists and not original_is_wav:
            checked_sources.append(
                _checked_source(
                    source_type="unsupported_original_source",
                    source_path=original_path,
                    exists=True,
                    is_wav=False,
                    usable=False,
                    reason="original_source_requires_audio_extraction",
                )
            )

            return _selection(
                status="skipped_unsupported_source",
                selected_path=original_path,
                selected_type="unsupported_original_source",
                checked_sources=checked_sources,
                require_existing_file=require_existing_file,
                original_source_path=original_path,
                preprocessing_manifest_path=manifest_path,
                recommendation="extract_audio_first",
                requires_extraction=True,
                metadata=safe_metadata,
            )

        checked_sources.append(
            _checked_source(
                source_type="original_wav",
                source_path=original_path,
                exists=original_exists,
                is_wav=original_is_wav,
                usable=False,
                reason="original_source_missing_or_unusable",
            )
        )
    else:
        checked_sources.append(
            _checked_source(
                source_type="original_wav",
                source_path=None,
                exists=False,
                is_wav=False,
                usable=False,
                reason="original_source_not_declared",
            )
        )

    return _selection(
        status="unavailable",
        selected_path=None,
        selected_type="none",
        checked_sources=checked_sources,
        require_existing_file=require_existing_file,
        original_source_path=original_path,
        preprocessing_manifest_path=manifest_path,
        recommendation="no_audio_source_available",
        errors=["no_beat_detection_source_available"],
        metadata=safe_metadata,
    )


def _load_manifest_from_path(path: Any) -> tuple[Any | None, str | None]:
    manifest_path = _safe_text(path)

    if not manifest_path:
        return None, None

    try:
        path_obj = Path(manifest_path)
    except Exception:
        return None, manifest_path

    if not path_obj.exists():
        return None, str(path_obj)

    try:
        with path_obj.open("r", encoding="utf-8") as file:
            return json.load(file), str(path_obj)
    except Exception:
        return None, str(path_obj)


def select_beat_detection_source_for_job(
    job: Any,
    require_existing_file: bool = True,
    allow_original_wav_fallback: bool = True,
    metadata: dict[str, Any] | None = None,
) -> BeatDetectionSourceSelection:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    job_metadata = _get_value(job, "metadata")
    if not isinstance(job_metadata, dict):
        job_metadata = {}

    preprocessing_manifest = _get_value(job, "preprocessing_manifest")
    preprocessing_manifest_path = _safe_text(_get_value(job, "preprocessing_manifest_path"))

    if preprocessing_manifest is None and preprocessing_manifest_path:
        loaded_manifest, loaded_path = _load_manifest_from_path(preprocessing_manifest_path)
        preprocessing_manifest = loaded_manifest
        if loaded_path:
            safe_metadata["preprocessing_manifest_path"] = loaded_path

    if preprocessing_manifest is None:
        preprocessing_manifest = _get_value(job, "manifest")

    if preprocessing_manifest is None:
        preprocessing_manifest = job_metadata.get("preprocessing_manifest")

    if preprocessing_manifest_path and "preprocessing_manifest_path" not in safe_metadata:
        safe_metadata["preprocessing_manifest_path"] = preprocessing_manifest_path

    original_source_path = _first_text_from_keys(job, ORIGINAL_SOURCE_FIELDS)

    if not original_source_path:
        original_source_path = _first_text_from_keys(
            job_metadata,
            ["raw_video_path", "source_path"],
        )

    return select_beat_detection_source(
        preprocessing_manifest=preprocessing_manifest,
        original_source_path=original_source_path,
        require_existing_file=require_existing_file,
        allow_original_wav_fallback=allow_original_wav_fallback,
        metadata=safe_metadata,
    )
