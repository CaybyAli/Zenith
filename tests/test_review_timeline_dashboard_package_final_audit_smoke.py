from pathlib import Path

from core.review_timeline_dashboard_package_runner import (
    apply_review_timeline_dashboard_package_run_report_to_job,
    run_review_timeline_dashboard_package_for_job,
)
from core.review_timeline_dashboard_package_signal_adapter import (
    adapt_review_timeline_dashboard_package_report_to_signals,
)
from models.review_timeline_dashboard_package import (
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
)


ROOT = Path(__file__).resolve().parents[1]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _item():
    return {
        "timeline_item_id": "review_timeline_item_final_audit_0",
        "source_segment_id": "segment_final_audit_0",
        "start_seconds": 0.0,
        "end_seconds": 6.0,
        "source_start_seconds": 0.0,
        "source_end_seconds": 6.0,
        "duration_seconds": 6.0,
        "action": "keep_review",
        "final_decision": "keep",
        "protection_status": "normal",
        "censor_sfx_required": False,
        "continuity_blocked": False,
        "review_required": True,
        "review_reason": "needs_human_review",
        "safety_flags": ["review_only", "human_review"],
        "notes": [],
        "metadata": {},
    }


def _job():
    item = _item()

    plan = {
        "plan_id": "review_timeline_plan_final_audit",
        "job_id": "job_dashboard_final_audit",
        "status": "pending_review",
        "items": [item],
        "total_items": 1,
        "total_duration_seconds": 6.0,
        "review_required_count": 1,
        "protected_count": 0,
        "censor_required_count": 0,
        "continuity_blocked_count": 0,
        "warnings": [],
        "errors": [],
        "metadata": {"review_only": True},
    }

    return {
        "job_id": "job_dashboard_final_audit",
        "review_timeline_plan": plan,
        "review_timeline_plan_report": {
            "status": "pending_review",
            "review_timeline_plan": plan,
            "items": [item],
        },
        "review_timeline_plan_items": [item],
        "review_timeline_plan_status": "pending_review",
        "review_timeline_plan_id": "review_timeline_plan_final_audit",
        "timeline_approval_gate": {
            "approval_gate_id": "timeline_approval_gate_final_audit",
            "job_id": "job_dashboard_final_audit",
            "approval_status": "pending_review",
            "gate_status": "pending_review",
            "can_proceed_to_execution": False,
            "can_render": False,
            "requires_human_approval": True,
            "blocking_reasons": [],
            "warnings": [],
        },
        "timeline_approval_gate_id": "timeline_approval_gate_final_audit",
        "timeline_approval_status": "pending_review",
        "timeline_can_proceed_to_execution": False,
        "timeline_can_render": False,
        "timeline_approval_blocking_reasons": [],
        "timeline_approval_warnings": [],
        "timeline_safety_validator": {
            "safety_validation_id": "timeline_safety_validation_final_audit",
            "job_id": "job_dashboard_final_audit",
            "source_review_timeline_plan_id": "review_timeline_plan_final_audit",
            "source_timeline_approval_gate_id": "timeline_approval_gate_final_audit",
            "validation_status": "passed",
            "is_safe_for_future_execution": False,
            "is_safe_for_render": False,
            "requires_manual_review": True,
            "blocking_errors": [],
            "warnings": [],
            "item_results": [
                {
                    "item_index": 0,
                    "item_id": "review_timeline_item_final_audit_0",
                    "action": "keep_review",
                    "protection_status": "normal",
                    "start_seconds": 0.0,
                    "end_seconds": 6.0,
                    "duration_seconds": 6.0,
                    "is_valid": True,
                    "blocking_errors": [],
                    "warnings": [],
                    "metadata": {},
                }
            ],
            "total_items_checked": 1,
            "invalid_timing_count": 0,
            "overlap_count": 0,
            "gap_count": 0,
            "protected_violation_count": 0,
            "censor_violation_count": 0,
            "continuity_violation_count": 0,
            "approval_violation_count": 0,
            "future_execution_safety_status": "requires_approval_or_review",
            "metadata": {"safety_validator_only": True},
        },
        "timeline_safety_validation_id": "timeline_safety_validation_final_audit",
        "timeline_safety_validation_status": "passed",
        "timeline_is_safe_for_future_execution": False,
        "timeline_is_safe_for_render": False,
        "timeline_safety_requires_manual_review": True,
        "timeline_safety_blocking_errors": [],
        "timeline_safety_warnings": [],
    }


def test_2b35_files_exist():
    required_files = [
        ROOT / "models" / "review_timeline_dashboard_package.py",
        ROOT / "core" / "review_timeline_dashboard_package_builder.py",
        ROOT / "core" / "review_timeline_dashboard_package_runner.py",
        ROOT / "core" / "review_timeline_dashboard_package_signal_adapter.py",
    ]

    for path in required_files:
        assert path.exists(), f"missing file: {path}"


def test_2b35_builds_and_applies_dashboard_package_without_render_permission():
    job = _job()

    report = run_review_timeline_dashboard_package_for_job(job)
    updated_job = apply_review_timeline_dashboard_package_run_report_to_job(
        job,
        report,
    )

    assert report.status == REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY
    assert report.dashboard_package is not None
    assert report.dashboard_package.metadata["dashboard_only"] is True
    assert report.dashboard_package.metadata["media_unchanged"] is True
    assert report.dashboard_package.metadata["no_execution_in_2b_35"] is True
    assert report.dashboard_package.metadata["no_render_in_2b_35"] is True

    assert updated_job["review_timeline_dashboard_package_status"] == (
        REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY
    )
    assert updated_job["review_timeline_dashboard_can_render"] is False
    assert updated_job["review_timeline_dashboard_is_safe_for_render"] is False
    assert updated_job["review_timeline_dashboard_summary"]["total_items"] == 1
    assert len(updated_job["review_timeline_dashboard_item_cards"]) == 1


def test_2b35_signal_adapter_exports_dashboard_only_signals():
    report = run_review_timeline_dashboard_package_for_job(_job())
    result = adapt_review_timeline_dashboard_package_report_to_signals(report)

    signal_types = {signal["signal_type"] for signal in result.signals}

    assert "review_timeline_dashboard_package_ready" in signal_types
    assert "review_timeline_dashboard_item_card" in signal_types

    for signal in result.signals:
        assert signal["metadata"]["dashboard_only"] is True
        assert signal["metadata"]["media_unchanged"] is True
        assert signal["metadata"]["no_execution_in_2b_35"] is True
        assert signal["metadata"]["no_render_in_2b_35"] is True


def test_2b35_is_connected_to_pipeline_and_registry():
    pipeline_text = _text(ROOT / "core" / "gaming_pipeline.py")
    registry_text = _text(ROOT / "core" / "unified_edit_signal_registry.py")

    assert "run_review_timeline_dashboard_package_for_job(" in pipeline_text
    assert "apply_review_timeline_dashboard_package_run_report_to_job(" in pipeline_text
    assert pipeline_text.index(
        "run_review_timeline_dashboard_package_for_job("
    ) > pipeline_text.index("run_timeline_safety_validator_for_job(")

    assert "adapt_review_timeline_dashboard_package_report_to_signals" in registry_text
    assert "SOURCE_REVIEW_TIMELINE_DASHBOARD_PACKAGE" in registry_text
    assert "review_timeline_dashboard_package_report" in registry_text


def test_2b35_does_not_contain_media_execution_calls():
    files_to_check = [
        ROOT / "models" / "review_timeline_dashboard_package.py",
        ROOT / "core" / "review_timeline_dashboard_package_builder.py",
        ROOT / "core" / "review_timeline_dashboard_package_runner.py",
        ROOT / "core" / "review_timeline_dashboard_package_signal_adapter.py",
    ]

    forbidden = [
        "ffmpeg",
        "subprocess",
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

    for path in files_to_check:
        text = _text(path).lower()
        for word in forbidden:
            assert word.lower() not in text, f"{word} found in {path}"