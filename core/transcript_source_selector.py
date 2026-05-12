from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SOURCE_TYPE_SPEECH = "speech_audio"
SOURCE_TYPE_ANALYSIS = "analysis_audio"
SOURCE_TYPE_RAW_VIDEO = "raw_video"

_AUDIO_EXTENSIONS = {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus"}
_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}


@dataclass
class TranscriptSourceSelection:
    status: str
    selected_path: str | None = None
    selected_type: str | None = None
    checked_sources: list[dict[str, Any]] = field(default_factory=list)
    recommendation: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "selected_path": self.selected_path,
            "selected_type": self.selected_type,
            "checked_sources": list(self.checked_sources),
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }


def _safe_text(value: Any) -> str | None:
    if value is None:
        return None

    try:
        text = str(value).strip()
    except Exception:
        return None

    return text or None


def _path_exists(path: str | None) -> bool:
    if not path:
        return False

    try:
        return Path(path).is_file()
    except OSError:
        return False


def _path_size(path: str | None) -> int | None:
    if not path:
        return None

    try:
        return Path(path).stat().st_size
    except OSError:
        return None


def _extension(path: str | None) -> str:
    if not path:
        return ""

    try:
        return Path(path).suffix.lower()
    except Exception:
        return ""


def _is_audio_path(path: str | None) -> bool:
    return _extension(path) in _AUDIO_EXTENSIONS


def _is_video_path(path: str | None) -> bool:
    return _extension(path) in _VIDEO_EXTENSIONS


def _checked_entry(
    source_type: str,
    path: str | None,
    exists: bool,
    usable: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "type": source_type,
        "path": path,
        "exists": exists,
        "usable": usable,
        "reason": reason,
    }


def _get(source: Any, key: str) -> Any:
    if source is None:
        return None

    if isinstance(source, dict):
        return source.get(key)

    return getattr(source, key, None)


def _first_text(source: Any, keys: list[str]) -> str | None:
    for key in keys:
        text = _safe_text(_get(source, key))
        if text:
            return text

    return None


def _extract_preprocessing_paths(manifest: Any) -> tuple[str | None, str | None]:
    if manifest is None:
        return None, None

    speech_path = _safe_text(_get(manifest, "speech_audio_path"))
    analysis_path = _safe_text(_get(manifest, "analysis_audio_path"))
    return speech_path, analysis_path


def select_transcript_source(
    preprocessing_manifest: Any | None = None,
    raw_video_path: str | None = None,
    allow_raw_video_fallback: bool = True,
    require_existing_file: bool = True,
    metadata: dict[str, Any] | None = None,
) -> TranscriptSourceSelection:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    checked: list[dict[str, Any]] = []

    speech_path, analysis_path = _extract_preprocessing_paths(preprocessing_manifest)
    raw_path = _safe_text(raw_video_path)

    declared_any_preprocessed = bool(speech_path or analysis_path)

    if speech_path:
        speech_exists = _path_exists(speech_path)
        speech_usable = speech_exists or not require_existing_file

        if speech_usable:
            checked.append(
                _checked_entry(
                    source_type=SOURCE_TYPE_SPEECH,
                    path=speech_path,
                    exists=speech_exists,
                    usable=True,
                    reason="selected_speech_audio",
                )
            )
            return TranscriptSourceSelection(
                status="selected",
                selected_path=speech_path,
                selected_type=SOURCE_TYPE_SPEECH,
                checked_sources=checked,
                recommendation="transcribe_speech_audio",
                metadata=safe_metadata,
            )

        checked.append(
            _checked_entry(
                source_type=SOURCE_TYPE_SPEECH,
                path=speech_path,
                exists=False,
                usable=False,
                reason="preprocessed_speech_audio_missing",
            )
        )
    else:
        checked.append(
            _checked_entry(
                source_type=SOURCE_TYPE_SPEECH,
                path=None,
                exists=False,
                usable=False,
                reason="speech_audio_not_declared",
            )
        )

    if analysis_path:
        analysis_exists = _path_exists(analysis_path)
        analysis_usable = analysis_exists or not require_existing_file

        if analysis_usable:
            checked.append(
                _checked_entry(
                    source_type=SOURCE_TYPE_ANALYSIS,
                    path=analysis_path,
                    exists=analysis_exists,
                    usable=True,
                    reason="selected_analysis_audio_fallback",
                )
            )
            return TranscriptSourceSelection(
                status="selected_fallback",
                selected_path=analysis_path,
                selected_type=SOURCE_TYPE_ANALYSIS,
                checked_sources=checked,
                recommendation="transcribe_analysis_audio",
                warnings=["analysis_audio_used_for_transcript"],
                metadata=safe_metadata,
            )

        checked.append(
            _checked_entry(
                source_type=SOURCE_TYPE_ANALYSIS,
                path=analysis_path,
                exists=False,
                usable=False,
                reason="preprocessed_analysis_audio_missing",
            )
        )
    else:
        checked.append(
            _checked_entry(
                source_type=SOURCE_TYPE_ANALYSIS,
                path=None,
                exists=False,
                usable=False,
                reason="analysis_audio_not_declared",
            )
        )

    if declared_any_preprocessed:
        return TranscriptSourceSelection(
            status="blocked_missing_preprocessed_audio",
            selected_path=None,
            selected_type=None,
            checked_sources=checked,
            recommendation="generate_preprocessed_audio",
            errors=["preprocessed_audio_missing"],
            metadata=safe_metadata,
        )

    if not allow_raw_video_fallback or not raw_path:
        if raw_path:
            checked.append(
                _checked_entry(
                    source_type=SOURCE_TYPE_RAW_VIDEO,
                    path=raw_path,
                    exists=_path_exists(raw_path),
                    usable=False,
                    reason="raw_video_fallback_disabled",
                )
            )

        return TranscriptSourceSelection(
            status="skipped_no_audio_source",
            selected_path=None,
            selected_type=None,
            checked_sources=checked,
            recommendation="no_audio_source_available",
            warnings=["no_audio_source_available"],
            metadata=safe_metadata,
        )

    raw_exists = _path_exists(raw_path)
    raw_is_media = _is_audio_path(raw_path) or _is_video_path(raw_path)
    raw_usable = (raw_exists or not require_existing_file) and raw_is_media

    if raw_usable:
        checked.append(
            _checked_entry(
                source_type=SOURCE_TYPE_RAW_VIDEO,
                path=raw_path,
                exists=raw_exists,
                usable=True,
                reason="selected_raw_video_fallback",
            )
        )
        return TranscriptSourceSelection(
            status="selected_fallback",
            selected_path=raw_path,
            selected_type=SOURCE_TYPE_RAW_VIDEO,
            checked_sources=checked,
            recommendation="transcribe_raw_video",
            warnings=["raw_video_used_for_transcript"],
            metadata=safe_metadata,
        )

    checked.append(
        _checked_entry(
            source_type=SOURCE_TYPE_RAW_VIDEO,
            path=raw_path,
            exists=raw_exists,
            usable=False,
            reason="raw_video_missing_or_unsupported",
        )
    )

    return TranscriptSourceSelection(
        status="skipped_no_audio_source",
        selected_path=None,
        selected_type=None,
        checked_sources=checked,
        recommendation="no_audio_source_available",
        warnings=["no_audio_source_available"],
        metadata=safe_metadata,
    )


def select_transcript_source_for_job(
    job: Any,
    allow_raw_video_fallback: bool = True,
    require_existing_file: bool = True,
    metadata: dict[str, Any] | None = None,
) -> TranscriptSourceSelection:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    preprocessing_manifest = _get(job, "preprocessing_manifest")

    if not isinstance(preprocessing_manifest, dict):
        preprocessing_manifest = None

    raw_path = _first_text(
        job,
        [
            "raw_video_path",
            "source_path",
            "input_path",
            "video_path",
        ],
    )

    audio_size = _path_size(
        _safe_text(_get(preprocessing_manifest, "speech_audio_path"))
        if preprocessing_manifest
        else None
    )
    if audio_size is not None:
        safe_metadata["speech_audio_size_bytes"] = audio_size

    return select_transcript_source(
        preprocessing_manifest=preprocessing_manifest,
        raw_video_path=raw_path,
        allow_raw_video_fallback=allow_raw_video_fallback,
        require_existing_file=require_existing_file,
        metadata=safe_metadata,
    )
