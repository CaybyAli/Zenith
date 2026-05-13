from pathlib import Path

from core.cut_list_runner import (
    apply_cut_list_run_report_to_job,
    run_cut_list_generation_for_job,
)
from models.cut_list import (
    CUT_LIST_ACTION_CENSOR_KEEP,
    CUT_LIST_ACTION_PROTECT,
    CUT_LIST_ACTION_REVIEW_REMOVE,
    CUT_LIST_STATUS_SKIPPED_NO_SEGMENTS,
    CutListItem,
    CutListPlan,
)
from models.cut_list_run import CutListRunReport
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]


def _make_job(extra=None):
    data = {
        "job_id": "job_cut_list_test",
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
    if extra:
        data.update(extra)
    return Job.from_dict(data)


def test_cut_list_run_report_roundtrip():
    plan = CutListPlan(
        status="ok",
        items=[
            CutListItem(
                item_id="cutlist_seg_1",
                segment_id="seg_1",
                proposed_action=CUT_LIST_ACTION_PROTECT,
            )
        ],
        recommendation="cut_list_candidates_generated",
    )
    plan.refresh_counts()

    report = CutListRunReport(
        status="ok",
        cut_list_plan=plan,
        items=plan.items,
        item_count=1,
        protect_count=1,
        recommendation="cut_list_candidates_generated",
    )

    restored = CutListRunReport.from_dict(report.to_dict())

    assert restored.status == "ok"
    assert restored.source == "cut_list_generator"
    assert restored.item_count == 1
    assert restored.protect_count == 1
    assert restored.items[0].proposed_action == CUT_LIST_ACTION_PROTECT


def test_runner_uses_segment_classification_segments():
    job = _make_job(
        {
            "segment_classification_segments": [
                {
                    "segment_id": "seg_1",
                    "segment_type": "protected_context",
                    "is_protected": True,
                }
            ],
            "murch_scoring_segment_scores": [
                {
                    "segment_id": "seg_1",
                    "murch_score": 0.8,
                    "tier": "protected",
                }
            ],
        }
    )

    report = run_cut_list_generation_for_job(job)

    assert report.item_count == 1
    assert report.protect_count == 1
    assert report.items[0].segment_id == "seg_1"


def test_runner_uses_murch_scoring_segment_scores():
    job = _make_job(
        {
            "segment_classification_segments": [
                {
                    "segment_id": "seg_high",
                    "segment_type": "highlight",
                    "content_value_score": 0.9,
                }
            ],
            "murch_scoring_segment_scores": [
                {
                    "segment_id": "seg_high",
                    "murch_score": 0.95,
                    "tier": "high",
                }
            ],
        }
    )

    report = run_cut_list_generation_for_job(job)

    assert report.item_count == 1
    assert report.items[0].murch_score == 0.95
    assert report.keep_count + report.review_keep_count == 1


def test_runner_skipped_no_segments():
    job = _make_job()

    report = run_cut_list_generation_for_job(job)

    assert report.status == CUT_LIST_STATUS_SKIPPED_NO_SEGMENTS
    assert report.item_count == 0
    assert report.recommendation == "cut_list_skipped_no_segments"


def test_apply_writes_job_fields():
    job = _make_job()
    report = CutListRunReport(
        status="ok",
        items=[
            CutListItem(
                item_id="cutlist_seg_1",
                segment_id="seg_1",
                proposed_action=CUT_LIST_ACTION_CENSOR_KEEP,
            )
        ],
        item_count=1,
        censor_keep_count=1,
        recommendation="cut_list_candidates_generated",
    )

    apply_cut_list_run_report_to_job(job, report)

    assert job.cut_list_status == "ok"
    assert job.cut_list_item_count == 1
    assert job.cut_list_censor_keep_count == 1
    assert job.cut_list_recommendation == "cut_list_candidates_generated"
    assert job.cut_list_items[0]["proposed_action"] == CUT_LIST_ACTION_CENSOR_KEEP


def test_old_jobs_are_still_loadable():
    job = _make_job()

    assert job.cut_list_report == {}
    assert job.cut_list_status is None
    assert job.cut_list_items == []
    assert job.cut_list_item_count == 0
    assert job.cut_list_recommendation is None


def test_job_to_dict_contains_cut_list_fields():
    job = _make_job()
    data = job.to_dict()

    assert "cut_list_report" in data
    assert "cut_list_status" in data
    assert "cut_list_items" in data
    assert "cut_list_item_count" in data
    assert "cut_list_recommendation" in data


def test_censor_keep_is_counted():
    job = _make_job(
        {
            "segment_classification_segments": [
                {
                    "segment_id": "seg_censor",
                    "segment_type": "censor_required_segment",
                    "censor_required": True,
                }
            ],
            "murch_scoring_segment_scores": [
                {
                    "segment_id": "seg_censor",
                    "murch_score": 0.5,
                }
            ],
        }
    )

    report = run_cut_list_generation_for_job(job)

    assert report.censor_keep_count == 1
    assert report.items[0].proposed_action == CUT_LIST_ACTION_CENSOR_KEEP


def test_protect_is_counted():
    job = _make_job(
        {
            "segment_classification_segments": [
                {
                    "segment_id": "seg_protect",
                    "segment_type": "protected_context",
                    "is_protected": True,
                }
            ],
            "murch_scoring_segment_scores": [
                {
                    "segment_id": "seg_protect",
                    "murch_score": 0.5,
                    "tier": "protected",
                }
            ],
        }
    )

    report = run_cut_list_generation_for_job(job)

    assert report.protect_count == 1
    assert report.items[0].proposed_action == CUT_LIST_ACTION_PROTECT


def test_review_remove_stays_review_only():
    job = _make_job(
        {
            "segment_classification_segments": [
                {
                    "segment_id": "seg_dead",
                    "segment_type": "dead_candidate",
                    "content_value_score": 0.1,
                }
            ],
            "murch_scoring_segment_scores": [
                {
                    "segment_id": "seg_dead",
                    "murch_score": 0.1,
                }
            ],
        }
    )

    report = run_cut_list_generation_for_job(job)

    assert report.review_remove_count == 1
    assert report.items[0].proposed_action == CUT_LIST_ACTION_REVIEW_REMOVE
    assert report.items[0].proposed_action != "REMOVE"
    assert report.items[0].proposed_action != "CUT"


def test_runner_does_not_crash_on_broken_segments():
    job = _make_job(
        {
            "segment_classification_segments": [
                {
                    "segment_id": "broken",
                    "segment_type": None,
                    "start_seconds": "bad",
                    "end_seconds": "bad",
                    "content_value_score": "bad",
                }
            ],
            "murch_scoring_segment_scores": [
                {
                    "segment_id": "broken",
                    "murch_score": "bad",
                }
            ],
        }
    )

    report = run_cut_list_generation_for_job(job)

    assert report.item_count == 1
    assert report.errors == []


def test_new_files_have_no_bom_and_end_with_newline():
    files = [
        ROOT / "models" / "cut_list_run.py",
        ROOT / "core" / "cut_list_runner.py",
        ROOT / "models" / "job.py",
        ROOT / "tests" / "test_cut_list_runner_smoke.py",
    ]

    for path in files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        assert raw.endswith(b"\n")
