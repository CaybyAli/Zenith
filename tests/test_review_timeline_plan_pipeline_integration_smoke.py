from pathlib import Path

from models.job import Job


ROOT = Path(__file__).resolve().parents[1]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _pipeline_review_timeline_block() -> str:
    text = _text(ROOT / "core" / "gaming_pipeline.py")
    start = text.index("# ── Review Timeline Plan (2B-32)")
    end = text.index("# ── End Review Timeline Plan", start)
    return text[start:end]


def _make_job():
    return Job.from_dict(
        {
            "job_id": "job_review_timeline_pipeline",
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
    )


def test_job_has_review_timeline_plan_fields():
    job = _make_job()
    data = job.to_dict()

    required_fields = [
        "review_timeline_plan_report",
        "review_timeline_plan",
        "review_timeline_plan_status",
        "review_timeline_plan_id",
        "review_timeline_plan_items",
        "review_timeline_plan_item_count",
        "review_timeline_plan_total_duration_seconds",
        "review_timeline_plan_review_required_count",
        "review_timeline_plan_protected_count",
        "review_timeline_plan_censor_required_count",
        "review_timeline_plan_continuity_blocked_count",
        "review_timeline_plan_recommendation",
    ]

    for field in required_fields:
        assert hasattr(job, field)
        assert field in data


def test_pipeline_contains_review_timeline_plan_block():
    block = _pipeline_review_timeline_block()

    assert "REVIEW_TIMELINE_PLAN_STARTED" in block
    assert "REVIEW_TIMELINE_PLAN_DONE" in block
    assert "REVIEW_TIMELINE_PLAN_SKIPPED" in block
    assert "REVIEW_TIMELINE_PLAN_FAILED" in block
    assert "run_review_timeline_plan_for_job(" in block
    assert "apply_review_timeline_plan_run_report_to_job(" in block
    assert 'step_name="review_timeline_plan_done"' in block
    assert "review_only" in block
    assert "approval_required" in block


def test_pipeline_review_timeline_plan_runs_after_cut_list_finalization():
    text = _text(ROOT / "core" / "gaming_pipeline.py")

    assert text.index("REVIEW_TIMELINE_PLAN_STARTED") > text.index(
        "CUT_LIST_FINALIZATION_DONE"
    )


def test_pipeline_review_timeline_block_has_no_unsafe_execution_terms():
    block = _pipeline_review_timeline_block().lower()

    forbidden = [
        "ffmpeg",
        "timelinebuilder",
        "highlightselector",
        ".render(",
        "renderprocessor",
        "apply_final_cutlist",
        "execute_final_cutlist",
        "force_cut",
        "auto_cut",
        "auto_trim",
        "auto_highlight",
        "auto_hook",
        "auto_mute",
        "censor_now",
        "delete_segment",
        "drop_segment",
        "remove_now",
    ]

    for word in forbidden:
        assert word not in block, f"{word} found in review timeline plan block"
