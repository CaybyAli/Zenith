from pathlib import Path

from models.job import Job


ROOT = Path(__file__).resolve().parents[1]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _make_job():
    return Job.from_dict(
        {
            "job_id": "job_review_timeline_dashboard_pipeline",
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


def test_job_has_review_timeline_dashboard_package_fields():
    job = _make_job()
    data = job.to_dict()

    required_fields = [
        "review_timeline_dashboard_package_report",
        "review_timeline_dashboard_package",
        "review_timeline_dashboard_package_id",
        "review_timeline_dashboard_package_status",
        "review_timeline_dashboard_review_status",
        "review_timeline_dashboard_approval_status",
        "review_timeline_dashboard_safety_status",
        "review_timeline_dashboard_can_proceed_to_execution",
        "review_timeline_dashboard_can_render",
        "review_timeline_dashboard_requires_manual_review",
        "review_timeline_dashboard_is_safe_for_future_execution",
        "review_timeline_dashboard_is_safe_for_render",
        "review_timeline_dashboard_summary",
        "review_timeline_dashboard_counters",
        "review_timeline_dashboard_item_cards",
        "review_timeline_dashboard_approval_panel",
        "review_timeline_dashboard_safety_panel",
        "review_timeline_dashboard_warnings",
        "review_timeline_dashboard_blocking_errors",
        "review_timeline_dashboard_actions",
    ]

    for field in required_fields:
        assert hasattr(job, field)
        assert field in data


def test_job_from_dict_preserves_review_timeline_dashboard_package_fields():
    job = Job.from_dict(
        {
            "job_id": "job_review_timeline_dashboard_from_dict",
            "job_type": "gaming",
            "channel_type": "gaming_main",
            "target_format": "short",
            "target_platforms": ["youtube"],
            "status": "routed",
            "mode": "normal",
            "autopublish_class": "manual_only",
            "confidence_score": 0.0,
            "validator_status": "not_validated",
            "review_timeline_dashboard_package_status": "ready_for_dashboard",
            "review_timeline_dashboard_package_id": "dashboard_package_test",
            "review_timeline_dashboard_can_render": True,
            "review_timeline_dashboard_is_safe_for_render": True,
            "review_timeline_dashboard_summary": {"total_items": 1},
            "review_timeline_dashboard_item_cards": [
                {"item_id": "review_timeline_item_0"}
            ],
            "review_timeline_dashboard_actions": ["review_timeline"],
        }
    )

    assert job.review_timeline_dashboard_package_status == "ready_for_dashboard"
    assert job.review_timeline_dashboard_package_id == "dashboard_package_test"
    assert job.review_timeline_dashboard_summary["total_items"] == 1
    assert len(job.review_timeline_dashboard_item_cards) == 1
    assert "review_timeline" in job.review_timeline_dashboard_actions

    assert job.review_timeline_dashboard_can_render is False
    assert job.review_timeline_dashboard_is_safe_for_render is False


def test_pipeline_imports_dashboard_package_runner():
    text = _text(ROOT / "core" / "gaming_pipeline.py")

    assert "from core.review_timeline_dashboard_package_runner import" in text
    assert "run_review_timeline_dashboard_package_for_job" in text
    assert "apply_review_timeline_dashboard_package_run_report_to_job" in text


def test_pipeline_runs_dashboard_package_after_timeline_safety_validator():
    text = _text(ROOT / "core" / "gaming_pipeline.py")

    assert text.index("run_review_timeline_dashboard_package_for_job(") > text.index(
        "run_timeline_safety_validator_for_job("
    )
    assert text.index(
        "apply_review_timeline_dashboard_package_run_report_to_job("
    ) > text.index("apply_timeline_safety_validator_run_report_to_job(")


def test_pipeline_dashboard_package_is_dashboard_only_and_no_render():
    text = _text(ROOT / "core" / "gaming_pipeline.py")
    start = text.index("run_review_timeline_dashboard_package_for_job(")
    block = text[start : start + 900]

    assert '"phase": "2B-35"' in block
    assert '"dashboard_only": True' in block
    assert '"media_unchanged": True' in block
    assert '"no_execution_in_2b_35": True' in block
    assert '"no_render_in_2b_35": True' in block

    forbidden = [
        "ffmpeg",
        ".render(",
        "RenderProcessor",
        "FinalRenderDriver",
        "apply_final_cutlist",
        "execute_final_cutlist",
        "delete_segment",
        "drop_segment",
        "remove_file",
        "delete_media",
    ]

    lower_block = block.lower()
    for word in forbidden:
        assert word.lower() not in lower_block, f"{word} found in 2B-35 block"