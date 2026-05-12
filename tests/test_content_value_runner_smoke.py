from __future__ import annotations

from pathlib import Path

from core.content_value_runner import (
    apply_content_value_run_report_to_job,
    run_content_value_for_job,
)
from models.content_value_run import ContentValueRunReport
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
        job_id="job_content_value_001",
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


def _add_segments(job: Job) -> None:
    job.transcript_segments = [
        {
            "segment_id": "high",
            "start_seconds": 1.0,
            "end_seconds": 3.0,
            "duration_seconds": 2.0,
            "text": "what a huge clutch win",
        },
        {
            "segment_id": "mid",
            "start_seconds": 4.0,
            "end_seconds": 6.0,
            "duration_seconds": 2.0,
            "text": "chat saw the play",
        },
        {
            "segment_id": "low",
            "start_seconds": 7.0,
            "end_seconds": 8.0,
            "duration_seconds": 1.0,
            "text": "",
        },
        {
            "segment_id": "protected",
            "start_seconds": 9.0,
            "end_seconds": 10.0,
            "duration_seconds": 1.0,
            "text": "why?",
        },
    ]


def _add_optional_reports(job: Job) -> None:
    job.keyword_emotion_report = {
        "segment_scores": [
            {
                "segment_id": "high",
                "overall_keyword_score": 0.92,
                "dominant_category": "hype",
            },
            {"segment_id": "mid", "overall_keyword_score": 0.7},
        ]
    }
    job.interaction_classification_report = {
        "segment_classifications": [
            {
                "segment_id": "high",
                "interaction_type": "question_answer",
                "confidence": 0.9,
            },
            {"segment_id": "mid", "interaction_type": "chat_reaction", "confidence": 0.7},
            {
                "segment_id": "protected",
                "interaction_type": "context_needed",
                "context_needed": True,
                "confidence": 0.9,
            },
        ]
    }
    job.visual_energy_report = {
        "visual_energy_segments": [
            {"segment_id": "high", "classification": "peak_visual_energy", "score": 0.9},
            {"segment_id": "mid", "classification": "high_visual_energy", "score": 0.72},
        ]
    }
    job.face_reaction_report = {
        "face_reaction_segments": [
            {"segment_id": "high", "reaction_type": "shock", "reaction_score": 0.9}
        ]
    }
    job.motion_analysis_report = {
        "motion_analysis_segments": [
            {"segment_id": "high", "motion_classification": "high_motion", "motion_score": 0.82}
        ]
    }
    job.screen_content_report = {
        "screen_content_segments": [
            {"segment_id": "high", "screen_type": "victory_screen", "confidence": 0.9}
        ]
    }
    job.energy_peak_report = {
        "energy_peaks": [
            {"segment_id": "high", "peak_type": "high_energy_peak", "peak_score": 0.9},
            {"segment_id": "mid", "peak_type": "local_max_peak", "peak_score": 0.7},
        ]
    }
    job.sentence_boundary_report = {
        "protection_zones": [
            {"segment_id": "protected", "start_seconds": 9.0, "end_seconds": 10.0}
        ]
    }


def test_content_value_run_report_roundtrip() -> None:
    report = ContentValueRunReport(
        status="ok",
        segment_scores=[{"segment_id": "s1"}],
        segment_score_count=1,
        high_value_count=1,
        recommendation="review_content_value_segments",
    )

    restored = ContentValueRunReport.from_dict(report.to_dict())

    assert restored.to_dict() == report.to_dict()


def test_runner_uses_job_transcript_and_optional_reports() -> None:
    job = _make_job()
    _add_segments(job)
    _add_optional_reports(job)

    report = run_content_value_for_job(job)

    assert report.status == "ok"
    assert report.segment_score_count == 4
    assert report.high_value_count == 1
    assert report.mid_value_count >= 1
    assert report.protected_context_count == 1
    assert report.hook_candidate_count >= 1


def test_runner_skips_without_inputs() -> None:
    report = run_content_value_for_job(_make_job())

    assert report.status == "skipped_no_inputs"
    assert report.recommendation == "content_value_skipped_no_inputs"


def test_apply_content_value_run_report_to_job_writes_fields() -> None:
    job = _make_job()
    report = ContentValueRunReport(
        status="ok",
        segment_scores=[{"segment_id": "s1", "final_score": 0.8}],
        segment_score_count=1,
        high_value_count=1,
        hook_candidate_count=1,
        avg_content_value_score=0.8,
        max_content_value_score=0.8,
        min_content_value_score=0.8,
        recommendation="review_content_value_segments",
    )

    apply_content_value_run_report_to_job(job, report)

    assert job.content_value_status == "ok"
    assert job.content_value_segment_score_count == 1
    assert job.content_value_high_value_count == 1
    assert job.content_value_hook_candidate_count == 1
    assert job.content_value_avg_score == 0.8
    assert job.content_value_recommendation == "review_content_value_segments"


def test_old_jobs_load_without_content_value_fields() -> None:
    legacy = {
        "job_id": "legacy_content_value",
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

    assert restored.content_value_report == {}
    assert restored.content_value_segment_scores == []
    assert restored.content_value_segment_score_count == 0
    assert restored.content_value_recommendation is None


def test_job_to_dict_contains_content_value_fields() -> None:
    job = _make_job()
    data = job.to_dict()

    assert "content_value_report" in data
    assert "content_value_segment_scores" in data
    assert "content_value_recommendation" in data


def test_counts_are_set_for_value_tiers() -> None:
    job = _make_job()
    _add_segments(job)
    _add_optional_reports(job)

    report = run_content_value_for_job(job)

    assert report.high_value_count == 1
    assert report.mid_value_count >= 1
    assert report.low_value_count >= 1
    assert report.protected_context_count == 1


def test_hook_candidate_count_is_set() -> None:
    job = _make_job()
    _add_segments(job)
    _add_optional_reports(job)

    report = run_content_value_for_job(job)

    assert report.hook_candidate_count >= 1


def test_invalid_segments_do_not_crash_runner() -> None:
    job = _make_job()
    job.transcript_segments = [None, "bad", {"text": ""}]

    report = run_content_value_for_job(job)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.segment_score_count == 1


def test_content_value_runner_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "models/content_value_run.py",
        "core/content_value_runner.py",
        "models/job.py",
        "tests/test_content_value_runner_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
