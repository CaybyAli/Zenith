from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from core.sentence_boundary_runner import (
    apply_sentence_boundary_run_report_to_job,
    run_sentence_boundary_for_job,
)
from models.job import Job
from models.sentence_boundary_run import SentenceBoundaryRunReport
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _make_job() -> Job:
    return Job(
        job_id="sentence_boundary_job",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="video.mp4",
    )


def test_run_report_roundtrip() -> None:
    report = SentenceBoundaryRunReport(
        status="ok",
        transcript_source="preprocessed_audio",
        boundaries=[{"boundary_id": "b1"}],
        protection_zones=[{"zone_id": "z1"}],
        boundary_count=1,
        protection_zone_count=1,
        recommendation="use_sentence_boundary_protection",
        metadata={"stage": "test"},
    )

    restored = SentenceBoundaryRunReport.from_dict(report.to_dict())

    assert restored.status == "ok"
    assert restored.transcript_source == "preprocessed_audio"
    assert restored.boundaries == [{"boundary_id": "b1"}]
    assert restored.protection_zones == [{"zone_id": "z1"}]


def test_run_sentence_boundary_for_job_uses_job_transcript_segments() -> None:
    job = _make_job()
    job.transcript_source_type = "preprocessed_audio"
    job.transcript_segments = [
        {"start_seconds": 0.0, "end_seconds": 1.0, "text": "This is complete."}
    ]

    report = run_sentence_boundary_for_job(job)

    assert report.status == "ok"
    assert report.transcript_source == "preprocessed_audio"
    assert report.boundary_count == 1
    assert report.safe_boundary_count == 1


def test_run_sentence_boundary_skips_without_transcript() -> None:
    job = _make_job()

    report = run_sentence_boundary_for_job(job)

    assert report.status == "skipped_no_transcript_segments"
    assert report.recommendation == "sentence_boundary_skipped_no_transcript"
    assert report.boundary_count == 0


def test_apply_sentence_boundary_report_writes_job_fields() -> None:
    job = _make_job()
    report = SentenceBoundaryRunReport(
        status="ok",
        boundaries=[{"boundary_id": "b1"}],
        protection_zones=[{"zone_id": "z1"}],
        boundary_count=1,
        protection_zone_count=1,
        complete_sentence_count=1,
        safe_boundary_count=1,
        recommendation="use_sentence_boundary_protection",
    )

    apply_sentence_boundary_run_report_to_job(job, report)

    assert job.sentence_boundary_report == report.to_dict()
    assert job.sentence_boundary_status == "ok"
    assert job.sentence_boundary_boundaries == [{"boundary_id": "b1"}]
    assert job.sentence_boundary_protection_zones == [{"zone_id": "z1"}]
    assert job.sentence_boundary_boundary_count == 1
    assert job.sentence_boundary_recommendation == "use_sentence_boundary_protection"


def test_old_jobs_load_with_sentence_boundary_defaults() -> None:
    old_data = {
        "job_id": "legacy_sentence_boundary",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }

    job = Job.from_dict(old_data)

    assert job.sentence_boundary_report == {}
    assert job.sentence_boundary_status is None
    assert job.sentence_boundary_boundaries == []
    assert job.sentence_boundary_protection_zones == []
    assert job.sentence_boundary_boundary_count == 0
    assert job.sentence_boundary_recommendation is None


def test_job_to_dict_contains_sentence_boundary_fields() -> None:
    job = _make_job()
    data = job.to_dict()

    required_fields = {
        "sentence_boundary_report",
        "sentence_boundary_status",
        "sentence_boundary_boundaries",
        "sentence_boundary_protection_zones",
        "sentence_boundary_boundary_count",
        "sentence_boundary_protection_zone_count",
        "sentence_boundary_complete_sentence_count",
        "sentence_boundary_open_fragment_count",
        "sentence_boundary_question_count",
        "sentence_boundary_open_question_count",
        "sentence_boundary_safe_boundary_count",
        "sentence_boundary_unsafe_boundary_count",
        "sentence_boundary_recommendation",
    }

    assert required_fields.issubset(data.keys())
    assert required_fields.issubset({field.name for field in fields(Job)})


def test_question_and_open_sentence_create_protection_zones() -> None:
    job = _make_job()
    job.transcript_segments = [
        {"start_seconds": 0.0, "end_seconds": 1.0, "text": "Why did that happen?"},
        {"start_seconds": 1.2, "end_seconds": 2.0, "text": "because we"},
    ]

    report = run_sentence_boundary_for_job(job)

    assert report.protection_zone_count >= 2
    zone_types = {zone["zone_type"] for zone in report.protection_zones}
    assert "protect_question_context" in zone_types
    assert "protect_open_fragment" in zone_types


def test_runner_does_not_crash_on_invalid_segments() -> None:
    job = _make_job()
    job.transcript_segments = [{"start_seconds": -1.0, "end_seconds": 0.0, "text": ""}]

    report = run_sentence_boundary_for_job(job)

    assert report.status in {"completed_with_warnings", "failed"}
    assert isinstance(report.to_dict(), dict)


def test_sentence_boundary_runner_files_have_no_bom() -> None:
    for relative_path in [
        "models/sentence_boundary_run.py",
        "core/sentence_boundary_runner.py",
        "models/job.py",
        "tests/test_sentence_boundary_runner_smoke.py",
    ]:
        assert not _path(relative_path).read_bytes().startswith(b"\xef\xbb\xbf")


def test_sentence_boundary_runner_files_end_with_newline() -> None:
    for relative_path in [
        "models/sentence_boundary_run.py",
        "core/sentence_boundary_runner.py",
        "models/job.py",
        "tests/test_sentence_boundary_runner_smoke.py",
    ]:
        assert _path(relative_path).read_bytes().endswith(b"\n")
