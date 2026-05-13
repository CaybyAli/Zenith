from pathlib import Path

from models.job import Job


ROOT = Path(__file__).resolve().parents[1]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _pipeline_timeline_safety_validator_block() -> str:
    text = _text(ROOT / "core" / "gaming_pipeline.py")
    start = text.index("Timeline Safety Validator (2B-34)")
    end = text.index("End Timeline Safety Validator", start)
    return text[start:end]


def _make_job():
    return Job.from_dict(
        {
            "job_id": "job_timeline_safety_pipeline",
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


def test_job_has_timeline_safety_validator_fields():
    job = _make_job()
    data = job.to_dict()

    required_fields = [
        "timeline_safety_validator_report",
        "timeline_safety_validator",
        "timeline_safety_validation_id",
        "timeline_safety_validation_status",
        "timeline_is_safe_for_future_execution",
        "timeline_is_safe_for_render",
        "timeline_safety_requires_manual_review",
        "timeline_safety_blocking_errors",
        "timeline_safety_warnings",
        "timeline_safety_item_results",
        "timeline_safety_invalid_timing_count",
        "timeline_safety_overlap_count",
        "timeline_safety_gap_count",
        "timeline_safety_protected_violation_count",
        "timeline_safety_censor_violation_count",
        "timeline_safety_continuity_violation_count",
        "timeline_safety_approval_violation_count",
    ]

    for field in required_fields:
        assert hasattr(job, field)
        assert field in data


def test_pipeline_contains_timeline_safety_validator_block():
    block = _pipeline_timeline_safety_validator_block()

    assert "TIMELINE_SAFETY_VALIDATOR_PASSED" in block
    assert "TIMELINE_SAFETY_VALIDATOR_PASSED_WITH_WARNINGS" in block
    assert "TIMELINE_SAFETY_VALIDATOR_BLOCKED" in block
    assert "TIMELINE_SAFETY_VALIDATOR_FAILED" in block

    assert "run_timeline_safety_validator_for_job(" in block
    assert "apply_timeline_safety_validator_run_report_to_job(" in block

    assert "review_only" in block
    assert "safety_validator_only" in block
    assert "media_unchanged" in block
    assert "no_execution_in_2b_34" in block
    assert "no_render_in_2b_34" in block


def test_pipeline_timeline_safety_validator_runs_after_approval_gate():
    text = _text(ROOT / "core" / "gaming_pipeline.py")

    assert text.index("Timeline Safety Validator (2B-34)") > text.index(
        "Timeline Approval Gate (2B-33)"
    )
    assert text.index("run_timeline_safety_validator_for_job(") > text.index(
        "run_timeline_approval_gate_for_job("
    )


def test_pipeline_order_is_2b32_then_2b33_then_2b34():
    text = _text(ROOT / "core" / "gaming_pipeline.py")

    index_2b32 = text.index("Review Timeline Plan (2B-32)")
    index_2b33 = text.index("Timeline Approval Gate (2B-33)")
    index_2b34 = text.index("Timeline Safety Validator (2B-34)")

    assert index_2b32 < index_2b33 < index_2b34


def test_pipeline_safety_validator_does_not_execute_media_work():
    block = _pipeline_timeline_safety_validator_block().lower()

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
        "mute",
        "delete_media",
        "remove_file",
    ]

    for word in forbidden:
        assert word not in block, f"{word} found in timeline safety block"


def test_pipeline_safety_validator_keeps_render_false_in_2b_34():
    block = _pipeline_timeline_safety_validator_block()

    assert '"is_safe_for_render": False' in block
    assert "no_render_in_2b_34" in block
    assert "timeline_safety_validator_review_only" in block
