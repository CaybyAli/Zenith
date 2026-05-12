from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Iterable

from core.ffmpeg_helper import get_ffmpeg_path
from models.scene_change import (
    CHANGE_TYPE_FLASH,
    CHANGE_TYPE_HARD,
    CHANGE_TYPE_SOFT,
    CHANGE_TYPE_UNKNOWN,
    SCENE_STATUS_COMPLETED_WITH_WARNINGS,
    SCENE_STATUS_FAILED,
    SCENE_STATUS_OK,
    SCENE_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    SceneChangePoint,
    SceneChangeResult,
)


DEFAULT_SCENE_THRESHOLD = 0.30
DEFAULT_SOFT_THRESHOLD = 0.18
DEFAULT_FLASH_THRESHOLD = 0.85
DEFAULT_MIN_DISTANCE_SECONDS = 0.25
DEFAULT_FLASH_NEIGHBOR_WINDOW_SECONDS = 0.40

_VIDEO_SUFFIXES = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".ts",
    ".wmv",
    ".flv",
}

_FRAME_LINE_RE = re.compile(
    r"frame:\s*(?P<frame>\d+)\s+pts:\s*(?P<pts>-?\d+)\s+pts_time:\s*(?P<pts_time>-?\d+(?:\.\d+)?)"
)
_SCENE_SCORE_RE = re.compile(r"lavfi\.scene_score\s*=\s*(?P<score>-?\d+(?:\.\d+)?)")
_DURATION_RE = re.compile(
    r"Duration:\s*(?P<h>\d+):(?P<m>\d+):(?P<s>\d+(?:\.\d+)?)"
)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_probable_video_path(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in _VIDEO_SUFFIXES:
        return True
    return False


def _build_recommendation(
    scene_change_count: int,
    hard_change_count: int,
    soft_transition_count: int,
    false_positive_candidate_count: int,
    duration_seconds: float | None,
) -> str:
    if scene_change_count <= 0:
        return "no_scene_changes_detected"

    high_density = False
    if duration_seconds is not None and duration_seconds > 0:
        per_minute = scene_change_count / (duration_seconds / 60.0)
        if per_minute >= 30:
            high_density = True

    if false_positive_candidate_count >= max(1, scene_change_count // 2):
        return "review_flash_or_explosion_candidates"

    if high_density:
        return "high_scene_change_density_review"

    if hard_change_count > 0 and soft_transition_count == 0:
        return "use_hard_scene_changes"

    if hard_change_count == 0 and soft_transition_count > 0:
        return "soft_transitions_only"

    return "scene_changes_available"


def parse_ffmpeg_scene_output(text: str) -> list[dict[str, Any]]:
    if not isinstance(text, str) or not text:
        return []

    points: list[dict[str, Any]] = []
    pending_frame: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        frame_match = _FRAME_LINE_RE.search(line)
        if frame_match:
            try:
                frame_index = int(frame_match.group("frame"))
            except (TypeError, ValueError):
                frame_index = None

            try:
                pts_time = float(frame_match.group("pts_time"))
            except (TypeError, ValueError):
                pts_time = 0.0

            pending_frame = {
                "frame_index": frame_index,
                "time_seconds": max(0.0, pts_time),
                "scene_score": None,
            }
            continue

        score_match = _SCENE_SCORE_RE.search(line)
        if score_match:
            try:
                score = float(score_match.group("score"))
            except (TypeError, ValueError):
                score = 0.0

            if pending_frame is None:
                pending_frame = {
                    "frame_index": None,
                    "time_seconds": 0.0,
                    "scene_score": _clamp(score, 0.0, 1.0),
                }
            else:
                pending_frame["scene_score"] = _clamp(score, 0.0, 1.0)

            if pending_frame.get("scene_score") is not None:
                points.append(pending_frame)
                pending_frame = None

    return points


def parse_ffmpeg_duration_seconds(text: str) -> float | None:
    if not isinstance(text, str) or not text:
        return None

    match = _DURATION_RE.search(text)
    if not match:
        return None

    try:
        hours = int(match.group("h"))
        minutes = int(match.group("m"))
        seconds = float(match.group("s"))
    except (TypeError, ValueError):
        return None

    total = hours * 3600 + minutes * 60 + seconds
    if total <= 0:
        return None
    return total


def classify_scene_change(
    scene_score: float,
    *,
    scene_threshold: float = DEFAULT_SCENE_THRESHOLD,
    soft_threshold: float = DEFAULT_SOFT_THRESHOLD,
) -> str:
    safe_score = _safe_float(scene_score, 0.0)
    safe_scene_threshold = _safe_float(scene_threshold, DEFAULT_SCENE_THRESHOLD)
    safe_soft_threshold = _safe_float(soft_threshold, DEFAULT_SOFT_THRESHOLD)

    if safe_soft_threshold > safe_scene_threshold:
        safe_soft_threshold = safe_scene_threshold

    if safe_score >= safe_scene_threshold:
        return CHANGE_TYPE_HARD
    if safe_score >= safe_soft_threshold:
        return CHANGE_TYPE_SOFT
    return CHANGE_TYPE_UNKNOWN


def _confidence_from_score(score: float, scene_threshold: float) -> float:
    safe_score = _safe_float(score, 0.0)
    safe_threshold = _safe_float(scene_threshold, DEFAULT_SCENE_THRESHOLD)
    if safe_threshold <= 0:
        safe_threshold = DEFAULT_SCENE_THRESHOLD

    if safe_score <= 0:
        return 0.0

    ratio = safe_score / safe_threshold
    if ratio >= 1.0:
        return _clamp(0.6 + 0.4 * (safe_score - safe_threshold) / max(safe_threshold, 0.0001))
    return _clamp(safe_score / safe_threshold * 0.6)


def _build_points(
    raw_points: Iterable[dict[str, Any]],
    *,
    scene_threshold: float,
    soft_threshold: float,
) -> list[SceneChangePoint]:
    points: list[SceneChangePoint] = []

    for raw in raw_points:
        if not isinstance(raw, dict):
            continue

        score = _safe_float(raw.get("scene_score"), 0.0)
        if score < soft_threshold:
            continue

        change_type = classify_scene_change(
            score,
            scene_threshold=scene_threshold,
            soft_threshold=soft_threshold,
        )
        confidence = _confidence_from_score(score, scene_threshold)

        time_seconds = max(0.0, _safe_float(raw.get("time_seconds"), 0.0))

        frame_index_raw = raw.get("frame_index")
        try:
            frame_index = int(frame_index_raw) if frame_index_raw is not None else None
        except (TypeError, ValueError):
            frame_index = None

        points.append(
            SceneChangePoint(
                time_seconds=time_seconds,
                frame_index=frame_index,
                scene_score=score,
                change_type=change_type,
                confidence=confidence,
                is_false_positive_candidate=False,
                reason="ffmpeg_scene_score",
            )
        )

    points.sort(key=lambda point: point.time_seconds)
    return points


def filter_or_mark_near_duplicates(
    points: list[SceneChangePoint],
    *,
    min_distance_seconds: float = DEFAULT_MIN_DISTANCE_SECONDS,
    flash_neighbor_window_seconds: float = DEFAULT_FLASH_NEIGHBOR_WINDOW_SECONDS,
    flash_threshold: float = DEFAULT_FLASH_THRESHOLD,
) -> list[SceneChangePoint]:
    if not points:
        return []

    safe_min_distance = max(0.0, _safe_float(min_distance_seconds, DEFAULT_MIN_DISTANCE_SECONDS))
    safe_flash_window = max(
        safe_min_distance,
        _safe_float(flash_neighbor_window_seconds, DEFAULT_FLASH_NEIGHBOR_WINDOW_SECONDS),
    )
    safe_flash_threshold = _safe_float(flash_threshold, DEFAULT_FLASH_THRESHOLD)

    sorted_points = sorted(
        [point for point in points if isinstance(point, SceneChangePoint)],
        key=lambda point: point.time_seconds,
    )

    kept: list[SceneChangePoint] = []

    for point in sorted_points:
        if not kept:
            kept.append(point)
            continue

        previous = kept[-1]
        distance = point.time_seconds - previous.time_seconds

        if distance < safe_min_distance:
            previous_score = previous.scene_score
            current_score = point.scene_score

            if current_score > previous_score:
                replaced = previous
                kept[-1] = point
                kept[-1].warnings = list(point.warnings)
                if "near_duplicate_dropped_neighbor" not in kept[-1].warnings:
                    kept[-1].warnings.append("near_duplicate_dropped_neighbor")
                kept[-1].metadata = dict(kept[-1].metadata)
                kept[-1].metadata["dropped_neighbor_time_seconds"] = replaced.time_seconds
                kept[-1].metadata["dropped_neighbor_scene_score"] = replaced.scene_score
            else:
                if "near_duplicate_dropped_neighbor" not in previous.warnings:
                    previous.warnings.append("near_duplicate_dropped_neighbor")
                previous.metadata.setdefault(
                    "dropped_neighbor_time_seconds", point.time_seconds
                )
                previous.metadata.setdefault(
                    "dropped_neighbor_scene_score", point.scene_score
                )
            continue

        kept.append(point)

    for index, point in enumerate(kept):
        if point.scene_score < safe_flash_threshold:
            continue

        previous_distance: float | None = None
        next_distance: float | None = None

        if index > 0:
            previous_distance = point.time_seconds - kept[index - 1].time_seconds
        if index + 1 < len(kept):
            next_distance = kept[index + 1].time_seconds - point.time_seconds

        is_close_to_previous = (
            previous_distance is not None and previous_distance <= safe_flash_window
        )
        is_close_to_next = (
            next_distance is not None and next_distance <= safe_flash_window
        )

        if is_close_to_previous or is_close_to_next:
            point.change_type = CHANGE_TYPE_FLASH
            point.is_false_positive_candidate = True
            if "flash_or_explosion_candidate" not in point.warnings:
                point.warnings.append("flash_or_explosion_candidate")
            point.reason = "flash_neighbor_heuristic"

    return kept


def _summarize_counts(points: Iterable[SceneChangePoint]) -> tuple[int, int, int, int]:
    scene_change_count = 0
    hard_change_count = 0
    soft_transition_count = 0
    false_positive_candidate_count = 0

    for point in points:
        scene_change_count += 1
        if point.change_type == CHANGE_TYPE_HARD:
            hard_change_count += 1
        elif point.change_type == CHANGE_TYPE_SOFT:
            soft_transition_count += 1
        if point.is_false_positive_candidate:
            false_positive_candidate_count += 1

    return (
        scene_change_count,
        hard_change_count,
        soft_transition_count,
        false_positive_candidate_count,
    )


def _make_failed_result(
    *,
    input_path: str,
    error: str,
    threshold: float,
    metadata: dict[str, Any] | None = None,
    status: str = SCENE_STATUS_FAILED,
) -> SceneChangeResult:
    return SceneChangeResult(
        status=status,
        input_path=input_path,
        scene_changes=[],
        scene_change_count=0,
        hard_change_count=0,
        soft_transition_count=0,
        false_positive_candidate_count=0,
        threshold=threshold,
        duration_seconds=None,
        recommendation="scene_detection_failed" if status == SCENE_STATUS_FAILED else "no_video_source",
        warnings=[],
        errors=[error] if error else [],
        metadata=dict(metadata or {}),
    )


def _run_ffmpeg_scene_detection(
    *,
    ffmpeg_path: str,
    input_path: Path,
    soft_threshold: float,
    timeout_seconds: float,
) -> tuple[int, str, str]:
    safe_soft = max(0.0, min(1.0, _safe_float(soft_threshold, DEFAULT_SOFT_THRESHOLD)))
    filter_chain = f"select='gte(scene,{safe_soft:.4f})',metadata=print"

    cmd = [
        ffmpeg_path,
        "-hide_banner",
        "-nostats",
        "-i",
        str(input_path),
        "-an",
        "-sn",
        "-vf",
        filter_chain,
        "-vsync",
        "vfr",
        "-f",
        "null",
        "-",
    ]

    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return completed.returncode, completed.stdout or "", completed.stderr or ""


def analyze_scene_changes(
    input_path: str | Path,
    *,
    scene_threshold: float = DEFAULT_SCENE_THRESHOLD,
    soft_threshold: float = DEFAULT_SOFT_THRESHOLD,
    flash_threshold: float = DEFAULT_FLASH_THRESHOLD,
    min_distance_seconds: float = DEFAULT_MIN_DISTANCE_SECONDS,
    flash_neighbor_window_seconds: float = DEFAULT_FLASH_NEIGHBOR_WINDOW_SECONDS,
    timeout_seconds: float = 120.0,
    ffmpeg_path_override: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> SceneChangeResult:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    safe_scene_threshold = max(0.0, min(1.0, _safe_float(scene_threshold, DEFAULT_SCENE_THRESHOLD)))
    safe_soft_threshold = max(0.0, min(1.0, _safe_float(soft_threshold, DEFAULT_SOFT_THRESHOLD)))
    if safe_soft_threshold > safe_scene_threshold:
        safe_soft_threshold = safe_scene_threshold

    safe_flash_threshold = max(0.0, min(1.0, _safe_float(flash_threshold, DEFAULT_FLASH_THRESHOLD)))
    safe_min_distance = max(0.0, _safe_float(min_distance_seconds, DEFAULT_MIN_DISTANCE_SECONDS))
    safe_flash_window = max(
        safe_min_distance,
        _safe_float(flash_neighbor_window_seconds, DEFAULT_FLASH_NEIGHBOR_WINDOW_SECONDS),
    )
    safe_timeout = max(1.0, _safe_float(timeout_seconds, 120.0))

    if input_path is None:
        return _make_failed_result(
            input_path="",
            error="missing_input_path",
            threshold=safe_scene_threshold,
            metadata=safe_metadata,
        )

    try:
        path = Path(input_path)
    except TypeError:
        return _make_failed_result(
            input_path=str(input_path),
            error="invalid_input_path",
            threshold=safe_scene_threshold,
            metadata=safe_metadata,
        )

    input_str = str(path)

    if not path.exists():
        return _make_failed_result(
            input_path=input_str,
            error="input_file_missing",
            threshold=safe_scene_threshold,
            metadata=safe_metadata,
        )

    if not path.is_file():
        return _make_failed_result(
            input_path=input_str,
            error="input_path_not_a_file",
            threshold=safe_scene_threshold,
            metadata=safe_metadata,
        )

    if not _is_probable_video_path(path):
        return SceneChangeResult(
            status=SCENE_STATUS_SKIPPED_NO_VIDEO_SOURCE,
            input_path=input_str,
            scene_changes=[],
            scene_change_count=0,
            hard_change_count=0,
            soft_transition_count=0,
            false_positive_candidate_count=0,
            threshold=safe_scene_threshold,
            duration_seconds=None,
            recommendation="no_video_source",
            warnings=["unsupported_video_extension"],
            errors=[],
            metadata=safe_metadata,
        )

    if ffmpeg_path_override:
        ffmpeg_path = str(ffmpeg_path_override)
        if not Path(ffmpeg_path).exists():
            return _make_failed_result(
                input_path=input_str,
                error="ffmpeg_unavailable",
                threshold=safe_scene_threshold,
                metadata={**safe_metadata, "ffmpeg_path_override": ffmpeg_path},
            )
    else:
        try:
            ffmpeg_path = get_ffmpeg_path()
        except FileNotFoundError as exc:
            return _make_failed_result(
                input_path=input_str,
                error="ffmpeg_unavailable",
                threshold=safe_scene_threshold,
                metadata={**safe_metadata, "error_detail": str(exc)},
            )

    try:
        return_code, stdout_text, stderr_text = _run_ffmpeg_scene_detection(
            ffmpeg_path=ffmpeg_path,
            input_path=path,
            soft_threshold=safe_soft_threshold,
            timeout_seconds=safe_timeout,
        )
    except FileNotFoundError as exc:
        return _make_failed_result(
            input_path=input_str,
            error="ffmpeg_unavailable",
            threshold=safe_scene_threshold,
            metadata={**safe_metadata, "error_detail": str(exc)},
        )
    except subprocess.TimeoutExpired:
        return _make_failed_result(
            input_path=input_str,
            error="ffmpeg_timeout",
            threshold=safe_scene_threshold,
            metadata={**safe_metadata, "timeout_seconds": safe_timeout},
        )
    except OSError as exc:
        return _make_failed_result(
            input_path=input_str,
            error="ffmpeg_invocation_failed",
            threshold=safe_scene_threshold,
            metadata={**safe_metadata, "error_detail": str(exc)},
        )

    combined_text = (stderr_text or "") + "\n" + (stdout_text or "")
    duration_seconds = parse_ffmpeg_duration_seconds(combined_text)
    raw_points = parse_ffmpeg_scene_output(combined_text)

    if return_code != 0 and not raw_points:
        return _make_failed_result(
            input_path=input_str,
            error="ffmpeg_returned_non_zero",
            threshold=safe_scene_threshold,
            metadata={
                **safe_metadata,
                "return_code": return_code,
                "stderr_tail": (stderr_text or "")[-2000:],
            },
        )

    points = _build_points(
        raw_points,
        scene_threshold=safe_scene_threshold,
        soft_threshold=safe_soft_threshold,
    )
    points = filter_or_mark_near_duplicates(
        points,
        min_distance_seconds=safe_min_distance,
        flash_neighbor_window_seconds=safe_flash_window,
        flash_threshold=safe_flash_threshold,
    )

    (
        scene_change_count,
        hard_change_count,
        soft_transition_count,
        false_positive_candidate_count,
    ) = _summarize_counts(points)

    warnings: list[str] = []
    errors: list[str] = []

    if return_code != 0:
        warnings.append("ffmpeg_returned_non_zero_with_results")

    if scene_change_count == 0:
        warnings.append("no_scene_changes_detected")

    if scene_change_count > 0 and false_positive_candidate_count > 0:
        warnings.append("contains_false_positive_candidates")

    status = SCENE_STATUS_OK
    if warnings:
        status = SCENE_STATUS_COMPLETED_WITH_WARNINGS

    recommendation = _build_recommendation(
        scene_change_count=scene_change_count,
        hard_change_count=hard_change_count,
        soft_transition_count=soft_transition_count,
        false_positive_candidate_count=false_positive_candidate_count,
        duration_seconds=duration_seconds,
    )

    result_metadata = dict(safe_metadata)
    result_metadata.update(
        {
            "ffmpeg_return_code": return_code,
            "raw_point_count": len(raw_points),
            "soft_threshold": safe_soft_threshold,
            "flash_threshold": safe_flash_threshold,
            "min_distance_seconds": safe_min_distance,
            "flash_neighbor_window_seconds": safe_flash_window,
        }
    )

    return SceneChangeResult(
        status=status,
        input_path=input_str,
        scene_changes=points,
        scene_change_count=scene_change_count,
        hard_change_count=hard_change_count,
        soft_transition_count=soft_transition_count,
        false_positive_candidate_count=false_positive_candidate_count,
        threshold=safe_scene_threshold,
        duration_seconds=duration_seconds,
        recommendation=recommendation,
        warnings=warnings,
        errors=errors,
        metadata=result_metadata,
    )
