from __future__ import annotations

from typing import Any

from models.visual_energy import (
    CLASSIFICATION_HIGH_VISUAL_ENERGY,
    CLASSIFICATION_LOW_VISUAL_ENERGY,
    CLASSIFICATION_MEDIUM_VISUAL_ENERGY,
    CLASSIFICATION_PEAK_VISUAL_ENERGY,
    CLASSIFICATION_TECHNICAL_WARNING,
    CLASSIFICATION_UNKNOWN,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_OK,
    STATUS_SKIPPED_NO_VISUAL_SOURCES,
    VisualEnergyPoint,
    VisualEnergyResult,
    VisualEnergySegment,
)


SCREEN_CONTENT_SCORE_WEIGHTS = {
    "gameplay": 0.65,
    "victory_screen": 0.90,
    "death_screen": 0.55,
    "scoreboard": 0.45,
    "menu": 0.25,
    "lobby": 0.25,
    "loading": 0.10,
    "black_screen": 0.05,
    "unknown": 0.30,
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _clamp_score(value: Any) -> float:
    return round(max(0.0, min(1.0, _safe_float(value, 0.0))), 3)


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, dict):
        return dict(value)

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        converted = to_dict()
        if isinstance(converted, dict):
            return dict(converted)

    if hasattr(value, "__dict__"):
        return dict(vars(value))

    return {}


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    result: list[dict[str, Any]] = []
    for item in value:
        item_dict = _as_dict(item)
        if item_dict:
            result.append(item_dict)

    return result


def _get_report_items(report: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    data = _as_dict(report)
    for key in keys:
        items = _as_dict_list(data.get(key))
        if items:
            return items

    return []


def _has_visual_source(report: Any, item_keys: tuple[str, ...]) -> bool:
    data = _as_dict(report)
    if not data:
        return False

    for key in item_keys:
        value = data.get(key)
        if isinstance(value, list) and value:
            return True

    for count_key in (
        "point_count",
        "segment_count",
        "window_count",
        "reaction_window_count",
        "scene_change_count",
        "stutter_segment_count",
        "freeze_segment_count",
    ):
        if _safe_float(data.get(count_key), 0.0) > 0:
            return True

    return False


def _get_time_seconds(item: dict[str, Any]) -> float | None:
    for key in ("time_seconds", "start_seconds", "timestamp_seconds"):
        if item.get(key) is not None:
            return _safe_float(item.get(key), 0.0)
    return None


def _get_end_seconds(item: dict[str, Any]) -> float | None:
    if item.get("end_seconds") is not None:
        return _safe_float(item.get("end_seconds"), 0.0)
    return None


def _collect_times_from_items(items: list[dict[str, Any]]) -> list[float]:
    times: list[float] = []

    for item in items:
        start_time = _get_time_seconds(item)
        end_time = _get_end_seconds(item)

        if start_time is not None:
            times.append(round(start_time, 3))

        if end_time is not None:
            times.append(round(end_time, 3))
            if start_time is not None:
                midpoint = start_time + ((end_time - start_time) / 2.0)
                times.append(round(max(0.0, midpoint), 3))

    return times


def _collect_sample_times(
    scene_change_report: Any | None,
    motion_analysis_report: Any | None,
    face_reaction_report: Any | None,
    stutter_detection_report: Any | None,
    screen_content_report: Any | None,
) -> list[float]:
    times: list[float] = []

    times.extend(
        _collect_times_from_items(
            _get_report_items(
                motion_analysis_report,
                ("points", "motion_points", "segments", "motion_segments"),
            )
        )
    )
    times.extend(
        _collect_times_from_items(
            _get_report_items(face_reaction_report, ("reaction_windows", "windows", "points"))
        )
    )
    times.extend(
        _collect_times_from_items(
            _get_report_items(
                screen_content_report,
                ("points", "screen_content_points", "segments", "screen_content_segments"),
            )
        )
    )
    times.extend(
        _collect_times_from_items(
            _get_report_items(
                stutter_detection_report,
                ("points", "stutter_detection_points", "segments", "stutter_detection_segments"),
            )
        )
    )
    times.extend(
        _collect_times_from_items(
            _get_report_items(
                scene_change_report,
                ("points", "scene_changes", "changes", "segments"),
            )
        )
    )

    clean_times = sorted({round(time_value, 3) for time_value in times if time_value >= 0.0})
    return clean_times


def _find_active_segment(
    segments: list[dict[str, Any]],
    time_seconds: float,
) -> dict[str, Any] | None:
    for segment in segments:
        start_seconds = _safe_float(segment.get("start_seconds"), 0.0)
        end_seconds = _safe_float(segment.get("end_seconds"), start_seconds)

        if start_seconds <= time_seconds <= end_seconds:
            return segment

    return None


def _find_nearest_item(
    items: list[dict[str, Any]],
    time_seconds: float,
) -> dict[str, Any] | None:
    best_item: dict[str, Any] | None = None
    best_distance: float | None = None

    for item in items:
        item_time = _get_time_seconds(item)
        if item_time is None:
            continue

        distance = abs(item_time - time_seconds)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_item = item

    return best_item


def _score_from_item(
    item: dict[str, Any] | None,
    score_keys: tuple[str, ...],
    default: float = 0.0,
) -> float:
    if not item:
        return default

    for key in score_keys:
        if item.get(key) is not None:
            return _clamp_score(item.get(key))

    return default


def _motion_score_at_time(report: Any | None, time_seconds: float) -> float:
    points = _get_report_items(report, ("points", "motion_points"))
    segments = _get_report_items(report, ("segments", "motion_segments"))

    active_segment = _find_active_segment(segments, time_seconds)
    if active_segment:
        return _score_from_item(
            active_segment,
            ("avg_motion_score", "max_motion_score", "motion_score", "confidence"),
        )

    nearest_point = _find_nearest_item(points, time_seconds)
    return _score_from_item(
        nearest_point,
        ("motion_score", "avg_motion_score", "max_motion_score", "confidence"),
    )


def _face_reaction_score_at_time(report: Any | None, time_seconds: float) -> float:
    windows = _get_report_items(report, ("reaction_windows", "windows", "points"))

    active_window = _find_active_segment(windows, time_seconds)
    if active_window:
        return _score_from_item(
            active_window,
            (
                "reaction_score",
                "face_reaction_score",
                "expression_change_score",
                "motion_score",
                "confidence",
            ),
        )

    nearest_window = _find_nearest_item(windows, time_seconds)
    return _score_from_item(
        nearest_window,
        (
            "reaction_score",
            "face_reaction_score",
            "expression_change_score",
            "motion_score",
            "confidence",
        ),
    )


def _screen_type_from_item(item: dict[str, Any] | None) -> str:
    if not item:
        return "unknown"

    return _safe_string(
        item.get("screen_type") or item.get("classification") or item.get("label"),
        "unknown",
    )


def _screen_content_score_at_time(report: Any | None, time_seconds: float) -> float:
    points = _get_report_items(report, ("points", "screen_content_points"))
    segments = _get_report_items(report, ("segments", "screen_content_segments"))

    active_segment = _find_active_segment(segments, time_seconds)
    if active_segment:
        screen_type = _screen_type_from_item(active_segment)
        return SCREEN_CONTENT_SCORE_WEIGHTS.get(screen_type, 0.30)

    nearest_point = _find_nearest_item(points, time_seconds)
    screen_type = _screen_type_from_item(nearest_point)
    return SCREEN_CONTENT_SCORE_WEIGHTS.get(screen_type, 0.30)


def _scene_change_score_at_time(report: Any | None, time_seconds: float) -> float:
    items = _get_report_items(report, ("points", "scene_changes", "changes", "segments"))

    nearest_item = _find_nearest_item(items, time_seconds)
    if not nearest_item:
        return 0.0

    nearest_time = _get_time_seconds(nearest_item)
    if nearest_time is not None and abs(nearest_time - time_seconds) > 1.5:
        return 0.0

    return _score_from_item(
        nearest_item,
        (
            "scene_change_score",
            "change_score",
            "cut_score",
            "confidence",
            "score",
        ),
        0.5,
    )


def _stutter_penalty_at_time(report: Any | None, time_seconds: float) -> float:
    points = _get_report_items(report, ("points", "stutter_detection_points"))
    segments = _get_report_items(report, ("segments", "stutter_detection_segments"))

    active_segment = _find_active_segment(segments, time_seconds)
    if active_segment:
        classification = _safe_string(active_segment.get("classification"), "").lower()
        if "stutter" in classification or "freeze" in classification:
            return _score_from_item(
                active_segment,
                ("max_duplicate_score", "avg_duplicate_score", "confidence"),
                1.0,
            )

    nearest_point = _find_nearest_item(points, time_seconds)
    if not nearest_point:
        return 0.0

    classification = _safe_string(nearest_point.get("classification"), "").lower()
    is_duplicate = bool(nearest_point.get("is_duplicate_candidate"))

    if is_duplicate or "duplicate" in classification or "stutter" in classification or "freeze" in classification:
        return _score_from_item(
            nearest_point,
            ("duplicate_score", "confidence", "score"),
            0.75,
        )

    return 0.0


def classify_visual_energy_score(
    visual_energy_score: float,
    stutter_penalty_score: float = 0.0,
) -> str:
    if _clamp_score(stutter_penalty_score) >= 0.75:
        return CLASSIFICATION_TECHNICAL_WARNING

    score = _clamp_score(visual_energy_score)

    if score >= 0.85:
        return CLASSIFICATION_PEAK_VISUAL_ENERGY
    if score >= 0.65:
        return CLASSIFICATION_HIGH_VISUAL_ENERGY
    if score >= 0.30:
        return CLASSIFICATION_MEDIUM_VISUAL_ENERGY
    if score < 0.30:
        return CLASSIFICATION_LOW_VISUAL_ENERGY

    return CLASSIFICATION_UNKNOWN


def _recommendation_for_classification(classification: str) -> str:
    if classification == CLASSIFICATION_PEAK_VISUAL_ENERGY:
        return "review_visual_highlight_candidate"
    if classification == CLASSIFICATION_HIGH_VISUAL_ENERGY:
        return "review_visual_engagement_candidate"
    if classification == CLASSIFICATION_LOW_VISUAL_ENERGY:
        return "review_possible_trim_low_visual_energy"
    if classification == CLASSIFICATION_TECHNICAL_WARNING:
        return "review_visual_technical_warning"
    if classification == CLASSIFICATION_MEDIUM_VISUAL_ENERGY:
        return "review_visual_continuity"

    return "review_unknown_visual_energy"


def build_visual_energy_points(
    scene_change_report: Any | None = None,
    motion_analysis_report: Any | None = None,
    face_reaction_report: Any | None = None,
    stutter_detection_report: Any | None = None,
    screen_content_report: Any | None = None,
    unified_edit_signals: Any | None = None,
) -> list[VisualEnergyPoint]:
    del unified_edit_signals

    sample_times = _collect_sample_times(
        scene_change_report=scene_change_report,
        motion_analysis_report=motion_analysis_report,
        face_reaction_report=face_reaction_report,
        stutter_detection_report=stutter_detection_report,
        screen_content_report=screen_content_report,
    )

    points: list[VisualEnergyPoint] = []

    for time_seconds in sample_times:
        motion_score = _motion_score_at_time(motion_analysis_report, time_seconds)
        face_reaction_score = _face_reaction_score_at_time(face_reaction_report, time_seconds)
        screen_content_score = _screen_content_score_at_time(screen_content_report, time_seconds)
        scene_change_score = _scene_change_score_at_time(scene_change_report, time_seconds)
        stutter_penalty_score = _stutter_penalty_at_time(stutter_detection_report, time_seconds)

        combined_video_score = _clamp_score(
            (motion_score * 0.35)
            + (face_reaction_score * 0.25)
            + (screen_content_score * 0.20)
            + (scene_change_score * 0.10)
        )

        visual_energy_score = _clamp_score(
            combined_video_score - (stutter_penalty_score * 0.10)
        )

        classification = classify_visual_energy_score(
            visual_energy_score=visual_energy_score,
            stutter_penalty_score=stutter_penalty_score,
        )

        source_counts = {
            "scene_change": 1 if _as_dict(scene_change_report) else 0,
            "motion_analysis": 1 if _as_dict(motion_analysis_report) else 0,
            "face_reaction": 1 if _as_dict(face_reaction_report) else 0,
            "stutter_detection": 1 if _as_dict(stutter_detection_report) else 0,
            "screen_content": 1 if _as_dict(screen_content_report) else 0,
        }

        active_source_count = sum(source_counts.values())
        confidence = _clamp_score(active_source_count / 5.0)

        warnings: list[str] = []
        if classification == CLASSIFICATION_TECHNICAL_WARNING:
            warnings.append("stutter_or_freeze_visual_warning")

        points.append(
            VisualEnergyPoint(
                time_seconds=round(time_seconds, 3),
                visual_energy_score=visual_energy_score,
                motion_score=motion_score,
                face_reaction_score=face_reaction_score,
                screen_content_score=screen_content_score,
                scene_change_score=scene_change_score,
                stutter_penalty_score=stutter_penalty_score,
                combined_video_score=combined_video_score,
                classification=classification,
                confidence=confidence,
                source_counts=source_counts,
                metadata={
                    "score_formula": (
                        "motion*0.35 + face*0.25 + screen*0.20 "
                        "+ scene*0.10 - stutter*0.10"
                    ),
                    "no_cut_decision": True,
                    "no_auto_remove": True,
                    "no_auto_highlight": True,
                },
                warnings=warnings,
                errors=[],
            )
        )

    return points


def _guess_point_step(points: list[VisualEnergyPoint]) -> float:
    if len(points) < 2:
        return 1.0

    sorted_times = sorted(point.time_seconds for point in points)
    gaps = [
        round(sorted_times[index + 1] - sorted_times[index], 3)
        for index in range(len(sorted_times) - 1)
        if sorted_times[index + 1] > sorted_times[index]
    ]

    if not gaps:
        return 1.0

    return max(0.001, min(gaps))


def _make_segment_from_points(
    grouped_points: list[VisualEnergyPoint],
    end_seconds: float,
) -> VisualEnergySegment:
    start_seconds = grouped_points[0].time_seconds
    scores = [point.visual_energy_score for point in grouped_points]
    classification = grouped_points[0].classification

    warnings: list[str] = []
    for point in grouped_points:
        warnings.extend(point.warnings)

    return VisualEnergySegment(
        start_seconds=round(start_seconds, 3),
        end_seconds=round(max(end_seconds, start_seconds), 3),
        duration_seconds=round(max(0.0, end_seconds - start_seconds), 3),
        avg_visual_energy_score=round(sum(scores) / len(scores), 3),
        max_visual_energy_score=max(scores),
        min_visual_energy_score=min(scores),
        classification=classification,
        recommendation=_recommendation_for_classification(classification),
        metadata={
            "point_count": len(grouped_points),
            "no_cut_decision": True,
            "no_auto_remove": True,
            "no_auto_highlight": True,
        },
        warnings=warnings,
        errors=[],
    )


def build_visual_energy_segments(
    points: list[VisualEnergyPoint],
) -> list[VisualEnergySegment]:
    if not points:
        return []

    sorted_points = sorted(points, key=lambda point: point.time_seconds)
    point_step = _guess_point_step(sorted_points)

    segments: list[VisualEnergySegment] = []
    current_group: list[VisualEnergyPoint] = [sorted_points[0]]

    for point in sorted_points[1:]:
        current_classification = current_group[-1].classification

        if point.classification == current_classification:
            current_group.append(point)
            continue

        segments.append(
            _make_segment_from_points(
                grouped_points=current_group,
                end_seconds=point.time_seconds,
            )
        )
        current_group = [point]

    final_end_seconds = sorted_points[-1].time_seconds + point_step
    segments.append(
        _make_segment_from_points(
            grouped_points=current_group,
            end_seconds=final_end_seconds,
        )
    )

    return segments


def _get_duration_seconds(
    reports: tuple[Any | None, ...],
    segments: list[VisualEnergySegment],
) -> float | None:
    durations: list[float] = []

    for report in reports:
        data = _as_dict(report)
        duration = data.get("duration_seconds")
        if duration is not None:
            durations.append(_safe_float(duration, 0.0))

    if segments:
        durations.append(max(segment.end_seconds for segment in segments))

    if not durations:
        return None

    return round(max(durations), 3)


def _has_any_visual_source(
    scene_change_report: Any | None,
    motion_analysis_report: Any | None,
    face_reaction_report: Any | None,
    stutter_detection_report: Any | None,
    screen_content_report: Any | None,
) -> bool:
    return any(
        (
            _has_visual_source(
                scene_change_report,
                ("points", "scene_changes", "changes", "segments"),
            ),
            _has_visual_source(
                motion_analysis_report,
                ("points", "motion_points", "segments", "motion_segments"),
            ),
            _has_visual_source(face_reaction_report, ("reaction_windows", "windows", "points")),
            _has_visual_source(
                stutter_detection_report,
                ("points", "stutter_detection_points", "segments", "stutter_detection_segments"),
            ),
            _has_visual_source(
                screen_content_report,
                ("points", "screen_content_points", "segments", "screen_content_segments"),
            ),
        )
    )


def calculate_visual_energy(
    scene_change_report: Any | None = None,
    motion_analysis_report: Any | None = None,
    face_reaction_report: Any | None = None,
    stutter_detection_report: Any | None = None,
    screen_content_report: Any | None = None,
    unified_edit_signals: Any | None = None,
    frame_sample_rate: float = 2.0,
) -> VisualEnergyResult:
    has_source = _has_any_visual_source(
        scene_change_report=scene_change_report,
        motion_analysis_report=motion_analysis_report,
        face_reaction_report=face_reaction_report,
        stutter_detection_report=stutter_detection_report,
        screen_content_report=screen_content_report,
    )

    if not has_source:
        return VisualEnergyResult(
            status=STATUS_SKIPPED_NO_VISUAL_SOURCES,
            points=[],
            segments=[],
            point_count=0,
            segment_count=0,
            high_energy_segment_count=0,
            low_energy_segment_count=0,
            technical_warning_segment_count=0,
            duration_seconds=None,
            frame_sample_rate=frame_sample_rate,
            recommendation="skipped_no_visual_sources",
            warnings=["no_visual_sources_available"],
            errors=[],
            metadata={
                "no_cut_decision": True,
                "no_auto_remove": True,
                "no_auto_highlight": True,
            },
        )

    points = build_visual_energy_points(
        scene_change_report=scene_change_report,
        motion_analysis_report=motion_analysis_report,
        face_reaction_report=face_reaction_report,
        stutter_detection_report=stutter_detection_report,
        screen_content_report=screen_content_report,
        unified_edit_signals=unified_edit_signals,
    )

    if not points:
        return VisualEnergyResult(
            status=STATUS_SKIPPED_NO_VISUAL_SOURCES,
            points=[],
            segments=[],
            point_count=0,
            segment_count=0,
            high_energy_segment_count=0,
            low_energy_segment_count=0,
            technical_warning_segment_count=0,
            duration_seconds=None,
            frame_sample_rate=frame_sample_rate,
            recommendation="skipped_no_visual_points",
            warnings=["no_visual_energy_points_built"],
            errors=[],
            metadata={
                "no_cut_decision": True,
                "no_auto_remove": True,
                "no_auto_highlight": True,
            },
        )

    segments = build_visual_energy_segments(points)

    high_energy_segment_count = sum(
        1
        for segment in segments
        if segment.classification
        in {
            CLASSIFICATION_HIGH_VISUAL_ENERGY,
            CLASSIFICATION_PEAK_VISUAL_ENERGY,
        }
    )
    low_energy_segment_count = sum(
        1
        for segment in segments
        if segment.classification == CLASSIFICATION_LOW_VISUAL_ENERGY
    )
    technical_warning_segment_count = sum(
        1
        for segment in segments
        if segment.classification == CLASSIFICATION_TECHNICAL_WARNING
    )

    warnings: list[str] = []
    for point in points:
        warnings.extend(point.warnings)
    for segment in segments:
        warnings.extend(segment.warnings)

    if technical_warning_segment_count > 0:
        recommendation = "review_visual_technical_warnings"
    elif high_energy_segment_count > 0:
        recommendation = "review_visual_energy_candidates"
    elif low_energy_segment_count == len(segments):
        recommendation = "review_low_visual_energy_timeline"
    else:
        recommendation = "review_visual_energy_timeline"

    status = STATUS_COMPLETED_WITH_WARNINGS if warnings else STATUS_OK

    return VisualEnergyResult(
        status=status,
        points=points,
        segments=segments,
        point_count=len(points),
        segment_count=len(segments),
        high_energy_segment_count=high_energy_segment_count,
        low_energy_segment_count=low_energy_segment_count,
        technical_warning_segment_count=technical_warning_segment_count,
        duration_seconds=_get_duration_seconds(
            (
                scene_change_report,
                motion_analysis_report,
                face_reaction_report,
                stutter_detection_report,
                screen_content_report,
            ),
            segments,
        ),
        frame_sample_rate=frame_sample_rate,
        recommendation=recommendation,
        warnings=warnings,
        errors=[],
        metadata={
            "source_reports": {
                "scene_change": bool(_as_dict(scene_change_report)),
                "motion_analysis": bool(_as_dict(motion_analysis_report)),
                "face_reaction": bool(_as_dict(face_reaction_report)),
                "stutter_detection": bool(_as_dict(stutter_detection_report)),
                "screen_content": bool(_as_dict(screen_content_report)),
            },
            "no_cut_decision": True,
            "no_auto_remove": True,
            "no_auto_highlight": True,
        },
    )


def _get_job_value(job: Any, names: tuple[str, ...]) -> Any | None:
    if isinstance(job, dict):
        for name in names:
            if name in job:
                return job.get(name)
        return None

    for name in names:
        if hasattr(job, name):
            return getattr(job, name)

    return None


def calculate_visual_energy_from_job(job: Any) -> VisualEnergyResult:
    return calculate_visual_energy(
        scene_change_report=_get_job_value(
            job,
            (
                "scene_change_report",
                "scene_change_detection_report",
                "scene_change_run_report",
            ),
        ),
        motion_analysis_report=_get_job_value(
            job,
            (
                "motion_analysis_report",
                "motion_report",
            ),
        ),
        face_reaction_report=_get_job_value(
            job,
            (
                "face_reaction_report",
                "facecam_reaction_report",
                "reaction_report",
            ),
        ),
        stutter_detection_report=_get_job_value(
            job,
            (
                "stutter_detection_report",
                "duplicate_stutter_report",
            ),
        ),
        screen_content_report=_get_job_value(
            job,
            (
                "screen_content_report",
                "screen_content_classification_report",
            ),
        ),
        unified_edit_signals=_get_job_value(
            job,
            (
                "unified_edit_signals",
                "edit_signals",
            ),
        ),
    )
