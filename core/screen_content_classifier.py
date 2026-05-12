from __future__ import annotations

from pathlib import Path
from typing import Any

from models.screen_content_classification import (
    SCREEN_TYPE_BLACK_SCREEN,
    SCREEN_TYPE_DEATH_SCREEN,
    SCREEN_TYPE_GAMEPLAY,
    SCREEN_TYPE_INTRO_OUTRO_CANDIDATE,
    SCREEN_TYPE_LOADING,
    SCREEN_TYPE_LOBBY,
    SCREEN_TYPE_MENU,
    SCREEN_TYPE_SCOREBOARD,
    SCREEN_TYPE_UNKNOWN,
    SCREEN_TYPE_VALUES,
    SCREEN_TYPE_VICTORY_SCREEN,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_SKIPPED_NO_VIDEO_SOURCE,
    ScreenContentClassificationResult,
    ScreenContentPoint,
    ScreenContentSegment,
)


DEFAULT_FRAME_SAMPLE_RATE = 2.0
DEFAULT_RESIZE_WIDTH = 320
DEFAULT_RESIZE_HEIGHT = 180
DEFAULT_BLACK_BRIGHTNESS_THRESHOLD = 0.08
DEFAULT_UI_DENSITY_THRESHOLD = 0.35
DEFAULT_TEXT_LIKE_THRESHOLD = 0.25
DEFAULT_CONFIDENCE_THRESHOLD = 0.50


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp_score(value: Any, default: float = 0.0) -> float:
    return max(0.0, min(1.0, _safe_float(value, default)))


def _normalize_template_hint(metadata: dict[str, Any] | None) -> str | None:
    if not isinstance(metadata, dict):
        return None

    hint = str(metadata.get("template_hint") or "").strip().lower()
    if hint in SCREEN_TYPE_VALUES and hint != SCREEN_TYPE_UNKNOWN:
        return hint
    return None


def _recommendation_for_screen_type(screen_type: str) -> str:
    if screen_type == SCREEN_TYPE_GAMEPLAY:
        return "keep_content_context"
    if screen_type in {SCREEN_TYPE_MENU, SCREEN_TYPE_LOBBY}:
        return "review_possible_trim_menu_or_lobby"
    if screen_type == SCREEN_TYPE_LOADING:
        return "review_possible_trim_loading"
    if screen_type == SCREEN_TYPE_SCOREBOARD:
        return "review_scoreboard_context"
    if screen_type == SCREEN_TYPE_DEATH_SCREEN:
        return "review_death_screen_context"
    if screen_type == SCREEN_TYPE_VICTORY_SCREEN:
        return "keep_or_highlight_victory_screen"
    if screen_type == SCREEN_TYPE_BLACK_SCREEN:
        return "review_possible_trim_black_screen"
    if screen_type == SCREEN_TYPE_INTRO_OUTRO_CANDIDATE:
        return "review_intro_outro_boundary"
    return "review_unknown_screen_content"


def _is_review_candidate(screen_type: str) -> bool:
    return screen_type not in {SCREEN_TYPE_GAMEPLAY, SCREEN_TYPE_VICTORY_SCREEN}


def _prepare_frame(frame: Any, resize_width: int, resize_height: int) -> tuple[Any, Any]:
    import cv2

    safe_resize_width = max(16, int(resize_width or DEFAULT_RESIZE_WIDTH))
    safe_resize_height = max(16, int(resize_height or DEFAULT_RESIZE_HEIGHT))

    if frame is None:
        raise ValueError("frame_is_none")

    if len(getattr(frame, "shape", ())) == 2:
        bgr_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif len(frame.shape) >= 3 and frame.shape[2] == 4:
        bgr_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    else:
        bgr_frame = frame

    resized = cv2.resize(bgr_frame, (safe_resize_width, safe_resize_height))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    return resized, gray


def _edge_density(gray: Any) -> tuple[float, Any]:
    import cv2
    import numpy as np

    edges = cv2.Canny(gray, 60, 160)
    return _clamp_score(float(np.mean(edges > 0))), edges


def _line_structure_score(edges: Any) -> float:
    import cv2
    import numpy as np

    height, width = edges.shape[:2]
    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (max(12, width // 12), 1),
    )
    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, max(8, height // 12)),
    )
    horizontal = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
    line_density = (float(np.mean(horizontal > 0)) + float(np.mean(vertical > 0))) / 2.0
    return _clamp_score(line_density * 8.0)


def _text_like_region_score(edges: Any) -> float:
    import cv2

    height, width = edges.shape[:2]
    total_area = max(1.0, float(height * width))

    component_count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
        edges,
        8,
    )
    small_component_area = 0.0
    small_component_count = 0

    for index in range(1, component_count):
        x, y, w, h, area = stats[index]
        _ = (x, y)
        if area < 3 or area > 600:
            continue
        if w <= 1 or h <= 1:
            continue
        if w > width * 0.45 or h > height * 0.30:
            continue
        small_component_area += float(area)
        small_component_count += 1

    area_score = (small_component_area / total_area) * 22.0
    count_score = min(0.5, small_component_count / 260.0)
    return _clamp_score(area_score + count_score)


def _motion_context_score(previous_gray_frame: Any | None, current_gray_frame: Any) -> float:
    if previous_gray_frame is None:
        return 0.0

    import cv2
    import numpy as np

    try:
        if previous_gray_frame.shape != current_gray_frame.shape:
            previous_gray_frame = cv2.resize(
                previous_gray_frame,
                (current_gray_frame.shape[1], current_gray_frame.shape[0]),
            )
        diff = cv2.absdiff(previous_gray_frame, current_gray_frame)
        return _clamp_score(float(np.mean(diff) / 255.0))
    except Exception:
        return 0.0


def _classify_metrics(
    *,
    brightness_score: float,
    saturation_score: float,
    edge_density_score: float,
    motion_context_score: float,
    text_like_region_score: float,
    ui_density_score: float,
    line_structure_score: float,
    metadata: dict[str, Any],
    black_brightness_threshold: float,
    ui_density_threshold: float,
    text_like_threshold: float,
    confidence_threshold: float,
) -> tuple[str, float]:
    template_hint = _normalize_template_hint(metadata)
    if template_hint is not None:
        return template_hint, 0.95

    safe_black_threshold = _clamp_score(
        black_brightness_threshold,
        DEFAULT_BLACK_BRIGHTNESS_THRESHOLD,
    )
    safe_ui_threshold = _clamp_score(
        ui_density_threshold,
        DEFAULT_UI_DENSITY_THRESHOLD,
    )
    safe_text_threshold = _clamp_score(
        text_like_threshold,
        DEFAULT_TEXT_LIKE_THRESHOLD,
    )
    safe_confidence_threshold = _clamp_score(
        confidence_threshold,
        DEFAULT_CONFIDENCE_THRESHOLD,
    )

    if (
        brightness_score <= safe_black_threshold
        and edge_density_score <= 0.035
        and saturation_score <= 0.20
    ):
        confidence = 0.90 + min(0.09, safe_black_threshold - brightness_score)
        return SCREEN_TYPE_BLACK_SCREEN, _clamp_score(confidence)

    boundary_hint = str(metadata.get("boundary_hint") or "").strip().lower()
    if (
        boundary_hint in {"intro", "outro", "start", "end"}
        and brightness_score <= safe_black_threshold * 1.8
        and edge_density_score <= 0.08
    ):
        return SCREEN_TYPE_INTRO_OUTRO_CANDIDATE, 0.76

    if (
        line_structure_score >= 0.36
        and text_like_region_score >= safe_text_threshold
    ) or (
        text_like_region_score >= safe_text_threshold + 0.20
        and ui_density_score >= safe_ui_threshold
    ):
        confidence = max(
            safe_confidence_threshold,
            0.62 + (line_structure_score * 0.22) + (text_like_region_score * 0.16),
        )
        return SCREEN_TYPE_SCOREBOARD, _clamp_score(confidence)

    if (
        ui_density_score >= safe_ui_threshold
        or text_like_region_score >= safe_text_threshold
    ):
        confidence = max(
            safe_confidence_threshold,
            0.58 + (ui_density_score * 0.20) + (text_like_region_score * 0.12),
        )
        return SCREEN_TYPE_MENU, _clamp_score(confidence)

    if (
        motion_context_score <= 0.025
        and edge_density_score <= 0.08
        and saturation_score <= 0.35
    ):
        confidence = max(safe_confidence_threshold, 0.58 + (0.08 - edge_density_score))
        return SCREEN_TYPE_LOADING, _clamp_score(confidence)

    if edge_density_score >= 0.045 or saturation_score >= 0.20 or motion_context_score >= 0.04:
        confidence = max(
            safe_confidence_threshold,
            0.54
            + min(0.22, edge_density_score * 1.8)
            + min(0.15, saturation_score * 0.22)
            + min(0.10, motion_context_score * 0.6),
        )
        return SCREEN_TYPE_GAMEPLAY, _clamp_score(confidence)

    return SCREEN_TYPE_UNKNOWN, safe_confidence_threshold


def classify_screen_frame(
    frame: Any,
    time_seconds: float = 0.0,
    frame_index: int | None = None,
    previous_gray_frame: Any | None = None,
    metadata: dict[str, Any] | None = None,
    resize_width: int = DEFAULT_RESIZE_WIDTH,
    resize_height: int = DEFAULT_RESIZE_HEIGHT,
    black_brightness_threshold: float = DEFAULT_BLACK_BRIGHTNESS_THRESHOLD,
    ui_density_threshold: float = DEFAULT_UI_DENSITY_THRESHOLD,
    text_like_threshold: float = DEFAULT_TEXT_LIKE_THRESHOLD,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> ScreenContentPoint:
    safe_metadata = dict(metadata or {})

    try:
        import cv2
        import numpy as np
    except Exception as exc:
        return ScreenContentPoint(
            time_seconds=round(_safe_float(time_seconds), 6),
            frame_index=frame_index,
            screen_type=SCREEN_TYPE_UNKNOWN,
            confidence=0.0,
            metadata=safe_metadata,
            errors=[f"opencv_or_numpy_unavailable: {exc}"],
        )

    try:
        resized, gray = _prepare_frame(frame, resize_width, resize_height)
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)

        brightness_score = _clamp_score(float(np.mean(gray) / 255.0))
        saturation_score = _clamp_score(float(np.mean(hsv[:, :, 1]) / 255.0))
        edge_density_score, edges = _edge_density(gray)
        line_score = _line_structure_score(edges)
        text_like_score = _text_like_region_score(edges)
        motion_score = _motion_context_score(previous_gray_frame, gray)
        ui_density_score = _clamp_score(
            (edge_density_score * 3.4)
            + (text_like_score * 0.55)
            + (line_score * 0.45)
        )

        screen_type, confidence = _classify_metrics(
            brightness_score=brightness_score,
            saturation_score=saturation_score,
            edge_density_score=edge_density_score,
            motion_context_score=motion_score,
            text_like_region_score=text_like_score,
            ui_density_score=ui_density_score,
            line_structure_score=line_score,
            metadata=safe_metadata,
            black_brightness_threshold=black_brightness_threshold,
            ui_density_threshold=ui_density_threshold,
            text_like_threshold=text_like_threshold,
            confidence_threshold=confidence_threshold,
        )

        point_metadata = dict(safe_metadata)
        point_metadata.update(
            {
                "line_structure_score": round(line_score, 6),
                "resize_width": max(16, int(resize_width or DEFAULT_RESIZE_WIDTH)),
                "resize_height": max(16, int(resize_height or DEFAULT_RESIZE_HEIGHT)),
                "ocr_enabled": False,
            }
        )

        return ScreenContentPoint(
            time_seconds=round(_safe_float(time_seconds), 6),
            frame_index=frame_index,
            screen_type=screen_type,
            confidence=round(_clamp_score(confidence), 6),
            brightness_score=round(brightness_score, 6),
            saturation_score=round(saturation_score, 6),
            edge_density_score=round(edge_density_score, 6),
            motion_context_score=round(motion_score, 6),
            text_like_region_score=round(text_like_score, 6),
            ui_density_score=round(ui_density_score, 6),
            is_review_candidate=_is_review_candidate(screen_type),
            metadata=point_metadata,
            warnings=[],
            errors=[],
        )

    except Exception as exc:
        return ScreenContentPoint(
            time_seconds=round(_safe_float(time_seconds), 6),
            frame_index=frame_index,
            screen_type=SCREEN_TYPE_UNKNOWN,
            confidence=0.0,
            metadata=safe_metadata,
            errors=[f"screen_frame_classification_failed: {exc}"],
        )


def _create_segment_from_points(
    points: list[ScreenContentPoint],
    seconds_per_point: float,
) -> ScreenContentSegment | None:
    if not points:
        return None

    start_seconds = points[0].time_seconds
    end_seconds = points[-1].time_seconds + seconds_per_point
    duration_seconds = max(0.0, end_seconds - start_seconds)
    confidences = [point.confidence for point in points]
    screen_type = points[0].screen_type

    return ScreenContentSegment(
        start_seconds=round(start_seconds, 6),
        end_seconds=round(end_seconds, 6),
        duration_seconds=round(duration_seconds, 6),
        screen_type=screen_type,
        avg_confidence=round(sum(confidences) / len(confidences), 6),
        max_confidence=round(max(confidences), 6),
        point_count=len(points),
        recommendation=_recommendation_for_screen_type(screen_type),
        metadata={
            "first_point_time_seconds": points[0].time_seconds,
            "last_point_time_seconds": points[-1].time_seconds,
        },
        warnings=[],
        errors=[],
    )


def build_screen_content_segments(
    points: list[ScreenContentPoint],
    frame_sample_rate: float = DEFAULT_FRAME_SAMPLE_RATE,
) -> list[ScreenContentSegment]:
    if not points:
        return []

    safe_sample_rate = frame_sample_rate if frame_sample_rate > 0 else DEFAULT_FRAME_SAMPLE_RATE
    seconds_per_point = 1.0 / safe_sample_rate
    max_gap = max(seconds_per_point * 1.75, seconds_per_point + 0.001)

    segments: list[ScreenContentSegment] = []
    current_points: list[ScreenContentPoint] = []

    for point in sorted(points, key=lambda item: item.time_seconds):
        if not current_points:
            current_points = [point]
            continue

        previous_point = current_points[-1]
        same_type = point.screen_type == previous_point.screen_type
        close_enough = point.time_seconds - previous_point.time_seconds <= max_gap

        if same_type and close_enough:
            current_points.append(point)
            continue

        segment = _create_segment_from_points(current_points, seconds_per_point)
        if segment is not None:
            segments.append(segment)
        current_points = [point]

    if current_points:
        segment = _create_segment_from_points(current_points, seconds_per_point)
        if segment is not None:
            segments.append(segment)

    return segments


def _build_result(
    *,
    status: str,
    input_path: str,
    points: list[ScreenContentPoint] | None = None,
    segments: list[ScreenContentSegment] | None = None,
    duration_seconds: float | None = None,
    frame_sample_rate: float = DEFAULT_FRAME_SAMPLE_RATE,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ScreenContentClassificationResult:
    safe_points = points or []
    safe_segments = segments or []

    gameplay_count = sum(
        1 for segment in safe_segments if segment.screen_type == SCREEN_TYPE_GAMEPLAY
    )
    menu_count = sum(
        1
        for segment in safe_segments
        if segment.screen_type in {SCREEN_TYPE_MENU, SCREEN_TYPE_LOBBY}
    )
    loading_count = sum(
        1 for segment in safe_segments if segment.screen_type == SCREEN_TYPE_LOADING
    )
    scoreboard_count = sum(
        1 for segment in safe_segments if segment.screen_type == SCREEN_TYPE_SCOREBOARD
    )
    death_count = sum(
        1 for segment in safe_segments if segment.screen_type == SCREEN_TYPE_DEATH_SCREEN
    )
    victory_count = sum(
        1 for segment in safe_segments if segment.screen_type == SCREEN_TYPE_VICTORY_SCREEN
    )
    black_count = sum(
        1 for segment in safe_segments if segment.screen_type == SCREEN_TYPE_BLACK_SCREEN
    )

    recommendation = "review_unknown_screen_content"
    if gameplay_count > 0 and not any(
        [loading_count, black_count, death_count, scoreboard_count]
    ):
        recommendation = "keep_content_context"
    if menu_count > 0:
        recommendation = "review_possible_trim_menu_or_lobby"
    if scoreboard_count > 0:
        recommendation = "review_scoreboard_context"
    if victory_count > 0:
        recommendation = "keep_or_highlight_victory_screen"
    if death_count > 0:
        recommendation = "review_death_screen_context"
    if loading_count > 0:
        recommendation = "review_possible_trim_loading"
    if black_count > 0:
        recommendation = "review_possible_trim_black_screen"

    if status == STATUS_FAILED:
        recommendation = "screen_content_classification_failed"
    elif status == STATUS_SKIPPED_NO_VIDEO_SOURCE:
        recommendation = "no_video_source"

    return ScreenContentClassificationResult(
        status=status,
        input_path=input_path,
        points=safe_points,
        segments=safe_segments,
        point_count=len(safe_points),
        segment_count=len(safe_segments),
        gameplay_segment_count=gameplay_count,
        menu_segment_count=menu_count,
        loading_segment_count=loading_count,
        scoreboard_segment_count=scoreboard_count,
        death_screen_segment_count=death_count,
        victory_screen_segment_count=victory_count,
        black_screen_segment_count=black_count,
        duration_seconds=duration_seconds,
        frame_sample_rate=frame_sample_rate,
        recommendation=recommendation,
        warnings=warnings or [],
        errors=errors or [],
        metadata=metadata or {},
    )


def analyze_screen_content_from_frames(
    frames: list[Any],
    input_path: str = "frames",
    frame_sample_rate: float = DEFAULT_FRAME_SAMPLE_RATE,
    resize_width: int = DEFAULT_RESIZE_WIDTH,
    resize_height: int = DEFAULT_RESIZE_HEIGHT,
    black_brightness_threshold: float = DEFAULT_BLACK_BRIGHTNESS_THRESHOLD,
    ui_density_threshold: float = DEFAULT_UI_DENSITY_THRESHOLD,
    text_like_threshold: float = DEFAULT_TEXT_LIKE_THRESHOLD,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    frame_indices: list[int | None] | None = None,
    frame_metadata: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ScreenContentClassificationResult:
    try:
        import cv2
    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=input_path,
            frame_sample_rate=frame_sample_rate,
            errors=[f"opencv_or_numpy_unavailable: {exc}"],
            metadata=metadata,
        )

    try:
        import numpy  # noqa: F401
    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=input_path,
            frame_sample_rate=frame_sample_rate,
            errors=[f"opencv_or_numpy_unavailable: {exc}"],
            metadata=metadata,
        )

    if not frames:
        return _build_result(
            status=STATUS_COMPLETED_WITH_WARNINGS,
            input_path=input_path,
            frame_sample_rate=frame_sample_rate,
            warnings=["no_frames_provided"],
            metadata=metadata,
        )

    safe_sample_rate = frame_sample_rate if frame_sample_rate > 0 else DEFAULT_FRAME_SAMPLE_RATE
    points: list[ScreenContentPoint] = []
    previous_gray = None

    try:
        for index, frame in enumerate(frames):
            frame_index = None
            if frame_indices is not None and index < len(frame_indices):
                frame_index = frame_indices[index]

            point_metadata = dict(metadata or {})
            if frame_metadata is not None and index < len(frame_metadata):
                point_metadata.update(dict(frame_metadata[index] or {}))

            point = classify_screen_frame(
                frame=frame,
                time_seconds=index / safe_sample_rate,
                frame_index=frame_index,
                previous_gray_frame=previous_gray,
                metadata=point_metadata,
                resize_width=resize_width,
                resize_height=resize_height,
                black_brightness_threshold=black_brightness_threshold,
                ui_density_threshold=ui_density_threshold,
                text_like_threshold=text_like_threshold,
                confidence_threshold=confidence_threshold,
            )
            points.append(point)

            _resized, previous_gray = _prepare_frame(frame, resize_width, resize_height)

    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=input_path,
            points=points,
            frame_sample_rate=safe_sample_rate,
            errors=[f"screen_content_frame_analysis_failed: {exc}"],
            metadata=metadata,
        )

    segments = build_screen_content_segments(points, frame_sample_rate=safe_sample_rate)
    warnings: list[str] = []
    if len(points) < 2:
        warnings.append("not_enough_sampled_frames_for_screen_content_context")

    status = STATUS_OK
    if warnings:
        status = STATUS_COMPLETED_WITH_WARNINGS

    result_metadata = dict(metadata or {})
    result_metadata.update(
        {
            "resize_width": max(16, _safe_int(resize_width, DEFAULT_RESIZE_WIDTH)),
            "resize_height": max(16, _safe_int(resize_height, DEFAULT_RESIZE_HEIGHT)),
            "black_brightness_threshold": black_brightness_threshold,
            "ui_density_threshold": ui_density_threshold,
            "text_like_threshold": text_like_threshold,
            "confidence_threshold": confidence_threshold,
            "ocr_enabled": False,
        }
    )

    duration_seconds = len(frames) / safe_sample_rate if safe_sample_rate > 0 else None

    return _build_result(
        status=status,
        input_path=input_path,
        points=points,
        segments=segments,
        duration_seconds=duration_seconds,
        frame_sample_rate=safe_sample_rate,
        warnings=warnings,
        errors=[],
        metadata=result_metadata,
    )


def classify_screen_content(
    input_path: str | Path,
    frame_sample_rate: float = DEFAULT_FRAME_SAMPLE_RATE,
    resize_width: int = DEFAULT_RESIZE_WIDTH,
    resize_height: int = DEFAULT_RESIZE_HEIGHT,
    black_brightness_threshold: float = DEFAULT_BLACK_BRIGHTNESS_THRESHOLD,
    ui_density_threshold: float = DEFAULT_UI_DENSITY_THRESHOLD,
    text_like_threshold: float = DEFAULT_TEXT_LIKE_THRESHOLD,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    metadata: dict[str, Any] | None = None,
) -> ScreenContentClassificationResult:
    if not input_path:
        return _build_result(
            status=STATUS_SKIPPED_NO_VIDEO_SOURCE,
            input_path="",
            frame_sample_rate=frame_sample_rate,
            warnings=["input_video_missing"],
            metadata=metadata,
        )

    path = Path(input_path)
    input_str = str(path)

    if not path.exists() or not path.is_file():
        return _build_result(
            status=STATUS_SKIPPED_NO_VIDEO_SOURCE,
            input_path=input_str,
            frame_sample_rate=frame_sample_rate,
            warnings=["input_video_missing"],
            metadata=metadata,
        )

    try:
        import cv2
    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=input_str,
            frame_sample_rate=frame_sample_rate,
            errors=[f"opencv_or_numpy_unavailable: {exc}"],
            metadata=metadata,
        )

    try:
        import numpy  # noqa: F401
    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=input_str,
            frame_sample_rate=frame_sample_rate,
            errors=[f"opencv_or_numpy_unavailable: {exc}"],
            metadata=metadata,
        )

    cap = None

    try:
        cap = cv2.VideoCapture(input_str)
        if not cap.isOpened():
            return _build_result(
                status=STATUS_FAILED,
                input_path=input_str,
                frame_sample_rate=frame_sample_rate,
                errors=["video_capture_not_opened"],
                metadata=metadata,
            )

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if fps <= 0:
            fps = 30.0

        safe_sample_rate = frame_sample_rate if frame_sample_rate > 0 else DEFAULT_FRAME_SAMPLE_RATE
        sample_every_frames = max(1, int(round(fps / safe_sample_rate)))

        duration_seconds = None
        if frame_count > 0 and fps > 0:
            duration_seconds = frame_count / fps

        sampled_frames: list[Any] = []
        frame_indices: list[int | None] = []
        frame_index = 0

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if frame_index % sample_every_frames == 0:
                sampled_frames.append(frame)
                frame_indices.append(frame_index)

            frame_index += 1

        if not sampled_frames:
            return _build_result(
                status=STATUS_FAILED,
                input_path=input_str,
                duration_seconds=duration_seconds,
                frame_sample_rate=safe_sample_rate,
                errors=["no_frames_read"],
                metadata={
                    **dict(metadata or {}),
                    "fps": fps,
                    "frame_count": frame_count,
                },
            )

        result_metadata = dict(metadata or {})
        result_metadata.update(
            {
                "fps": fps,
                "frame_count": frame_count,
                "sample_every_frames": sample_every_frames,
            }
        )

        result = analyze_screen_content_from_frames(
            frames=sampled_frames,
            input_path=input_str,
            frame_sample_rate=safe_sample_rate,
            resize_width=resize_width,
            resize_height=resize_height,
            black_brightness_threshold=black_brightness_threshold,
            ui_density_threshold=ui_density_threshold,
            text_like_threshold=text_like_threshold,
            confidence_threshold=confidence_threshold,
            frame_indices=frame_indices,
            metadata=result_metadata,
        )
        result.duration_seconds = duration_seconds
        return result

    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=input_str,
            frame_sample_rate=frame_sample_rate,
            errors=[f"screen_content_classification_failed: {exc}"],
            metadata=metadata,
        )

    finally:
        if cap is not None:
            cap.release()
