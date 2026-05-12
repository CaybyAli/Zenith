from __future__ import annotations

from pathlib import Path
from typing import Any

from models.scene_change_source import SceneChangeSourceSelection


_VIDEO_SUFFIXES = {
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v",
    ".mpg", ".mpeg", ".ts", ".wmv", ".flv",
}

_FALLBACK_FIELDS = [
    "input_file",
    "source_file",
    "video_path",
    "file_path",
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


def path_exists(path: Any) -> bool:
    text = _safe_text(path)
    if not text:
        return False
    try:
        return Path(text).exists()
    except Exception:
        return False


def is_video_path(path: Any) -> bool:
    text = _safe_text(path)
    if not text:
        return False
    try:
        return Path(text).suffix.lower() in _VIDEO_SUFFIXES
    except Exception:
        return False


def _checked_source(
    source_type: str,
    source_path: str | None,
    exists: bool,
    usable: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "type": source_type,
        "path": source_path,
        "exists": exists,
        "usable": usable,
        "reason": reason,
    }


def _selection(
    status: str,
    selected_path: str | None,
    selected_type: str | None,
    checked_sources: list[dict[str, Any]],
    recommendation: str,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> SceneChangeSourceSelection:
    return SceneChangeSourceSelection(
        status=status,
        selected_path=selected_path,
        selected_type=selected_type,
        checked_sources=checked_sources,
        source_exists=path_exists(selected_path),
        recommendation=recommendation,
        warnings=list(warnings or []),
        errors=list(errors or []),
        metadata=dict(metadata or {}),
    )


def select_scene_change_source(
    raw_video_path: str | None = None,
    preprocessing_manifest: Any | None = None,
    fallback_paths: dict[str, str | None] | None = None,
    require_existing_file: bool = True,
    metadata: dict[str, Any] | None = None,
) -> SceneChangeSourceSelection:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    checked_sources: list[dict[str, Any]] = []

    # Priority 1: raw_video_path
    candidate = _safe_text(raw_video_path)
    if candidate:
        exists = path_exists(candidate)
        usable = exists or not require_existing_file

        if usable:
            checked_sources.append(
                _checked_source(
                    source_type="raw_video_path",
                    source_path=candidate,
                    exists=exists,
                    usable=True,
                    reason="selected_raw_video_path",
                )
            )
            return _selection(
                status="selected",
                selected_path=candidate,
                selected_type="raw_video_path",
                checked_sources=checked_sources,
                recommendation="analyze_video",
                metadata=safe_metadata,
            )

        checked_sources.append(
            _checked_source(
                source_type="raw_video_path",
                source_path=candidate,
                exists=False,
                usable=False,
                reason="raw_video_path_missing",
            )
        )
        return _selection(
            status="blocked_missing_video_source",
            selected_path=candidate,
            selected_type="raw_video_path",
            checked_sources=checked_sources,
            recommendation="fix_raw_video_path",
            errors=["raw_video_path_file_missing"],
            metadata=safe_metadata,
        )

    checked_sources.append(
        _checked_source(
            source_type="raw_video_path",
            source_path=None,
            exists=False,
            usable=False,
            reason="raw_video_path_not_declared",
        )
    )

    # Priority 2: preprocessing_manifest["source_path"]
    manifest_source: str | None = None
    if preprocessing_manifest is not None:
        manifest_source = _safe_text(_get_value(preprocessing_manifest, "source_path"))

    if manifest_source:
        exists = path_exists(manifest_source)
        usable = exists or not require_existing_file

        if usable:
            checked_sources.append(
                _checked_source(
                    source_type="preprocessing_source_path",
                    source_path=manifest_source,
                    exists=exists,
                    usable=True,
                    reason="selected_preprocessing_manifest_source",
                )
            )
            return _selection(
                status="selected_fallback",
                selected_path=manifest_source,
                selected_type="preprocessing_source_path",
                checked_sources=checked_sources,
                recommendation="analyze_video",
                warnings=["used_preprocessing_manifest_source_path"],
                metadata=safe_metadata,
            )

        checked_sources.append(
            _checked_source(
                source_type="preprocessing_source_path",
                source_path=manifest_source,
                exists=False,
                usable=False,
                reason="preprocessing_source_path_missing",
            )
        )
        return _selection(
            status="blocked_missing_video_source",
            selected_path=manifest_source,
            selected_type="preprocessing_source_path",
            checked_sources=checked_sources,
            recommendation="fix_preprocessing_source_path",
            errors=["preprocessing_source_path_file_missing"],
            metadata=safe_metadata,
        )

    checked_sources.append(
        _checked_source(
            source_type="preprocessing_source_path",
            source_path=None,
            exists=False,
            usable=False,
            reason="preprocessing_source_path_not_declared",
        )
    )

    # Priority 3: fallback fields
    if fallback_paths:
        for field_name, field_value in fallback_paths.items():
            candidate = _safe_text(field_value)
            if not candidate:
                checked_sources.append(
                    _checked_source(
                        source_type=f"fallback_{field_name}",
                        source_path=None,
                        exists=False,
                        usable=False,
                        reason="fallback_field_not_declared",
                    )
                )
                continue

            exists = path_exists(candidate)
            usable = exists or not require_existing_file

            if usable:
                checked_sources.append(
                    _checked_source(
                        source_type="fallback_video_path",
                        source_path=candidate,
                        exists=exists,
                        usable=True,
                        reason=f"selected_fallback_{field_name}",
                    )
                )
                return _selection(
                    status="selected_fallback",
                    selected_path=candidate,
                    selected_type="fallback_video_path",
                    checked_sources=checked_sources,
                    recommendation="analyze_video",
                    warnings=[f"used_fallback_{field_name}"],
                    metadata=safe_metadata,
                )

            checked_sources.append(
                _checked_source(
                    source_type=f"fallback_{field_name}",
                    source_path=candidate,
                    exists=False,
                    usable=False,
                    reason="fallback_path_missing",
                )
            )

    return _selection(
        status="skipped_no_video_source",
        selected_path=None,
        selected_type="none",
        checked_sources=checked_sources,
        recommendation="no_video_source_available",
        errors=["no_scene_change_video_source_available"],
        metadata=safe_metadata,
    )


def select_scene_change_source_for_job(
    job: Any,
    require_existing_file: bool = True,
    metadata: dict[str, Any] | None = None,
) -> SceneChangeSourceSelection:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    raw_video_path = _safe_text(_get_value(job, "raw_video_path"))

    preprocessing_manifest = _get_value(job, "preprocessing_manifest")
    if not isinstance(preprocessing_manifest, dict):
        preprocessing_manifest = None

    fallback_paths: dict[str, str | None] = {}
    for field_name in _FALLBACK_FIELDS:
        value = _safe_text(_get_value(job, field_name))
        if value:
            fallback_paths[field_name] = value

    return select_scene_change_source(
        raw_video_path=raw_video_path,
        preprocessing_manifest=preprocessing_manifest,
        fallback_paths=fallback_paths if fallback_paths else None,
        require_existing_file=require_existing_file,
        metadata=safe_metadata,
    )
