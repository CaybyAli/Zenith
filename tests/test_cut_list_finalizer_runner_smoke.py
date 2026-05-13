from pathlib import Path

from core.cut_list_finalizer_runner import (
    apply_cut_list_finalization_run_report_to_job,
    run_cut_list_finalization_for_job,
)
from models.final_cut_list import (
    FINAL_ACTION_BLOCKED_BY_CONTINUITY,
    FINAL_ACTION_CENSOR_KEEP,
    FINAL_ACTION_PROTECT,
    FINAL_ACTION_REMOVE_REVIEW,
)
from models.final_cut_list_run import FinalCutListRunReport
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_FILES = [
    ROOT / "models" / "final_cut_list_run.py",
    ROOT / "core" / "cut_list_finalizer_runner.py",
    ROOT / "models" / "job.py",
]
TEST_FILE = ROOT / "tests" / "test_cut_list_finalizer_runner_smoke.py"


def _job_data() -> dict:
    return {
        "job_id": "job_final_cut_list_runner",
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


def _job() -> Job:
    return Job.from_dict(_job_data())


def _cut_item(action="REVIEW_KEEP", item_id="item_1", segment_id="seg_1"):
    return {
        "item_id": item_id,
        "segment_id": segment_id,
        "start_seconds": 1.0,
        "end_seconds": 3.0,
        "proposed_action": action,
        "action_confidence": 0.8,
    }


def test_run_report_roundtrip():
    report = FinalCutListRunReport(
        status="ok",
        final_item_count=1,
        final_keep_review_count=1,
        recommendation="final_cut_list_ready_for_review",
        metadata={"review_only": True},
    )

    assert FinalCutListRunReport.from_dict(report.to_dict()).to_dict() == (
        report.to_dict()
    )


def test_runner_uses_job_cut_list_items():
    job = _job()
    job.cut_list_items = [_cut_item("REVIEW_KEEP")]

    report = run_cut_list_finalization_for_job(job)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.final_item_count == 1
    assert report.final_keep_review_count == 1


def test_runner_uses_continuity_check_issues():
    job = _job()
    job.cut_list_items = [_cut_item("KEEP")]
    job.continuity_check_issues = [
        {
            "issue_id": "issue_1",
            "source_item_id": "item_1",
            "issue_type": "sentence_break_risk",
            "severity": "critical",
            "is_blocking": True,
        }
    ]

    report = run_cut_list_finalization_for_job(job)

    assert report.final_items[0].final_action == FINAL_ACTION_BLOCKED_BY_CONTINUITY
    assert report.blocking_issue_count == 1


def test_runner_uses_clip_duration_recommendations():
    job = _job()
    job.cut_list_items = [_cut_item("REVIEW_KEEP")]
    job.clip_duration_recommendations = [
        {
            "source_item_id": "item_1",
            "duration_status": "too_long_review",
            "confidence": 0.9,
        }
    ]

    report = run_cut_list_finalization_for_job(job)

    assert report.final_trim_review_count == 1


def test_runner_uses_transition_decision_decisions():
    job = _job()
    job.cut_list_items = [_cut_item("REVIEW_KEEP")]
    job.transition_decision_decisions = [
        {
            "source_item_id": "item_1",
            "transition_type": "technical_transition_review",
        }
    ]

    report = run_cut_list_finalization_for_job(job)

    assert report.final_technical_review_count == 1


def test_skipped_no_inputs():
    report = run_cut_list_finalization_for_job(_job())

    assert report.status == "skipped_no_inputs"
    assert report.recommendation == "final_cut_list_skipped_no_inputs"


def test_apply_writes_job_fields():
    job = _job()
    report = run_cut_list_finalization_for_job(
        {
            **_job_data(),
            "cut_list_items": [_cut_item("CENSOR_KEEP")],
        }
    )

    apply_cut_list_finalization_run_report_to_job(job, report)

    assert job.final_cut_list_report["source"] == "cut_list_finalizer"
    assert job.final_cut_list_status == report.status
    assert job.final_cut_list_item_count == 1
    assert job.final_cut_list_censor_keep_count == 1
    assert job.final_cut_list_recommendation == report.recommendation


def test_old_jobs_load_and_to_dict_contains_fields():
    job = Job.from_dict(_job_data())
    data = job.to_dict()

    assert job.final_cut_list_report == {}
    assert job.final_cut_list_items == []
    assert job.final_cut_list_recommendation is None
    assert "final_cut_list_report" in data
    assert "final_cut_list_item_count" in data
    assert "final_cut_list_recommendation" in data


def test_counts_for_censor_protect_and_review_remove():
    job = _job()
    job.cut_list_items = [
        _cut_item("CENSOR_KEEP", "item_censor", "seg_censor"),
        _cut_item("PROTECT", "item_protect", "seg_protect"),
        _cut_item("REVIEW_REMOVE", "item_remove", "seg_remove"),
    ]

    report = run_cut_list_finalization_for_job(job)

    assert report.final_censor_keep_count == 1
    assert report.final_protect_count == 1
    assert report.final_remove_review_count == 1
    assert FINAL_ACTION_CENSOR_KEEP in [item.final_action for item in report.final_items]
    assert FINAL_ACTION_PROTECT in [item.final_action for item in report.final_items]
    assert FINAL_ACTION_REMOVE_REVIEW in [item.final_action for item in report.final_items]


def test_no_crash_with_broken_inputs():
    job = _job()
    job.cut_list_items = [None, "bad"]

    report = run_cut_list_finalization_for_job(job)

    assert report.status in {"ok", "completed_with_warnings", "failed"}
    assert isinstance(report.errors, list)


def test_no_bom_and_newline():
    for path in PRODUCT_FILES + [TEST_FILE]:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        assert raw.endswith(b"\n"), path
