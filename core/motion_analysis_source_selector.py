from __future__ import annotations

from pathlib import Path
from typing import Any

from models.motion_analysis_source import (
    MOTION_SELECTED_TYPE_FALLBACK_VIDEO_PATH,
    MOTION_SELECTED_TYPE_NONE,
    MOTION_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH,
    MOTION_SELECTED_TYPE_RAW_VIDEO_PATH,
    MOTION_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    MOTION_SOURCE_STATUS_FAILED,
    MOTION_SOURCE_STATUS_SELECTED,
    MOTION_SOURCE_STATUS_SELECTED_FALLBACK,
    MOTION_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    MotionAnalysisSourceSelection,
)


FALLBACK_VIDEO_FIELDS = (
    "input_file",
    "source_file",
    "video_path",
    "file_path",
)


def _get_value(source: Any, key: str, default: Any = None) -> Any:
    if source is None:
        return default

    if isinstance(source, dict):
        return source.get(key, default)

    return getattr(source, key, default)


def _as_clean_path(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def _path_exists(path: str | None) -> bool:
    if not path:
        return False

    try:
        return Path(path).is_file()
    except OSError:
        return False


def _checked_source(
    source_type: str,
    path: str | None,
    exists: bool,
    status: str,
) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "path": path,
        "exists": exists,
        "status": status,
    }


def _get_preprocessing_source_path(job: Any) -> str | None:
    preprocessing_manifest = _get_value(job, "preprocessing_manifest")

    if not isinstance(preprocessing_manifest, dict):
        return None

    return _as_clean_path(preprocessing_manifest.get("source_path"))


def select_motion_analysis_source(job: Any) -> MotionAnalysisSourceSelection:
    checked_sources: list[dict[str, Any]] = []

    try:
        raw_video_path = _as_clean_path(_get_value(job, "raw_video_path"))
        raw_exists = _path_exists(raw_video_path)

        if raw_video_path:
            checked_sources.append(
                _checked_source(
                    source_type=MOTION_SELECTED_TYPE_RAW_VIDEO_PATH,
                    path=raw_video_path,
                    exists=raw_exists,
                    status="exists" if raw_exists else "missing",
                )
            )

            if raw_exists:
                return MotionAnalysisSourceSelection(
                    status=MOTION_SOURCE_STATUS_SELECTED,
                    selected_path=raw_video_path,
                    selected_type=MOTION_SELECTED_TYPE_RAW_VIDEO_PATH,
                    checked_sources=checked_sources,
                    source_exists=True,
                    recommendation="run_motion_analysis",
                    warnings=[],
                    errors=[],
                    metadata={},
                )

            return MotionAnalysisSourceSelection(
                status=MOTION_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
                selected_path=raw_video_path,
                selected_type=MOTION_SELECTED_TYPE_RAW_VIDEO_PATH,
                checked_sources=checked_sources,
                source_exists=False,
                recommendation="fix_missing_raw_video_path",
                warnings=["raw_video_path_is_set_but_file_is_missing"],
                errors=[],
                metadata={},
            )

        preprocessing_source_path = _get_preprocessing_source_path(job)
        preprocessing_exists = _path_exists(preprocessing_source_path)

        if preprocessing_source_path:
            checked_sources.append(
                _checked_source(
                    source_type=MOTION_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH,
                    path=preprocessing_source_path,
                    exists=preprocessing_exists,
                    status="exists" if preprocessing_exists else "missing",
                )
            )

            if preprocessing_exists:
                return MotionAnalysisSourceSelection(
                    status=MOTION_SOURCE_STATUS_SELECTED_FALLBACK,
                    selected_path=preprocessing_source_path,
                    selected_type=MOTION_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH,
                    checked_sources=checked_sources,
                    source_exists=True,
                    recommendation="run_motion_analysis",
                    warnings=["used_preprocessing_manifest_source_path_fallback"],
                    errors=[],
                    metadata={},
                )

        for field_name in FALLBACK_VIDEO_FIELDS:
            fallback_path = _as_clean_path(_get_value(job, field_name))
            fallback_exists = _path_exists(fallback_path)

            if not fallback_path:
                continue

            checked_sources.append(
                _checked_source(
                    source_type=f"{MOTION_SELECTED_TYPE_FALLBACK_VIDEO_PATH}:{field_name}",
                    path=fallback_path,
                    exists=fallback_exists,
                    status="exists" if fallback_exists else "missing",
                )
            )

            if fallback_exists:
                return MotionAnalysisSourceSelection(
                    status=MOTION_SOURCE_STATUS_SELECTED_FALLBACK,
                    selected_path=fallback_path,
                    selected_type=MOTION_SELECTED_TYPE_FALLBACK_VIDEO_PATH,
                    checked_sources=checked_sources,
                    source_exists=True,
                    recommendation="run_motion_analysis",
                    warnings=[f"used_fallback_video_field:{field_name}"],
                    errors=[],
                    metadata={
                        "fallback_field": field_name,
                    },
                )

        return MotionAnalysisSourceSelection(
            status=MOTION_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE,
            selected_path=None,
            selected_type=MOTION_SELECTED_TYPE_NONE,
            checked_sources=checked_sources,
            source_exists=False,
            recommendation="provide_video_source",
            warnings=["no_motion_analysis_video_source_found"],
            errors=[],
            metadata={},
        )

    except Exception as exc:
        return MotionAnalysisSourceSelection(
            status=MOTION_SOURCE_STATUS_FAILED,
            selected_path=None,
            selected_type=MOTION_SELECTED_TYPE_NONE,
            checked_sources=checked_sources,
            source_exists=False,
            recommendation="review_source_selector_error",
            warnings=[],
            errors=[f"motion_analysis_source_selection_failed: {exc}"],
            metadata={},
        )
