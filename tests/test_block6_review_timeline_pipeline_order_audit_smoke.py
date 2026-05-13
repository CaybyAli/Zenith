from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = ROOT / "core" / "gaming_pipeline.py"


def _pipeline_text() -> str:
    return PIPELINE_PATH.read_text(encoding="utf-8")


def _index_or_fail(text: str, token: str) -> int:
    index = text.find(token)
    assert index != -1, f"Missing token in gaming_pipeline.py: {token}"
    return index


def test_block6_pipeline_runs_review_timeline_modules_in_safe_order() -> None:
    text = _pipeline_text()

    review_plan_index = _index_or_fail(
        text,
        "run_review_timeline_plan_for_job",
    )
    approval_gate_index = _index_or_fail(
        text,
        "run_timeline_approval_gate_for_job",
    )
    safety_validator_index = _index_or_fail(
        text,
        "run_timeline_safety_validator_for_job",
    )
    dashboard_package_index = _index_or_fail(
        text,
        "run_review_timeline_dashboard_package_for_job",
    )

    assert review_plan_index < approval_gate_index
    assert approval_gate_index < safety_validator_index
    assert safety_validator_index < dashboard_package_index


def test_block6_pipeline_blocks_dashboard_before_safety_validator() -> None:
    text = _pipeline_text()

    safety_validator_index = _index_or_fail(
        text,
        "run_timeline_safety_validator_for_job",
    )
    dashboard_package_index = _index_or_fail(
        text,
        "run_review_timeline_dashboard_package_for_job",
    )

    assert safety_validator_index < dashboard_package_index


def test_block6_pipeline_blocks_safety_validator_before_approval_gate() -> None:
    text = _pipeline_text()

    approval_gate_index = _index_or_fail(
        text,
        "run_timeline_approval_gate_for_job",
    )
    safety_validator_index = _index_or_fail(
        text,
        "run_timeline_safety_validator_for_job",
    )

    assert approval_gate_index < safety_validator_index


def test_block6_pipeline_blocks_approval_gate_before_review_plan() -> None:
    text = _pipeline_text()

    review_plan_index = _index_or_fail(
        text,
        "run_review_timeline_plan_for_job",
    )
    approval_gate_index = _index_or_fail(
        text,
        "run_timeline_approval_gate_for_job",
    )

    assert review_plan_index < approval_gate_index


def test_block6_pipeline_contains_required_safety_metadata() -> None:
    text = _pipeline_text()

    required_tokens = [
        "review_only",
        "approval_gate_only",
        "safety_validator_only",
        "dashboard_only",
        "media_unchanged",
        "no_execution_in_2b_34",
        "no_execution_in_2b_35",
        "no_render_in_2b_34",
        "no_render_in_2b_35",
    ]

    missing_tokens = [
        token
        for token in required_tokens
        if token not in text
    ]

    assert missing_tokens == []


def test_block6_pipeline_applies_each_report_to_job_after_each_safe_step() -> None:
    text = _pipeline_text()

    expected_apply_functions = [
        "apply_review_timeline_plan_run_report_to_job",
        "apply_timeline_approval_gate_run_report_to_job",
        "apply_timeline_safety_validator_run_report_to_job",
        "apply_review_timeline_dashboard_package_run_report_to_job",
    ]

    missing_apply_functions = [
        function_name
        for function_name in expected_apply_functions
        if function_name not in text
    ]

    assert missing_apply_functions == []


def test_block6_pipeline_does_not_place_dashboard_before_safety_metadata() -> None:
    text = _pipeline_text()

    safety_validator_metadata = _index_or_fail(
        text,
        '"no_render_in_2b_34": True',
    )
    dashboard_metadata = _index_or_fail(
        text,
        '"no_render_in_2b_35": True',
    )

    assert safety_validator_metadata < dashboard_metadata