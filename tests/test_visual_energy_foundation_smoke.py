from __future__ import annotations

from pathlib import Path

from core.visual_energy_calculator import (
    build_visual_energy_segments,
    calculate_visual_energy,
    classify_visual_energy_score,
)
from models.visual_energy import (
    CLASSIFICATION_HIGH_VISUAL_ENERGY,
    CLASSIFICATION_LOW_VISUAL_ENERGY,
    CLASSIFICATION_MEDIUM_VISUAL_ENERGY,
    CLASSIFICATION_PEAK_VISUAL_ENERGY,
    CLASSIFICATION_TECHNICAL_WARNING,
    STATUS_OK,
    STATUS_SKIPPED_NO_VISUAL_SOURCES,
    VisualEnergyPoint,
    VisualEnergyResult,
    VisualEnergySegment,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = [
    PROJECT_ROOT / "models" / "visual_energy.py",
    PROJECT_ROOT / "core" / "visual_energy_calculator.py",
    PROJECT_ROOT / "tests" / "test_visual_energy_foundation_smoke.py",
]


def test_visual_energy_point_roundtrip() -> None:
    point = VisualEnergyPoint(
        time_seconds=1.5,
        visual_energy_score=0.75,
        motion_score=0.8,
        face_reaction_score=0.7,
        screen_content_score=0.65,
        scene_change_score=0.5,
        stutter_penalty_score=0.0,
        combined_video_score=0.75,
        classification=CLASSIFICATION_HIGH_VISUAL_ENERGY,
        confidence=0.9,
        source_counts={"motion_analysis": 1},
        metadata={"source": "smoke"},
        warnings=["warning"],
        errors=[],
    )

    restored = VisualEnergyPoint.from_dict(point.to_dict())

    assert restored.to_dict() == point.to_dict()


def test_visual_energy_segment_roundtrip() -> None:
    segment = VisualEnergySegment(
        start_seconds=1.0,
        end_seconds=3.0,
        duration_seconds=2.0,
        avg_visual_energy_score=0.8,
        max_visual_energy_score=0.9,
        min_visual_energy_score=0.7,
        classification=CLASSIFICATION_HIGH_VISUAL_ENERGY,
        recommendation="review_visual_engagement_candidate",
        metadata={"point_count": 2},
        warnings=[],
        errors=[],
    )

    restored = VisualEnergySegment.from_dict(segment.to_dict())

    assert restored.to_dict() == segment.to_dict()


def test_visual_energy_result_roundtrip() -> None:
    point = VisualEnergyPoint(
        time_seconds=1.0,
        visual_energy_score=0.9,
        classification=CLASSIFICATION_PEAK_VISUAL_ENERGY,
    )
    segment = VisualEnergySegment(
        start_seconds=1.0,
        end_seconds=2.0,
        duration_seconds=1.0,
        avg_visual_energy_score=0.9,
        max_visual_energy_score=0.9,
        min_visual_energy_score=0.9,
        classification=CLASSIFICATION_PEAK_VISUAL_ENERGY,
        recommendation="review_visual_highlight_candidate",
    )

    result = VisualEnergyResult(
        status=STATUS_OK,
        points=[point],
        segments=[segment],
        point_count=1,
        segment_count=1,
        high_energy_segment_count=1,
        low_energy_segment_count=0,
        technical_warning_segment_count=0,
        duration_seconds=2.0,
        frame_sample_rate=2.0,
        recommendation="review_visual_energy_candidates",
        warnings=[],
        errors=[],
        metadata={"source": "smoke"},
    )

    restored = VisualEnergyResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_classify_visual_energy_score_detects_low() -> None:
    assert classify_visual_energy_score(0.1) == CLASSIFICATION_LOW_VISUAL_ENERGY


def test_classify_visual_energy_score_detects_medium() -> None:
    assert classify_visual_energy_score(0.4) == CLASSIFICATION_MEDIUM_VISUAL_ENERGY


def test_classify_visual_energy_score_detects_high() -> None:
    assert classify_visual_energy_score(0.7) == CLASSIFICATION_HIGH_VISUAL_ENERGY


def test_classify_visual_energy_score_detects_peak() -> None:
    assert classify_visual_energy_score(0.9) == CLASSIFICATION_PEAK_VISUAL_ENERGY


def test_stutter_or_freeze_can_create_technical_warning() -> None:
    result = calculate_visual_energy(
        motion_analysis_report={
            "points": [
                {
                    "time_seconds": 1.0,
                    "motion_score": 0.9,
                    "confidence": 0.9,
                }
            ],
            "point_count": 1,
        },
        stutter_detection_report={
            "segments": [
                {
                    "start_seconds": 0.0,
                    "end_seconds": 2.0,
                    "classification": "freeze_segment",
                    "max_duplicate_score": 0.95,
                }
            ],
            "segment_count": 1,
            "freeze_segment_count": 1,
        },
    )

    assert result.technical_warning_segment_count >= 1
    assert any(
        point.classification == CLASSIFICATION_TECHNICAL_WARNING
        for point in result.points
    )


def test_missing_sources_do_not_crash() -> None:
    result = calculate_visual_energy(
        motion_analysis_report={
            "points": [
                {
                    "time_seconds": 1.0,
                    "motion_score": 0.5,
                    "confidence": 0.8,
                }
            ],
            "point_count": 1,
        }
    )

    assert result.status in {STATUS_OK, "completed_with_warnings"}
    assert result.point_count >= 1
    assert result.segment_count >= 1


def test_no_sources_returns_skipped_no_visual_sources() -> None:
    result = calculate_visual_energy()

    assert result.status == STATUS_SKIPPED_NO_VISUAL_SOURCES
    assert result.point_count == 0
    assert result.segment_count == 0
    assert result.recommendation == "skipped_no_visual_sources"


def test_motion_face_gameplay_is_higher_than_loading_or_black() -> None:
    high_result = calculate_visual_energy(
        motion_analysis_report={
            "points": [
                {
                    "time_seconds": 1.0,
                    "motion_score": 1.0,
                    "confidence": 1.0,
                }
            ],
            "point_count": 1,
        },
        face_reaction_report={
            "reaction_windows": [
                {
                    "start_seconds": 0.0,
                    "end_seconds": 2.0,
                    "reaction_score": 1.0,
                }
            ]
        },
        screen_content_report={
            "points": [
                {
                    "time_seconds": 1.0,
                    "screen_type": "gameplay",
                    "confidence": 1.0,
                }
            ],
            "point_count": 1,
        },
    )

    low_result = calculate_visual_energy(
        motion_analysis_report={
            "points": [
                {
                    "time_seconds": 1.0,
                    "motion_score": 0.0,
                    "confidence": 1.0,
                }
            ],
            "point_count": 1,
        },
        screen_content_report={
            "points": [
                {
                    "time_seconds": 1.0,
                    "screen_type": "black_screen",
                    "confidence": 1.0,
                }
            ],
            "point_count": 1,
        },
    )

    assert high_result.points[0].visual_energy_score > low_result.points[0].visual_energy_score


def test_build_visual_energy_segments_groups_same_classes() -> None:
    points = [
        VisualEnergyPoint(
            time_seconds=0.0,
            visual_energy_score=0.1,
            classification=CLASSIFICATION_LOW_VISUAL_ENERGY,
        ),
        VisualEnergyPoint(
            time_seconds=1.0,
            visual_energy_score=0.2,
            classification=CLASSIFICATION_LOW_VISUAL_ENERGY,
        ),
        VisualEnergyPoint(
            time_seconds=2.0,
            visual_energy_score=0.7,
            classification=CLASSIFICATION_HIGH_VISUAL_ENERGY,
        ),
        VisualEnergyPoint(
            time_seconds=3.0,
            visual_energy_score=0.8,
            classification=CLASSIFICATION_HIGH_VISUAL_ENERGY,
        ),
    ]

    segments = build_visual_energy_segments(points)

    assert len(segments) == 2
    assert segments[0].classification == CLASSIFICATION_LOW_VISUAL_ENERGY
    assert segments[1].classification == CLASSIFICATION_HIGH_VISUAL_ENERGY


def test_new_visual_energy_files_have_no_bom() -> None:
    for file_path in NEW_FILES:
        data = file_path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), str(file_path)


def test_new_visual_energy_files_end_with_newline() -> None:
    for file_path in NEW_FILES:
        data = file_path.read_bytes()
        assert data.endswith(b"\n"), str(file_path)
