from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.visual_energy_runner import (
    apply_visual_energy_run_report_to_job,
    run_visual_energy_for_job,
)
from models.job import Job
from models.visual_energy import (
    CLASSIFICATION_HIGH_VISUAL_ENERGY,
    STATUS_OK,
    STATUS_SKIPPED_NO_VISUAL_SOURCES,
    VisualEnergyPoint,
    VisualEnergyResult,
    VisualEnergySegment,
)
from models.visual_energy_run import VisualEnergyRunReport


REPO_ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = [
    REPO_ROOT / "models" / "visual_energy_run.py",
    REPO_ROOT / "core" / "visual_energy_runner.py",
    REPO_ROOT / "models" / "job.py",
    REPO_ROOT / "tests" / "test_visual_energy_runner_smoke.py",
]


def _fake_visual_energy_result() -> VisualEnergyResult:
    point = VisualEnergyPoint(
        time_seconds=1.0,
        visual_energy_score=0.72,
        motion_score=0.9,
        face_reaction_score=0.8,
        screen_content_score=0.65,
        scene_change_score=0.2,
        stutter_penalty_score=0.0,
        combined_video_score=0.72,
        classification=CLASSIFICATION_HIGH_VISUAL_ENERGY,
        confidence=0.8,
    )

    segment = VisualEnergySegment(
        start_seconds=1.0,
        end_seconds=2.0,
        duration_seconds=1.0,
        avg_visual_energy_score=0.72,
        max_visual_energy_score=0.72,
        min_visual_energy_score=0.72,
        classification=CLASSIFICATION_HIGH_VISUAL_ENERGY,
        recommendation="review_visual_engagement_candidate",
    )

    return VisualEnergyResult(
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
        metadata={"fake": True},
    )


def test_visual_energy_run_report_roundtrip() -> None:
    result = _fake_visual_energy_result()

    report = VisualEnergyRunReport(
        status=STATUS_OK,
        source="visual_energy_runner",
        visual_energy_result=result,
        visual_energy_points=[point.to_dict() for point in result.points],
        visual_energy_segments=[segment.to_dict() for segment in result.segments],
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
        metadata={"unit": "test"},
    )

    restored = VisualEnergyRunReport.from_dict(report.to_dict())

    assert restored.to_dict() == report.to_dict()


def test_runner_uses_job_visual_sources() -> None:
    job = SimpleNamespace(
        motion_analysis_report={
            "motion_points": [
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
                    "start_seconds": 0.5,
                    "end_seconds": 1.5,
                    "reaction_score": 0.9,
                }
            ]
        },
        screen_content_report={
            "screen_content_points": [
                {
                    "time_seconds": 1.0,
                    "screen_type": "gameplay",
                    "confidence": 1.0,
                }
            ],
            "point_count": 1,
        },
        scene_change_report={},
        stutter_detection_report={},
    )

    report = run_visual_energy_for_job(job)

    assert report.status == STATUS_OK
    assert report.point_count >= 1
    assert report.segment_count >= 1
    assert report.high_energy_segment_count >= 1
    assert report.visual_energy_points
    assert report.visual_energy_segments
    assert report.recommendation == "review_visual_energy_candidates"


def test_missing_sources_are_safe() -> None:
    job = SimpleNamespace(
        motion_analysis_report={},
        face_reaction_report={},
        screen_content_report={},
        scene_change_report={},
        stutter_detection_report={},
    )

    report = run_visual_energy_for_job(job)

    assert report.status == STATUS_SKIPPED_NO_VISUAL_SOURCES
    assert report.point_count == 0
    assert report.segment_count == 0
    assert report.visual_energy_points == []
    assert report.visual_energy_segments == []
    assert report.warnings


def test_apply_visual_energy_run_report_to_job_writes_fields() -> None:
    job = SimpleNamespace()
    result = _fake_visual_energy_result()

    report = VisualEnergyRunReport(
        status=STATUS_OK,
        source="visual_energy_runner",
        visual_energy_result=result,
        visual_energy_points=[point.to_dict() for point in result.points],
        visual_energy_segments=[segment.to_dict() for segment in result.segments],
        point_count=1,
        segment_count=1,
        high_energy_segment_count=1,
        low_energy_segment_count=0,
        technical_warning_segment_count=0,
        duration_seconds=2.0,
        frame_sample_rate=2.0,
        recommendation="review_visual_energy_candidates",
    )

    updated_job = apply_visual_energy_run_report_to_job(job, report)

    assert updated_job.visual_energy_report
    assert updated_job.visual_energy_status == STATUS_OK
    assert updated_job.visual_energy_result
    assert updated_job.visual_energy_points
    assert updated_job.visual_energy_segments
    assert updated_job.visual_energy_point_count == 1
    assert updated_job.visual_energy_segment_count == 1
    assert updated_job.visual_energy_high_segment_count == 1
    assert updated_job.visual_energy_low_segment_count == 0
    assert updated_job.visual_energy_technical_warning_segment_count == 0
    assert updated_job.visual_energy_duration_seconds == 2.0
    assert updated_job.visual_energy_frame_sample_rate == 2.0
    assert updated_job.visual_energy_recommendation == "review_visual_energy_candidates"


def test_old_jobs_without_visual_energy_fields_are_still_loadable() -> None:
    old_job_data = {
        "job_id": "old_job_without_visual_energy",
        "job_type": "gaming",
        "channel_type": "gaming_main",
    }

    job = Job.from_dict(old_job_data)

    assert job.visual_energy_report == {}
    assert job.visual_energy_status is None
    assert job.visual_energy_result == {}
    assert job.visual_energy_points == []
    assert job.visual_energy_segments == []
    assert job.visual_energy_point_count == 0
    assert job.visual_energy_segment_count == 0
    assert job.visual_energy_high_segment_count == 0
    assert job.visual_energy_low_segment_count == 0
    assert job.visual_energy_technical_warning_segment_count == 0
    assert job.visual_energy_duration_seconds is None
    assert job.visual_energy_frame_sample_rate == 2.0
    assert job.visual_energy_recommendation is None


def test_job_to_dict_contains_visual_energy_fields() -> None:
    job = Job.from_dict(
        {
            "job_id": "visual_energy_to_dict_job",
            "job_type": "gaming",
            "channel_type": "gaming_main",
        }
    )

    data = job.to_dict()

    required_fields = [
        "visual_energy_report",
        "visual_energy_status",
        "visual_energy_result",
        "visual_energy_points",
        "visual_energy_segments",
        "visual_energy_point_count",
        "visual_energy_segment_count",
        "visual_energy_high_segment_count",
        "visual_energy_low_segment_count",
        "visual_energy_technical_warning_segment_count",
        "visual_energy_duration_seconds",
        "visual_energy_frame_sample_rate",
        "visual_energy_recommendation",
    ]

    for field_name in required_fields:
        assert field_name in data


def test_new_visual_energy_runner_files_do_not_have_bom() -> None:
    for file_path in NEW_FILES:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_new_visual_energy_runner_files_end_with_newline() -> None:
    for file_path in NEW_FILES:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
