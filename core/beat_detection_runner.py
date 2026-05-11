from __future__ import annotations

from pathlib import Path
from typing import Any

from core.beat_detection_source_selector import (
    select_beat_detection_source,
    select_beat_detection_source_for_job,
)
from core.beat_detector import analyze_wav_beats
from models.beat_detection_run import BeatDetectionRunReport


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            converted = to_dict()
            if isinstance(converted, dict):
                return dict(converted)
        except Exception:
            return {}

    return {}


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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_wav_existing(path: Any) -> bool:
    text = _safe_text(path)

    if not text:
        return False

    try:
        path_obj = Path(text)
        return path_obj.suffix.lower() == ".wav" and path_obj.exists()
    except Exception:
        return False


def _merge_unique(left: list[str], right: list[str]) -> list[str]:
    merged: list[str] = []

    for value in [*left, *right]:
        text = _safe_text(value)
        if text and text not in merged:
            merged.append(text)

    return merged


def _strength_stats(beats: list[dict[str, Any]]) -> tuple[float, float, dict[str, Any]]:
    if not beats:
        return 0.0, 0.0, {}

    strengths = [_safe_float(beat.get("strength"), 0.0) for beat in beats]
    max_strength = max(strengths) if strengths else 0.0
    avg_strength = sum(strengths) / len(strengths) if strengths else 0.0

    top_beat = max(
        beats,
        key=lambda beat: (
            _safe_float(beat.get("strength"), 0.0),
            _safe_float(beat.get("confidence"), 0.0),
            _safe_float(beat.get("energy"), 0.0),
        ),
    )

    return max_strength, avg_strength, dict(top_beat)


def _report_from_blocked_selection(
    status: str,
    recommendation: str,
    selection_dict: dict[str, Any],
    metadata: dict[str, Any],
    extra_errors: list[str] | None = None,
) -> BeatDetectionRunReport:
    selection_warnings = selection_dict.get("warnings")
    if not isinstance(selection_warnings, list):
        selection_warnings = []

    selection_errors = selection_dict.get("errors")
    if not isinstance(selection_errors, list):
        selection_errors = []

    return BeatDetectionRunReport(
        status=status,
        source_selection=selection_dict,
        selected_path=_safe_text(selection_dict.get("selected_path")),
        selected_type=_safe_text(selection_dict.get("selected_type")),
        recommendation=recommendation,
        warnings=[str(item) for item in selection_warnings],
        errors=_merge_unique(
            [str(item) for item in selection_errors],
            list(extra_errors or []),
        ),
        metadata=metadata,
    )


def build_beat_detection_run_report(
    preprocessing_manifest: Any | None = None,
    original_source_path: str | None = None,
    source_selection: Any | None = None,
    frame_ms: float = 50.0,
    hop_ms: float = 25.0,
    peak_threshold: float = 1.35,
    min_beat_distance_seconds: float = 0.25,
    require_existing_file: bool = True,
    allow_original_wav_fallback: bool = True,
    metadata: dict[str, Any] | None = None,
) -> BeatDetectionRunReport:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    try:
        if source_selection is None:
            selection = select_beat_detection_source(
                preprocessing_manifest=preprocessing_manifest,
                original_source_path=original_source_path,
                require_existing_file=require_existing_file,
                allow_original_wav_fallback=allow_original_wav_fallback,
                metadata=safe_metadata,
            )
            selection_dict = selection.to_dict()
        else:
            selection_dict = _safe_dict(source_selection)

        selection_status = _safe_text(selection_dict.get("status")) or "failed"
        selected_path = _safe_text(selection_dict.get("selected_path"))
        selected_type = _safe_text(selection_dict.get("selected_type"))

        if selection_status == "missing_preprocessed_audio":
            return _report_from_blocked_selection(
                status="blocked_missing_preprocessed_audio",
                recommendation="generate_preprocessed_audio",
                selection_dict=selection_dict,
                metadata=safe_metadata,
            )

        if selection_status == "skipped_unsupported_source":
            return _report_from_blocked_selection(
                status="skipped_unsupported_source",
                recommendation="extract_audio_first",
                selection_dict=selection_dict,
                metadata=safe_metadata,
            )

        if selection_status == "unavailable":
            return _report_from_blocked_selection(
                status="skipped_no_audio_source",
                recommendation="no_audio_source_available",
                selection_dict=selection_dict,
                metadata=safe_metadata,
            )

        if selection_status not in {"selected", "selected_fallback"}:
            return _report_from_blocked_selection(
                status="failed",
                recommendation="retry_or_fix_audio",
                selection_dict=selection_dict,
                metadata=safe_metadata,
                extra_errors=["invalid_beat_detection_source_selection"],
            )

        if not _is_wav_existing(selected_path):
            return _report_from_blocked_selection(
                status="failed",
                recommendation="retry_or_fix_audio",
                selection_dict=selection_dict,
                metadata=safe_metadata,
                extra_errors=["selected_wav_source_missing_or_invalid"],
            )

        detection_result = analyze_wav_beats(
            selected_path,
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            peak_threshold=peak_threshold,
            min_beat_distance_seconds=min_beat_distance_seconds,
            metadata=safe_metadata,
        )

        detection_dict = detection_result.to_dict()
        beats = detection_dict.get("beats")
        if not isinstance(beats, list):
            beats = []

        safe_beats = [dict(beat) for beat in beats if isinstance(beat, dict)]
        max_strength, avg_strength, top_beat = _strength_stats(safe_beats)

        detector_status = _safe_text(detection_dict.get("status")) or "failed"
        beat_count = int(detection_dict.get("beat_count") or len(safe_beats))

        if detector_status == "failed":
            report_status = "failed"
            recommendation = "retry_or_fix_audio"
        elif beat_count > 0:
            report_status = "ok" if detector_status == "ok" else "completed_with_warnings"
            recommendation = "use_beat_timeline"
        else:
            report_status = "completed_with_warnings"
            recommendation = "no_beats_detected"

        selection_warnings = selection_dict.get("warnings")
        if not isinstance(selection_warnings, list):
            selection_warnings = []

        selection_errors = selection_dict.get("errors")
        if not isinstance(selection_errors, list):
            selection_errors = []

        detector_warnings = detection_dict.get("warnings")
        if not isinstance(detector_warnings, list):
            detector_warnings = []

        detector_errors = detection_dict.get("errors")
        if not isinstance(detector_errors, list):
            detector_errors = []

        return BeatDetectionRunReport(
            status=report_status,
            source_selection=selection_dict,
            selected_path=selected_path,
            selected_type=selected_type,
            beat_detection_result=detection_dict,
            beats=safe_beats,
            beat_count=beat_count,
            estimated_bpm=detection_dict.get("estimated_bpm"),
            average_beat_interval_seconds=detection_dict.get(
                "average_beat_interval_seconds"
            ),
            duration_seconds=_safe_float(detection_dict.get("duration_seconds"), 0.0),
            sample_rate=detection_dict.get("sample_rate"),
            channels=detection_dict.get("channels"),
            energy_frame_count=int(detection_dict.get("energy_frame_count") or 0),
            peak_threshold=peak_threshold,
            min_beat_distance_seconds=min_beat_distance_seconds,
            max_beat_strength=max_strength,
            avg_beat_strength=avg_strength,
            top_beat=top_beat,
            recommendation=recommendation,
            warnings=_merge_unique(
                [str(item) for item in selection_warnings],
                [str(item) for item in detector_warnings],
            ),
            errors=_merge_unique(
                [str(item) for item in selection_errors],
                [str(item) for item in detector_errors],
            ),
            metadata=safe_metadata,
        )

    except Exception as exc:
        return BeatDetectionRunReport(
            status="failed",
            recommendation="retry_or_fix_audio",
            warnings=[],
            errors=["beat_detection_runner_failed"],
            metadata={
                **safe_metadata,
                "error_detail": str(exc),
            },
        )


def run_beat_detection_for_job(
    job: Any,
    source_selection: Any | None = None,
    frame_ms: float = 50.0,
    hop_ms: float = 25.0,
    peak_threshold: float = 1.35,
    min_beat_distance_seconds: float = 0.25,
    require_existing_file: bool = True,
    allow_original_wav_fallback: bool = True,
    metadata: dict[str, Any] | None = None,
) -> BeatDetectionRunReport:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    try:
        if source_selection is None:
            selected_source = select_beat_detection_source_for_job(
                job=job,
                require_existing_file=require_existing_file,
                allow_original_wav_fallback=allow_original_wav_fallback,
                metadata=safe_metadata,
            )
        else:
            selected_source = source_selection

        return build_beat_detection_run_report(
            source_selection=selected_source,
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            peak_threshold=peak_threshold,
            min_beat_distance_seconds=min_beat_distance_seconds,
            require_existing_file=require_existing_file,
            allow_original_wav_fallback=allow_original_wav_fallback,
            metadata=safe_metadata,
        )

    except Exception as exc:
        return BeatDetectionRunReport(
            status="failed",
            recommendation="retry_or_fix_audio",
            warnings=[],
            errors=["beat_detection_runner_failed"],
            metadata={
                **safe_metadata,
                "error_detail": str(exc),
            },
        )
