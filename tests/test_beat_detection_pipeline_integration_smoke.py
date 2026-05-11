from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from models.job import Job
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    PipelineType,
    TargetFormat,
    ValidatorStatus,
)


def _job_payload() -> dict:
    return {
        "job_id": "job_beat_pipeline_test",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "longform",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
        "pipeline_type": "gaming_pipeline",
        "raw_video_path": "input/demo.mp4",
    }


def _job_object() -> Job:
    return Job(
        job_id="job_beat_pipeline_test",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        pipeline_type=PipelineType.GAMING,
        raw_video_path="input/demo.mp4",
    )


def _gaming_pipeline_source() -> str:
    return Path("core/gaming_pipeline.py").read_text(encoding="utf-8")


def test_job_roundtrip_keeps_all_beat_detection_fields() -> None:
    payload = _job_payload()
    payload.update(
        {
            "beat_detection_report": {"status": "ok"},
            "beat_detection_status": "ok",
            "beat_detection_selected_path": "preprocessed/music.wav",
            "beat_detection_selected_type": "music_reference_audio",
            "beat_detection_source_selection": {"selected_type": "music_reference_audio"},
            "beat_detection_result": {"status": "ok"},
            "beat_detection_beats": [{"time_seconds": 0.5, "strength": 0.9}],
            "beat_detection_beat_count": 1,
            "beat_detection_estimated_bpm": 120.0,
            "beat_detection_average_beat_interval_seconds": 0.5,
            "beat_detection_duration_seconds": 2.0,
            "beat_detection_sample_rate": 1000,
            "beat_detection_channels": 1,
            "beat_detection_energy_frame_count": 12,
            "beat_detection_peak_threshold": 1.35,
            "beat_detection_min_beat_distance_seconds": 0.25,
            "beat_detection_max_beat_strength": 0.9,
            "beat_detection_avg_beat_strength": 0.9,
            "beat_detection_top_beat": {"time_seconds": 0.5, "strength": 0.9},
            "beat_detection_recommendation": "use_beat_timeline",
        }
    )

    job = Job.from_dict(payload)
    data = job.to_dict()

    assert data["beat_detection_report"]["status"] == "ok"
    assert data["beat_detection_status"] == "ok"
    assert data["beat_detection_selected_path"] == "preprocessed/music.wav"
    assert data["beat_detection_selected_type"] == "music_reference_audio"
    assert data["beat_detection_source_selection"]["selected_type"] == "music_reference_audio"
    assert data["beat_detection_result"]["status"] == "ok"
    assert data["beat_detection_beats"][0]["time_seconds"] == 0.5
    assert data["beat_detection_beat_count"] == 1
    assert data["beat_detection_estimated_bpm"] == 120.0
    assert data["beat_detection_average_beat_interval_seconds"] == 0.5
    assert data["beat_detection_duration_seconds"] == 2.0
    assert data["beat_detection_sample_rate"] == 1000
    assert data["beat_detection_channels"] == 1
    assert data["beat_detection_energy_frame_count"] == 12
    assert data["beat_detection_peak_threshold"] == 1.35
    assert data["beat_detection_min_beat_distance_seconds"] == 0.25
    assert data["beat_detection_max_beat_strength"] == 0.9
    assert data["beat_detection_avg_beat_strength"] == 0.9
    assert data["beat_detection_top_beat"]["strength"] == 0.9
    assert data["beat_detection_recommendation"] == "use_beat_timeline"


def test_old_jobs_without_beat_detection_fields_do_not_crash() -> None:
    job = Job.from_dict(_job_payload())

    assert job.beat_detection_report == {}
    assert job.beat_detection_status is None
    assert job.beat_detection_selected_path is None
    assert job.beat_detection_selected_type is None
    assert job.beat_detection_source_selection == {}
    assert job.beat_detection_result == {}
    assert job.beat_detection_beats == []
    assert job.beat_detection_beat_count == 0
    assert job.beat_detection_estimated_bpm is None
    assert job.beat_detection_recommendation is None


def test_gaming_pipeline_contains_beat_detection_integration_markers() -> None:
    source = _gaming_pipeline_source()

    assert "from core.beat_detection_runner import run_beat_detection_for_job" in source
    assert "BEAT_DETECTION_STARTED" in source
    assert "BEAT_DETECTION_DONE" in source
    assert "BEAT_DETECTION_COMPLETED_WITH_WARNINGS" in source
    assert "BEAT_DETECTION_BLOCKED" in source
    assert "BEAT_DETECTION_SKIPPED" in source
    assert "BEAT_DETECTION_FAILED" in source
    assert "beat_detection_done" in source


def test_gaming_pipeline_uses_runner_not_low_level_detector_or_selector() -> None:
    source = _gaming_pipeline_source()

    assert "run_beat_detection_for_job(" in source
    assert "analyze_wav_beats(" not in source
    assert "select_beat_detection_source(" not in source


def test_gaming_pipeline_order_is_correct() -> None:
    source = _gaming_pipeline_source()

    assert source.index("PREPROCESSING_READY") < source.index("BEAT_DETECTION_STARTED")
    assert source.index("ENERGY_PEAK_DETECTION_STARTED") < source.index("BEAT_DETECTION_STARTED")
    assert source.index("AUDIO_NORMALIZATION_STARTED") < source.index("BEAT_DETECTION_STARTED")
    assert source.index("BEAT_DETECTION_STARTED") < source.index("STATE_ANALYZING")


def test_gaming_pipeline_contains_job_field_assignments() -> None:
    source = _gaming_pipeline_source()

    required_assignments = [
        "job.beat_detection_report =",
        "job.beat_detection_status =",
        "job.beat_detection_selected_path =",
        "job.beat_detection_selected_type =",
        "job.beat_detection_beat_count =",
        "job.beat_detection_estimated_bpm =",
        "job.beat_detection_recommendation =",
    ]

    for assignment in required_assignments:
        assert assignment in source


def test_pipeline_like_report_sets_values_on_job() -> None:
    from core.gaming_pipeline import _apply_beat_detection_report_to_job

    job = _job_object()
    report = SimpleNamespace(
        status="ok",
        source_selection={"status": "selected"},
        selected_path="preprocessed/music.wav",
        selected_type="music_reference_audio",
        beat_detection_result={"status": "ok"},
        beats=[{"time_seconds": 0.5, "strength": 0.9}],
        beat_count=1,
        estimated_bpm=120.0,
        average_beat_interval_seconds=0.5,
        duration_seconds=2.0,
        sample_rate=1000,
        channels=1,
        energy_frame_count=12,
        peak_threshold=1.35,
        min_beat_distance_seconds=0.25,
        max_beat_strength=0.9,
        avg_beat_strength=0.9,
        top_beat={"time_seconds": 0.5, "strength": 0.9},
        recommendation="use_beat_timeline",
        to_dict=lambda: {"status": "ok", "beat_count": 1},
    )

    _apply_beat_detection_report_to_job(job, report)

    assert job.beat_detection_report == {"status": "ok", "beat_count": 1}
    assert job.beat_detection_status == "ok"
    assert job.beat_detection_selected_path == "preprocessed/music.wav"
    assert job.beat_detection_selected_type == "music_reference_audio"
    assert job.beat_detection_source_selection == {"status": "selected"}
    assert job.beat_detection_result == {"status": "ok"}
    assert job.beat_detection_beats == [{"time_seconds": 0.5, "strength": 0.9}]
    assert job.beat_detection_beat_count == 1
    assert job.beat_detection_estimated_bpm == 120.0
    assert job.beat_detection_recommendation == "use_beat_timeline"


def test_beat_detection_pipeline_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("models/job.py"),
        Path("core/gaming_pipeline.py"),
        Path("tests/test_beat_detection_pipeline_integration_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"
