from __future__ import annotations

from pathlib import Path

from core.dead_content_runner import (
    apply_dead_content_run_report_to_job,
    run_dead_content_detection_for_job,
)
from models.dead_content_run import DeadContentRunReport
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


def _make_job() -> Job:
    return Job(
        job_id="job_dead_content_001",
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


def test_dead_content_run_report_roundtrip() -> None:
    report = DeadContentRunReport(
        status="ok",
        candidates=[{"candidate_id": "c1"}],
        segment_scores=[{"segment_id": "s1"}],
        candidate_count=1,
        segment_score_count=1,
        recommendation="review_dead_content_candidates",
    )

    restored = DeadContentRunReport.from_dict(report.to_dict())

    assert restored.to_dict() == report.to_dict()


def test_runner_uses_job_transcript_and_optional_reports() -> None:
    job = _make_job()
    job.transcript_segments = [
        {
            "segment_id": "s1",
            "start_seconds": 1.0,
            "end_seconds": 2.0,
            "duration_seconds": 1.0,
            "text": "waiting",
        }
    ]
    job.screen_content_report = {
        "screen_content_segments": [
            {
                "start_seconds": 1.0,
                "end_seconds": 2.0,
                "screen_type": "loading",
                "avg_confidence": 0.9,
            }
        ]
    }

    report = run_dead_content_detection_for_job(job)

    assert report.status == "ok"
    assert report.candidate_count == 1
    assert report.loading_or_menu_candidate_count == 1


def test_runner_skips_without_inputs() -> None:
    report = run_dead_content_detection_for_job(_make_job())

    assert report.status == "skipped_no_inputs"
    assert report.recommendation == "dead_content_skipped_no_inputs"


def test_apply_dead_content_run_report_to_job_writes_fields() -> None:
    job = _make_job()
    report = DeadContentRunReport(
        status="ok",
        candidates=[{"candidate_id": "c1"}],
        segment_scores=[{"segment_id": "s1"}],
        candidate_count=1,
        segment_score_count=1,
        low_value_candidate_count=1,
        recommendation="review_dead_content_candidates",
    )

    apply_dead_content_run_report_to_job(job, report)

    assert job.dead_content_status == "ok"
    assert job.dead_content_candidate_count == 1
    assert job.dead_content_low_value_candidate_count == 1
    assert job.dead_content_recommendation == "review_dead_content_candidates"


def test_old_jobs_load_without_dead_content_fields() -> None:
    legacy = {
        "job_id": "legacy_dead_content",
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

    assert restored.dead_content_report == {}
    assert restored.dead_content_candidates == []
    assert restored.dead_content_candidate_count == 0
    assert restored.dead_content_recommendation is None


def test_job_to_dict_contains_dead_content_fields() -> None:
    job = _make_job()
    data = job.to_dict()

    assert "dead_content_report" in data
    assert "dead_content_candidates" in data
    assert "dead_content_recommendation" in data


def test_private_meta_remains_review_candidate() -> None:
    job = _make_job()
    job.transcript_segments = [
        {"segment_id": "s1", "start_seconds": 1.0, "end_seconds": 2.0, "text": "real name"}
    ]
    job.interaction_classification_report = {
        "segment_classifications": [
            {
                "segment_id": "i1",
                "start_seconds": 1.0,
                "end_seconds": 2.0,
                "interaction_type": "private_or_meta_candidate",
                "confidence": 0.9,
            }
        ]
    }

    report = run_dead_content_detection_for_job(job)

    assert report.private_or_meta_candidate_count == 1
    assert report.candidates[0]["recommendation"] == "review_private_or_meta_candidate"


def test_protected_context_remains_protected() -> None:
    job = _make_job()
    job.transcript_segments = [
        {"segment_id": "s1", "start_seconds": 1.0, "end_seconds": 2.0, "text": "why?"}
    ]
    job.interaction_classification_report = {
        "segment_classifications": [
            {
                "segment_id": "i1",
                "start_seconds": 1.0,
                "end_seconds": 2.0,
                "interaction_type": "question_answer",
                "context_needed": True,
                "confidence": 0.9,
            }
        ]
    }

    report = run_dead_content_detection_for_job(job)

    assert report.protected_candidate_count == 1
    assert report.candidates[0]["recommendation"] == "review_protected_context"


def test_invalid_segments_do_not_crash_runner() -> None:
    job = _make_job()
    job.transcript_segments = [None, "bad", {"text": ""}]

    report = run_dead_content_detection_for_job(job)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.segment_score_count == 1


def test_dead_content_runner_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "models/dead_content_run.py",
        "core/dead_content_runner.py",
        "tests/test_dead_content_runner_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
