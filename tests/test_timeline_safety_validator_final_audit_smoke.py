from pathlib import Path

from core.timeline_safety_validator import TimelineSafetyValidator
from core.timeline_safety_validator_signal_adapter import (
    adapt_timeline_safety_validator_report_to_signals,
)
from models.job import Job
from models.timeline_safety_validator import (
    TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34,
    TIMELINE_SAFETY_STATUS_BLOCKED,
    TIMELINE_SAFETY_STATUS_PASSED,
)


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    ROOT / "models" / "timeline_safety_validator.py",
    ROOT / "core" / "timeline_safety_validator.py",
    ROOT / "core" / "timeline_safety_validator_runner.py",
    ROOT / "core" / "timeline_safety_validator_signal_adapter.py",
]

CHANGED_PRODUCT_FILES = PRODUCT_FILES + [
    ROOT / "models" / "job.py",
    ROOT / "core" / "gaming_pipeline.py",
    ROOT / "core" / "unified_edit_signal_registry.py",
]

TEST_FILES = [
    ROOT / "tests" / "test_timeline_safety_validator_smoke.py",
    ROOT / "tests" / "test_timeline_safety_validator_runner_smoke.py",
    ROOT / "tests" / "test_timeline_safety_validator_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_timeline_safety_validator_registry_integration_smoke.py",
    ROOT / "tests" / "test_timeline_safety_validator_final_audit_smoke.py",
]

FORBIDDEN_OPERATIONAL_TERMS = [
    "subprocess",
    "os.system",
    "ffmpeg",
    "render_video",
    "execute_final_cutlist",
    "apply_final_cutlist",
    "timelinebuilder",
    "highlightselector",
    "moviepy",
    "cv2.videowriter",
    "write_videofile",
    "mute",
    "delete_media",
    "remove_file",
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
]

ALLOWED_RENDER_FIELD_TEXT = [
    "is_safe_for_render",
    "timeline_is_safe_for_render",
    "timeline_can_render",
    "can_render",
    "no_render_in_2b_34",
    "render_not_allowed_in_2b_34",
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _pipeline_timeline_safety_validator_block() -> str:
    text = _text(ROOT / "core" / "gaming_pipeline.py")
    start = text.index("Timeline Safety Validator (2B-34)")
    end = text.index("End Timeline Safety Validator", start)
    return text[start:end]


def _make_job(extra=None):
    data = {
        "job_id": "job_timeline_safety_final_audit",
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


def _item(extra=None):
    data = {
        "timeline_item_id": "item_1",
        "start_seconds": 0.0,
        "end_seconds": 5.0,
        "source_start_seconds": 0.0,
        "source_end_seconds": 5.0,
        "duration_seconds": 5.0,
        "action": "keep_review",
        "protection_status": "normal",
        "censor_sfx_required": False,
        "continuity_blocked": False,
        "review_required": True,
        "safety_flags": ["review_only", "human_review"],
        "metadata": {
            "safety_flags": ["review_only", "human_review"],
        },
    }
    if extra:
        data.update(extra)
    return data


def _plan(items=None):
    if items is None:
        items = [_item()]

    return {
        "plan_id": "review_timeline_plan_final_audit",
        "job_id": "job_timeline_safety_final_audit",
        "status": "pending_review",
        "items": items,
        "total_items": len(items),
        "warnings": [],
        "errors": [],
        "metadata": {
            "review_only": True,
            "approval_required": True,
        },
    }


def _job(plan=None, **extra):
    if plan is None:
        plan = _plan()

    data = {
        "job_id": "job_timeline_safety_final_audit",
        "review_timeline_plan": plan,
        "review_timeline_plan_items": plan.get("items", []),
        "timeline_approval_gate": {
            "approval_gate_id": "timeline_approval_gate_final_audit",
        },
        "timeline_approval_status": "approved",
        "timeline_can_proceed_to_execution": True,
        "timeline_can_render": False,
    }
    data.update(extra)
    return data


def test_all_2b34_product_files_exist():
    for path in PRODUCT_FILES:
        assert path.exists(), str(path)


def test_all_2b34_test_files_exist():
    for path in TEST_FILES:
        assert path.exists(), str(path)


def test_job_has_timeline_safety_validator_fields_final_audit():
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


def test_valid_timeline_passes_future_execution_but_never_render():
    report = TimelineSafetyValidator().validate(_job())
    validation = report.timeline_safety_validation

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_PASSED
    assert validation.is_safe_for_future_execution is True
    assert validation.is_safe_for_render is False
    assert report.is_safe_for_render is False


def test_render_true_is_blocked_even_when_approval_is_approved():
    report = TimelineSafetyValidator().validate(
        _job(
            timeline_can_render=True,
        )
    )
    validation = report.timeline_safety_validation

    assert validation.validation_status == TIMELINE_SAFETY_STATUS_BLOCKED
    assert validation.is_safe_for_future_execution is False
    assert validation.is_safe_for_render is False
    assert TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34 in (
        validation.blocking_errors
    )


def test_timeline_safety_signal_adapter_marks_no_execution_and_no_render():
    report = TimelineSafetyValidator().validate(_job())

    result = adapt_timeline_safety_validator_report_to_signals(report)

    assert result.signal_count == 1

    signal = result.signals[0]
    assert signal["signal_type"] == "timeline_safety_passed"
    assert signal["metadata"]["is_safe_for_future_execution"] is True
    assert signal["metadata"]["is_safe_for_render"] is False
    assert signal["metadata"]["safety_validator_only"] is True
    assert signal["metadata"]["media_unchanged"] is True
    assert signal["metadata"]["no_execution_in_2b_34"] is True
    assert signal["metadata"]["no_render_in_2b_34"] is True


def test_pipeline_timeline_safety_validator_block_exists_after_2b33():
    text = _text(ROOT / "core" / "gaming_pipeline.py")
    block = _pipeline_timeline_safety_validator_block()

    assert "TIMELINE_SAFETY_VALIDATOR_PASSED" in block
    assert "TIMELINE_SAFETY_VALIDATOR_BLOCKED" in block
    assert "run_timeline_safety_validator_for_job(" in block
    assert "apply_timeline_safety_validator_run_report_to_job(" in block

    assert text.index("Review Timeline Plan (2B-32)") < text.index(
        "Timeline Approval Gate (2B-33)"
    )
    assert text.index("Timeline Approval Gate (2B-33)") < text.index(
        "Timeline Safety Validator (2B-34)"
    )


def test_registry_contains_timeline_safety_validator_source():
    text = _text(ROOT / "core" / "unified_edit_signal_registry.py")

    assert 'SOURCE_TIMELINE_SAFETY_VALIDATOR = "timeline_safety_validator"' in text
    assert "adapt_timeline_safety_validator_report_to_signals" in text
    assert "timeline_safety_validator_report" in text
    assert "timeline_safety_validator" in text


def test_2b34_product_files_do_not_contain_forbidden_operational_terms():
    for path in PRODUCT_FILES:
        lowered = _text(path).lower()

        for word in FORBIDDEN_OPERATIONAL_TERMS:
            assert word not in lowered, f"{word} found in {path}"


def test_pipeline_timeline_safety_block_has_no_forbidden_operational_terms():
    lowered = _pipeline_timeline_safety_validator_block().lower()

    for word in FORBIDDEN_OPERATIONAL_TERMS:
        assert word not in lowered, f"{word} found in timeline safety block"


def test_2b34_files_have_no_bom_and_end_with_newline():
    for path in CHANGED_PRODUCT_FILES + TEST_FILES:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), str(path)
        assert raw.endswith(b"\n"), str(path)


def test_no_hard_media_paths_in_2b34_product_files():
    forbidden_path_fragments = [
        "d:\\",
        "c:\\",
        "/mnt/",
        "/users/",
        "/home/",
        "exports/",
        "output/",
    ]

    for path in PRODUCT_FILES:
        lowered = _text(path).lower()
        for fragment in forbidden_path_fragments:
            assert fragment not in lowered, f"{fragment} found in {path}"


def test_render_word_only_appears_as_allowed_safety_field_text():
    for path in PRODUCT_FILES:
        lowered = _text(path).lower()

        if "render" not in lowered:
            continue

        cleaned = lowered
        for allowed in ALLOWED_RENDER_FIELD_TEXT:
            cleaned = cleaned.replace(allowed, "")

        assert "render" not in cleaned, f"unexpected render usage found in {path}"
