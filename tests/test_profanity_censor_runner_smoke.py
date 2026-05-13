from __future__ import annotations

from pathlib import Path

from core.profanity_censor_runner import (
    apply_profanity_censor_run_report_to_job,
    run_profanity_censor_for_job,
)
from models.job import Job
from models.profanity_censor_run import ProfanityCensorRunReport
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


def _make_job() -> Job:
    return Job(
        job_id="job_profanity_censor_001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
    )


def test_run_report_roundtrip() -> None:
    report = ProfanityCensorRunReport(
        status="ok",
        matches=[{"match_id": "m1"}],
        segment_results=[{"segment_id": "s1"}],
        match_count=1,
        severe_match_count=1,
        censor_required_count=1,
        recommendation="review_censor_sfx_overlay_candidates",
    )

    restored = ProfanityCensorRunReport.from_dict(report.to_dict())

    assert restored.to_dict() == report.to_dict()


def test_runner_uses_job_transcript_segments() -> None:
    job = _make_job()
    job.transcript_segments = [
        {
            "start_seconds": 1.0,
            "end_seconds": 2.0,
            "text": "SEVERE_TOKEN",
        }
    ]

    report = run_profanity_censor_for_job(job)

    assert report.match_count == 1
    assert report.severe_match_count == 1


def test_runner_skips_without_transcript() -> None:
    report = run_profanity_censor_for_job(_make_job())

    assert report.status == "skipped_no_transcript_segments"
    assert report.recommendation == "profanity_censor_skipped_no_transcript"


def test_apply_report_writes_job_fields() -> None:
    job = _make_job()
    report = ProfanityCensorRunReport(
        status="ok",
        matches=[{"match_id": "m1"}],
        segment_results=[{"segment_id": "s1"}],
        match_count=1,
        severe_match_count=1,
        censor_required_count=1,
        word_level_match_count=1,
        recommendation="review_censor_sfx_overlay_candidates",
    )

    apply_profanity_censor_run_report_to_job(job, report)

    assert job.profanity_censor_status == "ok"
    assert job.profanity_censor_match_count == 1
    assert job.profanity_censor_severe_match_count == 1
    assert job.profanity_censor_required_count == 1
    assert job.profanity_censor_word_level_match_count == 1
    assert job.profanity_censor_recommendation == "review_censor_sfx_overlay_candidates"


def test_old_jobs_load_without_profanity_censor_fields() -> None:
    legacy = {
        "job_id": "legacy_profanity_censor",
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

    restored = Job.from_dict(legacy)

    assert restored.profanity_censor_report == {}
    assert restored.profanity_censor_matches == []
    assert restored.profanity_censor_match_count == 0
    assert restored.profanity_censor_recommendation is None


def test_job_to_dict_contains_profanity_censor_fields() -> None:
    data = _make_job().to_dict()

    assert "profanity_censor_report" in data
    assert "profanity_censor_matches" in data
    assert "profanity_censor_recommendation" in data


def test_mild_stays_without_censor_required() -> None:
    job = _make_job()
    job.transcript_segments = [
        {"start_seconds": 1.0, "end_seconds": 2.0, "text": "damn"}
    ]

    report = run_profanity_censor_for_job(job)

    assert report.mild_match_count == 1
    assert report.censor_required_count == 0


def test_severe_creates_censor_required() -> None:
    job = _make_job()
    job.transcript_segments = [
        {"start_seconds": 1.0, "end_seconds": 2.0, "text": "SEVERE_TOKEN"}
    ]

    report = run_profanity_censor_for_job(job)

    assert report.severe_match_count == 1
    assert report.censor_required_count == 1


def test_invalid_segments_do_not_crash_runner() -> None:
    job = _make_job()
    job.transcript_segments = [None, "bad", {"text": ""}]

    report = run_profanity_censor_for_job(job)

    assert report.status in {"completed_with_warnings", "failed"}
    assert isinstance(report.errors, list)


def test_profanity_censor_runner_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "models/profanity_censor_run.py",
        "core/profanity_censor_runner.py",
        "models/job.py",
        "tests/test_profanity_censor_runner_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
