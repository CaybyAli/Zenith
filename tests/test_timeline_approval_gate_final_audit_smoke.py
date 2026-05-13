from pathlib import Path

from core.timeline_approval_gate import build_timeline_approval_gate
from core.timeline_approval_gate_signal_adapter import (
    adapt_timeline_approval_gate_report_to_signals,
)
from models.job import Job
from models.timeline_approval_gate import (
    TIMELINE_APPROVAL_GATE_STATUS_APPROVED,
    TIMELINE_APPROVAL_GATE_STATUS_BLOCKED,
    TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW,
    TIMELINE_APPROVAL_REASON_CONTINUITY_BLOCKED,
    TIMELINE_APPROVAL_REASON_MISSING_REVIEW_TIMELINE_PLAN,
    TIMELINE_APPROVAL_STATUS_APPROVED,
    TIMELINE_APPROVAL_STATUS_BLOCKED,
    TIMELINE_APPROVAL_STATUS_PENDING_REVIEW,
)


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    ROOT / "models" / "timeline_approval_gate.py",
    ROOT / "core" / "timeline_approval_gate.py",
    ROOT / "core" / "timeline_approval_gate_runner.py",
    ROOT / "core" / "timeline_approval_gate_signal_adapter.py",
]

CHANGED_PRODUCT_FILES = PRODUCT_FILES + [
    ROOT / "models" / "job.py",
    ROOT / "core" / "gaming_pipeline.py",
    ROOT / "core" / "unified_edit_signal_registry.py",
]

TEST_FILES = [
    ROOT / "tests" / "test_timeline_approval_gate_smoke.py",
    ROOT / "tests" / "test_timeline_approval_gate_runner_smoke.py",
    ROOT / "tests" / "test_timeline_approval_gate_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_timeline_approval_gate_registry_integration_smoke.py",
    ROOT / "tests" / "test_timeline_approval_gate_final_audit_smoke.py",
]

FORBIDDEN_OPERATIONAL_TERMS = [
    "apply_final_cutlist",
    "execute_final_cutlist",
    "timeline_apply_now",
    "force_cut",
    "auto_cut",
    "auto_trim",
    "auto_highlight",
    "highlight_now",
    "auto_hook",
    "auto_mute",
    "censor_now",
    "delete_segment",
    "drop_segment",
    "remove_now",
    "hard_remove",
    "ffmpeg",
    "timelinebuilder",
    "highlightselector",
    ".render(",
]


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
            "job_id": "job_timeline_approval_final_audit",
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


def _review_timeline_plan(extra=None):
    data = {
        "plan_id": "review_timeline_plan_final_audit",
        "job_id": "job_timeline_approval_final_audit",
        "status": "pending_review",
        "items": [
            {
                "timeline_item_id": "item_1",
                "source_segment_id": "seg_1",
                "action": "keep_review",
                "protection_status": "normal",
                "review_required": True,
                "censor_sfx_required": False,
                "continuity_blocked": False,
            }
        ],
        "total_items": 1,
        "review_required_count": 1,
        "protected_count": 0,
        "censor_required_count": 0,
        "continuity_blocked_count": 0,
        "warnings": [],
        "metadata": {
            "review_only": True,
            "approval_required": True,
        },
    }
    if extra:
        data.update(extra)
    return data


def test_all_2b33_product_files_exist():
    for path in PRODUCT_FILES:
        assert path.exists(), str(path)


def test_all_2b33_test_files_exist():
    for path in TEST_FILES:
        assert path.exists(), str(path)


def test_job_has_timeline_approval_gate_fields_final_audit():
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


def test_missing_plan_and_continuity_blocks_are_strict():
    missing_gate = build_timeline_approval_gate(
        review_timeline_plan=None,
        job_id="job_missing_plan_final_audit",
    )

    assert missing_gate.approval_status == TIMELINE_APPROVAL_STATUS_BLOCKED
    assert missing_gate.gate_status == TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
    assert missing_gate.can_proceed_to_execution is False
    assert missing_gate.can_render is False
    assert TIMELINE_APPROVAL_REASON_MISSING_REVIEW_TIMELINE_PLAN in (
        missing_gate.blocking_reasons
    )

    continuity_gate = build_timeline_approval_gate(
        review_timeline_plan=_review_timeline_plan(
            {
                "continuity_blocked_count": 1,
            }
        ),
        job_id="job_continuity_final_audit",
        approval_status=TIMELINE_APPROVAL_STATUS_APPROVED,
        approved_by="reviewer",
    )

    assert continuity_gate.approval_status == TIMELINE_APPROVAL_STATUS_BLOCKED
    assert continuity_gate.gate_status == TIMELINE_APPROVAL_GATE_STATUS_BLOCKED
    assert continuity_gate.can_proceed_to_execution is False
    assert continuity_gate.can_render is False
    assert continuity_gate.approved_by is None
    assert TIMELINE_APPROVAL_REASON_CONTINUITY_BLOCKED in (
        continuity_gate.blocking_reasons
    )


def test_pending_and_approved_gate_are_safe():
    pending_gate = build_timeline_approval_gate(
        review_timeline_plan=_review_timeline_plan(),
        job_id="job_pending_final_audit",
    )

    assert pending_gate.approval_status == TIMELINE_APPROVAL_STATUS_PENDING_REVIEW
    assert pending_gate.gate_status == TIMELINE_APPROVAL_GATE_STATUS_PENDING_REVIEW
    assert pending_gate.can_proceed_to_execution is False
    assert pending_gate.can_render is False
    assert pending_gate.requires_human_approval is True

    approved_gate = build_timeline_approval_gate(
        review_timeline_plan=_review_timeline_plan(),
        job_id="job_approved_final_audit",
        approval_status=TIMELINE_APPROVAL_STATUS_APPROVED,
        approved_by="reviewer",
    )

    assert approved_gate.approval_status == TIMELINE_APPROVAL_STATUS_APPROVED
    assert approved_gate.gate_status == TIMELINE_APPROVAL_GATE_STATUS_APPROVED
    assert approved_gate.can_proceed_to_execution is True
    assert approved_gate.can_render is False
    assert approved_gate.requires_human_approval is False
    assert approved_gate.metadata["future_allowed_after_approval"] is True
    assert approved_gate.metadata["can_render_in_2b_33"] is False


def test_timeline_approval_signal_adapter_marks_no_execution():
    gate = build_timeline_approval_gate(
        review_timeline_plan=_review_timeline_plan(),
        job_id="job_signal_final_audit",
        approval_status=TIMELINE_APPROVAL_STATUS_APPROVED,
        approved_by="reviewer",
    )

    result = adapt_timeline_approval_gate_report_to_signals(
        {
            "timeline_approval_gate": gate.to_dict(),
        }
    )

    assert result.signal_count == 1

    signal = result.signals[0]
    assert signal["signal_type"] == "timeline_approval_approved"
    assert signal["metadata"]["can_proceed_to_execution"] is True
    assert signal["metadata"]["can_render"] is False
    assert signal["metadata"]["approval_gate_only"] is True
    assert signal["metadata"]["media_unchanged"] is True
    assert signal["metadata"]["no_execution_in_2b_33"] is True


def test_pipeline_timeline_approval_gate_block_exists_after_2b32():
    text = _text(ROOT / "core" / "gaming_pipeline.py")
    block = _pipeline_timeline_approval_gate_block()

    assert "TIMELINE_APPROVAL_GATE_PENDING_REVIEW" in block
    assert "TIMELINE_APPROVAL_GATE_APPROVED" in block
    assert "TIMELINE_APPROVAL_GATE_BLOCKED" in block
    assert "run_timeline_approval_gate_for_job(" in block
    assert "apply_timeline_approval_gate_run_report_to_job(" in block

    assert text.index("# ── Timeline Approval Gate (2B-33)") > text.index(
        "# ── Review Timeline Plan (2B-32)"
    )


def test_registry_contains_timeline_approval_gate_source():
    text = _text(ROOT / "core" / "unified_edit_signal_registry.py")

    assert 'SOURCE_TIMELINE_APPROVAL_GATE = "timeline_approval_gate"' in text
    assert "adapt_timeline_approval_gate_report_to_signals" in text
    assert "timeline_approval_gate_report" in text
    assert "timeline_approval_gate" in text


def test_2b33_product_files_do_not_contain_forbidden_operational_terms():
    for path in PRODUCT_FILES:
        lowered = _text(path).lower()

        for word in FORBIDDEN_OPERATIONAL_TERMS:
            assert word not in lowered, f"{word} found in {path}"


def test_pipeline_timeline_approval_gate_block_has_no_forbidden_operational_terms():
    lowered = _pipeline_timeline_approval_gate_block().lower()

    for word in FORBIDDEN_OPERATIONAL_TERMS:
        assert word not in lowered, f"{word} found in timeline approval gate block"


def test_2b33_files_have_no_bom_and_end_with_newline():
    for path in CHANGED_PRODUCT_FILES + TEST_FILES:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), str(path)
        assert raw.endswith(b"\n"), str(path)
