from __future__ import annotations

from pathlib import Path

from core.unified_edit_signal_registry import (
    SOURCE_SCENE_CHANGE,
    build_unified_edit_signal_result,
)
from models.job import Job
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


REGISTRY_PATH = Path("core/unified_edit_signal_registry.py")
ADAPTER_PATH = Path("core/scene_change_signal_adapter.py")
TEST_PATH = Path("tests/test_scene_change_registry_integration_smoke.py")


def _make_job() -> Job:
    return Job(
        job_id="job_scene_change_registry_001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="input.mp4",
    )


def _scene_change_report() -> dict:
    return {
        "status": "ok",
        "scene_changes": [
            {
                "time_seconds": 10.0,
                "frame_index": 100,
                "scene_score": 0.91,
                "change_type": "hard_scene_change",
                "confidence": 0.94,
                "is_false_positive_candidate": False,
            },
            {
                "time_seconds": 20.0,
                "frame_index": 200,
                "scene_score": 0.42,
                "change_type": "soft_transition",
                "confidence": 0.66,
                "is_false_positive_candidate": False,
            },
            {
                "time_seconds": 30.0,
                "frame_index": 300,
                "scene_score": 0.98,
                "change_type": "flash_or_explosion_candidate",
                "confidence": 0.80,
                "is_false_positive_candidate": True,
                "warnings": ["flash_or_explosion_candidate"],
            },
        ],
    }


def test_registry_collects_scene_hard_cut_point_from_report() -> None:
    job = _make_job()
    job.scene_change_report = _scene_change_report()

    result = build_unified_edit_signal_result(job=job)

    assert result.signal_count >= 1
    assert SOURCE_SCENE_CHANGE in result.source_counts
    assert result.source_counts[SOURCE_SCENE_CHANGE] == 3
    assert result.type_counts["scene_hard_cut_point"] == 1
    assert any(
        signal["source"] == SOURCE_SCENE_CHANGE
        and signal["signal_type"] == "scene_hard_cut_point"
        for signal in result.signals
    )


def test_registry_collects_scene_soft_transition() -> None:
    job = _make_job()
    job.scene_change_report = _scene_change_report()

    result = build_unified_edit_signal_result(job=job)

    assert result.type_counts["scene_soft_transition"] == 1
    assert any(
        signal["source"] == SOURCE_SCENE_CHANGE
        and signal["signal_type"] == "scene_soft_transition"
        for signal in result.signals
    )


def test_registry_collects_flash_review_signal_safely() -> None:
    job = _make_job()
    job.scene_change_report = _scene_change_report()

    result = build_unified_edit_signal_result(job=job)

    assert result.type_counts["scene_flash_or_explosion_candidate"] == 1

    flash_signal = next(
        signal
        for signal in result.signals
        if signal["signal_type"] == "scene_flash_or_explosion_candidate"
    )

    assert flash_signal["source"] == SOURCE_SCENE_CHANGE
    assert flash_signal["action_hint"] == "review_false_positive_scene_change"
    assert flash_signal["action_hint"] != "candidate_cut_boundary"


def test_registry_falls_back_to_job_scene_changes() -> None:
    job = _make_job()
    job.scene_changes = _scene_change_report()["scene_changes"]

    result = build_unified_edit_signal_result(job=job)

    assert SOURCE_SCENE_CHANGE in result.source_counts
    assert result.source_counts[SOURCE_SCENE_CHANGE] == 3
    assert result.type_counts["scene_hard_cut_point"] == 1


def test_empty_scene_change_report_does_not_crash() -> None:
    job = _make_job()
    job.scene_change_report = {"scene_changes": []}

    result = build_unified_edit_signal_result(job=job)

    assert SOURCE_SCENE_CHANGE not in result.source_counts
    assert result.status in {"skipped_no_signals", "ok", "completed_with_warnings"}
    assert f"no_signals_from_{SOURCE_SCENE_CHANGE}" in result.warnings


def test_registry_remains_compatible_with_other_sources() -> None:
    job = _make_job()
    job.scene_change_report = _scene_change_report()
    job.silence_classifications = [
        {
            "start_seconds": 40.0,
            "end_seconds": 41.0,
            "duration_seconds": 1.0,
            "classification": "silence_remove",
            "remove_candidate": True,
            "confidence": 0.8,
            "reason": "long_silence",
        }
    ]

    result = build_unified_edit_signal_result(job=job)

    assert SOURCE_SCENE_CHANGE in result.source_counts
    assert "silence_classification" in result.source_counts
    assert result.type_counts["scene_hard_cut_point"] == 1
    assert result.type_counts["silence_remove_candidate"] == 1


def test_scene_change_registry_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        REGISTRY_PATH,
        ADAPTER_PATH,
        TEST_PATH,
    ]

    for path in paths:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"
