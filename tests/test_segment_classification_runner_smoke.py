from pathlib import Path

from core.segment_classification_runner import (
    apply_segment_classification_run_report_to_job,
    run_segment_classification_for_job,
)
from models.job import Job
from models.segment_classification import SegmentClassification
from models.segment_classification_run import SegmentClassificationRunReport


ROOT = Path(__file__).resolve().parents[1]


def _signal(signal_type: str, start: float = 10.0, end: float = 12.0) -> dict:
    return {
        "signal_id": f"sig_{signal_type}_{start}",
        "signal_type": signal_type,
        "source": "test",
        "start_seconds": start,
        "end_seconds": end,
        "score": 0.9,
        "confidence": 0.9,
        "metadata": {"test": True},
    }


def _minimal_job_data() -> dict:
    return {
        "job_id": "job_segment_classification_test",
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


def test_run_report_roundtrip() -> None:
    segment = SegmentClassification(
        segment_id="segment_1",
        segment_type="highlight",
        recommendation="review_segment_highlight_candidate",
    )
    report = SegmentClassificationRunReport(
        status="ok",
        segments=[segment],
        segment_count=1,
        highlight_count=1,
        recommendation="review_segment_classification",
    )

    loaded = SegmentClassificationRunReport.from_dict(report.to_dict())

    assert loaded.status == "ok"
    assert loaded.source == "segment_classifier"
    assert loaded.segment_count == 1
    assert loaded.highlight_count == 1
    assert loaded.segments[0].segment_type == "highlight"


def test_runner_uses_job_unified_edit_signals() -> None:
    job = Job.from_dict(
        {
            **_minimal_job_data(),
            "unified_edit_signals": [
                _signal("content_value_high_segment"),
            ],
        }
    )

    report = run_segment_classification_for_job(job)

    assert report.status == "ok"
    assert report.segment_count == 1
    assert report.highlight_count == 1
    assert report.segments[0].segment_type == "highlight"


def test_runner_skips_without_unified_signals() -> None:
    job = Job.from_dict(_minimal_job_data())

    report = run_segment_classification_for_job(job)

    assert report.status == "skipped_no_unified_signals"
    assert report.segment_count == 0
    assert report.recommendation == "segment_classifier_skipped_no_unified_signals"


def test_apply_writes_job_fields() -> None:
    job = Job.from_dict(
        {
            **_minimal_job_data(),
            "unified_edit_signals": [
                _signal("content_value_hook_candidate"),
            ],
        }
    )

    report = run_segment_classification_for_job(job)
    apply_segment_classification_run_report_to_job(job, report)

    assert job.segment_classification_status == "ok"
    assert job.segment_classification_segment_count == 1
    assert job.segment_classification_hook_candidate_count == 1
    assert job.segment_classification_recommendation == "review_segment_classification"
    assert job.segment_classification_segments[0]["segment_type"] == "hook_candidate"
    assert job.segment_classification_report["source"] == "segment_classifier"


def test_old_jobs_are_still_loadable() -> None:
    job = Job.from_dict(_minimal_job_data())

    assert job.segment_classification_report == {}
    assert job.segment_classification_status is None
    assert job.segment_classification_segments == []
    assert job.segment_classification_segment_count == 0
    assert job.segment_classification_recommendation is None


def test_job_to_dict_contains_segment_classification_fields() -> None:
    job = Job.from_dict(_minimal_job_data())
    data = job.to_dict()

    assert "segment_classification_report" in data
    assert "segment_classification_status" in data
    assert "segment_classification_segments" in data
    assert "segment_classification_segment_count" in data
    assert "segment_classification_highlight_count" in data
    assert "segment_classification_hook_candidate_count" in data
    assert "segment_classification_protected_context_count" in data
    assert "segment_classification_dead_candidate_count" in data
    assert "segment_classification_filler_count" in data
    assert "segment_classification_transition_count" in data
    assert "segment_classification_censor_required_count" in data
    assert "segment_classification_technical_warning_count" in data
    assert "segment_classification_recommendation" in data


def test_censor_required_segment_is_counted() -> None:
    job = Job.from_dict(
        {
            **_minimal_job_data(),
            "unified_edit_signals": [
                _signal("profanity_censor_sfx_required"),
            ],
        }
    )

    report = run_segment_classification_for_job(job)

    assert report.status == "ok"
    assert report.censor_required_count == 1
    assert report.segments[0].segment_type == "censor_required_segment"


def test_protected_context_is_counted() -> None:
    job = Job.from_dict(
        {
            **_minimal_job_data(),
            "unified_edit_signals": [
                _signal("sentence_boundary_protection"),
            ],
        }
    )

    report = run_segment_classification_for_job(job)

    assert report.status == "ok"
    assert report.protected_context_count == 1
    assert report.segments[0].segment_type == "protected_context"


def test_no_crash_with_broken_signals() -> None:
    job = Job.from_dict(
        {
            **_minimal_job_data(),
            "unified_edit_signals": [
                None,
                {"broken": True},
                "not_a_signal",
            ],
        }
    )

    report = run_segment_classification_for_job(job)

    assert report.status in {"skipped_no_unified_signals", "ok", "failed"}
    assert isinstance(report.errors, list)


def test_runner_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        ROOT / "models" / "segment_classification_run.py",
        ROOT / "core" / "segment_classification_runner.py",
        ROOT / "models" / "job.py",
        ROOT / "tests" / "test_segment_classification_runner_smoke.py",
    ]

    for path in files:
        content = path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert content.endswith(b"\n"), f"{path} does not end with newline"
