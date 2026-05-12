from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from core.interaction_classification_runner import (
    apply_interaction_classification_run_report_to_job,
    run_interaction_classification_for_job,
)
from models.interaction_classification_run import InteractionClassificationRunReport
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _make_job() -> Job:
    return Job(
        job_id="interaction_classification_job",
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
    report = InteractionClassificationRunReport(
        status="ok",
        transcript_source="preprocessed_audio",
        points=[{"interaction_id": "p1"}],
        segment_classifications=[{"segment_id": "s1"}],
        point_count=1,
        segment_classification_count=1,
        interaction_count=1,
        recommendation="use_interaction_classification_review_signals",
        metadata={"stage": "test"},
    )

    restored = InteractionClassificationRunReport.from_dict(report.to_dict())

    assert restored.to_dict() == report.to_dict()


def test_run_interaction_classification_for_job_uses_job_transcript_segments() -> None:
    job = _make_job()
    job.transcript_source_type = "preprocessed_audio"
    job.transcript_segments = [
        {"start_seconds": 0.0, "end_seconds": 1.0, "text": "Nils komm mal."}
    ]

    report = run_interaction_classification_for_job(job)

    assert report.status == "ok"
    assert report.transcript_source == "preprocessed_audio"
    assert report.interaction_count == 1


def test_runner_uses_optional_reports_without_crash() -> None:
    job = _make_job()
    job.transcript_segments = [
        {"start_seconds": 0.0, "end_seconds": 1.0, "text": "Warum so?"}
    ]
    job.sentence_boundary_report = {"status": "ok", "boundaries": []}
    job.keyword_emotion_report = {"status": "ok", "segment_scores": []}

    report = run_interaction_classification_for_job(job)

    assert report.status == "ok"
    assert report.question_answer_count == 1


def test_skipped_no_transcript_segments() -> None:
    job = _make_job()

    report = run_interaction_classification_for_job(job)

    assert report.status == "skipped_no_transcript_segments"
    assert report.recommendation == "interaction_classification_skipped_no_transcript"


def test_apply_report_writes_job_fields() -> None:
    job = _make_job()
    report = InteractionClassificationRunReport(
        status="ok",
        points=[{"interaction_id": "p1"}],
        segment_classifications=[{"segment_id": "s1"}],
        point_count=1,
        segment_classification_count=1,
        monologue_count=1,
        interaction_count=2,
        question_answer_count=3,
        chat_reaction_count=4,
        callout_count=5,
        commentary_count=6,
        private_or_meta_count=7,
        context_needed_count=8,
        recommendation="use_interaction_classification_review_signals",
    )

    apply_interaction_classification_run_report_to_job(job, report)

    assert job.interaction_classification_report == report.to_dict()
    assert job.interaction_classification_status == "ok"
    assert job.interaction_classification_points == [{"interaction_id": "p1"}]
    assert job.interaction_classification_segments == [{"segment_id": "s1"}]
    assert job.interaction_classification_point_count == 1
    assert job.interaction_classification_segment_count == 1
    assert job.interaction_classification_context_needed_count == 8


def test_old_jobs_load_with_interaction_classification_defaults() -> None:
    old_data = {
        "job_id": "legacy_interaction",
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

    assert job.interaction_classification_report == {}
    assert job.interaction_classification_status is None
    assert job.interaction_classification_points == []
    assert job.interaction_classification_segments == []
    assert job.interaction_classification_point_count == 0


def test_job_to_dict_contains_interaction_classification_fields() -> None:
    job = _make_job()
    data = job.to_dict()
    required_fields = {
        "interaction_classification_report",
        "interaction_classification_status",
        "interaction_classification_points",
        "interaction_classification_segments",
        "interaction_classification_point_count",
        "interaction_classification_segment_count",
        "interaction_classification_monologue_count",
        "interaction_classification_interaction_count",
        "interaction_classification_question_answer_count",
        "interaction_classification_chat_reaction_count",
        "interaction_classification_callout_count",
        "interaction_classification_commentary_count",
        "interaction_classification_private_or_meta_count",
        "interaction_classification_context_needed_count",
        "interaction_classification_recommendation",
    }

    assert required_fields.issubset(data.keys())
    assert required_fields.issubset({field.name for field in fields(Job)})


def test_mixed_transcript_produces_multiple_types() -> None:
    job = _make_job()
    job.transcript_segments = [
        {"start_seconds": 0.0, "end_seconds": 1.0, "text": "Ich bin jetzt hier."},
        {"start_seconds": 2.0, "end_seconds": 3.0, "text": "Chat was meint ihr?"},
        {"start_seconds": 4.0, "end_seconds": 5.0, "text": "Links pass auf!"},
    ]

    report = run_interaction_classification_for_job(job)
    types = {segment["interaction_type"] for segment in report.segment_classifications}

    assert {"monologue", "chat_reaction", "callout"}.issubset(types)


def test_runner_does_not_crash_on_invalid_segments() -> None:
    job = _make_job()
    job.transcript_segments = [None, {"text": ""}]

    report = run_interaction_classification_for_job(job)

    assert report.status == "completed_with_warnings"
    assert isinstance(report.to_dict(), dict)


def test_interaction_runner_files_have_no_bom() -> None:
    for relative_path in [
        "models/interaction_classification_run.py",
        "core/interaction_classification_runner.py",
        "models/job.py",
        "tests/test_interaction_classification_runner_smoke.py",
    ]:
        assert not _path(relative_path).read_bytes().startswith(b"\xef\xbb\xbf")


def test_interaction_runner_files_end_with_newline() -> None:
    for relative_path in [
        "models/interaction_classification_run.py",
        "core/interaction_classification_runner.py",
        "models/job.py",
        "tests/test_interaction_classification_runner_smoke.py",
    ]:
        assert _path(relative_path).read_bytes().endswith(b"\n")
