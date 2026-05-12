from __future__ import annotations

from pathlib import Path

import pytest

from core.screen_content_classifier import (
    analyze_screen_content_from_frames,
    build_screen_content_segments,
    classify_screen_content,
    classify_screen_frame,
)
from models.screen_content_classification import (
    SCREEN_TYPE_BLACK_SCREEN,
    SCREEN_TYPE_DEATH_SCREEN,
    SCREEN_TYPE_GAMEPLAY,
    SCREEN_TYPE_LOADING,
    SCREEN_TYPE_LOBBY,
    SCREEN_TYPE_MENU,
    SCREEN_TYPE_SCOREBOARD,
    SCREEN_TYPE_VICTORY_SCREEN,
    ScreenContentClassificationResult,
    ScreenContentPoint,
    ScreenContentSegment,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _point(screen_type: str, time_seconds: float) -> ScreenContentPoint:
    return ScreenContentPoint(
        time_seconds=time_seconds,
        frame_index=int(time_seconds * 2),
        screen_type=screen_type,
        confidence=0.8,
        brightness_score=0.4,
        saturation_score=0.4,
        edge_density_score=0.2,
        motion_context_score=0.1,
        text_like_region_score=0.1,
        ui_density_score=0.1,
        is_review_candidate=screen_type != SCREEN_TYPE_GAMEPLAY,
    )


def _solid_frame(value: int):
    np = pytest.importorskip("numpy")
    return np.full((180, 320, 3), value, dtype=np.uint8)


def _gameplay_like_frame():
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    frame = np.zeros((180, 320, 3), dtype=np.uint8)
    frame[:, :] = (40, 120, 35)
    cv2.circle(frame, (80, 80), 30, (30, 210, 80), -1)
    cv2.rectangle(frame, (190, 50), (270, 130), (180, 60, 40), -1)
    cv2.line(frame, (0, 160), (319, 20), (250, 250, 40), 3)
    return frame


def test_screen_content_point_roundtrip():
    point = _point(SCREEN_TYPE_GAMEPLAY, 1.0)

    restored = ScreenContentPoint.from_dict(point.to_dict())

    assert restored.to_dict() == point.to_dict()


def test_screen_content_segment_roundtrip():
    segment = ScreenContentSegment(
        start_seconds=1.0,
        end_seconds=3.0,
        duration_seconds=2.0,
        screen_type=SCREEN_TYPE_LOADING,
        avg_confidence=0.75,
        max_confidence=0.90,
        point_count=4,
        recommendation="review_possible_trim_loading",
        metadata={"source": "unit_test"},
    )

    restored = ScreenContentSegment.from_dict(segment.to_dict())

    assert restored.to_dict() == segment.to_dict()


def test_screen_content_classification_result_roundtrip():
    point = _point(SCREEN_TYPE_BLACK_SCREEN, 0.0)
    segment = ScreenContentSegment(
        start_seconds=0.0,
        end_seconds=1.0,
        duration_seconds=1.0,
        screen_type=SCREEN_TYPE_BLACK_SCREEN,
        avg_confidence=0.9,
        max_confidence=0.9,
        point_count=2,
        recommendation="review_possible_trim_black_screen",
    )
    result = ScreenContentClassificationResult(
        status="ok",
        input_path="video.mp4",
        points=[point],
        segments=[segment],
        point_count=1,
        segment_count=1,
        gameplay_segment_count=0,
        menu_segment_count=0,
        loading_segment_count=0,
        scoreboard_segment_count=0,
        death_screen_segment_count=0,
        victory_screen_segment_count=0,
        black_screen_segment_count=1,
        duration_seconds=1.0,
        frame_sample_rate=2.0,
        recommendation="review_possible_trim_black_screen",
        metadata={"source": "unit_test"},
    )

    restored = ScreenContentClassificationResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_classify_screen_frame_black_screen():
    frame = _solid_frame(0)

    point = classify_screen_frame(frame)

    assert point.screen_type == SCREEN_TYPE_BLACK_SCREEN
    assert point.confidence >= 0.8


def test_classify_screen_frame_gameplay():
    frame = _gameplay_like_frame()

    point = classify_screen_frame(frame)

    assert point.screen_type == SCREEN_TYPE_GAMEPLAY
    assert point.confidence >= 0.5


def test_classify_screen_frame_menu_and_lobby_template_hints():
    frame = _solid_frame(90)

    menu_point = classify_screen_frame(frame, metadata={"template_hint": "menu"})
    lobby_point = classify_screen_frame(frame, metadata={"template_hint": "lobby"})

    assert menu_point.screen_type == SCREEN_TYPE_MENU
    assert lobby_point.screen_type == SCREEN_TYPE_LOBBY
    assert menu_point.is_review_candidate
    assert lobby_point.is_review_candidate


def test_classify_screen_frame_scoreboard_template_hint():
    frame = _solid_frame(120)

    point = classify_screen_frame(frame, metadata={"template_hint": "scoreboard"})

    assert point.screen_type == SCREEN_TYPE_SCOREBOARD
    assert point.confidence >= 0.9


def test_classify_screen_frame_victory_and_death_template_hints():
    frame = _solid_frame(110)

    victory_point = classify_screen_frame(
        frame,
        metadata={"template_hint": "victory_screen"},
    )
    death_point = classify_screen_frame(
        frame,
        metadata={"template_hint": "death_screen"},
    )

    assert victory_point.screen_type == SCREEN_TYPE_VICTORY_SCREEN
    assert death_point.screen_type == SCREEN_TYPE_DEATH_SCREEN
    assert victory_point.confidence >= 0.9
    assert death_point.confidence >= 0.9


def test_build_screen_content_segments_groups_same_screen_type_ranges():
    points = [
        _point(SCREEN_TYPE_GAMEPLAY, 0.0),
        _point(SCREEN_TYPE_GAMEPLAY, 0.5),
        _point(SCREEN_TYPE_LOADING, 1.0),
        _point(SCREEN_TYPE_LOADING, 1.5),
        _point(SCREEN_TYPE_GAMEPLAY, 2.0),
    ]

    segments = build_screen_content_segments(points, frame_sample_rate=2.0)

    assert [segment.screen_type for segment in segments] == [
        SCREEN_TYPE_GAMEPLAY,
        SCREEN_TYPE_LOADING,
        SCREEN_TYPE_GAMEPLAY,
    ]
    assert segments[1].point_count == 2
    assert segments[1].recommendation == "review_possible_trim_loading"


def test_missing_input_file_does_not_crash(tmp_path):
    missing_file = tmp_path / "missing_video.mp4"

    result = classify_screen_content(str(missing_file))

    assert result.status == "skipped_no_video_source"
    assert result.point_count == 0
    assert result.segment_count == 0
    assert result.warnings


def test_invalid_video_does_not_crash(tmp_path):
    invalid_video = tmp_path / "invalid_video.mp4"
    invalid_video.write_text("not a video", encoding="utf-8")

    result = classify_screen_content(str(invalid_video))

    assert result.status == "failed"
    assert result.point_count == 0
    assert result.segment_count == 0
    assert result.errors


def test_analyze_screen_content_from_frames_groups_synthetic_frames():
    frames = [_solid_frame(0), _gameplay_like_frame(), _gameplay_like_frame()]

    result = analyze_screen_content_from_frames(frames, frame_sample_rate=2.0)

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.point_count == 3
    assert result.segment_count >= 2
    assert result.black_screen_segment_count >= 1
    assert result.gameplay_segment_count >= 1


def test_real_mini_video_screen_content_if_opencv_available(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    video_path = tmp_path / "mini_screen_content_test.avi"
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(video_path), fourcc, 10.0, (64, 64))

    if not writer.isOpened():
        pytest.skip("opencv_video_writer_unavailable")

    try:
        for _ in range(8):
            writer.write(np.zeros((64, 64, 3), dtype=np.uint8))
        for index in range(12):
            frame = np.zeros((64, 64, 3), dtype=np.uint8)
            frame[:, :] = (30, 120, 40)
            cv2.circle(frame, (16 + index, 32), 10, (40, 220, 90), -1)
            writer.write(frame)
    finally:
        writer.release()

    result = classify_screen_content(
        str(video_path),
        frame_sample_rate=2.0,
        resize_width=64,
        resize_height=64,
    )

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.point_count > 0
    assert result.segment_count > 0


def test_new_screen_content_foundation_files_do_not_have_bom():
    files = [
        REPO_ROOT / "models" / "screen_content_classification.py",
        REPO_ROOT / "core" / "screen_content_classifier.py",
        REPO_ROOT / "tests" / "test_screen_content_classification_foundation_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_new_screen_content_foundation_files_end_with_newline():
    files = [
        REPO_ROOT / "models" / "screen_content_classification.py",
        REPO_ROOT / "core" / "screen_content_classifier.py",
        REPO_ROOT / "tests" / "test_screen_content_classification_foundation_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
