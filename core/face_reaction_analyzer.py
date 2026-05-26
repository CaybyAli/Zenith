from __future__ import annotations

from pathlib import Path
from typing import Any

from models.face_reaction_analysis import (
    REACTION_EXPRESSIVE_CANDIDATE,
    REACTION_HYPE_CANDIDATE,
    REACTION_LAUGH_CANDIDATE,
    REACTION_MOUTH_OPEN_CANDIDATE,
    REACTION_NEUTRAL_FACE,
    REACTION_NONE,
    REACTION_SHOCK_CANDIDATE,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_SKIPPED_NO_VIDEO_SOURCE,
    FaceReactionAnalysisResult,
    FaceReactionPoint,
    FaceReactionSegment,
)


DEFAULT_FRAME_SAMPLE_RATE = 2.0
DEFAULT_MIN_FACE_AREA_RATIO = 0.005
DEFAULT_HIGH_REACTION_THRESHOLD = 0.55
DEFAULT_MIN_SEGMENT_DURATION_SECONDS = 0.5
DEFAULT_RESIZE_WIDTH = 320
DEFAULT_RESIZE_HEIGHT = 180

_CANDIDATE_REACTION_TYPES = {
    REACTION_MOUTH_OPEN_CANDIDATE,
    REACTION_LAUGH_CANDIDATE,
    REACTION_SHOCK_CANDIDATE,
    REACTION_HYPE_CANDIDATE,
    REACTION_EXPRESSIVE_CANDIDATE,
}

_REACTION_PRIORITY = {
    REACTION_SHOCK_CANDIDATE: 5,
    REACTION_LAUGH_CANDIDATE: 4,
    REACTION_HYPE_CANDIDATE: 3,
    REACTION_EXPRESSIVE_CANDIDATE: 2,
    REACTION_MOUTH_OPEN_CANDIDATE: 1,
    REACTION_NEUTRAL_FACE: 0,
    REACTION_NONE: -1,
}


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


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_high_reaction_candidate(
    point: FaceReactionPoint,
    high_reaction_threshold: float,
) -> bool:
    if not point.face_detected:
        return False

    if point.reaction_type in _CANDIDATE_REACTION_TYPES:
        return True

    return point.reaction_score >= high_reaction_threshold


def classify_face_reaction(
    *,
    face_detected: bool,
    mouth_open_score: float = 0.0,
    eye_open_score: float = 0.0,
    expressiveness_score: float = 0.0,
    reaction_score: float | None = None,
    high_reaction_threshold: float = DEFAULT_HIGH_REACTION_THRESHOLD,
    metadata: dict[str, Any] | None = None,
) -> str:
    if not face_detected:
        return REACTION_NONE

    safe_mouth = _clamp_score(mouth_open_score)
    safe_eye = _clamp_score(eye_open_score)
    safe_expressive = _clamp_score(expressiveness_score)
    safe_threshold = _clamp_score(
        high_reaction_threshold,
        DEFAULT_HIGH_REACTION_THRESHOLD,
    )

    if reaction_score is None:
        safe_reaction = _clamp_score(
            (safe_mouth * 0.4) + (safe_eye * 0.15) + (safe_expressive * 0.45)
        )
    else:
        safe_reaction = _clamp_score(reaction_score)

    safe_metadata = metadata if isinstance(metadata, dict) else {}

    if bool(safe_metadata.get("laugh_candidate")):
        return REACTION_LAUGH_CANDIDATE

    if safe_mouth >= 0.72 and safe_eye >= 0.55:
        return REACTION_SHOCK_CANDIDATE

    if safe_reaction >= safe_threshold and safe_mouth >= 0.55:
        return REACTION_HYPE_CANDIDATE

    if safe_mouth >= 0.45 and safe_expressive >= 0.62 and safe_eye <= 0.45:
        return REACTION_LAUGH_CANDIDATE

    if safe_expressive >= 0.75 or safe_reaction >= safe_threshold:
        return REACTION_EXPRESSIVE_CANDIDATE

    if safe_mouth >= 0.45:
        return REACTION_MOUTH_OPEN_CANDIDATE

    return REACTION_NEUTRAL_FACE


def _recommendation_for_reaction_type(reaction_type: str) -> str:
    if reaction_type == REACTION_SHOCK_CANDIDATE:
        return "review_shock_reaction_candidate"
    if reaction_type == REACTION_LAUGH_CANDIDATE:
        return "review_laugh_reaction_candidate"
    if reaction_type == REACTION_MOUTH_OPEN_CANDIDATE:
        return "review_mouth_open_candidate"
    if reaction_type in {
        REACTION_HYPE_CANDIDATE,
        REACTION_EXPRESSIVE_CANDIDATE,
    }:
        return "review_high_face_reaction_candidate"
    if reaction_type == REACTION_NEUTRAL_FACE:
        return "context_face_presence"
    return "review_face_reaction_candidate"


def _dominant_reaction_type(points: list[FaceReactionPoint]) -> str:
    if not points:
        return REACTION_NONE

    return max(
        points,
        key=lambda point: (
            _REACTION_PRIORITY.get(point.reaction_type, -1),
            point.reaction_score,
        ),
    ).reaction_type


def _create_segment_from_points(
    points: list[FaceReactionPoint],
    seconds_per_point: float,
) -> FaceReactionSegment:
    start_seconds = points[0].time_seconds
    end_seconds = points[-1].time_seconds + seconds_per_point
    duration_seconds = max(0.0, end_seconds - start_seconds)

    reaction_scores = [point.reaction_score for point in points]
    face_area_ratios = [point.face_area_ratio for point in points]
    reaction_type = _dominant_reaction_type(points)

    return FaceReactionSegment(
        start_seconds=round(start_seconds, 6),
        end_seconds=round(end_seconds, 6),
        duration_seconds=round(duration_seconds, 6),
        avg_reaction_score=round(sum(reaction_scores) / len(reaction_scores), 6),
        max_reaction_score=round(max(reaction_scores), 6),
        avg_face_area_ratio=round(sum(face_area_ratios) / len(face_area_ratios), 6),
        reaction_type=reaction_type,
        recommendation=_recommendation_for_reaction_type(reaction_type),
        metadata={
            "point_count": len(points),
            "reaction_types": sorted({point.reaction_type for point in points}),
        },
        warnings=[],
        errors=[],
    )


def build_face_reaction_segments(
    points: list[FaceReactionPoint],
    frame_sample_rate: float = DEFAULT_FRAME_SAMPLE_RATE,
    high_reaction_threshold: float = DEFAULT_HIGH_REACTION_THRESHOLD,
    min_reaction_segment_duration_seconds: float = DEFAULT_MIN_SEGMENT_DURATION_SECONDS,
) -> list[FaceReactionSegment]:
    if not points:
        return []

    safe_sample_rate = frame_sample_rate if frame_sample_rate > 0 else DEFAULT_FRAME_SAMPLE_RATE
    seconds_per_point = 1.0 / safe_sample_rate
    safe_threshold = _clamp_score(
        high_reaction_threshold,
        DEFAULT_HIGH_REACTION_THRESHOLD,
    )
    safe_min_duration = max(
        0.0,
        _safe_float(
            min_reaction_segment_duration_seconds,
            DEFAULT_MIN_SEGMENT_DURATION_SECONDS,
        ),
    )

    segments: list[FaceReactionSegment] = []
    current_points: list[FaceReactionPoint] = []

    for point in sorted(points, key=lambda item: item.time_seconds):
        if not _is_high_reaction_candidate(point, safe_threshold):
            if current_points:
                segment = _create_segment_from_points(
                    current_points,
                    seconds_per_point,
                )
                if segment.duration_seconds >= safe_min_duration:
                    segments.append(segment)
                current_points = []
            continue

        if not current_points:
            current_points = [point]
            continue

        previous_point = current_points[-1]
        max_gap = max(seconds_per_point * 1.75, seconds_per_point + 0.001)
        if point.time_seconds - previous_point.time_seconds <= max_gap:
            current_points.append(point)
            continue

        segment = _create_segment_from_points(current_points, seconds_per_point)
        if segment.duration_seconds >= safe_min_duration:
            segments.append(segment)
        current_points = [point]

    if current_points:
        segment = _create_segment_from_points(current_points, seconds_per_point)
        if segment.duration_seconds >= safe_min_duration:
            segments.append(segment)

    return segments


def _build_result(
    *,
    status: str,
    input_path: str,
    points: list[FaceReactionPoint] | None = None,
    segments: list[FaceReactionSegment] | None = None,
    duration_seconds: float | None = None,
    frame_sample_rate: float = DEFAULT_FRAME_SAMPLE_RATE,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> FaceReactionAnalysisResult:
    safe_points = points or []
    safe_segments = segments or []

    face_detected_point_count = sum(1 for point in safe_points if point.face_detected)
    reaction_candidate_count = sum(
        1
        for point in safe_points
        if point.reaction_type in _CANDIDATE_REACTION_TYPES
    )
    high_reaction_segment_count = len(
        [
            segment
            for segment in safe_segments
            if segment.max_reaction_score >= DEFAULT_HIGH_REACTION_THRESHOLD
        ]
    )

    recommendation = "no_face_presence_detected"
    if high_reaction_segment_count > 0:
        recommendation = "review_face_reaction_candidates"
    elif face_detected_point_count > 0:
        recommendation = "face_presence_detected"
    if status == STATUS_FAILED:
        recommendation = "face_reaction_analysis_failed"
    elif status == STATUS_SKIPPED_NO_VIDEO_SOURCE:
        recommendation = "no_video_source"

    return FaceReactionAnalysisResult(
        status=status,
        input_path=input_path,
        points=safe_points,
        segments=safe_segments,
        point_count=len(safe_points),
        segment_count=len(safe_segments),
        face_detected_point_count=face_detected_point_count,
        reaction_candidate_count=reaction_candidate_count,
        high_reaction_segment_count=high_reaction_segment_count,
        duration_seconds=duration_seconds,
        frame_sample_rate=frame_sample_rate,
        recommendation=recommendation,
        warnings=warnings or [],
        errors=errors or [],
        metadata=metadata or {},
    )


def _load_haar_face_cascade(cv2: Any) -> tuple[Any | None, str | None]:
    try:
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    except Exception:
        return None, None

    if not cascade_path.is_file():
        return None, str(cascade_path)

    try:
        cascade = cv2.CascadeClassifier(str(cascade_path))
    except Exception:
        return None, str(cascade_path)

    if cascade.empty():
        return None, str(cascade_path)

    return cascade, str(cascade_path)


def _primary_face_box(faces: Any) -> tuple[dict[str, Any], int]:
    try:
        face_items = list(faces)
    except TypeError:
        face_items = []

    valid_faces: list[tuple[int, int, int, int]] = []
    for face in face_items:
        try:
            x, y, width, height = [int(value) for value in face[:4]]
        except Exception:
            continue
        if width > 0 and height > 0:
            valid_faces.append((x, y, width, height))

    if not valid_faces:
        return {}, 0

    x, y, width, height = max(valid_faces, key=lambda item: item[2] * item[3])
    return (
        {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        },
        len(valid_faces),
    )


def _face_proxy_scores(
    gray_frame: Any,
    face_box: dict[str, Any],
    previous_face_mean: float | None,
) -> tuple[float, float, float, float | None, dict[str, Any]]:
    try:
        import numpy as np
    except Exception:
        return 0.0, 0.0, 0.0, previous_face_mean, {}

    x = _safe_int(face_box.get("x"), 0)
    y = _safe_int(face_box.get("y"), 0)
    width = _safe_int(face_box.get("width"), 0)
    height = _safe_int(face_box.get("height"), 0)

    if width <= 0 or height <= 0:
        return 0.0, 0.0, 0.0, previous_face_mean, {}

    roi = gray_frame[y : y + height, x : x + width]
    if roi.size == 0:
        return 0.0, 0.0, 0.0, previous_face_mean, {}

    upper = roi[: max(1, height // 2), :]
    lower = roi[max(0, int(height * 0.58)) :, :]

    roi_mean = float(np.mean(roi))
    roi_std = float(np.std(roi))
    upper_std = float(np.std(upper)) if upper.size else 0.0
    lower_mean = float(np.mean(lower)) if lower.size else roi_mean
    lower_std = float(np.std(lower)) if lower.size else 0.0

    dark_mouth_proxy = max(0.0, (roi_mean - lower_mean) / 128.0)
    lower_contrast_proxy = min(1.0, lower_std / 64.0)
    mouth_open_score = _clamp_score(
        (dark_mouth_proxy * 0.55) + (lower_contrast_proxy * 0.45)
    )

    eye_open_score = _clamp_score(upper_std / 64.0)

    delta_score = 0.0
    if previous_face_mean is not None:
        delta_score = _clamp_score(abs(roi_mean - previous_face_mean) / 64.0)

    expressiveness_score = _clamp_score(
        (mouth_open_score * 0.45)
        + (eye_open_score * 0.20)
        + (delta_score * 0.25)
        + (min(1.0, roi_std / 96.0) * 0.10)
    )

    metadata = {
        "roi_mean": round(roi_mean, 6),
        "roi_std": round(roi_std, 6),
        "proxy_method": "haar_face_roi_without_landmarks",
    }

    return (
        mouth_open_score,
        eye_open_score,
        expressiveness_score,
        roi_mean,
        metadata,
    )


def _reaction_score(
    *,
    face_area_ratio: float,
    min_face_area_ratio: float,
    mouth_open_score: float,
    expressiveness_score: float,
) -> float:
    safe_min_area = max(0.0001, _safe_float(min_face_area_ratio, DEFAULT_MIN_FACE_AREA_RATIO))
    face_area_score = _clamp_score((face_area_ratio - safe_min_area) / 0.18)
    return _clamp_score(
        (face_area_score * 0.30)
        + (_clamp_score(mouth_open_score) * 0.35)
        + (_clamp_score(expressiveness_score) * 0.35)
    )


def _analyze_sampled_frames(
    *,
    frames: list[Any],
    input_path: str,
    frame_sample_rate: float,
    min_face_area_ratio: float,
    high_reaction_threshold: float,
    min_reaction_segment_duration_seconds: float,
    resize_width: int,
    resize_height: int,
    frame_indices: list[int | None] | None = None,
    duration_seconds: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> FaceReactionAnalysisResult:
    try:
        import cv2
    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=input_path,
            frame_sample_rate=frame_sample_rate,
            errors=[f"opencv_unavailable: {exc}"],
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
    safe_min_face_area_ratio = max(
        0.0,
        _safe_float(min_face_area_ratio, DEFAULT_MIN_FACE_AREA_RATIO),
    )
    safe_high_threshold = _clamp_score(
        high_reaction_threshold,
        DEFAULT_HIGH_REACTION_THRESHOLD,
    )

    cascade, cascade_path = _load_haar_face_cascade(cv2)

    warnings: list[str] = []
    if cascade is None:
        warnings.append("haar_cascade_unavailable")

    points: list[FaceReactionPoint] = []
    previous_face_mean: float | None = None

    try:
        for index, frame in enumerate(frames):
            frame_index = None
            if frame_indices is not None and index < len(frame_indices):
                frame_index = frame_indices[index]

            resized = cv2.resize(frame, (safe_resize_width, safe_resize_height))
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

            primary_box: dict[str, Any] = {}
            face_count = 0
            if cascade is not None:
                detected_faces = cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=4,
                    minSize=(24, 24),
                )
                primary_box, face_count = _primary_face_box(detected_faces)

            frame_area = float(safe_resize_width * safe_resize_height)
            face_area_ratio = 0.0
            if primary_box:
                face_area_ratio = (
                    float(primary_box["width"] * primary_box["height"]) / frame_area
                )

            face_detected = face_count > 0 and face_area_ratio >= safe_min_face_area_ratio

            mouth_open_score = 0.0
            eye_open_score = 0.0
            expressiveness_score = 0.0
            proxy_metadata: dict[str, Any] = {}
            if face_detected:
                (
                    mouth_open_score,
                    eye_open_score,
                    expressiveness_score,
                    previous_face_mean,
                    proxy_metadata,
                ) = _face_proxy_scores(gray, primary_box, previous_face_mean)

            score = _reaction_score(
                face_area_ratio=face_area_ratio,
                min_face_area_ratio=safe_min_face_area_ratio,
                mouth_open_score=mouth_open_score,
                expressiveness_score=expressiveness_score,
            )
            reaction_type = classify_face_reaction(
                face_detected=face_detected,
                mouth_open_score=mouth_open_score,
                eye_open_score=eye_open_score,
                expressiveness_score=expressiveness_score,
                reaction_score=score,
                high_reaction_threshold=safe_high_threshold,
            )

            face_area_score = _clamp_score(
                (face_area_ratio - safe_min_face_area_ratio) / 0.18
            )
            confidence = 0.0
            if face_detected:
                confidence = _clamp_score(0.45 + (face_area_score * 0.35) + 0.10)

            point_metadata = {
                "source": "frame_sample",
                "cascade_path": cascade_path,
                "resize_width": safe_resize_width,
                "resize_height": safe_resize_height,
                **proxy_metadata,
            }

            points.append(
                FaceReactionPoint(
                    time_seconds=round(index / safe_sample_rate, 6),
                    frame_index=frame_index,
                    face_detected=face_detected,
                    face_count=face_count,
                    primary_face_box=primary_box,
                    face_area_ratio=round(face_area_ratio, 6),
                    mouth_open_score=round(mouth_open_score, 6),
                    eye_open_score=round(eye_open_score, 6),
                    expressiveness_score=round(expressiveness_score, 6),
                    reaction_type=reaction_type,
                    reaction_score=round(score, 6),
                    confidence=round(confidence, 6),
                    metadata=point_metadata,
                    warnings=[],
                    errors=[],
                )
            )

    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=input_path,
            points=points,
            duration_seconds=duration_seconds,
            frame_sample_rate=safe_sample_rate,
            warnings=warnings,
            errors=[f"face_reaction_frame_analysis_failed: {exc}"],
            metadata=metadata,
        )

    segments = build_face_reaction_segments(
        points=points,
        frame_sample_rate=safe_sample_rate,
        high_reaction_threshold=safe_high_threshold,
        min_reaction_segment_duration_seconds=min_reaction_segment_duration_seconds,
    )

    if points and not any(point.face_detected for point in points):
        warnings.append("no_faces_detected")

    status = STATUS_OK
    if warnings:
        status = STATUS_COMPLETED_WITH_WARNINGS

    result_metadata = dict(metadata or {})
    result_metadata.update(
        {
            "cascade_path": cascade_path,
            "cascade_available": cascade is not None,
            "min_face_area_ratio": safe_min_face_area_ratio,
            "high_reaction_threshold": safe_high_threshold,
            "min_reaction_segment_duration_seconds": (
                min_reaction_segment_duration_seconds
            ),
            "resize_width": safe_resize_width,
            "resize_height": safe_resize_height,
        }
    )

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


def analyze_face_reactions_from_frames(
    frames: list[Any],
    input_path: str = "frames",
    frame_sample_rate: float = DEFAULT_FRAME_SAMPLE_RATE,
    min_face_area_ratio: float = DEFAULT_MIN_FACE_AREA_RATIO,
    high_reaction_threshold: float = DEFAULT_HIGH_REACTION_THRESHOLD,
    min_reaction_segment_duration_seconds: float = DEFAULT_MIN_SEGMENT_DURATION_SECONDS,
    resize_width: int = DEFAULT_RESIZE_WIDTH,
    resize_height: int = DEFAULT_RESIZE_HEIGHT,
    frame_indices: list[int | None] | None = None,
    metadata: dict[str, Any] | None = None,
) -> FaceReactionAnalysisResult:
    duration_seconds = None
    if frame_sample_rate > 0:
        duration_seconds = len(frames) / frame_sample_rate

    return _analyze_sampled_frames(
        frames=frames,
        input_path=input_path,
        frame_sample_rate=frame_sample_rate,
        min_face_area_ratio=min_face_area_ratio,
        high_reaction_threshold=high_reaction_threshold,
        min_reaction_segment_duration_seconds=min_reaction_segment_duration_seconds,
        resize_width=resize_width,
        resize_height=resize_height,
        frame_indices=frame_indices,
        duration_seconds=duration_seconds,
        metadata=metadata,
    )


def analyze_face_reactions(
    input_path: str | Path,
    frame_sample_rate: float = DEFAULT_FRAME_SAMPLE_RATE,
    min_face_area_ratio: float = DEFAULT_MIN_FACE_AREA_RATIO,
    high_reaction_threshold: float = DEFAULT_HIGH_REACTION_THRESHOLD,
    min_reaction_segment_duration_seconds: float = DEFAULT_MIN_SEGMENT_DURATION_SECONDS,
    resize_width: int = DEFAULT_RESIZE_WIDTH,
    resize_height: int = DEFAULT_RESIZE_HEIGHT,
    metadata: dict[str, Any] | None = None,
) -> FaceReactionAnalysisResult:
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
            errors=[f"opencv_unavailable: {exc}"],
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

        return _analyze_sampled_frames(
            frames=sampled_frames,
            input_path=input_str,
            frame_sample_rate=safe_sample_rate,
            min_face_area_ratio=min_face_area_ratio,
            high_reaction_threshold=high_reaction_threshold,
            min_reaction_segment_duration_seconds=(
                min_reaction_segment_duration_seconds
            ),
            resize_width=resize_width,
            resize_height=resize_height,
            frame_indices=frame_indices,
            duration_seconds=duration_seconds,
            metadata=result_metadata,
        )

    except Exception as exc:
        return _build_result(
            status=STATUS_FAILED,
            input_path=input_str,
            frame_sample_rate=frame_sample_rate,
            errors=[f"face_reaction_analysis_failed: {exc}"],
            metadata=metadata,
        )

    finally:
        if cap is not None:
            cap.release()
