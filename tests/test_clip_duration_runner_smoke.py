from pathlib import Path

from core.clip_duration_runner import (
    apply_clip_duration_run_report_to_job,
    run_clip_duration_optimization_for_job,
)
from models.clip_duration import (
    ClipDurationOptimizationPlan,
    ClipDurationRecommendation,
)
from models.clip_duration_run import ClipDurationRunReport
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = [
    ROOT / "models" / "clip_duration_run.py",
    ROOT / "core" / "clip_duration_runner.py",
    ROOT / "tests" / "test_clip_duration_runner_smoke.py",
]

BASE_JOB_DATA = {
    "job_id": "job_clip_duration_old",
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


def _cut_list_item(
    item_id: str,
    start_seconds: float,
    end_seconds: float,
    proposed_action: str,
    segment_type: str = "highlight",
):
    return {
        "id": item_id,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "proposed_action": proposed_action,
        "segment_type": segment_type,
    }


def test_clip_duration_run_report_roundtrip():
    recommendation = ClipDurationRecommendation(
        recommendation_id="rec_1",
        source_item_id="item_1",
        start_seconds=0.0,
        end_seconds=8.0,
        duration_seconds=8.0,
        proposed_action="KEEP",
        duration_status="duration_ok",
        recommended_min_duration_seconds=4.0,
        recommended_max_duration_seconds=90.0,
        is_duration_ok=True,
    )
    plan = ClipDurationOptimizationPlan(
        status="ok",
        recommendations=[recommendation],
        recommendation_count=1,
        duration_ok_count=1,
        recommendation="clip_duration_review_plan_ready",
    )
    report = ClipDurationRunReport(
        status="ok",
        clip_duration_plan=plan,
        recommendations=[recommendation],
        recommendation_count=1,
        duration_ok_count=1,
        recommendation="clip_duration_review_plan_ready",
        metadata={"source": "test"},
    )

    loaded = ClipDurationRunReport.from_dict(report.to_dict())

    assert loaded.to_dict() == report.to_dict()


def test_runner_uses_job_cut_list_items():
    job = {
        "cut_list_items": [
            _cut_list_item("good_keep", 0.0, 8.0, "KEEP", "highlight"),
        ],
    }

    report = run_clip_duration_optimization_for_job(job)

    assert report.status == "ok"
    assert report.recommendation_count == 1
    assert report.duration_ok_count == 1
    assert report.recommendations[0].source_item_id == "good_keep"


def test_runner_uses_fallback_cut_list_report():
    job = {
        "cut_list_report": {
            "items": [
                _cut_list_item("fallback_keep", 0.0, 8.0, "KEEP", "highlight"),
            ]
        }
    }

    report = run_clip_duration_optimization_for_job(job)

    assert report.status == "ok"
    assert report.recommendation_count == 1
    assert report.duration_ok_count == 1
    assert report.recommendations[0].source_item_id == "fallback_keep"


def test_runner_skips_when_no_cut_list_items_exist():
    job = {}

    report = run_clip_duration_optimization_for_job(job)

    assert report.status == "skipped_no_cut_list_items"
    assert report.recommendation_count == 0
    assert report.recommendation == "clip_duration_skipped_no_cut_list_items"


def test_apply_writes_clip_duration_fields_to_dict_job():
    job = {
        "cut_list_items": [
            _cut_list_item("good_keep", 0.0, 8.0, "KEEP", "highlight"),
        ],
    }
    report = run_clip_duration_optimization_for_job(job)

    apply_clip_duration_run_report_to_job(job, report)

    assert job["clip_duration_report"]["source"] == "clip_duration_optimizer"
    assert job["clip_duration_status"] == "ok"
    assert len(job["clip_duration_recommendations"]) == 1
    assert job["clip_duration_recommendation_count"] == 1
    assert job["clip_duration_ok_count"] == 1
    assert job["clip_duration_recommendation"] == "clip_duration_review_plan_ready"


def test_old_jobs_are_loadable_with_defaults():
    job = Job.from_dict(dict(BASE_JOB_DATA))

    assert job.clip_duration_report == {}
    assert job.clip_duration_status is None
    assert job.clip_duration_recommendations == []
    assert job.clip_duration_recommendation_count == 0
    assert job.clip_duration_recommendation is None


def test_job_to_dict_contains_clip_duration_fields():
    job = Job.from_dict(dict(BASE_JOB_DATA))
    data = job.to_dict()

    assert "clip_duration_report" in data
    assert "clip_duration_status" in data
    assert "clip_duration_recommendations" in data
    assert "clip_duration_recommendation_count" in data
    assert "clip_duration_ok_count" in data
    assert "clip_duration_too_short_count" in data
    assert "clip_duration_too_long_count" in data
    assert "clip_duration_trim_review_count" in data
    assert "clip_duration_extend_review_count" in data
    assert "clip_duration_protect_duration_count" in data
    assert "clip_duration_censor_keep_count" in data
    assert "clip_duration_technical_review_count" in data
    assert "clip_duration_invalid_timing_count" in data
    assert "clip_duration_recommendation" in data


def test_censor_keep_is_counted():
    job = {
        "cut_list_items": [
            _cut_list_item(
                "censor_keep",
                2.0,
                6.0,
                "CENSOR_KEEP",
                "censor_required_segment",
            ),
        ],
    }

    report = run_clip_duration_optimization_for_job(job)

    assert report.censor_keep_count == 1
    assert report.recommendations[0].duration_status == "censor_keep_duration"


def test_protect_is_counted():
    job = {
        "cut_list_items": [
            _cut_list_item(
                "protected_context",
                2.0,
                50.0,
                "PROTECT",
                "protected_context",
            ),
        ],
    }

    report = run_clip_duration_optimization_for_job(job)

    assert report.protect_duration_count == 1
    assert report.recommendations[0].duration_status == "protect_duration"


def test_invalid_timing_is_counted():
    job = {
        "cut_list_items": [
            _cut_list_item("invalid", 20.0, 10.0, "KEEP", "highlight"),
        ],
    }

    report = run_clip_duration_optimization_for_job(job)

    assert report.invalid_timing_count == 1
    assert report.recommendations[0].duration_status == "invalid_timing_review"


def test_runner_does_not_crash_with_broken_items():
    job = {
        "cut_list_items": [
            None,
            {"id": "broken_no_times", "proposed_action": "KEEP"},
            _cut_list_item("good_keep", 0.0, 8.0, "KEEP", "highlight"),
        ],
    }

    report = run_clip_duration_optimization_for_job(job)

    assert report.recommendation_count == 3
    assert report.duration_ok_count == 1
    assert report.invalid_timing_count >= 1


def test_apply_accepts_report_dict():
    job = {}
    report = run_clip_duration_optimization_for_job(
        {
            "cut_list_items": [
                _cut_list_item("good_keep", 0.0, 8.0, "KEEP", "highlight"),
            ]
        }
    )

    apply_clip_duration_run_report_to_job(job, report.to_dict())

    assert job["clip_duration_status"] == "ok"
    assert job["clip_duration_recommendation_count"] == 1


def test_new_files_have_no_bom_and_end_with_newline():
    for file_path in NEW_FILES:
        raw = file_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), file_path
        assert raw.endswith(b"\n"), file_path
