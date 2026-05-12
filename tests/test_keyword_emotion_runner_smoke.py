from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from core.keyword_emotion_runner import (
    apply_keyword_emotion_run_report_to_job,
    run_keyword_emotion_for_job,
)
from models.job import Job
from models.keyword_emotion_run import KeywordEmotionRunReport
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
        job_id="keyword_emotion_job",
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
    report = KeywordEmotionRunReport(
        status="ok",
        transcript_source="preprocessed_audio",
        matches=[{"match_id": "m1"}],
        segment_scores=[{"segment_id": "s1"}],
        match_count=1,
        segment_score_count=1,
        hype_match_count=1,
        recommendation="use_keyword_emotion_scoring",
        metadata={"stage": "test"},
    )

    restored = KeywordEmotionRunReport.from_dict(report.to_dict())

    assert restored.status == "ok"
    assert restored.transcript_source == "preprocessed_audio"
    assert restored.matches == [{"match_id": "m1"}]
    assert restored.segment_scores == [{"segment_id": "s1"}]


def test_run_keyword_emotion_for_job_uses_job_transcript_segments() -> None:
    job = _make_job()
    job.transcript_source_type = "preprocessed_audio"
    job.transcript_segments = [
        {"start_seconds": 0.0, "end_seconds": 1.0, "text": "That was insane."}
    ]

    report = run_keyword_emotion_for_job(job)

    assert report.status == "ok"
    assert report.transcript_source == "preprocessed_audio"
    assert report.match_count >= 1
    assert report.hype_match_count >= 1


def test_run_keyword_emotion_skips_without_transcript() -> None:
    job = _make_job()

    report = run_keyword_emotion_for_job(job)

    assert report.status == "skipped_no_transcript_segments"
    assert report.recommendation == "keyword_emotion_skipped_no_transcript"
    assert report.match_count == 0


def test_apply_keyword_emotion_report_writes_job_fields() -> None:
    job = _make_job()
    report = KeywordEmotionRunReport(
        status="ok",
        matches=[{"match_id": "m1"}],
        segment_scores=[{"segment_id": "s1"}],
        match_count=1,
        segment_score_count=1,
        hype_match_count=1,
        high_value_segment_count=1,
        recommendation="use_keyword_emotion_scoring",
    )

    apply_keyword_emotion_run_report_to_job(job, report)

    assert job.keyword_emotion_report == report.to_dict()
    assert job.keyword_emotion_status == "ok"
    assert job.keyword_emotion_matches == [{"match_id": "m1"}]
    assert job.keyword_emotion_segment_scores == [{"segment_id": "s1"}]
    assert job.keyword_emotion_match_count == 1
    assert job.keyword_emotion_hype_match_count == 1
    assert job.keyword_emotion_high_value_segment_count == 1


def test_old_jobs_load_with_keyword_emotion_defaults() -> None:
    old_data = {
        "job_id": "legacy_keyword_emotion",
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

    assert job.keyword_emotion_report == {}
    assert job.keyword_emotion_status is None
    assert job.keyword_emotion_matches == []
    assert job.keyword_emotion_segment_scores == []
    assert job.keyword_emotion_match_count == 0
    assert job.keyword_emotion_recommendation is None


def test_job_to_dict_contains_keyword_emotion_fields() -> None:
    job = _make_job()
    data = job.to_dict()
    required_fields = {
        "keyword_emotion_report",
        "keyword_emotion_status",
        "keyword_emotion_matches",
        "keyword_emotion_segment_scores",
        "keyword_emotion_match_count",
        "keyword_emotion_segment_score_count",
        "keyword_emotion_hype_match_count",
        "keyword_emotion_frustration_match_count",
        "keyword_emotion_shock_match_count",
        "keyword_emotion_laugh_match_count",
        "keyword_emotion_question_match_count",
        "keyword_emotion_high_value_segment_count",
        "keyword_emotion_recommendation",
    }

    assert required_fields.issubset(data.keys())
    assert required_fields.issubset({field.name for field in fields(Job)})


def test_mixed_language_transcript_creates_matches() -> None:
    job = _make_job()
    job.transcript_segments = [
        {"start_seconds": 0.0, "end_seconds": 1.0, "text": "krass no way"},
        {"start_seconds": 1.0, "end_seconds": 2.0, "text": "çok iyi haha"},
    ]

    report = run_keyword_emotion_for_job(job)

    languages = {match["language"] for match in report.matches}
    assert report.match_count >= 4
    assert {"de", "en", "tr"} & languages


def test_runner_does_not_crash_on_invalid_segments() -> None:
    job = _make_job()
    job.transcript_segments = [{"start_seconds": -1.0, "end_seconds": 0.0, "text": ""}]

    report = run_keyword_emotion_for_job(job)

    assert report.status in {"completed_with_warnings", "failed"}
    assert isinstance(report.to_dict(), dict)


def test_keyword_emotion_runner_files_have_no_bom() -> None:
    for relative_path in [
        "models/keyword_emotion_run.py",
        "core/keyword_emotion_runner.py",
        "models/job.py",
        "tests/test_keyword_emotion_runner_smoke.py",
    ]:
        assert not _path(relative_path).read_bytes().startswith(b"\xef\xbb\xbf")


def test_keyword_emotion_runner_files_end_with_newline() -> None:
    for relative_path in [
        "models/keyword_emotion_run.py",
        "core/keyword_emotion_runner.py",
        "models/job.py",
        "tests/test_keyword_emotion_runner_smoke.py",
    ]:
        assert _path(relative_path).read_bytes().endswith(b"\n")
