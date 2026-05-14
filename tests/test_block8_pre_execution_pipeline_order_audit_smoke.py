from __future__ import annotations

from pathlib import Path


PIPELINE = Path("core/gaming_pipeline.py")


def _text() -> str:
    return PIPELINE.read_text(encoding="utf-8")


def test_block8_pipeline_order_is_pre_execution_safe() -> None:
    text = _text()

    ordered_tokens = [
        "render_readiness_report = run_render_readiness_guard(job)",
        "render_plan_report = run_render_plan_for_job(job)",
        "render_blueprint_report = run_render_command_blueprint_for_job(job)",
        "render_asset_manifest_report = run_render_asset_manifest_for_job(job)",
        "run_render_execution_permission_gate_for_job(job)",
        "run_controlled_render_executor_for_job(job)",
    ]

    positions = [text.find(token) for token in ordered_tokens]
    assert all(position >= 0 for position in positions), dict(zip(ordered_tokens, positions))
    assert positions == sorted(positions), dict(zip(ordered_tokens, positions))


def test_block8_pipeline_prevents_later_blocks_from_running_before_previous_blocks() -> None:
    text = _text()

    readiness = text.find("render_readiness_report = run_render_readiness_guard(job)")
    plan = text.find("render_plan_report = run_render_plan_for_job(job)")
    blueprint = text.find("render_blueprint_report = run_render_command_blueprint_for_job(job)")
    asset = text.find("render_asset_manifest_report = run_render_asset_manifest_for_job(job)")
    permission = text.find("run_render_execution_permission_gate_for_job(job)")
    executor = text.find("run_controlled_render_executor_for_job(job)")

    assert readiness < plan
    assert plan < blueprint
    assert blueprint < asset
    assert asset < permission
    assert permission < executor


def test_block8_pipeline_contains_required_safety_metadata() -> None:
    text = _text()

    required_tokens = [
        "block8_render_export",
        "no_render_in_2b_45",
        "no_render_in_2b_46",
        "no_render_in_2b_47",
        "no_render_in_2b_48",
        "no_render_in_2b_49",
        "no_real_render_in_2b_50",
        "media_unchanged",
        "dry_run_only",
        "non_executable",
        "paths_are_hints_only",
        "final_human_approval_gate",
        "execution_steps_are_dry_run_only",
    ]

    missing = [token for token in required_tokens if token not in text]
    assert missing == []
