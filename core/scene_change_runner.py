from __future__ import annotations

from typing import Any

from core.scene_change_detector import analyze_scene_changes
from core.scene_change_source_selector import (
    select_scene_change_source,
    select_scene_change_source_for_job,
)
from models.scene_change_run import SceneChangeRunReport


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


def _merge_unique(left: list[str], right: list[str]) -> list[str]:
    merged: list[str] = []
    for value in [*left, *right]:
        text = _safe_text(value)
        if text and text not in merged:
            merged.append(text)
    return merged


def _report_from_blocked_selection(
    status: str,
    recommendation: str,
    selection_dict: dict[str, Any],
    metadata: dict[str, Any],
    extra_errors: list[str] | None = None,
) -> SceneChangeRunReport:
    selection_warnings = selection_dict.get("warnings")
    if not isinstance(selection_warnings, list):
        selection_warnings = []

    selection_errors = selection_dict.get("errors")
    if not isinstance(selection_errors, list):
        selection_errors = []

    return SceneChangeRunReport(
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


def build_scene_change_run_report(
    raw_video_path: str | None = None,
    preprocessing_manifest: Any | None = None,
    fallback_paths: dict[str, str | None] | None = None,
    source_selection: Any | None = None,
    scene_threshold: float = 0.30,
    soft_threshold: float = 0.18,
    flash_threshold: float = 0.85,
    min_distance_seconds: float = 0.25,
    flash_neighbor_window_seconds: float = 0.40,
    timeout_seconds: float = 120.0,
    require_existing_file: bool = True,
    metadata: dict[str, Any] | None = None,
) -> SceneChangeRunReport:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    try:
        if source_selection is None:
            selection = select_scene_change_source(
                raw_video_path=raw_video_path,
                preprocessing_manifest=preprocessing_manifest,
                fallback_paths=fallback_paths,
                require_existing_file=require_existing_file,
                metadata=safe_metadata,
            )
            selection_dict = selection.to_dict()
        else:
            selection_dict = _safe_dict(source_selection)

        selection_status = _safe_text(selection_dict.get("status")) or "failed"
        selected_path = _safe_text(selection_dict.get("selected_path"))
        selected_type = _safe_text(selection_dict.get("selected_type"))

        if selection_status == "skipped_no_video_source":
            return _report_from_blocked_selection(
                status="skipped_no_video_source",
                recommendation="no_video_source_available",
                selection_dict=selection_dict,
                metadata=safe_metadata,
            )

        if selection_status == "blocked_missing_video_source":
            return _report_from_blocked_selection(
                status="blocked_missing_video_source",
                recommendation="fix_video_source",
                selection_dict=selection_dict,
                metadata=safe_metadata,
            )

        if selection_status not in {"selected", "selected_fallback"}:
            return _report_from_blocked_selection(
                status="failed",
                recommendation="retry_or_fix_video_source",
                selection_dict=selection_dict,
                metadata=safe_metadata,
                extra_errors=["invalid_scene_change_source_selection"],
            )

        if not selected_path:
            return _report_from_blocked_selection(
                status="failed",
                recommendation="retry_or_fix_video_source",
                selection_dict=selection_dict,
                metadata=safe_metadata,
                extra_errors=["selected_video_path_missing"],
            )

        detection_result = analyze_scene_changes(
            selected_path,
            scene_threshold=scene_threshold,
            soft_threshold=soft_threshold,
            flash_threshold=flash_threshold,
            min_distance_seconds=min_distance_seconds,
            flash_neighbor_window_seconds=flash_neighbor_window_seconds,
            timeout_seconds=timeout_seconds,
            metadata=safe_metadata,
        )

        detection_dict = detection_result.to_dict()
        scene_changes_raw = detection_dict.get("scene_changes")
        if not isinstance(scene_changes_raw, list):
            scene_changes_raw = []
        safe_scene_changes = [
            dict(sc) for sc in scene_changes_raw if isinstance(sc, dict)
        ]

        detector_status = _safe_text(detection_dict.get("status")) or "failed"
        scene_change_count = int(
            detection_dict.get("scene_change_count") or len(safe_scene_changes)
        )
        hard_change_count = int(detection_dict.get("hard_change_count") or 0)
        soft_transition_count = int(detection_dict.get("soft_transition_count") or 0)
        false_positive_candidate_count = int(
            detection_dict.get("false_positive_candidate_count") or 0
        )
        threshold = float(detection_dict.get("threshold") or scene_threshold)
        duration_seconds_raw = detection_dict.get("duration_seconds")
        duration_seconds = (
            float(duration_seconds_raw) if duration_seconds_raw is not None else None
        )
        recommendation = (
            _safe_text(detection_dict.get("recommendation")) or "review"
        )

        if detector_status == "failed":
            report_status = "failed"
            recommendation = "scene_detection_failed"
        elif detector_status in {"ok", "completed_with_warnings"}:
            report_status = detector_status
        else:
            report_status = "completed_with_warnings"

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

        return SceneChangeRunReport(
            status=report_status,
            source_selection=selection_dict,
            selected_path=selected_path,
            selected_type=selected_type,
            scene_change_result=detection_dict,
            scene_changes=safe_scene_changes,
            scene_change_count=scene_change_count,
            hard_change_count=hard_change_count,
            soft_transition_count=soft_transition_count,
            false_positive_candidate_count=false_positive_candidate_count,
            threshold=threshold,
            duration_seconds=duration_seconds,
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
        return SceneChangeRunReport(
            status="failed",
            recommendation="scene_detection_failed",
            warnings=[],
            errors=["scene_change_runner_failed"],
            metadata={
                **safe_metadata,
                "error_detail": str(exc),
            },
        )


def run_scene_change_for_job(
    job: Any,
    source_selection: Any | None = None,
    scene_threshold: float = 0.30,
    soft_threshold: float = 0.18,
    flash_threshold: float = 0.85,
    min_distance_seconds: float = 0.25,
    flash_neighbor_window_seconds: float = 0.40,
    timeout_seconds: float = 120.0,
    require_existing_file: bool = True,
    metadata: dict[str, Any] | None = None,
) -> SceneChangeRunReport:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    try:
        if source_selection is None:
            selected_source = select_scene_change_source_for_job(
                job=job,
                require_existing_file=require_existing_file,
                metadata=safe_metadata,
            )
        else:
            selected_source = source_selection

        return build_scene_change_run_report(
            source_selection=selected_source,
            scene_threshold=scene_threshold,
            soft_threshold=soft_threshold,
            flash_threshold=flash_threshold,
            min_distance_seconds=min_distance_seconds,
            flash_neighbor_window_seconds=flash_neighbor_window_seconds,
            timeout_seconds=timeout_seconds,
            require_existing_file=require_existing_file,
            metadata=safe_metadata,
        )

    except Exception as exc:
        return SceneChangeRunReport(
            status="failed",
            recommendation="scene_detection_failed",
            warnings=[],
            errors=["scene_change_runner_failed"],
            metadata={
                **safe_metadata,
                "error_detail": str(exc),
            },
        )


def apply_scene_change_run_report_to_job(
    job: Any,
    report: SceneChangeRunReport,
) -> None:
    report_dict: dict[str, Any] = {}
    to_dict = getattr(report, "to_dict", None)
    if callable(to_dict):
        try:
            maybe_dict = to_dict()
            if isinstance(maybe_dict, dict):
                report_dict = dict(maybe_dict)
        except Exception:
            report_dict = {}

    job.scene_change_report = report_dict
    job.scene_change_status = getattr(report, "status", None)
    job.scene_change_selected_path = getattr(report, "selected_path", None)
    job.scene_change_selected_type = getattr(report, "selected_type", None)
    job.scene_change_result = dict(
        getattr(report, "scene_change_result", {}) or {}
    )
    job.scene_changes = list(getattr(report, "scene_changes", []) or [])
    job.scene_change_count = int(getattr(report, "scene_change_count", 0) or 0)
    job.scene_change_hard_count = int(getattr(report, "hard_change_count", 0) or 0)
    job.scene_change_soft_count = int(
        getattr(report, "soft_transition_count", 0) or 0
    )
    job.scene_change_false_positive_candidate_count = int(
        getattr(report, "false_positive_candidate_count", 0) or 0
    )
    job.scene_change_threshold = float(getattr(report, "threshold", 0.30) or 0.30)
    duration_seconds = getattr(report, "duration_seconds", None)
    job.scene_change_duration_seconds = (
        float(duration_seconds) if duration_seconds is not None else None
    )
    job.scene_change_recommendation = getattr(report, "recommendation", None)
