from __future__ import annotations

from pathlib import Path
from typing import Any

from models.stutter_detection import (
    CLASSIFICATION_DUPLICATE_FRAME_CANDIDATE,
    CLASSIFICATION_ENCODING_DROP_CANDIDATE,
    CLASSIFICATION_FREEZE_SEGMENT,
    CLASSIFICATION_NORMAL_FRAME,
    CLASSIFICATION_STUTTER_SEGMENT,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_SKIPPED_NO_VIDEO_SOURCE,
    StutterDetectionResult,
    StutterFramePoint,
    StutterSegment,
)


DEFAULT_FRAME_SAMPLE_RATE = 10.0
DEFAULT_DUPLICATE_SCORE_THRESHOLD = 0.985
DEFAULT_DIFFERENCE_SCORE_THRESHOLD = 0.015
DEFAULT_MIN_DUPLICATE_FRAMES_FOR_STUTTER = 4
DEFAULT_MIN_STUTTER_DURATION_SECONDS = 0.13
DEFAULT_MIN_FREEZE_DURATION_SECONDS = 1.0
DEFAULT_RESIZE_WIDTH = 160
DEFAULT_RESIZE_HEIGHT = 90


def _clamp_score(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            value = default
        safe_value = float(value)
    except (TypeError, ValueError):
        safe_value = default
    return max(0.0, min(1.0, safe_value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _recommendation_for_classification(classification: str) -> str:
    if classification == CLASSIFICATION_STUTTER_SEGMENT:
        return "review_stutter_segment"
    if classification == CLASSIFICATION_FREEZE_SEGMENT:
        return "review_freeze_segment"
    if classification == CLASSIFICATION_ENCODING_DROP_CANDIDATE:
        return "review_encoding_drop_candidate"
    return "review_stutter_detection"


def classify_stutter_point(
    *,
    duplicate_score: float,
    difference_score: float,
    duplicate_score_threshold: float = DEFAULT_DUPLICATE_SCORE_THRESHOLD,
    difference_score_threshold: float = DEFAULT_DIFFERENCE_SCORE_THRESHOLD,
) -> str:
    safe_duplicate_score = _clamp_score(duplicate_score)
    safe_difference_score = _clamp_score(difference_score, 1.0)
    safe_duplicate_threshold = _clamp_score(
        duplicate_score_threshold,
        DEFAULT_DUPLICATE_SCORE_THRESHOLD,
    )
    safe_difference_threshold = _clamp_score(
        difference_score_threshold,
        DEFAULT_DIFFERENCE_SCORE_THRESHOLD,
    )

    if (
        safe_duplicate_score >= safe_duplicate_threshold
        and safe_difference_score <= safe_difference_threshold
    ):
        return CLASSIFICATION_DUPLICATE_FRAME_CANDIDATE

    return CLASSIFICATION_NORMAL_FRAME


def _segment_classification(
    *,
    duplicate_frame_count: int,
    duration_seconds: float,
    min_duplicate_frames_for_stutter: int,
    min_stutter_duration_seconds: float,
) -> str | None:
    safe_min_duplicate = max(1, int(min_duplicate_frames_for_stutter or 1))
    safe_min_duration = max(
        0.0,
        _safe_float(
            min_stutter_duration_seconds,
            DEFAULT_MIN_STUTTER_DURATION_SECONDS,
        ),
    )
    freeze_duration = max(
        DEFAULT_MIN_FREEZE_DURATION_SECONDS,
        safe_min_duration * 4.0,
    )

    if duplicate_frame_count >= safe_min_duplicate:
        if duration_seconds >= freeze_duration:
            return CLASSIFICATION_FREEZE_SEGMENT
        return CLASSIFICATION_STUTTER_SEGMENT

    if duplicate_frame_count >= 2:
        return CLASSIFICATION_ENCODING_DROP_CANDIDATE

    return None


def _create_segment_from_points(
    points: list[StutterFramePoint],
    seconds_per_point: float,
    min_duplicate_frames_for_stutter: int,
    min_stutter_duration_seconds: float,
) -> StutterSegment | None:
    if not points:
        return None

    start_seconds = max(0.0, points[0].time_seconds - seconds_per_point)
    end_seconds = points[-1].time_seconds + seconds_per_point
    duration_seconds = max(0.0, end_seconds - start_seconds)
    duplicate_scores = [point.duplicate_score for point in points]
    duplicate_frame_count = len(points)

    classification = _segment_classification(
        duplicate_frame_count=duplicate_frame_count,
        duration_seconds=duration_seconds,
        min_duplicate_frames_for_stutter=min_duplicate_frames_for_stutter,
        min_stutter_duration_seconds=min_stutter_duration_seconds,
    )
    if classification is None:
        return None

    if (
        classification == CLASSIFICATION_STUTTER_SEGMENT
        and duration_seconds < min_stutter_duration_seconds
    ):
        return None

    return StutterSegment(
        start_seconds=round(start_seconds, 6),
        end_seconds=round(end_seconds, 6),
        duration_seconds=round(duration_seconds, 6),
        start_frame_index=points[0].frame_index,
        end_frame_index=points[-1].frame_index,
        duplicate_frame_count=duplicate_frame_count,
        avg_duplicate_score=round(sum(duplicate_scores) / len(duplicate_scores), 6),
        max_duplicate_score=round(max(duplicate_scores), 6),
        classification=classification,
        recommendation=_recommendation_for_classification(classification),
        metadata={
            "point_count": len(points),
            "first_duplicate_time_seconds": points[0].time_seconds,
            "last_duplicate_time_seconds": points[-1].time_seconds,
        },
        warnings=[],
        errors=[],
    )


def build_stutter_segments(
    points: list[StutterFramePoint],
    frame_sample_rate: float = DEFAULT_FRAME_SAMPLE_RATE,
    min_duplicate_frames_for_stutter: int = DEFAULT_MIN_DUPLICATE_FRAMES_FOR_STUTTER,
    min_stutter_duration_seconds: float = DEFAULT_MIN_STUTTER_DURATION_SECONDS,
) -> list[StutterSegment]:
    if not points:
        return []

    safe_sample_rate = frame_sample_rate if frame_sample_rate > 0 else DEFAULT_FRAME_SAMPLE_RATE
    seconds_per_point = 1.0 / safe_sample_rate
    max_gap = max(seconds_per_point * 1.75, seconds_per_point + 0.001)

    segments: list[StutterSegment] = []
    current_points: list[StutterFramePoint] = []

    for point in sorted(points, key=lambda item: item.time_seconds):
        if not point.is_duplicate_candidate:
            if current_points:
                segment = _create_segment_from_points(
                    current_points,
                    seconds_per_point,
                    min_duplicate_frames_for_stutter,
                    min_stutter_duration_seconds,
                )
                if segment is not None:
                    segments.append(segment)
                current_points = []
            continue

        if not current_points:
            current_points = [point]
            continue

        previous_point = current_points[-1]
        if point.time_seconds - previous_point.time_seconds <= max_gap:
            current_points.append(point)
            continue

        segment = _create_segment_from_points(
            current_points,
            seconds_per_point,
            min_duplicate_frames_for_stutter,
            min_stutter_duration_seconds,
        )
        if segment is not None:
            segments.append(segment)
        current_points = [point]

    if current_points:
        segment = _create_segment_from_points(
            current_points,
            seconds_per_point,
            min_duplicate_frames_for_stutter,
            min_stutter_duration_seconds,
        )
        if segment is not None:
            segments.append(segment)

    return segments


def _build_result(
    *,
    status: str,
    input_path: str,
    points: list[StutterFramePoint] | None = None,
    segments: list[StutterSegment] | None = None,
    duration_seconds: float | None = None,
    frame_sample_rate: float = DEFAULT_FRAME_SAMPLE_RATE,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> StutterDetectionResult:
    safe_points = points or []
    safe_segments = segments or []

    duplicate_candidate_count = sum(
        1 for point in safe_points if point.is_duplicate_candidate
    )
    stutter_segment_count = sum(
        1
        for segment in safe_segments
        if segment.classification == CLASSIFICATION_STUTTER_SEGMENT
    )
    freeze_segment_count = sum(
        1
        for segment in safe_segments
        if segment.classification == CLASSIFICATION_FREEZE_SEGMENT
    )
    encoding_drop_count = sum(
        1
        for segment in safe_segments
        if segment.classification == CLASSIFICATION_ENCODING_DROP_CANDIDATE
    )

    recommendation = "no_stutter_candidates_detected"
    if freeze_segment_count > 0:
        recommendation = "review_freeze_segment"
    elif stutter_segment_count > 0:
        recommendation = "review_stutter_segment"
    elif encoding_drop_count > 0:
        recommendation = "review_encoding_drop_candidate"

    if status == STATUS_FAILED:
        recommendation = "stutter_detection_failed"
    elif status == STATUS_SKIPPED_NO_VIDEO_SOURCE:
        recommendation = "no_video_source"

    return StutterDetectionResult(
        status=status,
        input_path=input_path,
        points=safe_points,
        segments=safe_segments,
        point_count=len(safe_points),
        segment_count=len(safe_segments),
        duplicate_candidate_count=duplicate_candidate_count,
        stutter_segment_count=stutter_segment_count,
        freeze_segment_count=freeze_segment_count,
        duration_seconds=duration_seconds,
        frame_sample_rate=frame_sample_rate,
        recommendation=recommendation,
        warnings=warnings or [],
        errors=errors or [],
        metadata=metadata or {},
    )


def _average_hash(gray_frame: Any, hash_size: int = 8) -> str:
    import cv2
    import numpy as np

    hash_frame = cv2.resize(gray_frame, (hash_size, hash_size))
    average_value = float(np.mean(hash_frame))
    bits = hash_frame >= average_value
    return "".join("1" if bool(bit) else "0" for bit in bits.flatten())


def _frame_difference_score(previous_gray: Any, current_gray: Any) -> float:
    import cv2
    import numpy as np

    diff = cv2.absdiff(previous_gray, current_gray)
    return _clamp_score(float(np.mean(diff) / 255.0))


def analyze_stutter_from_frames(
    frames: list[Any],
    input_path: str = "frames",
    frame_sample_rate: float = DEFAULT_FRAME_SAMPLE_RATE,
    duplicate_score_threshold: float = DEFAULT_DUPLICATE_SCORE_THRESHOLD,
    difference_score_threshold: float = DEFAULT_DIFFERENCE_SCORE_THRESHOLD,
    min_duplicate_frames_for_stutter: int = DEFAULT_MIN_DUPLICATE_FRAMES_FOR_STUTTER,
    min_stutter_duration_seconds: float = DEFAULT_MIN_STUTTER_DURATION_SECONDS,
    resize_width: int = DEFAULT_RESIZE_WIDTH,
    resize_height: int = DEFAULT_RESIZE_HEIGHT,
    frame_indices: list[int | None] | None = None,
    metadata: dict[str, Any] | None = None,
) -> StutterDetectionResult:
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
    safe_resize_width = max(16, int(resize_width or DEFAULT_RESIZE_WIDTH))
    safe_resize_height = max(16, int(resize_height or DEFAULT_RESIZE_HEIGHT))
    safe_duplicate_threshold = _clamp_score(
        duplicate_score_threshold,
        DEFAULT_DUPLICATE_SCORE_THRESHOLD,
    )
    safe_difference_threshold = _clamp_score(
        difference_score_threshold,
        DEFAULT_DIFFERENCE_SCORE_THRESHOLD,
    )

    points: list[StutterFramePoint] = []
    previous_gray = None
    previous_hash: str | None = None

    try:
        for index, frame in enumerate(frames):
            frame_index = None
            if frame_indices is not None and index < len(frame_indices):
                frame_index = frame_indices[index]

            resized = cv2.resize(frame, (safe_resize_width, safe_resize_height))
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            frame_hash = _average_hash(gray)

            if previous_gray is None:
                difference_score = 1.0
                duplicate_score = 0.0
            else:
                difference_score = _frame_difference_score(previous_gray, gray)
                duplicate_score = _clamp_score(1.0 - difference_score)

            classification = classify_stutter_point(
                duplicate_score=duplicate_score,
                difference_score=difference_score,
                duplicate_score_threshold=safe_duplicate_threshold,
                difference_score_threshold=safe_difference_threshold,
            )
            is_duplicate_candidate = (
                classification == CLASSIFICATION_DUPLICATE_FRAME_CANDIDATE
            )
            confidence = duplicate_score if is_duplicate_candidate else 1.0 - duplicate_score
            if previous_gray is None:
                confidence = 1.0

            points.append(
                StutterFramePoint(
                    time_seconds=round(index / safe_sample_rate, 6),
                    frame_index=frame_index,
                    frame_hash=frame_hash,
                    previous_frame_hash=previous_hash,
                    duplicate_score=round(duplicate_score, 6),
                    difference_score=round(difference_score, 6),
                    is_duplicate_candidate=is_duplicate_candidate,
                    classification=classification,
                    confidence=round(_clamp_score(confidence), 6),
                    metadata={
                        "source": "frame_sample",
                        "resize_width": safe_resize_width,
                        "resize_height": safe_resize_height,
                    },
                    warnings=[],
                    errors=[],
                )
            )

            previous_gray = gray
            previous_hash = frame_hash

    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=input_path,
            points=points,
            frame_sample_rate=safe_sample_rate,
            errors=[f"stutter_frame_analysis_failed: {exc}"],
            metadata=metadata,
        )

    segments = build_stutter_segments(
        points=points,
        frame_sample_rate=safe_sample_rate,
        min_duplicate_frames_for_stutter=min_duplicate_frames_for_stutter,
        min_stutter_duration_seconds=min_stutter_duration_seconds,
    )

    warnings: list[str] = []
    if len(points) < 2:
        warnings.append("not_enough_sampled_frames_for_stutter_detection")

    status = STATUS_OK
    if warnings:
        status = STATUS_COMPLETED_WITH_WARNINGS

    result_metadata = dict(metadata or {})
    result_metadata.update(
        {
            "duplicate_score_threshold": safe_duplicate_threshold,
            "difference_score_threshold": safe_difference_threshold,
            "min_duplicate_frames_for_stutter": min_duplicate_frames_for_stutter,
            "min_stutter_duration_seconds": min_stutter_duration_seconds,
            "resize_width": safe_resize_width,
            "resize_height": safe_resize_height,
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


def analyze_stutter_frames(
    input_path: str | Path,
    frame_sample_rate: float = DEFAULT_FRAME_SAMPLE_RATE,
    duplicate_score_threshold: float = DEFAULT_DUPLICATE_SCORE_THRESHOLD,
    difference_score_threshold: float = DEFAULT_DIFFERENCE_SCORE_THRESHOLD,
    min_duplicate_frames_for_stutter: int = DEFAULT_MIN_DUPLICATE_FRAMES_FOR_STUTTER,
    min_stutter_duration_seconds: float = DEFAULT_MIN_STUTTER_DURATION_SECONDS,
    resize_width: int = DEFAULT_RESIZE_WIDTH,
    resize_height: int = DEFAULT_RESIZE_HEIGHT,
    metadata: dict[str, Any] | None = None,
) -> StutterDetectionResult:
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
            if frame_index % sample_every_frames != 0:
                ok = cap.grab()
                if not ok:
                    break
                frame_index += 1
                continue

            ok, frame = cap.read()
            if not ok:
                break

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

        result = analyze_stutter_from_frames(
            frames=sampled_frames,
            input_path=input_str,
            frame_sample_rate=safe_sample_rate,
            duplicate_score_threshold=duplicate_score_threshold,
            difference_score_threshold=difference_score_threshold,
            min_duplicate_frames_for_stutter=min_duplicate_frames_for_stutter,
            min_stutter_duration_seconds=min_stutter_duration_seconds,
            resize_width=resize_width,
            resize_height=resize_height,
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
            errors=[f"stutter_detection_failed: {exc}"],
            metadata=metadata,
        )

    finally:
        if cap is not None:
            cap.release()
