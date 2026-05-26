from __future__ import annotations

from pathlib import Path
from typing import Any

from models.motion_analysis import (
    CLASSIFICATION_DEAD_VISUAL_CANDIDATE,
    CLASSIFICATION_HIGH_MOTION,
    CLASSIFICATION_LOW_MOTION,
    CLASSIFICATION_MEDIUM_MOTION,
    CLASSIFICATION_STATIC,
    MotionAnalysisResult,
    MotionPoint,
    MotionSegment,
    RECOMMENDATION_NONE,
    RECOMMENDATION_REVIEW,
    RECOMMENDATION_REVIEW_OR_TRIM_DEAD_VISUAL,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_SKIPPED_NO_VIDEO_SOURCE,
)


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def classify_motion_score(
    motion_score: float,
    low_motion_threshold: float = 0.08,
    high_motion_threshold: float = 0.35,
) -> str:
    score = _clamp_score(motion_score)

    if score < 0.02:
        return CLASSIFICATION_STATIC

    if score < low_motion_threshold:
        return CLASSIFICATION_LOW_MOTION

    if score >= high_motion_threshold:
        return CLASSIFICATION_HIGH_MOTION

    return CLASSIFICATION_MEDIUM_MOTION


def build_motion_points(
    raw_motion_values: list[float],
    frame_sample_rate: float = 2.0,
    low_motion_threshold: float = 0.08,
    high_motion_threshold: float = 0.35,
    frame_indices: list[int | None] | None = None,
) -> list[MotionPoint]:
    safe_sample_rate = frame_sample_rate if frame_sample_rate > 0 else 2.0
    seconds_per_point = 1.0 / safe_sample_rate

    points: list[MotionPoint] = []

    for index, raw_value in enumerate(raw_motion_values):
        score = _clamp_score(raw_value)
        frame_index = None

        if frame_indices is not None and index < len(frame_indices):
            frame_index = frame_indices[index]

        points.append(
            MotionPoint(
                time_seconds=round(index * seconds_per_point, 6),
                frame_index=frame_index,
                motion_score=score,
                raw_motion_value=float(raw_value),
                classification=classify_motion_score(
                    score,
                    low_motion_threshold=low_motion_threshold,
                    high_motion_threshold=high_motion_threshold,
                ),
                confidence=1.0,
                metadata={},
                warnings=[],
                errors=[],
            )
        )

    return points


def _is_low_or_static(classification: str) -> bool:
    return classification in {
        CLASSIFICATION_STATIC,
        CLASSIFICATION_LOW_MOTION,
    }


def _segment_classification_for_points(
    points: list[MotionPoint],
    dead_visual_min_duration_seconds: float,
    duration_seconds: float,
) -> str:
    classifications = {point.classification for point in points}

    if all(_is_low_or_static(point.classification) for point in points):
        if duration_seconds >= dead_visual_min_duration_seconds:
            return CLASSIFICATION_DEAD_VISUAL_CANDIDATE

        if classifications == {CLASSIFICATION_STATIC}:
            return CLASSIFICATION_STATIC

        return CLASSIFICATION_LOW_MOTION

    if CLASSIFICATION_HIGH_MOTION in classifications:
        return CLASSIFICATION_HIGH_MOTION

    return CLASSIFICATION_MEDIUM_MOTION


def _segment_recommendation(classification: str) -> str:
    if classification == CLASSIFICATION_DEAD_VISUAL_CANDIDATE:
        return RECOMMENDATION_REVIEW_OR_TRIM_DEAD_VISUAL

    if classification == CLASSIFICATION_HIGH_MOTION:
        return RECOMMENDATION_REVIEW

    return RECOMMENDATION_NONE


def _same_segment_family(previous: MotionPoint, current: MotionPoint) -> bool:
    previous_low = _is_low_or_static(previous.classification)
    current_low = _is_low_or_static(current.classification)

    if previous_low and current_low:
        return True

    return previous.classification == current.classification


def _create_segment_from_points(
    points: list[MotionPoint],
    seconds_per_point: float,
    dead_visual_min_duration_seconds: float,
) -> MotionSegment:
    start_seconds = points[0].time_seconds
    end_seconds = points[-1].time_seconds + seconds_per_point
    duration_seconds = max(0.0, end_seconds - start_seconds)

    scores = [point.motion_score for point in points]
    avg_motion_score = sum(scores) / len(scores)
    max_motion_score = max(scores)

    classification = _segment_classification_for_points(
        points=points,
        dead_visual_min_duration_seconds=dead_visual_min_duration_seconds,
        duration_seconds=duration_seconds,
    )

    return MotionSegment(
        start_seconds=round(start_seconds, 6),
        end_seconds=round(end_seconds, 6),
        duration_seconds=round(duration_seconds, 6),
        avg_motion_score=round(avg_motion_score, 6),
        max_motion_score=round(max_motion_score, 6),
        classification=classification,
        recommendation=_segment_recommendation(classification),
        metadata={
            "point_count": len(points),
        },
        warnings=[],
        errors=[],
    )


def build_motion_segments(
    points: list[MotionPoint],
    frame_sample_rate: float = 2.0,
    dead_visual_min_duration_seconds: float = 3.0,
) -> list[MotionSegment]:
    if not points:
        return []

    safe_sample_rate = frame_sample_rate if frame_sample_rate > 0 else 2.0
    seconds_per_point = 1.0 / safe_sample_rate

    segments: list[MotionSegment] = []
    current_points: list[MotionPoint] = [points[0]]

    for point in points[1:]:
        previous_point = current_points[-1]

        if _same_segment_family(previous_point, point):
            current_points.append(point)
            continue

        segments.append(
            _create_segment_from_points(
                points=current_points,
                seconds_per_point=seconds_per_point,
                dead_visual_min_duration_seconds=dead_visual_min_duration_seconds,
            )
        )
        current_points = [point]

    segments.append(
        _create_segment_from_points(
            points=current_points,
            seconds_per_point=seconds_per_point,
            dead_visual_min_duration_seconds=dead_visual_min_duration_seconds,
        )
    )

    return segments


def _build_result(
    status: str,
    input_path: str,
    points: list[MotionPoint] | None = None,
    segments: list[MotionSegment] | None = None,
    duration_seconds: float | None = None,
    frame_sample_rate: float = 2.0,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> MotionAnalysisResult:
    safe_points = points or []
    safe_segments = segments or []

    low_motion_segment_count = sum(
        1 for segment in safe_segments if segment.classification == CLASSIFICATION_LOW_MOTION
    )
    high_motion_segment_count = sum(
        1 for segment in safe_segments if segment.classification == CLASSIFICATION_HIGH_MOTION
    )
    dead_visual_candidate_count = sum(
        1
        for segment in safe_segments
        if segment.classification == CLASSIFICATION_DEAD_VISUAL_CANDIDATE
    )

    recommendation = RECOMMENDATION_NONE
    if dead_visual_candidate_count > 0:
        recommendation = RECOMMENDATION_REVIEW_OR_TRIM_DEAD_VISUAL
    elif high_motion_segment_count > 0:
        recommendation = RECOMMENDATION_REVIEW

    return MotionAnalysisResult(
        status=status,
        input_path=input_path,
        points=safe_points,
        segments=safe_segments,
        point_count=len(safe_points),
        segment_count=len(safe_segments),
        low_motion_segment_count=low_motion_segment_count,
        high_motion_segment_count=high_motion_segment_count,
        dead_visual_candidate_count=dead_visual_candidate_count,
        duration_seconds=duration_seconds,
        frame_sample_rate=frame_sample_rate,
        recommendation=recommendation,
        warnings=warnings or [],
        errors=errors or [],
        metadata=metadata or {},
    )


def analyze_motion_from_frames(
    frames: list[Any],
    input_path: str = "frames",
    frame_sample_rate: float = 2.0,
    low_motion_threshold: float = 0.08,
    high_motion_threshold: float = 0.35,
    dead_visual_min_duration_seconds: float = 3.0,
    resize_width: int = 160,
    resize_height: int = 90,
) -> MotionAnalysisResult:
    try:
        import cv2
        import numpy as np
    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=input_path,
            frame_sample_rate=frame_sample_rate,
            errors=[f"opencv_or_numpy_unavailable: {exc}"],
        )

    if not frames:
        return _build_result(
            status=STATUS_COMPLETED_WITH_WARNINGS,
            input_path=input_path,
            frame_sample_rate=frame_sample_rate,
            warnings=["no_frames_provided"],
        )

    try:
        raw_motion_values: list[float] = []
        previous_gray = None

        for frame in frames:
            resized = cv2.resize(frame, (resize_width, resize_height))
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

            if previous_gray is None:
                raw_motion_values.append(0.0)
                previous_gray = gray
                continue

            diff = cv2.absdiff(previous_gray, gray)
            raw_motion = float(np.mean(diff) / 255.0)
            raw_motion_values.append(raw_motion)

            previous_gray = gray

        points = build_motion_points(
            raw_motion_values=raw_motion_values,
            frame_sample_rate=frame_sample_rate,
            low_motion_threshold=low_motion_threshold,
            high_motion_threshold=high_motion_threshold,
        )
        segments = build_motion_segments(
            points=points,
            frame_sample_rate=frame_sample_rate,
            dead_visual_min_duration_seconds=dead_visual_min_duration_seconds,
        )

        return _build_result(
            status=STATUS_OK,
            input_path=input_path,
            points=points,
            segments=segments,
            duration_seconds=len(frames) / frame_sample_rate if frame_sample_rate > 0 else None,
            frame_sample_rate=frame_sample_rate,
            metadata={
                "source": "frames",
                "resize_width": resize_width,
                "resize_height": resize_height,
            },
        )

    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=input_path,
            frame_sample_rate=frame_sample_rate,
            errors=[f"frame_motion_analysis_failed: {exc}"],
        )


def analyze_motion(
    input_path: str,
    frame_sample_rate: float = 2.0,
    low_motion_threshold: float = 0.08,
    high_motion_threshold: float = 0.35,
    dead_visual_min_duration_seconds: float = 3.0,
    resize_width: int = 160,
    resize_height: int = 90,
) -> MotionAnalysisResult:
    path = Path(input_path)

    if not input_path or not path.exists() or not path.is_file():
        return _build_result(
            status=STATUS_SKIPPED_NO_VIDEO_SOURCE,
            input_path=input_path,
            frame_sample_rate=frame_sample_rate,
            warnings=["input_video_missing"],
        )

    try:
        import cv2
        import numpy as np
    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=str(path),
            frame_sample_rate=frame_sample_rate,
            errors=[f"opencv_or_numpy_unavailable: {exc}"],
        )

    cap = None

    try:
        cap = cv2.VideoCapture(str(path))

        if not cap.isOpened():
            return _build_result(
                status=STATUS_FAILED,
                input_path=str(path),
                frame_sample_rate=frame_sample_rate,
                errors=["video_capture_not_opened"],
            )

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        if fps <= 0:
            fps = 30.0

        safe_sample_rate = frame_sample_rate if frame_sample_rate > 0 else 2.0
        sample_every_frames = max(1, int(round(fps / safe_sample_rate)))

        duration_seconds = None
        if frame_count > 0 and fps > 0:
            duration_seconds = frame_count / fps

        raw_motion_values: list[float] = []
        frame_indices: list[int | None] = []

        previous_gray = None
        frame_index = 0

        while True:
            if frame_index % sample_every_frames != 0:
                ok = cap.grab()
                if not ok:
                    break
                frame_index += 1
                continue

            ok, frame = cap.read()
            if not ok:
                break

            resized = cv2.resize(frame, (resize_width, resize_height))
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

            if previous_gray is None:
                raw_motion_values.append(0.0)
                frame_indices.append(frame_index)
                previous_gray = gray
                frame_index += 1
                continue

            diff = cv2.absdiff(previous_gray, gray)
            raw_motion = float(np.mean(diff) / 255.0)
            raw_motion_values.append(raw_motion)
            frame_indices.append(frame_index)

            previous_gray = gray
            frame_index += 1

        if not raw_motion_values:
            return _build_result(
                status=STATUS_FAILED,
                input_path=str(path),
                duration_seconds=duration_seconds,
                frame_sample_rate=frame_sample_rate,
                errors=["no_frames_read"],
                metadata={
                    "fps": fps,
                    "frame_count": frame_count,
                },
            )

        points = build_motion_points(
            raw_motion_values=raw_motion_values,
            frame_sample_rate=frame_sample_rate,
            low_motion_threshold=low_motion_threshold,
            high_motion_threshold=high_motion_threshold,
            frame_indices=frame_indices,
        )
        segments = build_motion_segments(
            points=points,
            frame_sample_rate=frame_sample_rate,
            dead_visual_min_duration_seconds=dead_visual_min_duration_seconds,
        )

        status = STATUS_OK
        warnings: list[str] = []

        if len(points) < 2:
            status = STATUS_COMPLETED_WITH_WARNINGS
            warnings.append("not_enough_sampled_frames_for_motion_delta")

        return _build_result(
            status=status,
            input_path=str(path),
            points=points,
            segments=segments,
            duration_seconds=duration_seconds,
            frame_sample_rate=frame_sample_rate,
            warnings=warnings,
            metadata={
                "fps": fps,
                "frame_count": frame_count,
                "sample_every_frames": sample_every_frames,
                "resize_width": resize_width,
                "resize_height": resize_height,
            },
        )

    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=str(path),
            frame_sample_rate=frame_sample_rate,
            errors=[f"motion_analysis_failed: {exc}"],
        )

    finally:
        if cap is not None:
            cap.release()
