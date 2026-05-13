from pathlib import Path

from models.job import Job


ROOT = Path(__file__).resolve().parents[1]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _pipeline_timeline_approval_gate_block() -> str:
    text = _text(ROOT / "core" / "gaming_pipeline.py")
    start = text.index("# ── Timeline Approval Gate (2B-33)")
    end = text.index("# ── End Timeline Approval Gate", start)
    return text[start:end]


def _make_job():
    return Job.from_dict(
        {
            "job_id": "job_timeline_approval_pipeline",
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


def test_job_has_timeline_approval_gate_fields():
    job = _make_job()
    data = job.to_dict()

    required_fields = [
        "timeline_approval_gate_report",
        "timeline_approval_gate",
        "timeline_approval_gate_status",
        "timeline_approval_gate_id",
        "timeline_approval_status",
        "timeline_approval_requested_status",
        "timeline_approved_by",
        "timeline_rejected_by",
        "timeline_manual_change_reason",
        "timeline_can_proceed_to_execution",
        "timeline_can_render",
        "timeline_requires_human_approval",
        "timeline_approval_blocking_reasons",
        "timeline_approval_warnings",
    ]

    for field in required_fields:
        assert hasattr(job, field)
        assert field in data


def test_pipeline_contains_timeline_approval_gate_block():
    block = _pipeline_timeline_approval_gate_block()

    assert "TIMELINE_APPROVAL_GATE_APPROVED" in block
    assert "TIMELINE_APPROVAL_GATE_PENDING_REVIEW" in block
    assert "TIMELINE_APPROVAL_GATE_BLOCKED" in block
    assert "TIMELINE_APPROVAL_GATE_FAILED" in block

    assert "run_timeline_approval_gate_for_job(" in block
    assert "apply_timeline_approval_gate_run_report_to_job(" in block

    assert "review_only" in block
    assert "approval_gate_only" in block
    assert "media_unchanged" in block
    assert "no_execution_in_2b_33" in block


def test_pipeline_timeline_approval_gate_runs_after_review_timeline_plan():
    text = _text(ROOT / "core" / "gaming_pipeline.py")

    assert text.index("# ── Timeline Approval Gate (2B-33)") > text.index(
        "# ── Review Timeline Plan (2B-32)"
    )
    assert text.index("run_timeline_approval_gate_for_job(") > text.index(
        "run_review_timeline_plan_for_job("
    )


def test_pipeline_approval_gate_does_not_execute_media_work():
    block = _pipeline_timeline_approval_gate_block().lower()

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
        assert word not in block, f"{word} found in timeline approval gate block"


def test_pipeline_approval_gate_keeps_render_false_in_2b_33():
    block = _pipeline_timeline_approval_gate_block()

    assert '"can_render"' in block
    assert '"can_proceed_to_execution"' in block
    assert "no_execution_in_2b_33" in block
