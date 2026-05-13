from pathlib import Path

from core.review_timeline_plan_builder import build_review_timeline_plan
from core.review_timeline_plan_signal_adapter import (
    adapt_review_timeline_plan_report_to_signals,
)
from models.final_cut_list import (
    FINAL_ACTION_BLOCKED_BY_CONTINUITY,
    FINAL_ACTION_CENSOR_KEEP,
    FINAL_ACTION_PROTECT,
    FINAL_ACTION_REMOVE_REVIEW,
    FINAL_ACTION_TRIM_REVIEW,
)
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    ROOT / "models" / "review_timeline_plan.py",
    ROOT / "core" / "review_timeline_plan_builder.py",
    ROOT / "core" / "review_timeline_plan_runner.py",
    ROOT / "core" / "review_timeline_plan_signal_adapter.py",
]

CHANGED_PRODUCT_FILES = PRODUCT_FILES + [
    ROOT / "models" / "job.py",
    ROOT / "core" / "gaming_pipeline.py",
    ROOT / "core" / "unified_edit_signal_registry.py",
]

TEST_FILES = [
    ROOT / "tests" / "test_review_timeline_plan_builder_smoke.py",
    ROOT / "tests" / "test_review_timeline_plan_runner_smoke.py",
    ROOT / "tests" / "test_review_timeline_plan_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_review_timeline_plan_registry_integration_smoke.py",
    ROOT / "tests" / "test_review_timeline_plan_final_audit_smoke.py",
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
]


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
            "job_id": "job_review_timeline_final_audit",
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


def _final_item(action: str, index: int):
    return {
        "final_item_id": f"final_{index}",
        "source_item_id": f"cut_{index}",
        "segment_id": f"seg_{index}",
        "start_seconds": float(index * 10),
        "end_seconds": float(index * 10 + 5),
        "duration_seconds": 5.0,
        "final_action": action,
        "final_confidence": 0.85,
        "priority": "high",
        "continuity_blocked": action == FINAL_ACTION_BLOCKED_BY_CONTINUITY,
        "is_protected": action == FINAL_ACTION_PROTECT,
        "is_censor_keep": action == FINAL_ACTION_CENSOR_KEEP,
        "is_review_required": True,
        "reason": f"reason {action}",
        "decision_basis": {"test": True},
        "source_signal_ids": [f"sig_{index}"],
    }


def test_all_2b32_product_files_exist():
    for path in PRODUCT_FILES:
        assert path.exists(), str(path)


def test_all_2b32_test_files_exist():
    for path in TEST_FILES:
        assert path.exists(), str(path)


def test_job_has_review_timeline_plan_fields_final_audit():
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


def test_review_timeline_plan_preserves_safety_rules():
    plan = build_review_timeline_plan(
        final_cut_list_items=[
            _final_item(FINAL_ACTION_REMOVE_REVIEW, 1),
            _final_item(FINAL_ACTION_TRIM_REVIEW, 2),
            _final_item(FINAL_ACTION_PROTECT, 3),
            _final_item(FINAL_ACTION_CENSOR_KEEP, 4),
            _final_item(FINAL_ACTION_BLOCKED_BY_CONTINUITY, 5),
        ],
        job_id="job_review_timeline_safety_audit",
    )

    by_action = {item.action: item for item in plan.items}

    assert by_action["remove_review"].review_required is True
    assert "human_review_remove_candidate" in by_action["remove_review"].safety_flags

    assert by_action["trim_review"].review_required is True
    assert "trim_requires_review" in by_action["trim_review"].safety_flags

    assert by_action["protect"].protection_status == "protected"
    assert "protected_context_preserved" in by_action["protect"].safety_flags

    assert by_action["censor_keep"].censor_sfx_required is True
    assert by_action["censor_keep"].protection_status == "censor_protected"

    assert by_action["blocked_by_continuity"].continuity_blocked is True
    assert by_action["blocked_by_continuity"].review_required is True


def test_review_timeline_signal_adapter_marks_review_only():
    plan = build_review_timeline_plan(
        final_cut_list_items=[
            _final_item(FINAL_ACTION_REMOVE_REVIEW, 1),
            _final_item(FINAL_ACTION_CENSOR_KEEP, 2),
        ],
        job_id="job_review_timeline_signal_audit",
    )

    result = adapt_review_timeline_plan_report_to_signals(
        {
            "items": [item.to_dict() for item in plan.items],
        }
    )

    assert result.signal_count == 2
    for signal in result.signals:
        assert signal["metadata"]["review_only"] is True
        assert signal["metadata"]["approval_required"] is True


def test_pipeline_review_timeline_block_exists_after_finalizer():
    text = _text(ROOT / "core" / "gaming_pipeline.py")
    block = _pipeline_review_timeline_block()

    assert "REVIEW_TIMELINE_PLAN_STARTED" in block
    assert "REVIEW_TIMELINE_PLAN_DONE" in block
    assert text.index("REVIEW_TIMELINE_PLAN_STARTED") > text.index(
        "CUT_LIST_FINALIZATION_DONE"
    )


def test_registry_contains_review_timeline_plan_source():
    text = _text(ROOT / "core" / "unified_edit_signal_registry.py")

    assert 'SOURCE_REVIEW_TIMELINE_PLAN = "review_timeline_plan"' in text
    assert "adapt_review_timeline_plan_report_to_signals" in text
    assert "review_timeline_plan_report" in text
    assert "review_timeline_plan_items" in text


def test_2b32_product_files_do_not_contain_forbidden_operational_terms():
    for path in PRODUCT_FILES:
        lowered = _text(path).lower()

        for word in FORBIDDEN_OPERATIONAL_TERMS:
            assert word not in lowered, f"{word} found in {path}"


def test_pipeline_review_timeline_block_has_no_forbidden_operational_terms():
    lowered = _pipeline_review_timeline_block().lower()

    for word in FORBIDDEN_OPERATIONAL_TERMS:
        assert word not in lowered, f"{word} found in review timeline plan block"


def test_2b32_files_have_no_bom_and_end_with_newline():
    for path in CHANGED_PRODUCT_FILES + TEST_FILES:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), str(path)
        assert raw.endswith(b"\n"), str(path)
